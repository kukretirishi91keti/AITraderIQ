"""
Rate limiting middleware using slowapi.
Prevents API abuse and protects upstream data sources (yfinance).
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


# Global limiter instance
limiter = Limiter(
    key_func=_get_client_ip,
    default_limits=[DEFAULT_RATE],
    storage_uri=os.getenv("RATE_LIMIT_STORAGE", "memory://"),
)


def setup_rate_limiting(app):
    """Attach rate limiter to FastAPI app."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
