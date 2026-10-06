from fastapi import APIRouter, HTTPException, status

from auth.schemas import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)

from auth.service import (
    register_user,
    authenticate_user,
    generate_tokens,
    refresh_access_token,
)


router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
)
def register(request: RegisterRequest):

    try:
        user = register_user(
            request.username,
            request.password,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    return user


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(request: LoginRequest):

    user = authenticate_user(
        request.username,
        request.password,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    return generate_tokens(user)


@router.post(
    "/refresh",
    response_model=TokenResponse,
)
def refresh(request: RefreshRequest):

    try:
        return refresh_access_token(
            request.refresh_token
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
        )