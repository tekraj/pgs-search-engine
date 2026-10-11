"""`/api/v1/account/*`: sign-up, sign-in and the signed-in user's search history."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from pgs_db.security import hash_password, verify_password

from ..auth.dependencies import (
    INVALID_CREDENTIALS,
    ClientIp,
    burn_password_check,
    require_token_codec,
    too_many_attempts,
    unauthorized,
    upgraded_hash,
)
from ..auth.tokens import USER_AUDIENCE, TokenCodec
from ..auth.users import CurrentUser
from ..core.services import ServicesDep
from ..db.database import EmailTaken, UserAccount
from ..schemas.account import (
    AuthResponse,
    Cleared,
    DeleteAccountRequest,
    HistoryEntry,
    HistoryPage,
    Profile,
    RegisterRequest,
    SettingsUpdate,
    UserLoginRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/account", tags=["account"])

USER_ROLE = "USER"

_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"description": "Wrong credentials, or a missing/invalid/expired/signed-out token"},
    429: {"description": "Too many failed logins; see Retry-After"},
    503: {"description": "API_AUTH_SECRET is not set, or too many sign-ins are in progress"},
}


def _profile(account: UserAccount) -> Profile:
    return Profile(
        email=account.email, display_name=account.display_name, save_history=account.save_history
    )


def _auth_response(account: UserAccount, tokens: TokenCodec, services: ServicesDep) -> AuthResponse:
    ttl = services.settings.user_token_ttl_seconds
    token = tokens.issue(
        subject=account.email,
        user_id=account.id,
        role=USER_ROLE,
        audience=USER_AUDIENCE,
        ttl_seconds=ttl,
    )
    return AuthResponse(access_token=token, expires_in=ttl, user=_profile(account))


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account and sign in",
    responses={**_ERRORS, 409: {"description": "An account with this email exists"}},
)
def register(
    body: RegisterRequest,
    services: ServicesDep,
    tokens: Annotated[TokenCodec, Depends(require_token_codec)],
) -> AuthResponse:
    with services.passwords.slot():
        password_hash = hash_password(body.password)
    try:
        account = services.db.create_user(body.email, password_hash, body.display_name)
    except EmailTaken:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="An account with this email already exists."
        ) from None
    logger.info("user registered", extra={"user_id": account.id})
    return _auth_response(account, tokens, services)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Sign in with email and password",
    responses=_ERRORS,
)
def login(
    body: UserLoginRequest,
    services: ServicesDep,
    tokens: Annotated[TokenCodec, Depends(require_token_codec)],
    ip: ClientIp,
) -> AuthResponse:
    account = services.db.find_user(body.email)
    identity = f"user:{account.id}" if account else f"user-login:{body.email}"
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
        logger.info("user login failed")
        raise unauthorized(INVALID_CREDENTIALS)
    services.throttle.record_success(identity, ip)
    try:
        services.db.record_user_login(account.id, new_hash)
    except LookupError:  # deleted between the two statements
        raise unauthorized(INVALID_CREDENTIALS) from None
    return _auth_response(account, tokens, services)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Sign out: the bearer token stops working at once",
    responses=_ERRORS,
)
def logout(user: CurrentUser, services: ServicesDep) -> Response:
    services.db.revoke_token(user.token_id, datetime.fromtimestamp(user.token_expires_at, UTC))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=Profile, summary="The signed-in user", responses=_ERRORS)
def me(user: CurrentUser) -> Profile:
    return Profile(email=user.email, display_name=user.display_name, save_history=user.save_history)


@router.patch(
    "/settings",
    response_model=Profile,
    summary="Turn search-history recording on or off",
    responses=_ERRORS,
)
def update_settings(body: SettingsUpdate, user: CurrentUser, services: ServicesDep) -> Profile:
    services.db.set_save_history(user.user_id, body.save_history)
    return Profile(email=user.email, display_name=user.display_name, save_history=body.save_history)


@router.get(
    "/history",
    response_model=HistoryPage,
    summary="The user's recent searches, newest first",
    responses=_ERRORS,
)
def history(
    user: CurrentUser,
    services: ServicesDep,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    before: Annotated[int | None, Query(ge=1)] = None,
) -> HistoryPage:
    response.headers["Cache-Control"] = "no-store"
    rows = services.db.list_history(user.user_id, limit, before)
    return HistoryPage(
        items=[
            HistoryEntry(
                id=r.id,
                query=r.query_text,
                filters=r.filters,
                result_count=r.result_count,
                searched_at=r.searched_at,
            )
            for r in rows
        ],
        next_before=rows[-1].id if len(rows) == limit else None,
    )


@router.delete(
    "/history/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove one search from the history",
    responses={**_ERRORS, 404: {"description": "Not in this user's history"}},
)
def delete_history_item(item_id: int, user: CurrentUser, services: ServicesDep) -> Response:
    if not services.db.delete_history_item(user.user_id, item_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No such history entry.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/history", response_model=Cleared, summary="Clear the whole history", responses=_ERRORS
)
def clear_history(user: CurrentUser, services: ServicesDep) -> Cleared:
    return Cleared(deleted=services.db.clear_history(user.user_id))


@router.post(
    "/delete",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete the account and its history (asks for the password)",
    responses=_ERRORS,
)
def delete_account(
    body: DeleteAccountRequest, user: CurrentUser, services: ServicesDep, ip: ClientIp
) -> Response:
    identity = f"user:{user.user_id}"
    wait = services.throttle.retry_after(identity, ip)
    if wait:
        raise too_many_attempts(wait)
    account = services.db.get_user(user.user_id)
    with services.passwords.slot():
        ok = account is not None and verify_password(account.password_hash, body.password)
    if account is None or not ok:
        services.throttle.record_failure(identity, ip)
        raise unauthorized(INVALID_CREDENTIALS)
    services.db.delete_user(user.user_id)
    services.db.revoke_token(user.token_id, datetime.fromtimestamp(user.token_expires_at, UTC))
    logger.info("user deleted their account", extra={"user_id": user.user_id})
    return Response(status_code=status.HTTP_204_NO_CONTENT)
