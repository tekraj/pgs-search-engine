from pydantic import BaseModel, Field


class DomainCreate(BaseModel):
    domain: str = Field(min_length=3)
    enabled: bool = True
    crawl_enabled: bool = True


class DomainResponse(BaseModel):
    id: int
    domain: str
    enabled: bool
    crawl_enabled: bool