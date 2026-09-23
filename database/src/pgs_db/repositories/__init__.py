"""Repository layer: the only code that writes the database tables."""

from ._mapping import (
    crawl_stats_columns,
    document_row,
    signed_simhash,
    stored_file_row,
    unsigned_simhash,
)
from .bronze import BronzeRepository, SaveResult
from .silver import SilverRepository, derive_document_id

__all__ = [
    "BronzeRepository",
    "SaveResult",
    "SilverRepository",
    "derive_document_id",
    "crawl_stats_columns",
    "document_row",
    "signed_simhash",
    "stored_file_row",
    "unsigned_simhash",
]
