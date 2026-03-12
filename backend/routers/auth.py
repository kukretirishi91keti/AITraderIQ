"""
Authentication Router - Register, Login, Profile.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, field_validator
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from database.engine import get_db
from database.models import User
from auth.security import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_auth,
)

try:
    from middleware.rate_limit import limiter, AUTH_RATE

    def _auth_rate_limit(func):
        return limiter.limit(AUTH_RATE)(func)
except ImportError:
    def _auth_rate_limit(func):
        return func

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    username: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=255)
    trader_style: str = Field(default="swing")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid email address")
        return v.lower().strip()


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    trader_style: str | None = None
    risk_tolerance: str | None = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/register", status_code=status.HTTP_201_CREATED)
@_auth_rate_limit
async def register(request_obj: Request, request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Check if username already exists
    result = await db.execute(select(User).where(User.username == request.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        email=request.email,
        username=request.username,
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
        trader_style=request.trader_style,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(data={"sub": user.id})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "trader_style": user.trader_style,
        },
    }


async def _authenticate_user(username: str, password: str, db: AsyncSession) -> dict:
    """Shared login logic for both form-data and JSON endpoints."""
    result = await db.execute(
        select(User).where(
            (User.username == username) | (User.email == username)
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account deactivated")

    token = create_access_token(data={"sub": user.id})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "trader_style": user.trader_style,
            "risk_tolerance": user.risk_tolerance,
        },
    }


@router.post("/login")
@_auth_rate_limit
async def login(
    request_obj: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Login with form-data (OAuth2 standard). Used by Swagger /docs."""
    return await _authenticate_user(form_data.username, form_data.password, db)


@router.post("/login/json")
@_auth_rate_limit
async def login_json(
    request_obj: Request,
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Login with JSON body. Use this from frontend fetch()/axios calls."""
    return await _authenticate_user(request.username, request.password, db)


@router.get("/me")
async def get_profile(user: User = Depends(require_auth)):
    """Get current user profile."""
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "trader_style": user.trader_style,
        "risk_tolerance": user.risk_tolerance,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.put("/me")
async def update_profile(
    update: ProfileUpdate,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Update user profile."""
    if update.full_name is not None:
        user.full_name = update.full_name
    if update.trader_style is not None:
        user.trader_style = update.trader_style
    if update.risk_tolerance is not None:
        user.risk_tolerance = update.risk_tolerance

    user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "trader_style": user.trader_style,
        "risk_tolerance": user.risk_tolerance,
    }
