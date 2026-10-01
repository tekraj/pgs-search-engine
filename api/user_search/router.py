
from grpc_client import SearchGrpcClient
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import grpc

from user_search.schemas import (
    UserSearchResponse,
    SearchResultItem,
    SearchMetadata,
    RegionalCard,
)
from grpc_client import SearchGrpcClient

router = APIRouter()

grpc_client = SearchGrpcClient()


@router.get("/search", response_model=UserSearchResponse)
def search(
    q: str = Query("", description="Free-text search query"),
    province_code: str = Query("", description="P1 to P7"),
    district_code: str = Query("", description="D01 to D77"),
    municipality_id: str = Query("", description="e.g. MUN75340"),
    ward_number: int = Query(0, description="Ward number"),
    content_type: str = Query("all", description="all, web_page, document"),
    lang: str = Query("auto", description="auto, ne, en"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),

    """GET /api/v1/user/search"""
    try:
        response = grpc_client.search(
            query=q,
            province_code=province_code,
            district_code=district_code,
            municipality_id=municipality_id,
            ward_number=ward_number,
            content_type=content_type,
            language=lang,
            page=page,
            limit=limit,
        )
    except grpc.RpcError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Search service unavailable: {e.details()}",
        )

    results = [
        SearchResultItem(
            id=item.id,
            result_type=item.result_type,
            title=item.title,
            url=item.url,
            domain=item.domain,
            snippet=item.snippet,
            download_url=item.download_url or None,
            file_size_bytes=item.file_size_bytes or None,
            relevance_score=item.relevance_score or None,
        )
        for item in response.results
    ]

    regional_card = None
    if response.regional_card and response.regional_card.region_name_en:
        rc = response.regional_card
        regional_card = RegionalCard(
            region_name_en=rc.region_name_en,
            region_name_ne=rc.region_name_ne,
            official_website=rc.official_website,
            phone=rc.phone,
            email=rc.email,
            address=rc.address,
        )

    return UserSearchResponse(
        search_metadata=SearchMetadata(
            query=q,
            page=page,
            total_hits=response.total_hits,
            execution_time_ms=response.execution_time_ms,
        ),
        regional_card=regional_card,
        results=results,
    )