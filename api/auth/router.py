from fastapi import APIRouter

router = APIRouter()

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Role, Permission
from app.auth.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    require_role,
    require_permission
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Request schemas
class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# Register
@router.post("/register")
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db)
🙁
    existing_user = db.query(User).filter(
        (User.username == data.username) |
        (User.email == data.email)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Username or email already exists"
        )

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        is_active=True
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": "User registered successfully",
        "user_id": user.id
    }


# Login
@router.post("/login")
def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
🙁
    user = db.query(User).filter(
        User.username == data.username
    ).first()

    if (
        not user
        or not verify_password(data.password, user.hashed_password)
        or not user.is_active
    🙁
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer"
    }


# Refresh access token
@router.post("/refresh")
def refresh_token(
    data: RefreshRequest,
    db: Session = Depends(get_db)
🙁
    payload = decode_token(data.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token"
        )

    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token"
        )

    user = db.query(User).filter(
        User.id == user_id,
        User.is_active == True
    ).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found or inactive"
        )

    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer"
    }


# Logout
@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user)
🙁
    return {
        "message": "Logged out successfully. Delete stored tokens on the client."
    }


# Current user profile
@router.get("/me")
def get_profile(
    current_user: User = Depends(get_current_user)
🙁
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "roles": [role.name for role in current_user.roles],
        "permissions": list({
            permission.name
            for role in current_user.roles
            for permission in role.permissions
        })
    }


# Admin-only route
@router.get("/admin")
def admin_dashboard(
    current_user: User = Depends(require_role("admin"))
🙁
    return {
        "message": "Welcome to the admin dashboard"
    }


# Permission-protected route
@router.get("/reports")
def view_reports(
    current_user: User = Depends(
        require_permission("reports:read")
    )
🙁
    return {
        "message": "You have permission to view reports"
    }


# Assign a role to a user (admin only)
@router.post("/assign-role/{user_id}/{role_id}")
def assign_role(
    user_id: int,
    role_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin"))
🙁
    user = db.query(User).filter(User.id == user_id).first()
    role = db.query(Role).filter(Role.id == role_id).first()

    if not user or not role:
        raise HTTPException(
            status_code=404,
            detail="User or role not found"
        )

    if role not in user.roles:
        user.roles.append(role)
        db.commit()

    return {
        "message": "Role assigned successfully",
        "username": user.username,
        "role": role.name
    }


# Assign permission to a role (admin only)
@router.post("/assign-permission/{role_id}/{permission_id}")
def assign_permission(
    role_id: int,
    permission_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin"))
🙁
    role = db.query(Role).filter(Role.id == role_id).first()
    permission = db.query(Permission).filter(
        Permission.id == permission_id
    ).first()

    if not role or not permission:
        raise HTTPException(
            status_code=404,
            detail="Role or permission not found"
        )

    if permission not in role.permissions:
        role.permissions.append(permission)
        db.commit()

    return {
        "message": "Permission assigned successfully",
        "role": role.name,
        "permission": permission.name
    }   