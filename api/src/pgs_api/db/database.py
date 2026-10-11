"""PostgreSQL access for the API, through the shared pgs_db repositories.

`Database` is everything the routes read or write; `PgDatabase` implements it with one
pooled engine (pgs_db's `make_engine`: pre-ping, recycle, `DB_POOL_SIZE`,
`DB_APPLICATION_NAME`) connected as the API's own role, `pgs_api`. Every method opens a
short session of its own; nothing holds a transaction across a gRPC call or a password
hash. Tests replace the whole `Database` with a fake.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from pgs_db import (
    AccountsRepository,
    OpsRepository,
    ReferenceRepository,
    SearchLogRepository,
    StatsRepository,
    make_engine,
)
from pgs_db import health as db_health

# Seconds before a connection attempt gives up (psycopg's default is to wait forever).
CONNECT_TIMEOUT_SECONDS = 5
# Upper bounds for the API's own statements, below the pgs_api role's 10 s default.
HEALTH_STATEMENT_TIMEOUT = "3s"
SEARCH_LOG_STATEMENT_TIMEOUT = "2s"


@dataclass(frozen=True)
class AdminAccount:
    """An active admin_users row, detached from the session."""

    id: int
    username: str
    email: str | None
    role: str
    password_hash: str


@dataclass(frozen=True)
class UserAccount:
    """An active `users` row, detached from the session."""

    id: int
    email: str
    display_name: str | None
    password_hash: str
    save_history: bool


@dataclass(frozen=True)
class HistoryItem:
    id: int
    query_text: str
    filters: dict[str, Any]
    result_count: int
    searched_at: datetime


class EmailTaken(Exception):
    """An account with this email already exists."""


@dataclass(frozen=True)
class SearchLogEntry:
    """One answered search, for `search_queries` (and the user's history, if signed in)."""

    query_text: str
    result_count: int
    query_language: str | None
    filters: dict[str, Any]
    page_number: int
    latency_ms: int
    # Set when a signed-in user searched: the entry also goes into that user's history,
    # unless they turned history off or the token (`token_id`) has been signed out.
    user_id: int | None = None
    token_id: str | None = None


class Database(Protocol):
    def health(self) -> dict[str, Any]: ...

    def hierarchy(self) -> list[dict[str, Any]]: ...

    def geo_content(self, level: str, within: str | None) -> list[dict[str, Any]]: ...

    def find_admin(self, login: str) -> AdminAccount | None: ...

    def record_login(self, user_id: int, new_password_hash: str | None) -> None: ...

    def dashboard_summary(self) -> dict[str, Any]: ...

    def search_traffic(self, since: datetime, until: datetime) -> dict[str, Any]: ...

    def log_search(self, entry: SearchLogEntry) -> None: ...

    def is_token_revoked(self, token_id: str) -> bool: ...

    def revoke_token(self, token_id: str, expires_at: datetime) -> None: ...

    def count_login_failures(self, key: str, since: datetime) -> tuple[int, datetime | None]: ...

    def add_login_failures(self, keys: Sequence[str]) -> None: ...

    def clear_login_failures(self, keys: Sequence[str]) -> None: ...

    def find_user(self, email: str) -> UserAccount | None: ...

    def get_user(self, user_id: int) -> UserAccount | None: ...

    def create_user(
        self, email: str, password_hash: str, display_name: str | None
    ) -> UserAccount: ...

    def record_user_login(self, user_id: int, new_password_hash: str | None) -> None: ...

    def set_save_history(self, user_id: int, enabled: bool) -> None: ...

    def list_history(
        self, user_id: int, limit: int, before_id: int | None
    ) -> list[HistoryItem]: ...

    def delete_history_item(self, user_id: int, item_id: int) -> bool: ...

    def clear_history(self, user_id: int) -> int: ...

    def delete_user(self, user_id: int) -> None: ...

    def close(self) -> None: ...


def with_connect_timeout(database_url: str, seconds: int = CONNECT_TIMEOUT_SECONDS) -> str:
    """Add `connect_timeout` to a PostgreSQL URL that does not set one."""
    url = make_url(database_url)
    if url.drivername.startswith("postgresql") and "connect_timeout" not in url.query:
        url = url.update_query_dict({"connect_timeout": str(seconds)})
    return url.render_as_string(hide_password=False)


class PgDatabase:
    """`Database` on PostgreSQL via pgs_db."""

    def __init__(self, database_url: str) -> None:
        self._engine = make_engine(with_connect_timeout(database_url))
        self._sessions = sessionmaker(bind=self._engine, autoflush=False, expire_on_commit=False)

    def health(self) -> dict[str, Any]:
        with self._sessions() as session:
            session.execute(text(f"SET LOCAL statement_timeout = '{HEALTH_STATEMENT_TIMEOUT}'"))
            return db_health.check(session)

    def hierarchy(self) -> list[dict[str, Any]]:
        with self._sessions() as session:
            return ReferenceRepository(session).hierarchy()

    def geo_content(self, level: str, within: str | None) -> list[dict[str, Any]]:
        with self._sessions() as session:
            return StatsRepository(session).geo_content(level, within=within)

    def find_admin(self, login: str) -> AdminAccount | None:
        with self._sessions() as session:
            user = OpsRepository(session).get_admin(login)
            if user is None:
                return None
            return AdminAccount(
                id=user.id,
                username=user.username,
                email=user.email,
                role=user.role.value,
                password_hash=user.password_hash,
            )

    def record_login(self, user_id: int, new_password_hash: str | None) -> None:
        with self._sessions.begin() as session:
            ops = OpsRepository(session)
            ops.record_login(user_id)
            if new_password_hash is not None:
                ops.set_password_hash(user_id, new_password_hash)

    def dashboard_summary(self) -> dict[str, Any]:
        with self._sessions() as session:
            return StatsRepository(session).dashboard_summary()

    def search_traffic(self, since: datetime, until: datetime) -> dict[str, Any]:
        with self._sessions() as session:
            return SearchLogRepository(session).traffic(since, until)

    def log_search(self, entry: SearchLogEntry) -> None:
        with self._sessions.begin() as session:
            session.execute(text(f"SET LOCAL statement_timeout = '{SEARCH_LOG_STATEMENT_TIMEOUT}'"))
            SearchLogRepository(session).log_query(
                entry.query_text,
                result_count=entry.result_count,
                query_language=entry.query_language,
                filters=entry.filters or None,
                page_number=entry.page_number,
                latency_ms=entry.latency_ms,
            )
            if entry.user_id is not None:
                AccountsRepository(session).record_search(
                    entry.user_id,
                    query_text=entry.query_text,
                    result_count=entry.result_count,
                    filters=entry.filters or None,
                    token_id=entry.token_id,
                )

    def is_token_revoked(self, token_id: str) -> bool:
        with self._sessions() as session:
            return AccountsRepository(session).is_token_revoked(token_id)

    def revoke_token(self, token_id: str, expires_at: datetime) -> None:
        with self._sessions.begin() as session:
            AccountsRepository(session).revoke_token(token_id, expires_at)

    def count_login_failures(self, key: str, since: datetime) -> tuple[int, datetime | None]:
        with self._sessions() as session:
            return AccountsRepository(session).count_login_failures(key, since)

    def add_login_failures(self, keys: Sequence[str]) -> None:
        with self._sessions.begin() as session:
            AccountsRepository(session).add_login_failure(*keys)

    def clear_login_failures(self, keys: Sequence[str]) -> None:
        with self._sessions.begin() as session:
            AccountsRepository(session).clear_login_failures(*keys)

    @staticmethod
    def _account(user: Any) -> UserAccount:
        return UserAccount(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            password_hash=user.password_hash,
            save_history=user.save_history,
        )

    def find_user(self, email: str) -> UserAccount | None:
        with self._sessions() as session:
            user = AccountsRepository(session).get_user_by_email(email)
            return None if user is None else self._account(user)

    def get_user(self, user_id: int) -> UserAccount | None:
        with self._sessions() as session:
            user = AccountsRepository(session).get_user(user_id)
            return None if user is None else self._account(user)

    def create_user(self, email: str, password_hash: str, display_name: str | None) -> UserAccount:
        try:
            with self._sessions.begin() as session:
                user = AccountsRepository(session).create_user(
                    email, password_hash=password_hash, display_name=display_name
                )
                return self._account(user)
        except IntegrityError:
            raise EmailTaken(email) from None

    def record_user_login(self, user_id: int, new_password_hash: str | None) -> None:
        with self._sessions.begin() as session:
            accounts = AccountsRepository(session)
            accounts.record_login(user_id)
            if new_password_hash is not None:
                accounts.set_password_hash(user_id, new_password_hash)

    def set_save_history(self, user_id: int, enabled: bool) -> None:
        with self._sessions.begin() as session:
            AccountsRepository(session).set_save_history(user_id, enabled)

    def list_history(self, user_id: int, limit: int, before_id: int | None) -> list[HistoryItem]:
        with self._sessions() as session:
            rows = AccountsRepository(session).list_history(
                user_id, limit=limit, before_id=before_id
            )
            return [
                HistoryItem(r.id, r.query_text, r.filters or {}, r.result_count, r.searched_at)
                for r in rows
            ]

    def delete_history_item(self, user_id: int, item_id: int) -> bool:
        with self._sessions.begin() as session:
            return AccountsRepository(session).delete_history_item(user_id, item_id)

    def clear_history(self, user_id: int) -> int:
        with self._sessions.begin() as session:
            return AccountsRepository(session).clear_history(user_id)

    def delete_user(self, user_id: int) -> None:
        with self._sessions.begin() as session:
            AccountsRepository(session).delete_user(user_id)

    def close(self) -> None:
        self._engine.dispose()
