import socket
from datetime import UTC, datetime

import psutil

from api.monitoring.schemas import NodeHeartbeat, NodeStatus, Status

# Prime psutil so the first real reading is not a meaningless 0.0.
psutil.cpu_percent(interval=None)


class NodeRegistry:
    """Keeps the latest heartbeat per node and derives health from its age and load."""

    def __init__(
        self,
        stale_after_s: float = 45.0,
        offline_after_s: float = 120.0,
        resource_limit_percent: float = 90.0,
    ) -> None:
        self._stale_after = stale_after_s
        self._offline_after = offline_after_s
        self._limit = resource_limit_percent
        self._beats: dict[str, tuple[NodeHeartbeat, datetime]] = {}

    def record(self, beat: NodeHeartbeat, now: datetime | None = None) -> None:
        self._beats[beat.node_id] = (beat, now or datetime.now(UTC))

    def snapshot(self, now: datetime | None = None) -> list[NodeStatus]:
        current = now or datetime.now(UTC)
        nodes = [self._evaluate(beat, seen, current) for beat, seen in self._beats.values()]
        return sorted(nodes, key=lambda n: n.node_id)

    def _evaluate(self, beat: NodeHeartbeat, seen: datetime, now: datetime) -> NodeStatus:
        age = max((now - seen).total_seconds(), 0.0)
        status, reason = Status.HEALTHY, None

        if age > self._offline_after:
            status, reason = Status.DOWN, f"No heartbeat for {int(age)}s"
        elif age > self._stale_after:
            status, reason = Status.DEGRADED, f"Heartbeat is {int(age)}s old"
        else:
            hot = [
                label
                for label, value in (
                    ("CPU", beat.cpu_percent),
                    ("Memory", beat.memory_percent),
                    ("Disk", beat.disk_percent),
                )
                if value >= self._limit
            ]
            if hot:
                status, reason = Status.DEGRADED, f"{', '.join(hot)} above {self._limit:g}%"

        return NodeStatus(
            **beat.model_dump(),
            status=status,
            status_reason=reason,
            last_seen=seen,
            age_seconds=round(age, 1),
        )


def collect_local_heartbeat(node_id: str, role: str) -> NodeHeartbeat:
    """Read this machine's own metrics (used for the API host, and by the node agent)."""
    boot = datetime.fromtimestamp(psutil.boot_time(), UTC)
    return NodeHeartbeat(
        node_id=node_id,
        hostname=socket.gethostname(),
        role=role,
        ip_address=None,
        cpu_percent=psutil.cpu_percent(interval=None),
        memory_percent=psutil.virtual_memory().percent,
        disk_percent=psutil.disk_usage("/").percent,
        load_1m=psutil.getloadavg()[0],
        cpu_count=psutil.cpu_count() or 1,
        uptime_seconds=int((datetime.now(UTC) - boot).total_seconds()),
    )