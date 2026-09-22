"""Pydantic schemas for Nepal's geographic reference data."""

from pydantic import Field

from .base import ReadSchema, SchemaBase


class ProvinceBase(SchemaBase):
    """Fields shared by all province schemas."""

    code: str = Field(
        pattern=r"^P[1-7]$",
        description="Province code from P1 through P7",
    )
    name_en: str = Field(
        min_length=1,
        max_length=100,
        description="Province name in English",
    )
    name_ne: str = Field(
        min_length=1,
        max_length=100,
        description="Province name in Nepali",
    )


class ProvinceCreate(ProvinceBase):
    """Data required when creating a province."""


class ProvinceUpdate(SchemaBase):
    """Fields that may be changed for an existing province."""

    name_en: str | None = Field(default=None, min_length=1, max_length=100)
    name_ne: str | None = Field(default=None, min_length=1, max_length=100)


class ProvinceRead(ProvinceBase, ReadSchema):
    """Province data returned by the application."""