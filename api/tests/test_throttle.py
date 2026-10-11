from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from pgs_api.auth.throttle import LoginThrottle


class _Store:
    """In-memory FailureStore."""

    def __init__(self, clock: _Clock) -> None:
        self.rows: list[tuple[str, datetime]] = []
        self.clock = clock

    def count_login_failures(self, key: str, since: datetime) -> tuple[int, datetime | None]:
        times = [t for k, t in self.rows if k == key and t >= since]
        return len(times), min(times) if times else None

    def add_login_failures(self, keys: Sequence[str]) -> None:
        self.rows += [(k, self.clock.now) for k in keys]

    def clear_login_failures(self, keys: Sequence[str]) -> None:
        self.rows = [(k, t) for k, t in self.rows if k not in keys]


class _Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 11, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


def _throttle(max_failures: int = 3, account_max: int = 6) -> tuple[LoginThrottle, _Clock]:
    clock = _Clock()
    return LoginThrottle(_Store(clock), max_failures, account_max, 60, clock=clock), clock


def test_locks_one_address_after_max_failures_and_expires() -> None:
    throttle, clock = _throttle()
    for _ in range(3):
        assert throttle.retry_after("Admin", "1.1.1.1") == 0
        throttle.record_failure("Admin", "1.1.1.1")
    assert throttle.retry_after("admin", "1.1.1.1") > 0  # case-insensitive
    assert throttle.retry_after("admin", "2.2.2.2") == 0  # another address is not locked out
    assert throttle.retry_after("other", "1.1.1.1") == 0
    clock.now += timedelta(seconds=61)
    assert throttle.retry_after("admin", "1.1.1.1") == 0


def test_account_wide_limit_covers_spread_out_attacks() -> None:
    throttle, _ = _throttle()
    for n in range(6):
        throttle.record_failure("admin", f"9.9.9.{n}")
    assert throttle.retry_after("admin", "8.8.8.8") > 0


def test_success_clears_this_address_only() -> None:
    throttle, _ = _throttle(max_failures=2)
    throttle.record_failure("admin", "1.1.1.1")
    throttle.record_success("admin", "1.1.1.1")
    throttle.record_failure("admin", "1.1.1.1")
    assert throttle.retry_after("admin", "1.1.1.1") == 0
