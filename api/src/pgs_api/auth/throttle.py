"""Brake on failed logins, kept in PostgreSQL so every API process and restart shares it.

Two limits, both over a sliding window (`login_failures` rows):

- per (client address, account): `max_failures` wrong passwords from one address against
  one account lock out that address for that account only. Someone who knows an admin's
  name can no longer lock the admin out from everywhere.
- per account: `account_max_failures` (much higher) failures from anywhere refuse further
  logins to the account, which caps a spread-out attack. Real owners are rarely near it.

An account is identified by its id once it exists (so logging in with the username or the
email counts against the same limit) and by the typed login while it does not. The client
address comes from nginx's X-Real-IP.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Protocol


class FailureStore(Protocol):
    def count_login_failures(self, key: str, since: datetime) -> tuple[int, datetime | None]: ...

    def add_login_failures(self, keys: Sequence[str]) -> None: ...

    def clear_login_failures(self, keys: Sequence[str]) -> None: ...


def _utcnow() -> datetime:
    return datetime.now(UTC)


class LoginThrottle:
    def __init__(
        self,
        store: FailureStore,
        max_failures: int = 5,
        account_max_failures: int = 30,
        window_seconds: float = 900.0,
        *,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._store = store
        self._max = max_failures
        self._account_max = account_max_failures
        self._window = timedelta(seconds=window_seconds)
        self._clock = clock

    @staticmethod
    def _keys(identity: str, ip: str) -> tuple[str, str]:
        identity = identity.casefold()
        return f"ip:{ip}|{identity}"[:400], f"acct:{identity}"[:400]

    def retry_after(self, identity: str, ip: str) -> int:
        """Seconds until this address may try this account again; 0 when it may try now."""
        now = self._clock()
        since = now - self._window
        wait = 0
        for key, limit in zip(
            self._keys(identity, ip), (self._max, self._account_max), strict=True
        ):
            count, oldest = self._store.count_login_failures(key, since)
            if count >= limit and oldest is not None:
                wait = max(wait, int((oldest + self._window - now).total_seconds()) + 1)
        return max(wait, 1) if wait else 0

    def record_failure(self, identity: str, ip: str) -> None:
        self._store.add_login_failures(self._keys(identity, ip))

    def record_success(self, identity: str, ip: str) -> None:
        self._store.clear_login_failures(self._keys(identity, ip)[:1])
