"""
Rate limiting middleware using slowapi.
Prevents API abuse and protects upstream data sources (yfinance).

Keys by authenticated user ID when available, otherwise by client IP.
"""

import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request

# Rate limit defaults (configurable via env)
DEFAULT_RATE = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")
QUOTE_RATE = os.getenv("RATE_LIMIT_QUOTE", "30/minute")
AI_RATE = os.getenv("RATE_LIMIT_AI", "10/minute")
AUTH_RATE = os.getenv("RATE_LIMIT_AUTH", "5/minute")


def _get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For behind a proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


def _get_rate_limit_key(request: Request) -> str:
    """
    Return a per-user rate limit key when the request has a valid JWT,
    otherwise fall back to client IP.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            from jose import jwt as jose_jwt
            secret = os.getenv(
                "JWT_SECRET_KEY",
                "CHANGE-THIS-IN-PRODUCTION-use-openssl-rand-hex-32",
            )
            payload = jose_jwt.decode(token, secret, algorithms=["HS256"])
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except Exception:
            pass  # Fall through to IP-based key
    return _get_client_ip(request)


# Storage: prefer REDIS_URL (Railway add-on) → RATE_LIMIT_STORAGE → in-memory
# Redis keeps limits across deploys and works with multiple workers.
_storage_uri = (
    os.getenv("REDIS_URL")
    or os.getenv("RATE_LIMIT_STORAGE")
    or "memory://"
)

# Global limiter instance — keys by user ID when authenticated
limiter = Limiter(
    key_func=_get_rate_limit_key,
    default_limits=[DEFAULT_RATE],
    storage_uri=_storage_uri,
)


def setup_rate_limiting(app):
    """Attach rate limiter to FastAPI app."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
