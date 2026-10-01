from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Status(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


# Higher number = worse. Used to roll several statuses up into one.
SEVERITY: dict[Status, int] = {
    Status.HEALTHY: 0,
    Status.UNKNOWN: 1,
    Status.DEGRADED: 2,
    Status.DOWN: 3,
}


def worst(statuses: list[Status]) -> Status:
    """Return the most severe status in the list (UNKNOWN if the list is empty)."""
    if not statuses:
        return Status.UNKNOWN
    return max(statuses, key=lambda s: SEVERITY[s])


class ServiceCheck(BaseModel):
    name: str
    group: str
    target: str
    status: Status
    latency_ms: float | None = None
    detail: str | None = None
    checked_at: datetime


class NodeHeartbeat(BaseModel):
    """Payload a node agent posts every ~15 seconds."""

    node_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    hostname: str = Field(min_length=1, max_length=255)
    role: str = Field(default="worker", max_length=32)
    ip_address: str | None = Field(default=None, max_length=64)
    cpu_percent: float = Field(ge=0, le=100)
    memory_percent: float = Field(ge=0, le=100)
    disk_percent: float = Field(ge=0, le=100)
    load_1m: float = Field(ge=0)
    cpu_count: int = Field(ge=1)
    uptime_seconds: int = Field(ge=0)


class NodeStatus(NodeHeartbeat):
    status: Status
    status_reason: str | None = None
    last_seen: datetime
    age_seconds: float


class Summary(BaseModel):
    overall: Status
    services_total: int
    services_healthy: int
    services_degraded: int
    services_down: int
    nodes_total: int
    nodes_healthy: int
    nodes_degraded: int
    nodes_down: int


class Overview(BaseModel):
    generated_at: datetime
    summary: Summary
    services: list[ServiceCheck]
    nodes: list[NodeStatus]