import os
from datetime import UTC, datetime
from functools import lru_cache

from fastapi import APIRouter, status

from api.monitoring.auth import AdminOnly, AgentOnly
from api.monitoring.config import load_targets
from api.monitoring.nodes import NodeRegistry, collect_local_heartbeat
from api.monitoring.probes import ServiceMonitor
from api.monitoring.schemas import (
    NodeHeartbeat,
    NodeStatus,
    Overview,
    ServiceCheck,
    Status,
    Summary,
    worst,
)

router = APIRouter(prefix="/api/v1/admin/monitoring", tags=["admin-monitoring"])


@lru_cache
def get_service_monitor() -> ServiceMonitor:
    return ServiceMonitor(load_targets())


@lru_cache
def get_node_registry() -> NodeRegistry:
    return NodeRegistry()


def _count(statuses: list[Status], wanted: Status) -> int:
    return sum(1 for s in statuses if s is wanted)


def _record_api_node() -> None:
    """The API host reports itself, so the node list is never empty."""
    node_id = os.environ.get("PGS_API_NODE_ID", "api-local")
    get_node_registry().record(collect_local_heartbeat(node_id, role="api"))


@router.get("/services", response_model=list[ServiceCheck], dependencies=[AdminOnly])
async def list_services() -> list[ServiceCheck]:
    return await get_service_monitor().check_all()


@router.get("/nodes", response_model=list[NodeStatus], dependencies=[AdminOnly])
async def list_nodes() -> list[NodeStatus]:
    _record_api_node()
    return get_node_registry().snapshot()


@router.post(
    "/nodes/heartbeat",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[AgentOnly],
)
async def receive_heartbeat(beat: NodeHeartbeat) -> None:
    get_node_registry().record(beat)


@router.get("/overview", response_model=Overview, dependencies=[AdminOnly])
async def overview() -> Overview:
    services = await get_service_monitor().check_all()
    _record_api_node()
    nodes = get_node_registry().snapshot()

    service_states = [s.status for s in services]
    node_states = [n.status for n in nodes]
    return Overview(
        generated_at=datetime.now(UTC),
        summary=Summary(
            overall=worst(service_states + node_states),
            services_total=len(services),
            services_healthy=_count(service_states, Status.HEALTHY),
            services_degraded=_count(service_states, Status.DEGRADED),
            services_down=_count(service_states, Status.DOWN),
            nodes_total=len(nodes),
            nodes_healthy=_count(node_states, Status.HEALTHY),
            nodes_degraded=_count(node_states, Status.DEGRADED),
            nodes_down=_count(node_states, Status.DOWN),
        ),
        services=services,
        nodes=nodes,
    )