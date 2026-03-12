"""
JWT authentication and password hashing.
"""

import os
import sys
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.engine import get_db
from database.models import User

_logger = logging.getLogger(__name__)

# Configuration — fail loud if JWT secret is insecure
_INSECURE_DEFAULTS = {
    "CHANGE-THIS-IN-PRODUCTION-use-openssl-rand-hex-32",
    "change-this-in-production",
    "",
}
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
if SECRET_KEY in _INSECURE_DEFAULTS:
    if os.getenv("DEMO_MODE", "true").lower() == "true":
        # Allow insecure key in demo mode only, with a loud warning
        SECRET_KEY = "DEMO-ONLY-insecure-key-do-not-use-in-production"
        _logger.warning("JWT_SECRET_KEY not set — using demo-only key. DO NOT deploy to production!")
    else:
        print("[FATAL] JWT_SECRET_KEY is not set or uses a default value. "
              "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\"",
              file=sys.stderr)
        sys.exit(1)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 hours default

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme - tokenUrl must match the login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get current user from JWT token.
    Returns None if no token provided (allows mixed auth/public endpoints).
    Raises 401 if token is invalid.
    """
    if token is None:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


async def require_auth(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    """Dependency that requires authentication. Use on protected endpoints."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
