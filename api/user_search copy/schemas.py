# user_search/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List

class UserSearchRequest(BaseModel):
    """Schema for incoming search requests."""
    query: str = Field(..., min_length=1, description="Search term (name, email, etc.)")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum results to return")
    offset: int = Field(default=0, ge=0, description="Pagination offset")

class UserSearchResult(BaseModel):
    """Schema for a single user result."""
    user_id: str
    full_name: str
    email: str
    department: Optional[str] = None
    # Add more fields as needed from your gRPC proto

    class Config:
        from_attributes = True

class UserSearchResponse(BaseModel):
    """Schema for the API response."""
    results: List[UserSearchResult]
    total: int
    query: str