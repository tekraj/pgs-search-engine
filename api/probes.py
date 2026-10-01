import asyncio
import time
from datetime import UTC, datetime

import httpx

from api.monitoring.config import ServiceTarget
from api.monitoring.schemas import ServiceCheck, Status


def _now() -> datetime:
    return datetime.now(UTC)


def _result(
    target: ServiceTarget,
    status: Status,
    latency_ms: float | None,
    detail: str | None,
) -> ServiceCheck:
    return ServiceCheck(
        name=target.name,
        group=target.group,
        target=target.display_target,
        status=status,
        latency_ms=None if latency_ms is None else round(latency_ms, 1),
        detail=detail,
        checked_at=_now(),
    )


def _status_from_body(response: httpx.Response) -> tuple[Status, str | None]:
    """Understand Elasticsearch-style {"status": "green|yellow|red"} bodies."""
    try:
        body: object = response.json()
    except ValueError:
        return Status.HEALTHY, None
    if isinstance(body, dict):
        value = body.get("status")  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if value == "yellow":
            return Status.DEGRADED, "Reports yellow status"
        if value == "red":
            return Status.DOWN, "Reports red status"
    return Status.HEALTHY, None


async def probe_http(target: ServiceTarget, client: httpx.AsyncClient) -> ServiceCheck:
    assert target.url is not None
    started = time.perf_counter()
    try:
        response = await client.get(target.url, timeout=target.timeout_s)
    except httpx.TimeoutException:
        return _result(target, Status.DOWN, None, f"No response within {target.timeout_s:g}s")
    except httpx.HTTPError as exc:
        return _result(target, Status.DOWN, None, f"Request failed ({type(exc).__name__})")
    latency = (time.perf_counter() - started) * 1000

    if response.status_code >= 400:
        return _result(target, Status.DOWN, latency, f"HTTP {response.status_code}")

    status, detail = _status_from_body(response)
    if status is Status.HEALTHY and latency > target.degraded_ms:
        status, detail = Status.DEGRADED, f"Slow response ({latency:.0f} ms)"
    return _result(target, status, latency, detail)


async def probe_tcp(target: ServiceTarget) -> ServiceCheck:
    assert target.host is not None and target.port is not None
    started = time.perf_counter()
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(target.host, target.port), timeout=target.timeout_s
        )
    except TimeoutError:
        return _result(target, Status.DOWN, None, f"No response within {target.timeout_s:g}s")
    except OSError as exc:
        return _result(target, Status.DOWN, None, f"Connection failed ({type(exc).__name__})")
    latency = (time.perf_counter() - started) * 1000
    writer.close()
    await writer.wait_closed()

    if latency > target.degraded_ms:
        return _result(target, Status.DEGRADED, latency, f"Slow connect ({latency:.0f} ms)")
    return _result(target, Status.HEALTHY, latency, None)


class ServiceMonitor:
    """Runs all probes concurrently, caching results briefly so many admins can poll."""

    def __init__(self, targets: list[ServiceTarget], ttl_seconds: float = 5.0) -> None:
        self._targets = targets
        self._ttl = ttl_seconds
        self._lock = asyncio.Lock()
        self._cached: list[ServiceCheck] = []
        self._cached_at = 0.0

    async def check_all(self) -> list[ServiceCheck]:
        async with self._lock:
            if self._cached and time.monotonic() - self._cached_at < self._ttl:
                return self._cached
            async with httpx.AsyncClient(follow_redirects=True) as client:
                results = await asyncio.gather(
                    *(
                        probe_http(t, client) if t.kind == "http" else probe_tcp(t)
                        for t in self._targets
                    )
                )
            self._cached = list(results)
            self._cached_at = time.monotonic()
            return self._cached