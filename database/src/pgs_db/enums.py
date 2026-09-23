"""Fixed status values. Stored as VARCHAR + CHECK (not native PG enums) so the
Go scraper and Spark can insert plain strings without casts."""

import enum


class CrawlRunStatus(enum.StrEnum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ProcessingStatus(enum.StrEnum):
    UNPROCESSED = "UNPROCESSED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class DomainStatus(enum.StrEnum):
    PENDING = "PENDING"
    CRAWLING = "CRAWLING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DomainPriority(enum.StrEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"


class DomainCategory(enum.StrEnum):
    GOVERNMENT = "GOVERNMENT"
    NEWS = "NEWS"
    EDUCATION = "EDUCATION"
    FINANCE = "FINANCE"
    NGO = "NGO"
    COMMERCIAL = "COMMERCIAL"
    OTHER = "OTHER"


class LocalBodyType(enum.StrEnum):
    METROPOLITAN_CITY = "METROPOLITAN_CITY"
    SUB_METROPOLITAN_CITY = "SUB_METROPOLITAN_CITY"
    MUNICIPALITY = "MUNICIPALITY"
    RURAL_MUNICIPALITY = "RURAL_MUNICIPALITY"


class ContactType(enum.StrEnum):
    """Kind of contact detail extracted from a page.

    Mirrors the three contact sources Bronze already carries on
    `crawled_documents`: `emails`, `phones` and `social_links`.
    """

    EMAIL = "EMAIL"
    PHONE = "PHONE"
    SOCIAL = "SOCIAL"


class Language(enum.StrEnum):
    """Dominant language of a page's body text."""

    NE = "NE"
    EN = "EN"
    MIXED = "MIXED"
    OTHER = "OTHER"


class GeoTagMethod(enum.StrEnum):
    """How a geo tag was resolved against the gazetteer."""

    GAZETTEER = "GAZETTEER"  # place name matched in body text
    NER = "NER"  # named-entity recognition
    DOMAIN = "DOMAIN"  # the site itself belongs to a local body
    GEO_META = "GEO_META"  # geo.* meta tags / structured data
