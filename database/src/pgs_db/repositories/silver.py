"""The only place that writes the Silver tables.

Takes the Spark ETL's output payload (`ETL/spark/README.md` §5.2) and lands it in
`pages`, `page_geo_tags` and `page_contacts`. See `docs/bronze-silver-contract.md`.

Reprocessing is the normal case, not the exception: Spark re-runs, Airflow backfills
and nightly deep-dedup all re-emit pages that already exist. Every write here is
keyed so that re-running produces the same rows rather than duplicates.

It also owns the Bronze -> Silver work queue (`claim_bronze` and friends), since the
ETL is the only consumer of `crawled_documents.processing_status`.
"""

from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ..enums import ContactType, GeoTagMethod, Language, ProcessingStatus
from ..models import CrawledDocument, Page, PageContact, PageGeoTag
from ._mapping import blank_to_none, parse_timestamp
from .bronze import SaveResult

# §5.2 emits contact_info as parallel lists; Silver normalizes them into rows.
_CONTACT_SOURCES: tuple[tuple[str, ContactType], ...] = (
    ("emails", ContactType.EMAIL),
    ("phones", ContactType.PHONE),
    ("social_links", ContactType.SOCIAL),
)

# §5.2 language_detected is a lowercase code; anything unrecognized is OTHER.
_LANGUAGES: dict[str, Language] = {
    "ne": Language.NE,
    "en": Language.EN,
    "mixed": Language.MIXED,
}


def to_language(raw: Any) -> Language:
    """Map §5.2 `language_detected` ("ne", "en-US", "mixed", ...) to `Language`."""
    value = blank_to_none(raw)
    if not isinstance(value, str):
        return Language.OTHER
    # "en-US" / "ne_NP" -> the primary subtag.
    primary = value.strip().lower().replace("_", "-").split("-")[0]
    return _LANGUAGES.get(primary, Language.OTHER)


class SilverRepository:
    """Silver-layer writes for one SQLAlchemy session.

    The caller owns the transaction; nothing here commits, so one page plus its geo
    tags and contacts land as a single unit of work or not at all.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

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

        Keyed on `canonical_url`: every Bronze version of the same URL lands on one
        page, which is repointed at the newest Bronze row. `SaveResult.duplicate` is
        True when the page already existed.

        "Newest" is the highest `crawled_documents.id` -- a content change inserts a
        new Bronze row, so ids grow with content versions. If an older Bronze row is
        processed after a newer one (retries, backfills), the page is left untouched
        rather than rolled back to stale content.

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
        # Validate geo blocks before touching the database, so a bad payload fails
        # without a half-written page.
        geo_rows = self._geo_rows(payload.get("geo_location")) if replace_children else []

        stmt = insert(Page).values(row)
        updates = {col: getattr(stmt.excluded, col) for col in row if col != "canonical_url"}
        result = self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[Page.canonical_url],
                set_=updates,
                where=Page.crawled_document_id <= stmt.excluded.crawled_document_id,
            ).returning(Page.id, text("(xmax = 0)"))
        ).one_or_none()

        if result is None:
            # Conflict, but the WHERE refused it: this Bronze row is older than the
            # one the page already reflects. Nothing to write.
            page_id = self.session.scalar(
                select(Page.id).where(Page.canonical_url == row["canonical_url"])
            )
            assert page_id is not None
            return SaveResult(id=int(page_id), inserted=False)

        saved = SaveResult(id=int(result[0]), inserted=bool(result[1]))
        if replace_children:
            self._replace_geo_rows(saved.id, geo_rows)
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

        # §5.2 calls it source_url; the column is canonical_url.
        canonical_url = blank_to_none(payload.get("canonical_url")) or blank_to_none(
            payload.get("source_url")
        )
        if not canonical_url:
            raise ValueError("ETL payload is missing required field 'source_url'")

        # §5.2 calls it searchable_text.
        body_text = blank_to_none(payload.get("body_text")) or blank_to_none(
            payload.get("searchable_text")
        )
        if not body_text:
            raise ValueError("ETL payload is missing required field 'searchable_text'")
        body_text = str(body_text)

        resolved_hash = blank_to_none(content_hash) or blank_to_none(payload.get("content_hash"))
        if not resolved_hash:
            raise ValueError("a Silver page needs a content_hash for deduplication")

        word_count = payload.get("word_count")
        if word_count is None:
            word_count = len(body_text.split())

        published_raw = payload.get("published_at")
        published_at = (
            parse_timestamp(published_raw, "published_at")
            if blank_to_none(published_raw) is not None
            else None
        )

        return {
            "crawled_document_id": crawled_document_id,
            "domain_id": domain_id,
            "canonical_url": str(canonical_url),
            "title": blank_to_none(meta.get("title")),
            "description": blank_to_none(meta.get("description")),
            "body_text": body_text,
            "word_count": int(word_count),
            "keywords": meta.get("keywords") or None,
            # §5.2 calls it language_detected; SearchDocument calls it language.
            "language": to_language(
                payload.get("language_detected") or payload.get("language")
            ),
            "content_type": blank_to_none(payload.get("content_type")) or "web_page",
            "published_at": published_at,
            "content_hash": str(resolved_hash),
            "sim_hash": sim_hash if sim_hash is not None else payload.get("sim_hash"),
            # New or changed content has to be (re)indexed.
            "processing_status": ProcessingStatus.UNPROCESSED,
            "processing_error": None,
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
        return self._replace_geo_rows(page_id, self._geo_rows(geo))

    def _geo_rows(
        self, geo: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None
    ) -> list[dict[str, Any]]:
        blocks: Sequence[Mapping[str, Any]]
        if geo is None:
            blocks = []
        elif isinstance(geo, Mapping):
            blocks = [geo]
        else:
            blocks = list(geo)
        return [row for block in blocks if (row := self._geo_row(block)) is not None]

    def _replace_geo_rows(self, page_id: int, rows: list[dict[str, Any]]) -> list[int]:
        self.session.execute(delete(PageGeoTag).where(PageGeoTag.page_id == page_id))
        if not rows:
            return []
        stmt = insert(PageGeoTag).values([{"page_id": page_id, **row} for row in rows])
        saved = self.session.execute(
            stmt.on_conflict_do_nothing(
                constraint="uq_page_geo_tags_page_location"
            ).returning(PageGeoTag.id)
        ).scalars()
        return list(saved)

    def _geo_row(self, block: Mapping[str, Any]) -> dict[str, Any] | None:
        province_code = blank_to_none(block.get("province_code"))
        district_code = blank_to_none(block.get("district_code"))
        # §5.2 calls it municipality_id; it is local_bodies.code (e.g. MUN414).
        local_body_code = blank_to_none(block.get("local_body_code")) or blank_to_none(
            block.get("municipality_id")
        )
        if province_code is None and district_code is None and local_body_code is None:
            # Nothing resolved -- the CHECK would reject it, so skip rather than fail:
            # an untagged page is normal, not an error.
            return None

        # A resolved tag must say how it was resolved and how sure the ETL is.
        # No defaults: a silently-invented confidence would poison ranking.
        raw_method = blank_to_none(block.get("method"))
        if raw_method is None:
            raise ValueError("geo tag is missing required field 'method'")
        try:
            method = GeoTagMethod(str(raw_method).upper())
        except ValueError:
            raise ValueError(f"unknown geo tag method {raw_method!r}") from None

        raw_confidence = block.get("confidence")
        if raw_confidence is None:
            raise ValueError("geo tag is missing required field 'confidence'")
        confidence = float(raw_confidence)
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"geo tag confidence must be within 0..1, got {confidence}")

        ward = block.get("ward_number")
        return {
            "province_code": province_code,
            "district_code": district_code,
            "local_body_code": local_body_code,
            "ward_number": int(ward) if ward is not None else None,
            "method": method,
            "confidence": confidence,
            "mention_text": blank_to_none(block.get("mention_text")),
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

    # ------------------------------------------------------ bronze work queue

    def claim_bronze(self, limit: int = 100) -> list[CrawledDocument]:
        """Claim up to `limit` UNPROCESSED Bronze rows for this worker, oldest first.

        `FOR UPDATE SKIP LOCKED` lets several ETL workers claim concurrently without
        blocking on or double-claiming each other's rows. Claimed rows move to
        PROCESSING; commit promptly so other workers stop seeing them as locked
        candidates. `updated_at` doubles as the claim time for `release_stale`.
        """
        candidates = (
            select(CrawledDocument.id)
            .where(CrawledDocument.processing_status == ProcessingStatus.UNPROCESSED)
            .order_by(CrawledDocument.fetched_at, CrawledDocument.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        claimed = self.session.scalars(
            update(CrawledDocument)
            .where(CrawledDocument.id.in_(candidates.scalar_subquery()))
            .values(
                processing_status=ProcessingStatus.PROCESSING,
                processing_error=None,
                updated_at=func.now(),
            )
            .returning(CrawledDocument),
            execution_options={"synchronize_session": False},
        ).all()
        # UPDATE ... RETURNING does not preserve the subquery's order.
        return sorted(claimed, key=lambda doc: (doc.fetched_at, doc.id))

    def mark_bronze_processed(self, ids: Iterable[int]) -> int:
        """Mark Bronze rows done after their pages are saved. Returns rows updated."""
        id_list = list(ids)
        if not id_list:
            return 0
        result = self.session.execute(
            update(CrawledDocument)
            .where(CrawledDocument.id.in_(id_list))
            .values(processing_status=ProcessingStatus.PROCESSED, processing_error=None),
            execution_options={"synchronize_session": False},
        )
        return result.rowcount

    def mark_bronze_failed(self, crawled_document_id: int, error: str) -> None:
        """Park a Bronze row the ETL could not process, with the reason."""
        result = self.session.execute(
            update(CrawledDocument)
            .where(CrawledDocument.id == crawled_document_id)
            .values(processing_status=ProcessingStatus.FAILED, processing_error=error),
            execution_options={"synchronize_session": False},
        )
        if result.rowcount == 0:
            raise LookupError(f"crawled document {crawled_document_id} does not exist")

    def release_stale(self, older_than: timedelta) -> int:
        """Return PROCESSING claims older than `older_than` to the queue.

        Recovers rows whose worker died after committing its claim. Pick a window
        well above the slowest batch, or a live worker's rows get double-processed
        (harmless -- `save_page` is idempotent -- but wasted work).
        """
        result = self.session.execute(
            update(CrawledDocument)
            .where(
                CrawledDocument.processing_status == ProcessingStatus.PROCESSING,
                CrawledDocument.updated_at < func.now() - older_than,
            )
            .values(processing_status=ProcessingStatus.UNPROCESSED),
            execution_options={"synchronize_session": False},
        )
        return result.rowcount

    # ------------------------------------------------------ page -> indexer

    def page_for_bronze_document(self, crawled_document_id: int) -> Page | None:
        return self.session.scalar(
            select(Page).where(Page.crawled_document_id == crawled_document_id)
        )

    def mark_processed(
        self, page_id: int, *, when: datetime | None = None, error: str | None = None
    ) -> None:
        """Record the outcome of downstream processing (search indexing)."""
        page = self.session.get(Page, page_id)
        if page is None:
            raise LookupError(f"page {page_id} does not exist")
        page.processing_status = (
            ProcessingStatus.FAILED if error else ProcessingStatus.PROCESSED
        )
        page.processing_error = error
        page.updated_at = when or datetime.now(UTC)
