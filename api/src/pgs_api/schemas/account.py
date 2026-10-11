"""`/api/v1/account/*`: public-site sign-up, sign-in, profile and search history."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _email(value: object) -> object:
    if isinstance(value, str):
        value = value.strip().lower()
        if not _EMAIL.match(value):
            raise ValueError("enter a valid email address")
    return value


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=255)
    # Argon2id hashing rejects passwords under 12 characters (pgs_db.security).
    password: str = Field(min_length=12, max_length=1024)
    display_name: str | None = Field(default=None, max_length=100)

    @field_validator("email", mode="before")
    @classmethod
    def _valid_email(cls, value: object) -> object:
        return _email(value)


class UserLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("email", mode="before")
    @classmethod
    def _normalize(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class Profile(BaseModel):
    email: str
    display_name: str | None
    save_history: bool = Field(description="Searches are recorded in the user's history")


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="Seconds until the token expires")
    user: Profile


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    save_history: bool


class DeleteAccountRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=1, max_length=1024)


class HistoryEntry(BaseModel):
    id: int
    query: str
    filters: dict[str, Any]
    result_count: int
    searched_at: datetime


class HistoryPage(BaseModel):
    items: list[HistoryEntry]
    next_before: int | None = Field(
        description="Pass as ?before= to get the next (older) page; null at the end"
    )


class Cleared(BaseModel):
    deleted: int
