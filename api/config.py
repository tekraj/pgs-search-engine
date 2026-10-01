import json
import os
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator


class ServiceTarget(BaseModel):
    """One thing to probe. `group` is the pipeline stage shown in the dashboard."""

    model_config = ConfigDict(frozen=True)

    name: str
    group: str
    kind: Literal["http", "tcp"]
    url: str | None = None
    host: str | None = None
    port: int | None = None
    timeout_s: float = 2.0
    degraded_ms: float = 500.0

    @model_validator(mode="after")
    def _check_fields(self) -> Self:
        if self.kind == "http" and not self.url:
            raise ValueError(f"{self.name}: http targets need a url")
        if self.kind == "tcp" and (not self.host or self.port is None):
            raise ValueError(f"{self.name}: tcp targets need host and port")
        return self

    @property
    def display_target(self) -> str:
        return self.url if self.kind == "http" and self.url else f"{self.host}:{self.port}"


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def default_targets() -> list[ServiceTarget]:
    """Sensible local-dev defaults. Override hosts via env, or the whole list via file."""
    return [
        ServiceTarget(
            name="Crawler",
            group="Crawl",
            kind="http",
            url=_env("PGS_SCRAPER_HEALTH_URL", "http://localhost:8081/healthz"),
        ),
        ServiceTarget(
            name="URL frontier queue",
            group="Crawl",
            kind="tcp",
            host=_env("PGS_QUEUE_HOST", "localhost"),
            port=int(_env("PGS_QUEUE_PORT", "6379")),
        ),
        ServiceTarget(
            name="ETL worker",
            group="Process",
            kind="http",
            url=_env("PGS_ETL_HEALTH_URL", "http://localhost:8082/healthz"),
        ),
        ServiceTarget(
            name="PostgreSQL",
            group="Store",
            kind="tcp",
            host=_env("PGS_DB_HOST", "localhost"),
            port=int(_env("PGS_DB_PORT", "5432")),
        ),
        ServiceTarget(
            name="Elasticsearch",
            group="Index",
            kind="http",
            url=_env("PGS_ES_HEALTH_URL", "http://localhost:9200/_cluster/health"),
        ),
        ServiceTarget(
            name="Qdrant",
            group="Index",
            kind="http",
            url=_env("PGS_QDRANT_HEALTH_URL", "http://localhost:6333/healthz"),
        ),
    ]


def load_targets() -> list[ServiceTarget]:
    """Load targets from the JSON file in PGS_MONITOR_CONFIG, else use defaults."""
    path = os.environ.get("PGS_MONITOR_CONFIG")
    if not path:
        return default_targets()
    raw: object = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("PGS_MONITOR_CONFIG must contain a JSON list of targets")
    return [ServiceTarget.model_validate(item) for item in raw]  # pyright: ignore[reportUnknownVariableType]