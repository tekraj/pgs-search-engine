# pyright: basic
import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.monitoring import router as router_module
from api.monitoring.config import ServiceTarget
from api.monitoring.nodes import NodeRegistry
from api.monitoring.probes import ServiceMonitor, probe_tcp
from api.monitoring.schemas import NodeHeartbeat, Status, worst

ADMIN = {"X-Admin-Token": "admin-secret"}
AGENT = {"X-Agent-Token": "agent-secret"}


def beat(node_id: str = "n1", cpu: float = 10, mem: float = 20, disk: float = 30) -> NodeHeartbeat:
    return NodeHeartbeat(
        node_id=node_id,
        hostname=node_id,
        role="worker",
        cpu_percent=cpu,
        memory_percent=mem,
        disk_percent=disk,
        load_1m=0.5,
        cpu_count=4,
        uptime_seconds=1000,
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("PGS_ADMIN_TOKEN", "admin-secret")
    monkeypatch.setenv("PGS_AGENT_TOKEN", "agent-secret")
    dead = ServiceTarget(name="Dead", group="Store", kind="tcp", host="127.0.0.1", port=1)
    router_module.get_service_monitor.cache_clear()
    router_module.get_node_registry.cache_clear()
    app.dependency_overrides[router_module.get_service_monitor] = lambda: ServiceMonitor([dead])
    monitor = ServiceMonitor([dead])
    monkeypatch.setattr(router_module, "get_service_monitor", lambda: monitor)
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_admin_endpoints_reject_missing_and_wrong_token(client: TestClient) -> None:
    assert client.get("/api/v1/admin/monitoring/overview").status_code == 401
    bad = {"X-Admin-Token": "nope"}
    assert client.get("/api/v1/admin/monitoring/overview", headers=bad).status_code == 401


def test_fails_closed_when_token_unset(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PGS_ADMIN_TOKEN")
    assert client.get("/api/v1/admin/monitoring/nodes", headers=ADMIN).status_code == 503


def test_agent_token_cannot_read_and_admin_token_cannot_post(client: TestClient) -> None:
    body = beat().model_dump()
    url = "/api/v1/admin/monitoring/nodes/heartbeat"
    assert client.post(url, json=body, headers=ADMIN).status_code == 401
    assert client.get("/api/v1/admin/monitoring/nodes", headers=AGENT).status_code == 401


def test_heartbeat_then_overview(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/admin/monitoring/nodes/heartbeat", json=beat("k8s-w1").model_dump(), headers=AGENT
    )
    assert resp.status_code == 204

    data = client.get("/api/v1/admin/monitoring/overview", headers=ADMIN).json()
    ids = {n["node_id"] for n in data["nodes"]}
    assert {"k8s-w1", "api-local"} <= ids
    assert data["services"][0]["status"] == "down"
    assert data["summary"]["overall"] == "down"
    assert data["summary"]["services_down"] == 1


def test_heartbeat_validation(client: TestClient) -> None:
    bad = beat().model_dump() | {"cpu_percent": 250}
    resp = client.post("/api/v1/admin/monitoring/nodes/heartbeat", json=bad, headers=AGENT)
    assert resp.status_code == 422


def test_node_ages_into_degraded_then_down() -> None:
    reg = NodeRegistry(stale_after_s=45, offline_after_s=120)
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    reg.record(beat(), now=t0)
    assert reg.snapshot(t0 + timedelta(seconds=10))[0].status is Status.HEALTHY
    assert reg.snapshot(t0 + timedelta(seconds=60))[0].status is Status.DEGRADED
    assert reg.snapshot(t0 + timedelta(seconds=200))[0].status is Status.DOWN


def test_node_high_resource_is_degraded_with_reason() -> None:
    reg = NodeRegistry()
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    reg.record(beat(disk=95, cpu=92), now=t0)
    node = reg.snapshot(t0)[0]
    assert node.status is Status.DEGRADED
    assert node.status_reason == "CPU, Disk above 90%"


def test_tcp_probe_reports_down_and_up() -> None:
    async def run() -> tuple[Status, Status]:
        server = await asyncio.start_server(lambda r, w: w.close(), "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        up = await probe_tcp(
            ServiceTarget(name="u", group="g", kind="tcp", host="127.0.0.1", port=port)
        )
        server.close()
        await server.wait_closed()
        down = await probe_tcp(
            ServiceTarget(name="d", group="g", kind="tcp", host="127.0.0.1", port=port)
        )
        return up.status, down.status

    assert asyncio.run(run()) == (Status.HEALTHY, Status.DOWN)


def test_worst_rollup() -> None:
    assert worst([Status.HEALTHY, Status.DEGRADED]) is Status.DEGRADED
    assert worst([Status.DEGRADED, Status.DOWN, Status.HEALTHY]) is Status.DOWN
    assert worst([]) is Status.UNKNOWN