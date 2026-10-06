from uuid import uuid4

from core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    decode_token,
)


USERS: dict[str, dict] = {}


def register_user(
    username: str,
    password: str,
) -> dict:

    if any(
        user["username"] == username
        for user in USERS.values()
    ):
        raise ValueError("Username already exists")

    user_id = str(uuid4())

    USERS[user_id] = {
        "id": user_id,
        "username": username,
        "password": hash_password(password),
        "roles": ["user"],
    }

    return USERS[user_id]


def authenticate_user(
    username: str,
    password: str,
) -> dict | None:

    for user in USERS.values():

        if user["username"] != username:
            continue

        if not verify_password(
            password,
            user["password"],
        ):
            return None

        return user

    return None


def generate_tokens(user: dict) -> dict:

    roles = user["roles"]

    access_token = create_access_token(
        user["id"],
        user["username"],
        roles,
    )

    refresh_token = create_refresh_token(
        user["id"],
        user["username"],
        roles,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


def refresh_access_token(
    refresh_token: str,
) -> dict:

    try:
        payload = decode_token(refresh_token)
    except ValueError:
        raise ValueError("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise ValueError("Refresh token required")

    user_id = payload.get("sub")

    user = USERS.get(user_id)

    if not user:
        raise ValueError("User not found")

    return generate_tokens(user)