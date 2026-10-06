# user_search/router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from .schemas import UserSearchRequest, UserSearchResponse, UserSearchResult
from .grpc_client import get_grpc_client, UserSearchGrpcClient

router = APIRouter(prefix="/user", tags=["User Search"])

@router.get("/search", response_model=UserSearchResponse, summary="Search for users")
async def search_users(
    q: str = Query(..., min_length=1, description="Search query (name, email, etc.)"),
    limit: int = Query(10, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    client: UserSearchGrpcClient = Depends(get_grpc_client)
):
    """
    Search users via the backend gRPC service.
    """
    try:
        # Call the gRPC service
        raw_results, total = client.search_users(query=q, limit=limit, offset=offset)
        
        # Map to Pydantic models
        results = [UserSearchResult(**item) for item in raw_results]
        
        return UserSearchResponse(
            results=results,
            total=total,
            query=q
        )
    except Exception as e:
        # Log the error internally
        raise HTTPException(status_code=500, detail="Internal search service error.")