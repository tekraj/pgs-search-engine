from datetime import datetime, timedelta, timezone
from typing import Any

import hashlib
import hmac
import secrets

from jose import JWTError, jwt

from core.config import settings


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        100_000,
    )

    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_password: str) -> bool:
    try:
        salt_hex, digest_hex = stored_password.split("$", 1)

        salt = bytes.fromhex(salt_hex)

        calculated = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt,
            100_000,
        )

        return hmac.compare_digest(
            calculated.hex(),
            digest_hex,
        )

    except ValueError:
        return False


def create_access_token(
    user_id: str,
    username: str,
    roles: list[str],
) -> str:

    expire = datetime.now(timezone.utc) + timedelta(
        seconds=settings.jwt_expire_seconds
    )

    payload = {
        "sub": user_id,
        "username": username,
        "roles": roles,
        "type": "access",
        "exp": expire,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(
    user_id: str,
    username: str,
    roles: list[str],
) -> str:

    expire = datetime.now(timezone.utc) + timedelta(days=30)

    payload = {
        "sub": user_id,
        "username": username,
        "roles": roles,
        "type": "refresh",
        "exp": expire,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> dict[str, Any]:

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        return payload

    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc