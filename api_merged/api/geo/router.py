from fastapi import APIRouter, HTTPException, Query

from geo.schemas import GeoHierarchyResponse
from geo.service import get_geo_hierarchy

# Mounted in main.py at {api_v1_prefix}/user/geo
router = APIRouter()


@router.get(
    "/hierarchy",
    response_model=GeoHierarchyResponse,
    summary="Administrative hierarchy for the interactive map",
)
def geo_hierarchy(
    province_code: str | None = Query(None, pattern=r"^P[1-7]$", description="Province code, P1-P7"),
    district_code: str | None = Query(None, pattern=r"^D(0[1-9]|[1-6][0-9]|7[0-7])$", description="District code, D01-D77"),
    include_municipalities: bool = Query(True, description="Set false for a lighter province/district-only tree"),
) -> GeoHierarchyResponse:
    """GET /api/v1/user/geo/hierarchy"""
    try:
        return get_geo_hierarchy(province_code, district_code, include_municipalities)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
