"""Pydantic request/response schemas.

Phase 1 covers the Bronze tables plus the province reference schemas; district,
local-body and Silver/Gold schemas are still to come.
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
    # geography
    "ProvinceBase",
    "ProvinceCreate",
    "ProvinceRead",
    "ProvinceUpdate",
]
