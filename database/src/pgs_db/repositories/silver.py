"""The only place that writes the Silver tables.

Takes the Spark ETL's output payload (`ETL/spark/README.md` §5.2) and lands it in
`pages`, `page_geo_tags` and `page_contacts`. See `docs/bronze-silver-contract.md`.

Reprocessing is the normal case, not the exception: Spark re-runs, Airflow backfills
and nightly deep-dedup all re-emit pages that already exist. Every write here is
keyed so that re-running produces the same rows rather than duplicates.
"""

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ..enums import ContactType
from ..models import CrawledDocument, LocalBody, Page, PageContact, PageGeoTag
from ._mapping import blank_to_none, parse_timestamp
from .bronze import SaveResult

# §5.2 emits contact_info as parallel lists; Silver normalizes them into rows.
_CONTACT_SOURCES: tuple[tuple[str, ContactType], ...] = (
    ("emails", ContactType.EMAIL),
    ("phones", ContactType.PHONE),
    ("social_links", ContactType.SOCIAL),
)


def derive_document_id(content_hash: str) -> str:
    """Fallback stable id: same content always yields the same id.

    §5.2 shows `document_id` ("doc_8831a2b") as ETL-supplied. When Spark omits it,
    this keeps the column populated and stable across reprocessing. If Spark starts
    sending its own, that value wins.
    """
    return f"doc_{content_hash[:12]}"


class SilverRepository:
    """Silver-layer writes for one SQLAlchemy session.

    The caller owns the transaction; nothing here commits, so one page plus its geo
    tags and contacts land as a single unit of work or not at all.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    # -------------------------------------------------------------- resolution

    def local_body_id_for_code(self, code: str | None) -> int | None:
        """Resolve §5.2's `municipality_id` (e.g. MUN414) to `local_bodies.id`."""
        if not code:
            return None
        return self.session.scalar(select(LocalBody.id).where(LocalBody.code == code))

    # ------------------------------------------------------------------- pages

    def save_page(
        self,
        payload: Mapping[str, Any],
        *,
        crawled_document_id: int,
        domain_id: int | None = None,
        content_hash: str | None = None,
        sim_hash: int | None = None,
        replace_children: bool = True,
    ) -> SaveResult:
        """Upsert one Silver page from an ETL payload, with its geo tags and contacts.

        Keyed on `crawled_document_id`: reprocessing the same Bronze row updates its
        page in place. `SaveResult.duplicate` is True when the page already existed.

        `replace_children` re-derives geo tags and contacts from this payload,
        removing any that are no longer present -- so a reprocess that corrects a
        wrong geo tag actually corrects it instead of leaving both.
        """
        row = self._page_row(
            payload,
            crawled_document_id=crawled_document_id,
            domain_id=domain_id,
            content_hash=content_hash,
            sim_hash=sim_hash,
        )
        stmt = insert(Page).values(row)
        updates = {
            col: getattr(stmt.excluded, col)
            for col in row
            if col not in ("crawled_document_id", "document_id")
        }
        result = self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[Page.crawled_document_id], set_=updates
            ).returning(Page.id, text("(xmax = 0)"))
        ).one()
        saved = SaveResult(id=int(result[0]), inserted=bool(result[1]))

        if replace_children:
            self.replace_geo_tags(saved.id, payload.get("geo_location"))
            self.replace_contacts(saved.id, payload)
        return saved

    def _page_row(
        self,
        payload: Mapping[str, Any],
        *,
        crawled_document_id: int,
        domain_id: int | None,
        content_hash: str | None,
        sim_hash: int | None,
    ) -> dict[str, Any]:
        meta = payload.get("extracted_metadata") or {}

        source_url = blank_to_none(payload.get("source_url"))
        if not source_url:
            raise ValueError("ETL payload is missing required field 'source_url'")

        resolved_hash = blank_to_none(content_hash) or blank_to_none(payload.get("content_hash"))
        if not resolved_hash:
            raise ValueError("a Silver page needs a content_hash for deduplication")

        document_id = blank_to_none(payload.get("document_id")) or derive_document_id(
            str(resolved_hash)
        )

        published_raw = payload.get("published_at")
        published_at = (
            parse_timestamp(published_raw, "published_at")
            if blank_to_none(published_raw) is not None
            else None
        )

        return {
            "crawled_document_id": crawled_document_id,
            "domain_id": domain_id,
            "document_id": str(document_id),
            "source_url": str(source_url),
            "title": blank_to_none(meta.get("title")),
            "description": blank_to_none(meta.get("description")),
            "keywords": meta.get("keywords") or None,
            # §5.2 calls it language_detected; SearchDocument calls it language.
            "language": blank_to_none(payload.get("language_detected"))
            or blank_to_none(payload.get("language"))
            or "unknown",
            "content_type": blank_to_none(payload.get("content_type")) or "web_page",
            "published_at": published_at,
            "content_hash": str(resolved_hash),
            "sim_hash": sim_hash if sim_hash is not None else payload.get("sim_hash"),
            "processing_error": blank_to_none(payload.get("processing_error")),
        }

    def mark_duplicate_of(self, page_id: int, canonical_page_id: int) -> None:
        """Fold a page into a canonical record (ETL stage 3 fuzzy/exact dedup)."""
        if page_id == canonical_page_id:
            raise ValueError("a page cannot be a duplicate of itself")
        page = self.session.get(Page, page_id)
        if page is None:
            raise LookupError(f"page {page_id} does not exist")
        page.duplicate_of_id = canonical_page_id

    # --------------------------------------------------------------- geo tags

    def replace_geo_tags(
        self, page_id: int, geo: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None
    ) -> list[int]:
        """Re-derive a page's geo tags from the payload's `geo_location` block.

        Accepts one block (§5.2) or a list, since a news article can legitimately be
        about several places. Codes are stored; names come from the gazetteer.
        """
        blocks: Sequence[Mapping[str, Any]]
        if geo is None:
            blocks = []
        elif isinstance(geo, Mapping):
            blocks = [geo]
        else:
            blocks = list(geo)

        rows: list[dict[str, Any]] = []
        for block in blocks:
            row = self._geo_row(page_id, block)
            if row is not None:
                rows.append(row)

        self.session.execute(delete(PageGeoTag).where(PageGeoTag.page_id == page_id))
        if not rows:
            return []
        stmt = insert(PageGeoTag).values(rows)
        saved = self.session.execute(
            stmt.on_conflict_do_nothing(
                constraint="uq_page_geo_tags_page_location"
            ).returning(PageGeoTag.id)
        ).scalars()
        return list(saved)

    def _geo_row(self, page_id: int, block: Mapping[str, Any]) -> dict[str, Any] | None:
        local_body_id = block.get("local_body_id")
        if local_body_id is None:
            local_body_id = self.local_body_id_for_code(
                blank_to_none(block.get("municipality_id"))
            )

        province_code = blank_to_none(block.get("province_code"))
        district_code = blank_to_none(block.get("district_code"))
        if province_code is None and district_code is None and local_body_id is None:
            # Nothing resolved -- the CHECK would reject it, so skip rather than fail:
            # an untagged page is normal, not an error.
            return None

        ward = block.get("ward_number")
        return {
            "page_id": page_id,
            "province_code": province_code,
            "district_code": district_code,
            "local_body_id": local_body_id,
            "ward_number": int(ward) if ward is not None else None,
        }

    # --------------------------------------------------------------- contacts

    def replace_contacts(self, page_id: int, payload: Mapping[str, Any]) -> list[int]:
        """Re-derive a page's contacts from `extracted_metadata.contact_info`.

        Also accepts `social_links` beside `contact_info`, matching how Bronze keeps
        the three lists (`emails`, `phones`, `social_links`) on `crawled_documents`.
        """
        meta = payload.get("extracted_metadata") or {}
        contact_info = meta.get("contact_info") or {}

        rows: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for key, contact_type in _CONTACT_SOURCES:
            values = contact_info.get(key)
            if values is None:
                values = meta.get(key)
            for raw in values or []:
                value = blank_to_none(raw)
                if value is None:
                    continue
                dedupe_key = (contact_type.value, str(value))
                if dedupe_key in seen:  # the same address listed twice on one page
                    continue
                seen.add(dedupe_key)
                rows.append({"page_id": page_id, "type": contact_type, "value": str(value)})

        self.session.execute(delete(PageContact).where(PageContact.page_id == page_id))
        if not rows:
            return []
        stmt = insert(PageContact).values(rows)
        saved = self.session.execute(
            stmt.on_conflict_do_nothing(
                constraint="uq_page_contacts_page_type_value"
            ).returning(PageContact.id)
        ).scalars()
        return list(saved)

    # --------------------------------------------------------------- backlog

    def unprocessed_bronze_documents(self, limit: int = 100) -> list[CrawledDocument]:
        """Bronze rows with no Silver page yet -- the ETL's work queue."""
        return list(
            self.session.scalars(
                select(CrawledDocument)
                .outerjoin(Page, Page.crawled_document_id == CrawledDocument.id)
                .where(Page.id.is_(None))
                .order_by(CrawledDocument.fetched_at)
                .limit(limit)
            )
        )

    def page_for_bronze_document(self, crawled_document_id: int) -> Page | None:
        return self.session.scalar(
            select(Page).where(Page.crawled_document_id == crawled_document_id)
        )

    def mark_processed(
        self, page_id: int, *, when: datetime | None = None, error: str | None = None
    ) -> None:
        """Record the outcome of downstream processing (search indexing)."""
        from ..enums import ProcessingStatus

        page = self.session.get(Page, page_id)
        if page is None:
            raise LookupError(f"page {page_id} does not exist")
        page.processing_status = (
            ProcessingStatus.FAILED if error else ProcessingStatus.PROCESSED
        )
        page.processing_error = error
        page.updated_at = when or datetime.now(UTC)
