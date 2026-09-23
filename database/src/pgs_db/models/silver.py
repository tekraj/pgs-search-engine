"""Silver layer: one clean record per page, deduplicated and geo-tagged.

Written by the Spark ETL, read by the search indexer and the API. Every column
traces to the ETL team's own output contract (`ETL/spark/README.md` §5.2) or to
the search team's consuming model (`pgs_search.models.SearchDocument` /
`GeoLocation`). See `docs/bronze-silver-contract.md` for the field-by-field
provenance.

A page is keyed by its canonical URL, not by the Bronze row it came from: a
recrawl produces a new `crawled_documents` row, and Silver repoints the existing
page at it rather than creating a second page.

The denormalized geography names from §5.2 (`province_name_en`,
`municipality_type`, ...) are deliberately **not** stored here -- they are
derivable by joining `page_geo_tags` to the seeded gazetteer, and duplicating
837 rows of names onto every page would guarantee they drift.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base, IdMixin, TimestampMixin
from ..enums import ContactType, GeoTagMethod, Language, ProcessingStatus
from ._types import str_enum
from .crawl import CrawledDocument
from .domain import Domain
from .geography import District, LocalBody, Province

TextArray = ARRAY(Text)


class Page(IdMixin, TimestampMixin, Base):
    """One clean, deduplicated page. Silver output of `crawled_documents`."""

    __tablename__ = "pages"
    __table_args__ = (
        Index("ix_pages_processing_status", "processing_status"),
        Index("ix_pages_content_hash", "content_hash"),
        Index("ix_pages_published_at", "published_at"),
    )

    # --- Bronze linkage -----------------------------------------------------
    # The latest Bronze row this page was built from. Not unique: it moves
    # forward on every recrawl. RESTRICT so Bronze retention can't silently
    # delete a live page -- repoint or delete the page first.
    crawled_document_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("crawled_documents.id", ondelete="RESTRICT"), index=True
    )
    domain_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("domains.id"), index=True
    )

    # --- identity (§5.2 source_url) -----------------------------------------
    # UNIQUE: the idempotency key for the whole layer. Reprocessing any Bronze
    # row for the same canonical URL updates this page.
    canonical_url: Mapped[str] = mapped_column(Text, unique=True)

    # --- extracted content (§5.2 extracted_metadata, SearchDocument) --------
    title: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    body_text: Mapped[str] = mapped_column(Text)
    word_count: Mapped[int] = mapped_column(Integer)
    keywords: Mapped[list[str] | None] = mapped_column(TextArray)
    language: Mapped[Language] = mapped_column(str_enum(Language, "language"))
    content_type: Mapped[str] = mapped_column(String(32), default="web_page")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # --- deduplication (ETL §3: SHA256 exact + SimHash fuzzy) ---------------
    content_hash: Mapped[str] = mapped_column(String(64))
    sim_hash: Mapped[int | None] = mapped_column(BigInteger)
    # Set when this page was folded into a canonical record; NULL means canonical.
    duplicate_of_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("pages.id", ondelete="SET NULL"), index=True
    )

    # --- downstream processing state ----------------------------------------
    # UNPROCESSED until the search indexer has taken this page, mirroring the
    # same column on crawled_documents.
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        str_enum(ProcessingStatus, "processing_status"),
        default=ProcessingStatus.UNPROCESSED,
        server_default=ProcessingStatus.UNPROCESSED.value,
    )
    processing_error: Mapped[str | None] = mapped_column(Text)

    crawled_document: Mapped[CrawledDocument] = relationship()
    domain: Mapped[Domain | None] = relationship()
    duplicate_of: Mapped["Page | None"] = relationship(remote_side="Page.id")
    geo_tags: Mapped[list["PageGeoTag"]] = relationship(
        back_populates="page", cascade="all, delete-orphan"
    )
    contacts: Mapped[list["PageContact"]] = relationship(
        back_populates="page", cascade="all, delete-orphan"
    )


class PageGeoTag(IdMixin, TimestampMixin, Base):
    """Where a page is about, resolved against the seeded gazetteer.

    Codes are stored, never names: `province_name_en`, `municipality_type` and the
    rest of §5.2's `geo_location` block are produced by joining to `provinces`,
    `districts` and `local_bodies`.

    All three levels are nullable because resolution is partial in practice -- a
    municipality site resolves to a local body, while a national news article may
    only resolve to a district or province. The CHECK guarantees at least one.
    """

    __tablename__ = "page_geo_tags"
    __table_args__ = (
        CheckConstraint(
            "province_code IS NOT NULL OR district_code IS NOT NULL "
            "OR local_body_code IS NOT NULL",
            name="at_least_one_level",
        ),
        CheckConstraint("ward_number IS NULL OR ward_number > 0", name="ward_number_positive"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        # NULLS NOT DISTINCT (PostgreSQL 15+) so re-tagging a page with the same
        # partially-NULL location is idempotent rather than inserting a duplicate.
        UniqueConstraint(
            "page_id",
            "province_code",
            "district_code",
            "local_body_code",
            "ward_number",
            name="uq_page_geo_tags_page_location",
            postgresql_nulls_not_distinct=True,
        ),
        Index("ix_page_geo_tags_local_body_code", "local_body_code"),
        Index("ix_page_geo_tags_district_code", "district_code"),
        Index("ix_page_geo_tags_province_code", "province_code"),
    )

    page_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("pages.id", ondelete="CASCADE"), index=True
    )
    province_code: Mapped[str | None] = mapped_column(
        String(4), ForeignKey("provinces.code")
    )  # §5.2 geo_location.province_code
    district_code: Mapped[str | None] = mapped_column(
        String(4), ForeignKey("districts.code")
    )  # §5.2 geo_location.district_code
    local_body_code: Mapped[str | None] = mapped_column(
        String(16), ForeignKey("local_bodies.code")
    )  # §5.2 geo_location.municipality_id
    ward_number: Mapped[int | None] = mapped_column(Integer)  # §5.2 geo_location.ward_number

    # --- provenance of the tag ----------------------------------------------
    method: Mapped[GeoTagMethod] = mapped_column(str_enum(GeoTagMethod, "geo_tag_method"))
    confidence: Mapped[float] = mapped_column(Float)
    # The span that produced the tag, e.g. "पोखरा" or "Pokhara Metropolitan City".
    mention_text: Mapped[str | None] = mapped_column(Text)

    page: Mapped[Page] = relationship(back_populates="geo_tags")
    province: Mapped[Province | None] = relationship()
    district: Mapped[District | None] = relationship()
    local_body: Mapped[LocalBody | None] = relationship()


class PageContact(IdMixin, TimestampMixin, Base):
    """One contact detail found on a page (§5.2 extracted_metadata.contact_info).

    Bronze stores emails, phones and social links as three parallel arrays on
    `crawled_documents`; Silver normalizes them into rows so the API can query
    "every phone number for pages in Kaski" without unnesting arrays.
    """

    __tablename__ = "page_contacts"
    __table_args__ = (
        UniqueConstraint("page_id", "type", "value", name="uq_page_contacts_page_type_value"),
        Index("ix_page_contacts_type_value", "type", "value"),
    )

    page_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("pages.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[ContactType] = mapped_column(str_enum(ContactType, "contact_type"))
    value: Mapped[str] = mapped_column(Text)

    page: Mapped[Page] = relationship(back_populates="contacts")
