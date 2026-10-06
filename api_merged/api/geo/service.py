"""Builds the Province -> District -> Municipality tree and applies filters."""

from functools import lru_cache

from geo.data import (
    _DISTRICTS,
    _MUNICIPALITY_SEED,
    _PROVINCES,
    _load_extra_municipalities,
)
from geo.schemas import (
    DistrictNode,
    GeoHierarchyResponse,
    MunicipalityNode,
    ProvinceNode,
)


@lru_cache(maxsize=1)
def _build_hierarchy() -> tuple[ProvinceNode, ...]:
    """Build the full tree once and cache it (the data is static)."""
    districts_by_name: dict[str, DistrictNode] = {}
    provinces: list[ProvinceNode] = []
    district_no = 0

    for p_code, p_en, p_ne in _PROVINCES:
        district_nodes: list[DistrictNode] = []
        for d_en, d_ne in _DISTRICTS[p_code]:
            district_no += 1
            node = DistrictNode(district_code=f"D{district_no:02d}", name_en=d_en, name_ne=d_ne)
            district_nodes.append(node)
            districts_by_name[d_en] = node
        provinces.append(ProvinceNode(province_code=p_code, name_en=p_en, name_ne=p_ne, districts=district_nodes))

    for mun_id, en, ne, m_type, district_en, wards in _MUNICIPALITY_SEED + _load_extra_municipalities():
        district = districts_by_name.get(district_en)
        if district is None:
            continue  # skip rows that reference an unknown district
        district.municipalities.append(
            MunicipalityNode(municipality_id=mun_id, name_en=en, name_ne=ne, type=m_type, ward_count=wards)
        )

    return tuple(provinces)


def get_geo_hierarchy(
    province_code: str | None = None,
    district_code: str | None = None,
    include_municipalities: bool = True,
) -> GeoHierarchyResponse:
    """Return the hierarchy, optionally narrowed to one province and/or district."""
    provinces = list(_build_hierarchy())

    if province_code:
        provinces = [p for p in provinces if p.province_code == province_code]
        if not provinces:
            raise KeyError(f"Unknown province_code '{province_code}'")

    result: list[ProvinceNode] = []
    for p in provinces:
        districts = p.districts
        if district_code:
            districts = [d for d in districts if d.district_code == district_code]
        if not include_municipalities:
            districts = [d.model_copy(update={"municipalities": []}) for d in districts]
        result.append(p.model_copy(update={"districts": districts}))

    if district_code:
        result = [p for p in result if p.districts]
        if not result:
            raise KeyError(f"Unknown district_code '{district_code}'")

    return GeoHierarchyResponse(
        total_provinces=len(result),
        total_districts=sum(len(p.districts) for p in result),
        total_municipalities=sum(len(d.municipalities) for p in result for d in p.districts),
        provinces=result,
    )
