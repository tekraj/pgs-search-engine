import os
import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status


def _check(supplied: str | None, env_name: str) -> None:
    expected = os.environ.get(env_name)
    if not expected:
        # Fail closed: never expose admin data when no secret has been configured.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"{env_name} is not set on the server",
        )
    if supplied is None or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing token")


def require_admin(x_admin_token: Annotated[str | None, Header()] = None) -> None:
    _check(x_admin_token, "PGS_ADMIN_TOKEN")


def require_agent(x_agent_token: Annotated[str | None, Header()] = None) -> None:
    _check(x_agent_token, "PGS_AGENT_TOKEN")


AdminOnly = Depends(require_admin)
AgentOnly = Depends(require_agent)