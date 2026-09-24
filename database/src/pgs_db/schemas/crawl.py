"""Pydantic schemas for Bronze-layer crawling records."""

from datetime import datetime

from pydantic import Field, model_validator

from pgs_db.enums import CrawlRunStatus

from .base import ReadSchema, SchemaBase


class CrawlRunBase(SchemaBase):
    """Fields shared by all crawl-run schemas."""

    category: str | None = Field(default=None, max_length=64)
    status: CrawlRunStatus = CrawlRunStatus.RUNNING
    temporal_workflow_id: str | None = Field(default=None, max_length=255)
    started_at: datetime
    finished_at: datetime | None = None
    fetched_count: int = Field(default=0, ge=0)
    succeeded_count: int = Field(default=0, ge=0)
    failed_count: int = Field(default=0, ge=0)
    skipped_count: int = Field(default=0, ge=0)
    unique_url_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_dates(self) -> "CrawlRunBase":
        """Ensure that a crawl cannot finish before it starts."""

        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("finished_at cannot be earlier than started_at")

        return self


class CrawlRunCreate(CrawlRunBase):
    """Data required when creating a crawl run."""


class CrawlRunUpdate(SchemaBase):
    """Fields that may be updated while a crawl is running."""

    status: CrawlRunStatus | None = None
    finished_at: datetime | None = None
    fetched_count: int | None = Field(default=None, ge=0)
    succeeded_count: int | None = Field(default=None, ge=0)
    failed_count: int | None = Field(default=None, ge=0)
    skipped_count: int | None = Field(default=None, ge=0)
    unique_url_count: int | None = Field(default=None, ge=0)


class CrawlRunRead(CrawlRunBase, ReadSchema):
    """Crawl-run data returned by the application."""