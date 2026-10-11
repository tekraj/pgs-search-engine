"""`POST /api/v1/auth/login`, `POST /api/v1/auth/logout` and `GET /api/v1/auth/me`."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status

from pgs_db.security import verify_password

from ..auth.dependencies import (
    INVALID_CREDENTIALS,
    ClientIp,
    CurrentAdmin,
    burn_password_check,
    require_token_codec,
    too_many_attempts,
    unauthorized,
    upgraded_hash,
)
from ..auth.tokens import TokenCodec
from ..core.services import ServicesDep
from ..schemas.auth import LoginRequest, LoginResponse, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_AUTH_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"description": "Wrong credentials, or a missing/invalid/expired token"},
    429: {"description": "Too many failed logins; see Retry-After"},
    503: {"description": "API_AUTH_SECRET is not set, or too many sign-ins are in progress"},
}


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Exchange an admin's username or email and password for an access token",
    responses=_AUTH_ERRORS,
)
def login(
    body: LoginRequest,
    services: ServicesDep,
    tokens: Annotated[TokenCodec, Depends(require_token_codec)],
    ip: ClientIp,
) -> LoginResponse:
    account = services.db.find_admin(body.login)
    # By id once the account exists, so the username and the email share one limit.
    identity = f"admin:{account.id}" if account else f"admin-login:{body.login}"
    wait = services.throttle.retry_after(identity, ip)
    if wait:
        raise too_many_attempts(wait)
    new_hash: str | None = None
    with services.passwords.slot():
        if account is None:
            burn_password_check(body.password)
            ok = False
        else:
            ok = verify_password(account.password_hash, body.password)
            if ok:
                new_hash = upgraded_hash(account.password_hash, body.password)
    if account is None or not ok:
        services.throttle.record_failure(identity, ip)
        logger.info("admin login failed")
        raise unauthorized(INVALID_CREDENTIALS)
    services.throttle.record_success(identity, ip)
    try:
        services.db.record_login(account.id, new_hash)
    except LookupError:  # deleted between the two statements
        raise unauthorized(INVALID_CREDENTIALS) from None
    logger.info("admin login", extra={"username": account.username})
    return LoginResponse(
        access_token=tokens.issue(subject=account.username, user_id=account.id, role=account.role),
        expires_in=tokens.ttl_seconds,
        user=User(username=account.username, email=account.email, role=account.role),
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Sign out: the bearer token stops working at once",
    responses=_AUTH_ERRORS,
)
def logout(admin: CurrentAdmin, services: ServicesDep) -> Response:
    services.db.revoke_token(admin.token_id, datetime.fromtimestamp(admin.token_expires_at, UTC))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me",
    response_model=User,
    summary="The admin the bearer token belongs to",
    responses=_AUTH_ERRORS,
)
def me(admin: CurrentAdmin) -> User:
    return User(username=admin.username, email=admin.email, role=admin.role)
