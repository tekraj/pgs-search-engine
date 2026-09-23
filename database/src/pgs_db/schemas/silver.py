"""Pydantic schemas for the Silver tables.

Phase 2 scope. Field constraints mirror the column definitions in
`pgs_db.models.silver`, which in turn trace to `ETL/spark/README.md` §5.2 and the
search team's `SearchDocument` / `GeoLocation`.

`GeoLocationOut` is the one schema that is *not* column-shaped: it rebuilds §5.2's
denormalized `geo_location` block by joining the gazetteer, so the ETL and search
teams get back exactly the payload they expect without storing names per page.
"""

from datetime import datetime

from pydantic import Field, model_validator

from ..enums import ContactType, LocalBodyType, ProcessingStatus
from .base import ReadSchema, SchemaBase
from .bronze import SHA256_PATTERN


class PageContactBase(SchemaBase):
    """One contact detail extracted from a page."""

    type: ContactType
    value: str = Field(min_length=1)


class PageContactCreate(PageContactBase):
    """Data required to attach a contact to a page."""


class PageContactRead(PageContactBase, ReadSchema):
    """Contact data returned by the application."""

    page_id: int


class PageGeoTagBase(SchemaBase):
    """One administrative location a page is about.

    Codes only. All three levels are optional because geo resolution is partial in
    practice, but at least one must be present -- the same rule the CHECK enforces.
    """

    province_code: str | None = Field(default=None, pattern=r"^P[1-7]$")
    district_code: str | None = Field(default=None, pattern=r"^D[0-7][0-9]$")
    local_body_id: int | None = None
    ward_number: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _at_least_one_level(self) -> "PageGeoTagBase":
        if self.province_code is None and self.district_code is None and self.local_body_id is None:
            raise ValueError(
                "a geo tag needs at least one of province_code, district_code, local_body_id"
            )
        return self


class PageGeoTagCreate(PageGeoTagBase):
    """Data required to tag a page with a location."""


class PageGeoTagRead(PageGeoTagBase, ReadSchema):
    """Geo-tag data returned by the application."""

    page_id: int


class GeoLocationOut(SchemaBase):
    """§5.2's `geo_location` block, rebuilt from the gazetteer.

    This is what the ETL and search teams consume. The names are never stored on
    the page; they come from `provinces`, `districts` and `local_bodies`.
    """

    province_code: str | None = None
    province_name_en: str | None = None
    province_name_ne: str | None = None

    district_code: str | None = None
    district_name_en: str | None = None
    district_name_ne: str | None = None

    municipality_id: str | None = None
    municipality_type: LocalBodyType | None = None
    municipality_name_en: str | None = None
    municipality_name_ne: str | None = None

    ward_number: int | None = None

    @classmethod
    def from_tag(cls, tag: object) -> "GeoLocationOut":
        """Build the block from a `PageGeoTag` with its relationships loaded."""
        province = getattr(tag, "province", None)
        district = getattr(tag, "district", None)
        local_body = getattr(tag, "local_body", None)
        # A tag resolved only to a local body still knows its district and province.
        if district is None and local_body is not None:
            district = getattr(local_body, "district", None)
        if province is None and district is not None:
            province = getattr(district, "province", None)
        return cls(
            province_code=getattr(province, "code", None),
            province_name_en=getattr(province, "name_en", None),
            province_name_ne=getattr(province, "name_ne", None),
            district_code=getattr(district, "code", None),
            district_name_en=getattr(district, "name_en", None),
            district_name_ne=getattr(district, "name_ne", None),
            municipality_id=getattr(local_body, "code", None),
            municipality_type=getattr(local_body, "type", None),
            municipality_name_en=getattr(local_body, "name_en", None),
            municipality_name_ne=getattr(local_body, "name_ne", None),
            ward_number=getattr(tag, "ward_number", None),
        )


class PageBase(SchemaBase):
    """Column-shaped view of one Silver page.

    `searchable_text` is absent by design: full text goes to OpenSearch, and Bronze
    keeps the extracted text as provenance.
    """

    document_id: str = Field(min_length=1, max_length=64, description="Stable across reprocessing")
    source_url: str = Field(min_length=1)
    content_hash: str = Field(pattern=SHA256_PATTERN)

    crawled_document_id: int
    domain_id: int | None = None

    title: str | None = None
    description: str | None = None
    keywords: list[str] | None = None
    language: str = Field(default="unknown", max_length=16)
    content_type: str = Field(default="web_page", max_length=32)
    published_at: datetime | None = None

    sim_hash: int | None = None
    duplicate_of_id: int | None = None


class PageCreate(PageBase):
    """Data required to store one Silver page."""


class PageRead(PageBase, ReadSchema):
    """Silver page data returned by the application."""

    processing_status: ProcessingStatus = ProcessingStatus.UNPROCESSED
    processing_error: str | None = None


class PageWithRelations(PageRead):
    """A page together with its geo tags and contacts."""

    geo_tags: list[PageGeoTagRead] = Field(default_factory=list)
    contacts: list[PageContactRead] = Field(default_factory=list)
