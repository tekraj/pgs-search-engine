from pydantic import BaseModel
from typing import Optional


class RegionalCard(BaseModel):
    region_name_en: str 
    region_name_ne: str
    official_website: str
    phone: str
    email: str
    address: str


class SearchResultItem(BaseModel):
    id: str
    result_type: str
    title: str
    url: str
    domain: str
    snippet: str
    download_url: Optional[str] = None
    file_size_bytes: Optional[int] = None
    relevance_score: Optional[float] = None


class SearchMetadata(BaseModel):
    query: str
    page: int
    total_hits: int
    execution_time_ms: int


class UserSearchResponse(BaseModel):
    status: str = "success"
    search_metadata: SearchMetadata
    regional_card: Optional[RegionalCard] = None
    results: list[SearchResultItem]