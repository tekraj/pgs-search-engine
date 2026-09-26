from __future__ import annotations

from typing import Any


class OpenSearch:
    def __init__(self, *, hosts: list[dict[str, Any]] | None = None, **kwargs: Any) -> None:
        self.hosts = hosts or []
        self.kwargs = kwargs

    def search(self, *, index: str | None, body: dict[str, Any]) -> dict[str, Any]:
        return {"hits": {"hits": []}}
