"""Pydantic request/response schemas.

Phase 1 covers the Bronze tables plus the province reference schemas; Phase 2 adds
the Silver tables. District, local-body and Gold schemas are still to come.
"""

from .base import ReadSchema, SchemaBase
from .bronze import (
    CrawledDocumentBase,
    CrawledDocumentCreate,
    CrawledDocumentRead,
    CrawlRunBase,
    CrawlRunCreate,
    CrawlRunFinish,
    CrawlRunRead,
    CrawlRunStats,
    DomainBase,
    DomainCreate,
    DomainRead,
    DomainUpdate,
    StoredFileBase,
    StoredFileCreate,
    StoredFileRead,
)
from .geography import ProvinceBase, ProvinceCreate, ProvinceRead, ProvinceUpdate
from .silver import (
    GeoLocationOut,
    PageBase,
    PageContactBase,
    PageContactCreate,
    PageContactRead,
    PageCreate,
    PageGeoTagBase,
    PageGeoTagCreate,
    PageGeoTagRead,
    PageRead,
    PageWithRelations,
)

__all__ = [
    "ReadSchema",
    "SchemaBase",
    # bronze - domains
    "DomainBase",
    "DomainCreate",
    "DomainRead",
    "DomainUpdate",
    # bronze - crawl runs
    "CrawlRunBase",
    "CrawlRunCreate",
    "CrawlRunFinish",
    "CrawlRunRead",
    "CrawlRunStats",
    # bronze - documents
    "CrawledDocumentBase",
    "CrawledDocumentCreate",
    "CrawledDocumentRead",
    # bronze - stored files
    "StoredFileBase",
    "StoredFileCreate",
    "StoredFileRead",
    # silver
    "PageBase",
    "PageCreate",
    "PageRead",
    "PageWithRelations",
    "PageGeoTagBase",
    "PageGeoTagCreate",
    "PageGeoTagRead",
    "PageContactBase",
    "PageContactCreate",
    "PageContactRead",
    "GeoLocationOut",
    # geography
    "ProvinceBase",
    "ProvinceCreate",
    "ProvinceRead",
    "ProvinceUpdate",
]
