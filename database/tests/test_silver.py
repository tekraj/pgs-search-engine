"""Phase 2 tests: Bronze document -> Silver page -> geo tags + contacts.

Payloads are shaped exactly as `ETL/spark/README.md` §5.2 specifies, so if Spark
ever changes its output these tests are where it shows up first.
"""

from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from pgs_db import BronzeRepository, SilverRepository
from pgs_db.enums import ContactType, LocalBodyType, ProcessingStatus
from pgs_db.models import CrawledDocument, LocalBody, Page, PageContact, PageGeoTag
from pgs_db.repositories import derive_document_id
from pgs_db.schemas import GeoLocationOut, PageGeoTagCreate, PageRead

HOST = "pokharamun.gov.np"
SOURCE_URL = f"https://{HOST}/notice/detail/456"
CONTENT_HASH = "e" * 64
FETCHED = datetime(2026, 9, 23, 5, 5, tzinfo=UTC)


@pytest.fixture()
def bronze(session: Session) -> BronzeRepository:
    return BronzeRepository(session)


@pytest.fixture()
def silver(session: Session) -> SilverRepository:
    return SilverRepository(session)


@pytest.fixture()
def bronze_document(bronze: BronzeRepository) -> int:
    """A Bronze row for the page the ETL spec uses as its worked example."""
    return bronze.save_document(
        {
            "url": f"{SOURCE_URL}?utm_source=fb",
            "normalized_url": SOURCE_URL,
            "host": HOST,
            "title": "Local Governance Update Notice",
            "text": "Full extracted PDF text",
            "content_hash": CONTENT_HASH,
            "content_type": "application/pdf",
            "fetched_at": "2026-09-23T05:05:00Z",
            "status_code": 200,
            "depth": 3,
        },
        register_unknown_domains=True,
    ).id


def etl_payload(**overrides: Any) -> dict[str, Any]:
    """The Spark ETL output payload, verbatim from ETL/spark/README.md §5.2."""
    payload: dict[str, Any] = {
        "document_id": "doc_8831a2b",
        "source_url": SOURCE_URL,
        "language_detected": "mixed",
        "extracted_metadata": {
            "title": "Local Governance Update Notice",
            "description": "Official notice regarding municipal administration.",
            "keywords": ["nepal", "local government", "gandaki", "pokhara"],
            "contact_info": {
                "emails": ["info@pokharamun.gov.np"],
                "phones": ["+977-61-521105"],
            },
        },
        "geo_location": {
            "province_code": "P4",
            "district_code": "D38",
            "municipality_id": "MUN414",
            "ward_number": None,
        },
        "content_hash": CONTENT_HASH,
    }
    payload.update(overrides)
    return payload


class TestBronzeToSilverFlow:
    def test_full_flow_document_to_page_to_tags_and_contacts(
        self, silver: SilverRepository, bronze_document: int
    ) -> None:
        session = silver.session
        result = silver.save_page(etl_payload(), crawled_document_id=bronze_document)
        assert result.inserted
        session.flush()

        page = session.get(Page, result.id)
        assert page is not None
        assert page.crawled_document_id == bronze_document
        assert page.document_id == "doc_8831a2b"
        assert page.source_url == SOURCE_URL
        assert page.language == "mixed"  # §5.2 language_detected
        assert page.content_type == "web_page"
        assert page.keywords == ["nepal", "local government", "gandaki", "pokhara"]
        assert page.duplicate_of_id is None
        assert page.processing_status == ProcessingStatus.UNPROCESSED

        # geo tag resolved municipality_id -> local_bodies.id
        assert len(page.geo_tags) == 1
        tag = page.geo_tags[0]
        assert tag.province_code == "P4"
        assert tag.district_code == "D38"
        assert tag.local_body.code == "MUN414"
        assert tag.local_body.name_en == "Pokhara"

        # contacts normalized out of the parallel lists
        contacts = {(c.type, c.value) for c in page.contacts}
        assert contacts == {
            (ContactType.EMAIL, "info@pokharamun.gov.np"),
            (ContactType.PHONE, "+977-61-521105"),
        }

    def test_searchable_text_is_not_stored(
        self, silver: SilverRepository, bronze_document: int
    ) -> None:
        """Full text belongs in OpenSearch; passing it must not create a column."""
        result = silver.save_page(
            etl_payload(searchable_text="Full extracted PDF text goes here..."),
            crawled_document_id=bronze_document,
        )
        page = silver.session.get(Page, result.id)
        assert page is not None
        assert not hasattr(page, "searchable_text")

    def test_geo_names_come_from_the_gazetteer_not_the_page(
        self, silver: SilverRepository, bronze_document: int
    ) -> None:
        """§5.2's denormalized geo_location block is rebuilt by joining."""
        result = silver.save_page(etl_payload(), crawled_document_id=bronze_document)
        silver.session.flush()
        page = silver.session.get(Page, result.id)
        assert page is not None

        block = GeoLocationOut.from_tag(page.geo_tags[0])
        assert block.province_code == "P4"
        assert block.province_name_en == "Gandaki"
        assert block.district_name_en == "Kaski"
        assert block.district_name_ne == "कास्की"
        assert block.municipality_id == "MUN414"
        assert block.municipality_name_ne == "पोखरा"
        assert block.municipality_type == LocalBodyType.METROPOLITAN_CITY

    def test_page_validates_against_the_schema(
        self, silver: SilverRepository, bronze_document: int
    ) -> None:
        result = silver.save_page(etl_payload(), crawled_document_id=bronze_document)
        silver.session.flush()
        read = PageRead.model_validate(silver.session.get(Page, result.id))
        assert read.document_id == "doc_8831a2b"
        assert read.content_hash == CONTENT_HASH

    def test_timestamps_are_utc(self, silver: SilverRepository, bronze_document: int) -> None:
        result = silver.save_page(
            etl_payload(published_at="2026-09-20T10:30:00Z"),
            crawled_document_id=bronze_document,
        )
        silver.session.flush()
        page = silver.session.get(Page, result.id)
        assert page is not None
        assert page.published_at == datetime(2026, 9, 20, 10, 30, tzinfo=UTC)
        assert page.created_at.utcoffset() == UTC.utcoffset(None)


class TestStableIdsAndDeduplication:
    def test_document_id_is_derived_when_etl_omits_it(
        self, silver: SilverRepository, bronze_document: int
    ) -> None:
        payload = etl_payload()
        del payload["document_id"]
        result = silver.save_page(payload, crawled_document_id=bronze_document)
        page = silver.session.get(Page, result.id)
        assert page is not None
        assert page.document_id == derive_document_id(CONTENT_HASH)

    def test_derived_id_is_stable_for_the_same_content(self) -> None:
        assert derive_document_id(CONTENT_HASH) == derive_document_id(CONTENT_HASH)
        assert derive_document_id("a" * 64) != derive_document_id("b" * 64)

    def test_document_id_is_unique(
        self, silver: SilverRepository, bronze: BronzeRepository, bronze_document: int
    ) -> None:
        silver.save_page(etl_payload(), crawled_document_id=bronze_document)
        silver.session.flush()

        other_bronze = bronze.save_document(
            {
                "url": f"https://{HOST}/other",
                "normalized_url": f"https://{HOST}/other",
                "host": HOST,
                "content_hash": "f" * 64,
                "fetched_at": "2026-09-23T05:06:00Z",
                "depth": 1,
            }
        ).id
        with pytest.raises(IntegrityError):
            # same ETL document_id on a different Bronze row
            silver.save_page(
                etl_payload(content_hash="f" * 64), crawled_document_id=other_bronze
            )
            silver.session.flush()

    def test_mark_duplicate_of_links_to_canonical(
        self, silver: SilverRepository, bronze: BronzeRepository, bronze_document: int
    ) -> None:
        canonical = silver.save_page(etl_payload(), crawled_document_id=bronze_document)
        mirror_bronze = bronze.save_document(
            {
                "url": f"https://{HOST}/mirror",
                "normalized_url": f"https://{HOST}/mirror",
                "host": HOST,
                "content_hash": "f" * 64,
                "fetched_at": "2026-09-23T05:07:00Z",
                "depth": 1,
            }
        ).id
        mirror = silver.save_page(
            etl_payload(document_id="doc_mirror", content_hash="f" * 64),
            crawled_document_id=mirror_bronze,
        )
        silver.mark_duplicate_of(mirror.id, canonical.id)
        silver.session.flush()

        page = silver.session.get(Page, mirror.id)
        assert page is not None
        assert page.duplicate_of.id == canonical.id

    def test_page_cannot_be_its_own_duplicate(
        self, silver: SilverRepository, bronze_document: int
    ) -> None:
        result = silver.save_page(etl_payload(), crawled_document_id=bronze_document)
        with pytest.raises(ValueError, match="duplicate of itself"):
            silver.mark_duplicate_of(result.id, result.id)


class TestReprocessing:
    def test_reprocessing_updates_instead_of_duplicating(
        self, silver: SilverRepository, bronze_document: int
    ) -> None:
        first = silver.save_page(etl_payload(), crawled_document_id=bronze_document)
        second = silver.save_page(etl_payload(), crawled_document_id=bronze_document)
        silver.session.flush()

        assert first.inserted and second.duplicate and first.id == second.id
        assert silver.session.scalar(select(func.count()).select_from(Page)) == 1
        assert silver.session.scalar(select(func.count()).select_from(PageGeoTag)) == 1
        assert silver.session.scalar(select(func.count()).select_from(PageContact)) == 2

    def test_running_the_etl_five_times_is_stable(
        self, silver: SilverRepository, bronze_document: int
    ) -> None:
        for _ in range(5):
            silver.save_page(etl_payload(), crawled_document_id=bronze_document)
        silver.session.flush()
        assert silver.session.scalar(select(func.count()).select_from(Page)) == 1
        assert silver.session.scalar(select(func.count()).select_from(PageContact)) == 2

    def test_reprocessing_corrects_a_wrong_geo_tag(
        self, silver: SilverRepository, bronze_document: int
    ) -> None:
        silver.save_page(etl_payload(), crawled_document_id=bronze_document)
        silver.session.flush()

        corrected = etl_payload(
            geo_location={"province_code": "P3", "district_code": "D27", "ward_number": 5}
        )
        result = silver.save_page(corrected, crawled_document_id=bronze_document)
        silver.session.flush()

        page = silver.session.get(Page, result.id)
        assert page is not None
        assert len(page.geo_tags) == 1  # the wrong tag is gone, not kept alongside
        assert page.geo_tags[0].province_code == "P3"
        assert page.geo_tags[0].ward_number == 5

    def test_reprocessing_updates_changed_metadata(
        self, silver: SilverRepository, bronze_document: int
    ) -> None:
        silver.save_page(etl_payload(), crawled_document_id=bronze_document)
        updated = etl_payload()
        updated["extracted_metadata"]["title"] = "Corrected Title"
        result = silver.save_page(updated, crawled_document_id=bronze_document)
        silver.session.flush()
        page = silver.session.get(Page, result.id)
        assert page is not None
        silver.session.refresh(page)
        assert page.title == "Corrected Title"

    def test_multiple_locations_are_supported(
        self, silver: SilverRepository, bronze_document: int
    ) -> None:
        """A national news article can be about several districts."""
        result = silver.save_page(
            etl_payload(
                geo_location=[
                    {"district_code": "D38"},
                    {"district_code": "D39"},
                    {"province_code": "P4"},
                ]
            ),
            crawled_document_id=bronze_document,
        )
        silver.session.flush()
        page = silver.session.get(Page, result.id)
        assert page is not None
        assert len(page.geo_tags) == 3

    def test_duplicate_contacts_on_one_page_collapse(
        self, silver: SilverRepository, bronze_document: int
    ) -> None:
        payload = etl_payload()
        payload["extracted_metadata"]["contact_info"]["emails"] = [
            "info@pokharamun.gov.np",
            "info@pokharamun.gov.np",
        ]
        silver.save_page(payload, crawled_document_id=bronze_document)
        silver.session.flush()
        assert silver.session.scalar(select(func.count()).select_from(PageContact)) == 2


class TestGeographyAndValidation:
    def test_untagged_page_is_stored_without_geo(
        self, silver: SilverRepository, bronze_document: int
    ) -> None:
        """Most of the web is not about a place; that is not an error."""
        result = silver.save_page(
            etl_payload(geo_location=None), crawled_document_id=bronze_document
        )
        silver.session.flush()
        page = silver.session.get(Page, result.id)
        assert page is not None
        assert page.geo_tags == []

    def test_empty_geo_block_is_skipped_not_rejected(
        self, silver: SilverRepository, bronze_document: int
    ) -> None:
        result = silver.save_page(
            etl_payload(geo_location={"ward_number": None}),
            crawled_document_id=bronze_document,
        )
        silver.session.flush()
        page = silver.session.get(Page, result.id)
        assert page is not None
        assert page.geo_tags == []

    def test_unknown_municipality_code_resolves_to_null(
        self, silver: SilverRepository, bronze_document: int
    ) -> None:
        result = silver.save_page(
            etl_payload(
                geo_location={"district_code": "D38", "municipality_id": "MUN999999"}
            ),
            crawled_document_id=bronze_document,
        )
        silver.session.flush()
        page = silver.session.get(Page, result.id)
        assert page is not None
        assert page.geo_tags[0].local_body_id is None
        assert page.geo_tags[0].district_code == "D38"

    def test_geo_tag_needs_at_least_one_level(self, session: Session) -> None:
        with pytest.raises(ValueError, match="at least one"):
            PageGeoTagCreate(ward_number=3)

    def test_check_constraint_rejects_empty_geo_tag(
        self, silver: SilverRepository, bronze_document: int
    ) -> None:
        result = silver.save_page(etl_payload(), crawled_document_id=bronze_document)
        silver.session.flush()
        silver.session.add(PageGeoTag(page_id=result.id, ward_number=2))
        with pytest.raises(IntegrityError):
            silver.session.flush()

    def test_ward_number_must_be_positive(
        self, silver: SilverRepository, bronze_document: int
    ) -> None:
        result = silver.save_page(etl_payload(), crawled_document_id=bronze_document)
        silver.session.flush()
        silver.session.add(
            PageGeoTag(page_id=result.id, district_code="D38", ward_number=0)
        )
        with pytest.raises(IntegrityError):
            silver.session.flush()

    def test_missing_source_url_is_rejected_before_sql(
        self, silver: SilverRepository, bronze_document: int
    ) -> None:
        payload = etl_payload()
        del payload["source_url"]
        with pytest.raises(ValueError, match="source_url"):
            silver.save_page(payload, crawled_document_id=bronze_document)

    def test_missing_content_hash_is_rejected(
        self, silver: SilverRepository, bronze_document: int
    ) -> None:
        payload = etl_payload()
        del payload["content_hash"]
        with pytest.raises(ValueError, match="content_hash"):
            silver.save_page(payload, crawled_document_id=bronze_document)


class TestForeignKeys:
    def test_page_needs_a_real_bronze_document(self, silver: SilverRepository) -> None:
        with pytest.raises(IntegrityError):
            silver.save_page(etl_payload(), crawled_document_id=9_999_999)
            silver.session.flush()

    def test_geo_tag_needs_a_real_province(
        self, silver: SilverRepository, bronze_document: int
    ) -> None:
        result = silver.save_page(etl_payload(), crawled_document_id=bronze_document)
        silver.session.flush()
        silver.session.add(PageGeoTag(page_id=result.id, province_code="P9"))
        with pytest.raises(IntegrityError):
            silver.session.flush()

    def test_deleting_a_page_cascades_to_children(
        self, silver: SilverRepository, bronze_document: int
    ) -> None:
        result = silver.save_page(etl_payload(), crawled_document_id=bronze_document)
        silver.session.flush()
        page = silver.session.get(Page, result.id)
        assert page is not None
        silver.session.delete(page)
        silver.session.flush()

        assert silver.session.scalar(select(func.count()).select_from(PageGeoTag)) == 0
        assert silver.session.scalar(select(func.count()).select_from(PageContact)) == 0


class TestProcessingState:
    def test_mark_processed_and_failed(
        self, silver: SilverRepository, bronze_document: int
    ) -> None:
        result = silver.save_page(etl_payload(), crawled_document_id=bronze_document)
        silver.session.flush()

        silver.mark_processed(result.id)
        silver.session.flush()
        page = silver.session.get(Page, result.id)
        assert page is not None
        assert page.processing_status == ProcessingStatus.PROCESSED

        silver.mark_processed(result.id, error="opensearch timeout")
        silver.session.flush()
        silver.session.refresh(page)
        assert page.processing_status == ProcessingStatus.FAILED
        assert page.processing_error == "opensearch timeout"

    def test_mark_processed_on_missing_page_raises(self, silver: SilverRepository) -> None:
        with pytest.raises(LookupError):
            silver.mark_processed(9_999_999)

    def test_backlog_lists_bronze_rows_without_a_page(
        self, silver: SilverRepository, bronze_document: int
    ) -> None:
        backlog = silver.unprocessed_bronze_documents()
        assert bronze_document in {doc.id for doc in backlog}

        silver.save_page(etl_payload(), crawled_document_id=bronze_document)
        silver.session.flush()
        assert bronze_document not in {doc.id for doc in silver.unprocessed_bronze_documents()}

    def test_page_for_bronze_document_lookup(
        self, silver: SilverRepository, bronze_document: int
    ) -> None:
        assert silver.page_for_bronze_document(bronze_document) is None
        result = silver.save_page(etl_payload(), crawled_document_id=bronze_document)
        silver.session.flush()
        found = silver.page_for_bronze_document(bronze_document)
        assert found is not None and found.id == result.id


class TestRollback:
    def test_failed_child_write_rolls_back_the_page(self, session: Session) -> None:
        bronze_repo = BronzeRepository(session)
        silver_repo = SilverRepository(session)
        doc_id = bronze_repo.save_document(
            {
                "url": SOURCE_URL,
                "normalized_url": SOURCE_URL,
                "host": HOST,
                "content_hash": CONTENT_HASH,
                "fetched_at": "2026-09-23T05:05:00Z",
                "depth": 1,
            }
        ).id
        session.flush()

        savepoint = session.begin_nested()
        result = silver_repo.save_page(etl_payload(), crawled_document_id=doc_id)
        session.flush()
        savepoint.rollback()

        assert session.get(Page, result.id) is None
        assert session.scalar(select(func.count()).select_from(Page)) == 0
        assert session.scalar(select(func.count()).select_from(PageGeoTag)) == 0
        assert session.scalar(select(func.count()).select_from(PageContact)) == 0
        # Bronze is untouched by the Silver rollback.
        assert session.get(CrawledDocument, doc_id) is not None

    def test_session_recovers_after_an_integrity_error(self, session: Session) -> None:
        bronze_repo = BronzeRepository(session)
        silver_repo = SilverRepository(session)
        doc_id = bronze_repo.save_document(
            {
                "url": SOURCE_URL,
                "normalized_url": SOURCE_URL,
                "host": HOST,
                "content_hash": CONTENT_HASH,
                "fetched_at": "2026-09-23T05:05:00Z",
                "depth": 1,
            }
        ).id
        session.flush()

        savepoint = session.begin_nested()
        with pytest.raises(IntegrityError):
            silver_repo.save_page(etl_payload(), crawled_document_id=9_999_999)
            session.flush()
        savepoint.rollback()

        result = silver_repo.save_page(etl_payload(), crawled_document_id=doc_id)
        session.flush()
        assert result.inserted
        assert session.scalar(select(func.count()).select_from(Page)) == 1


class TestGazetteerIsSeeded:
    """Silver geo resolution depends on the Phase 1 gazetteer being loaded."""

    def test_pokhara_resolves(self, silver: SilverRepository, session: Session) -> None:
        if not session.scalar(select(func.count()).select_from(LocalBody)):
            pytest.skip("geography not seeded; run scripts/seed_geography.py")
        assert silver.local_body_id_for_code("MUN414") is not None
        assert silver.local_body_id_for_code("MUN999999") is None
        assert silver.local_body_id_for_code(None) is None
