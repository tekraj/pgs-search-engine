from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class DomainInfo(BaseModel):
    domain: str
    category: str
    status: str
    discovered_child_links: int
    scraped_pages: int
    failed_pages: int
    last_crawled_at: Optional[datetime] = None
    rate_limit_per_sec: int


class DomainListResponse(BaseModel):
    total_count: int
    domains: list[DomainInfo]


class AddDomainsRequest(BaseModel):
    domains: list[str] = Field(..., min_length=1)
    category: str
    priority: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"


class AddDomainsResponse(BaseModel):
    success: bool
    added_count: int
    message: str


class DomainActionRequest(BaseModel):
    action: Literal["PAUSE", "RESUME", "RE_CRAWL", "DELETE"]


class DomainActionResponse(BaseModel):
    success: bool
    message: str