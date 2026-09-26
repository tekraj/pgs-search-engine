"""Repository layer: the only code that writes the database tables."""

from ._mapping import (
    crawl_stats_columns,
    document_row,
    signed_simhash,
    stored_file_row,
    unsigned_simhash,
)
from .bronze import BronzeRepository, SaveResult
from .reference import ReferenceRepository
from .silver import SilverRepository

__all__ = [
    "BronzeRepository",
    "ReferenceRepository",
    "SaveResult",
    "SilverRepository",
    "crawl_stats_columns",
    "document_row",
    "signed_simhash",
    "stored_file_row",
    "unsigned_simhash",
]
