from enum import Enum

from pydantic import BaseModel, Field


class MunicipalityType(str, Enum):
    METROPOLITAN = "Metropolitan City"
    SUB_METROPOLITAN = "Sub-Metropolitan City"
    MUNICIPALITY = "Municipality"
    RURAL_MUNICIPALITY = "Rural Municipality"


class MunicipalityNode(BaseModel):
    municipality_id: str = Field(..., examples=["MUN75340"])
    name_en: str = Field(..., examples=["Pokhara"])
    name_ne: str = Field(..., examples=["पोखरा"])
    type: MunicipalityType
    ward_count: int | None = Field(None, ge=1, description="Number of wards (for ward_number filter)")


class DistrictNode(BaseModel):
    district_code: str = Field(..., examples=["D40"])
    name_en: str = Field(..., examples=["Kaski"])
    name_ne: str = Field(..., examples=["कास्की"])
    municipalities: list[MunicipalityNode] = Field(default_factory=list)


class ProvinceNode(BaseModel):
    province_code: str = Field(..., examples=["P4"])
    name_en: str = Field(..., examples=["Gandaki Province"])
    name_ne: str = Field(..., examples=["गण्डकी प्रदेश"])
    districts: list[DistrictNode] = Field(default_factory=list)


class GeoHierarchyResponse(BaseModel):
    status: str = "success"
    total_provinces: int
    total_districts: int
    total_municipalities: int
    provinces: list[ProvinceNode]

