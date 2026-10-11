"""Public-site user authentication: bearer tokens with the `user` audience.

Admin tokens do not work here and user tokens do not work on admin routes (the audience
differs). `current_user` also checks sign-out and that the account is still active;
`optional_user` is for routes that work for everyone and only add features (search
history) when a valid token is sent: it never fails and does no database work.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials

from ..core.services import ServicesDep
from .dependencies import (
    bearer_scheme,
    require_token_codec,
    unauthorized,
)
from .tokens import USER_AUDIENCE, TokenCodec, TokenError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UserPrincipal:
    user_id: int
    email: str
    display_name: str | None
    save_history: bool
    token_id: str
    token_expires_at: int


@dataclass(frozen=True)
class TokenUser:
    """What a verified user token says; nothing checked against the database."""

    user_id: int
    token_id: str


def optional_user(
    services: ServicesDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> TokenUser | None:
    if credentials is None or services.tokens is None:
        return None
    try:
        claims = services.tokens.verify(credentials.credentials, USER_AUDIENCE)
    except TokenError:
        return None
    return TokenUser(user_id=claims.user_id, token_id=claims.token_id)


OptionalUser = Annotated[TokenUser | None, Depends(optional_user)]


def current_user(
    services: ServicesDep,
    tokens: Annotated[TokenCodec, Depends(require_token_codec)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> UserPrincipal:
    if credentials is None:
        raise unauthorized("Missing bearer token.")
    try:
        claims = tokens.verify(credentials.credentials, USER_AUDIENCE)
    except TokenError as exc:
        logger.info("user token rejected", extra={"reason": str(exc)})
        raise unauthorized("Invalid or expired token.") from None
    if services.db.is_token_revoked(claims.token_id):
        raise unauthorized("This token was signed out.")
    account = services.db.get_user(claims.user_id)
    if account is None:
        raise unauthorized("This account is no longer active.")
    return UserPrincipal(
        user_id=account.id,
        email=account.email,
        display_name=account.display_name,
        save_history=account.save_history,
        token_id=claims.token_id,
        token_expires_at=claims.expires_at,
    )


CurrentUser = Annotated[UserPrincipal, Depends(current_user)]
