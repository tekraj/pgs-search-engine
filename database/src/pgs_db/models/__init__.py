"""Import every model here so Alembic autogenerate sees all tables."""

from .crawl import CrawledDocument, CrawlRun, StoredFile
from .domain import Domain
from .geography import District, LocalBody, Province
from .silver import Page, PageContact, PageGeoTag

__all__ = [
    # bronze
    "CrawlRun",
    "CrawledDocument",
    "StoredFile",
    # reference
    "Domain",
    "Province",
    "District",
    "LocalBody",
    # silver
    "Page",
    "PageGeoTag",
    "PageContact",
]
