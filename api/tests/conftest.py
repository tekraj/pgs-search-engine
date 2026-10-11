"""Fakes for the API's two outside dependencies (PostgreSQL and the search engine).

Run from the repository root: `.venv/bin/python -m pytest api/tests` (api/pyproject.toml
puts api/src and the search engine's generated stubs on the path).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import ExitStack
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, cast

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from pgs_api.app import create_app
from pgs_api.auth.throttle import LoginThrottle
from pgs_api.auth.tokens import TokenCodec
from pgs_api.core.services import PasswordWorkers, Services
from pgs_api.core.settings import Settings
from pgs_api.db.database import (
    AdminAccount,
    EmailTaken,
    HistoryItem,
    SearchLogEntry,
    UserAccount,
)
from pgs_api.grpc.client import SearchError, SearchHealth
from pgs_api.health.readiness import ReadinessProbe
from pgs_search.grpc.generated.search_pb2 import SearchRequest, SearchResponse

AUTH_SECRET = "test-secret-" + "x" * 40
PASSWORD = "correct horse battery staple"

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)


def dashboard_summary() -> dict[str, Any]:
    return {
        "timestamp": NOW,
        "domains": {
            "total_registered": 3,
            "pending": 1,
            "active_crawling": 1,
            "paused": 0,
            "completed": 1,
            "failed_or_blocked": 0,
        },
        "links": {"total_child_links_discovered": 42},
        "storage": {
            "total_raw_files": 10,
            "unprocessed_files": 2,
            "processing_files": 1,
            "processed_files": 6,
            "failed_files": 1,
            "quarantined_files": 0,
            "unprocessed_size_bytes": 0,
            "oldest_unprocessed_at": None,
            "total_storage_used_bytes": 1024,
        },
        "quarantine": {
            "count": 0,
            "size_bytes": 0,
            "size_mb": 0,
            "latest_threat_detected": None,
            "latest_scanned_at": None,
        },
        "errors_last_24h": {"WARN": 1, "ERROR": 0, "FATAL": 0},
    }


@dataclass
class FakeDatabase:
    admins: dict[str, AdminAccount] = field(default_factory=dict[str, AdminAccount])
    health_report: dict[str, Any] = field(default_factory=lambda: {"status": "ok", "problems": []})
    health_error: Exception | None = None
    log_error: Exception | None = None
    logged: list[SearchLogEntry] = field(default_factory=list[SearchLogEntry])
    logins: list[tuple[int, str | None]] = field(default_factory=list[tuple[int, str | None]])
    geo_calls: list[tuple[str, str | None]] = field(default_factory=list[tuple[str, str | None]])
    health_calls: int = 0
    users: dict[int, UserAccount] = field(default_factory=dict[int, UserAccount])
    history: list[tuple[int, HistoryItem]] = field(default_factory=list[tuple[int, HistoryItem]])
    revoked: set[str] = field(default_factory=set[str])
    failures: list[tuple[str, datetime]] = field(default_factory=list[tuple[str, datetime]])
    next_id: int = 100

    def health(self) -> dict[str, Any]:
        self.health_calls += 1
        if self.health_error is not None:
            raise self.health_error
        return self.health_report

    def hierarchy(self) -> list[dict[str, Any]]:
        return [
            {
                "code": "P4",
                "name_en": "Gandaki",
                "name_ne": "गण्डकी",
                "districts": [
                    {
                        "code": "D38",
                        "name_en": "Kaski",
                        "name_ne": "कास्की",
                        "local_bodies": [
                            {
                                "code": "MUN414",
                                "name_en": "Pokhara",
                                "name_ne": "पोखरा",
                                "type": "METROPOLITAN_CITY",
                            }
                        ],
                    }
                ],
            }
        ]

    def geo_content(self, level: str, within: str | None) -> list[dict[str, Any]]:
        self.geo_calls.append((level, within))
        return [
            {
                "level": level,
                "code": "P4",
                "page_count": 5,
                "document_count": 1,
                "domain_count": 2,
                "latest_published_at": None,
                "by_content_type": {"web_page": 5},
                "by_language": {"NE": 5},
                "by_category": {"UNCATEGORIZED": 5},
                "computed_at": NOW,
            }
        ]

    def find_admin(self, login: str) -> AdminAccount | None:
        value = login.strip().lower()
        for account in self.admins.values():
            if value in (account.username, account.email):
                return account
        return None

    def record_login(self, user_id: int, new_password_hash: str | None) -> None:
        self.logins.append((user_id, new_password_hash))

    def dashboard_summary(self) -> dict[str, Any]:
        return dashboard_summary()

    def search_traffic(self, since: datetime, until: datetime) -> dict[str, Any]:
        return {
            "searches": 2,
            "queries_per_second": 2 / (until - since).total_seconds(),
            "avg_latency_ms": 120.0,
            "p95_latency_ms": 180.0,
            "zero_result_rate": 0.5,
            "click_through_rate": 0.0,
        }

    def log_search(self, entry: SearchLogEntry) -> None:
        if self.log_error is not None:
            raise self.log_error
        self.logged.append(entry)

    def is_token_revoked(self, token_id: str) -> bool:
        return token_id in self.revoked

    def revoke_token(self, token_id: str, expires_at: datetime) -> None:
        self.revoked.add(token_id)

    def count_login_failures(self, key: str, since: datetime) -> tuple[int, datetime | None]:
        times = [t for k, t in self.failures if k == key and t >= since]
        return len(times), min(times) if times else None

    def add_login_failures(self, keys: Sequence[str]) -> None:
        self.failures += [(k, datetime.now(UTC)) for k in keys]

    def clear_login_failures(self, keys: Sequence[str]) -> None:
        self.failures = [(k, t) for k, t in self.failures if k not in keys]

    def find_user(self, email: str) -> UserAccount | None:
        return next((u for u in self.users.values() if u.email == email.strip().lower()), None)

    def get_user(self, user_id: int) -> UserAccount | None:
        return self.users.get(user_id)

    def create_user(self, email: str, password_hash: str, display_name: str | None) -> UserAccount:
        if self.find_user(email) is not None:
            raise EmailTaken(email)
        self.next_id += 1
        account = UserAccount(
            self.next_id, email.strip().lower(), display_name, password_hash, True
        )
        self.users[account.id] = account
        return account

    def record_user_login(self, user_id: int, new_password_hash: str | None) -> None:
        self.logins.append((user_id, new_password_hash))

    def set_save_history(self, user_id: int, enabled: bool) -> None:
        old = self.users[user_id]
        self.users[user_id] = UserAccount(
            old.id, old.email, old.display_name, old.password_hash, enabled
        )

    def list_history(self, user_id: int, limit: int, before_id: int | None) -> list[HistoryItem]:
        rows = [h for uid, h in self.history if uid == user_id]
        rows = [h for h in rows if before_id is None or h.id < before_id]
        return sorted(rows, key=lambda h: h.id, reverse=True)[:limit]

    def delete_history_item(self, user_id: int, item_id: int) -> bool:
        before = len(self.history)
        self.history = [(u, h) for u, h in self.history if not (u == user_id and h.id == item_id)]
        return len(self.history) < before

    def clear_history(self, user_id: int) -> int:
        before = len(self.history)
        self.history = [(u, h) for u, h in self.history if u != user_id]
        return before - len(self.history)

    def delete_user(self, user_id: int) -> None:
        self.users.pop(user_id, None)
        self.clear_history(user_id)

    def close(self) -> None:
        pass


@dataclass
class FakeSearch:
    response: SearchResponse = field(default_factory=SearchResponse)
    error: SearchError | None = None
    health_status: SearchHealth = field(default_factory=lambda: SearchHealth("ok", "SERVING"))
    requests: list[SearchRequest] = field(default_factory=list[SearchRequest])
    closed: bool = False

    def search(self, request: SearchRequest) -> SearchResponse:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.response

    def health(self) -> SearchHealth:
        return self.health_status

    def close(self) -> None:
        self.closed = True


@dataclass
class RecordingSearchLog:
    entries: list[SearchLogEntry] = field(default_factory=list[SearchLogEntry])

    def submit(self, entry: SearchLogEntry) -> bool:
        self.entries.append(entry)
        return True

    def close(self) -> None:
        pass


def make_settings(*, auth_secret: str | None = AUTH_SECRET) -> Settings:
    return Settings(
        database_url=SecretStr("postgresql+psycopg://pgs_api:pw@localhost:5432/pgs"),
        auth_secret=None if auth_secret is None else SecretStr(auth_secret),
    )


class ApiClient:
    """Starlette's TestClient with typed responses.

    Starlette declares its client against `httpx2` for type checkers; with plain httpx
    installed its methods are untyped, so calls go through `Any` and come back as
    `httpx.Response` (what they are at runtime).
    """

    def __init__(self, client: Any) -> None:
        self._client: Any = client

    def get(
        self,
        url: str,
        *,
        params: Mapping[str, str | int] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        return cast(httpx.Response, self._client.get(url, params=params, headers=headers))

    def post(
        self, url: str, *, json: object = None, headers: Mapping[str, str] | None = None
    ) -> httpx.Response:
        return cast(httpx.Response, self._client.post(url, json=json, headers=headers))

    def patch(
        self, url: str, *, json: object = None, headers: Mapping[str, str] | None = None
    ) -> httpx.Response:
        return cast(httpx.Response, self._client.patch(url, json=json, headers=headers))

    def delete(self, url: str, *, headers: Mapping[str, str] | None = None) -> httpx.Response:
        return cast(httpx.Response, self._client.delete(url, headers=headers))


def open_client(stack: ExitStack, app: FastAPI, **options: Any) -> ApiClient:
    """Start the app (its lifespan runs on enter, shutdown when `stack` closes)."""
    client: Any = TestClient(app, **options)
    return ApiClient(stack.enter_context(client))


@dataclass
class Harness:
    db: FakeDatabase
    search: FakeSearch
    search_log: RecordingSearchLog
    services: Services
    client: ApiClient


@pytest.fixture
def make_harness() -> Iterator[Callable[..., Harness]]:
    with ExitStack() as stack:

        def build(*, auth: bool = True, tokens: TokenCodec | None = None) -> Harness:
            settings = make_settings(auth_secret=AUTH_SECRET if auth else None)
            db = FakeDatabase()
            search = FakeSearch()
            search_log = RecordingSearchLog()
            codec = tokens or (
                TokenCodec(AUTH_SECRET, settings.token_ttl_seconds) if auth else None
            )
            services = Services(
                settings=settings,
                db=db,
                search=search,
                tokens=codec,
                search_log=search_log,
                readiness=ReadinessProbe(db, search, cache_seconds=0),
                throttle=LoginThrottle(db),
                passwords=PasswordWorkers(settings.password_workers),
            )
            app = create_app(settings, services_factory=lambda _settings: services)
            return Harness(db, search, search_log, services, open_client(stack, app))

        yield build


@pytest.fixture
def harness(make_harness: Callable[..., Harness]) -> Harness:
    return make_harness()
