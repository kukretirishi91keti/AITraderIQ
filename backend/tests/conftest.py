"""Shared fixtures for backend tests."""

import os
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import timedelta

# Force test environment BEFORE any app imports
os.environ["DEMO_MODE"] = "true"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["GROQ_API_KEY"] = ""  # Force rule-based AI fallback

# Each worker gets its own DB file to avoid SQLite locking across tests
_TEST_DB = f"sqlite+aiosqlite:///./test_{uuid.uuid4().hex[:8]}.db"
os.environ["DATABASE_URL"] = _TEST_DB

from main import app  # noqa: E402
from database.engine import engine, Base  # noqa: E402
from auth.security import create_access_token, hash_password  # noqa: E402


@pytest_asyncio.fixture
async def db():
    """Create fresh database tables for each test, drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db):
    """Async HTTP client for testing FastAPI endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ─── Auth helper fixtures ────────────────────────────────────────────────────


async def _register_user(client: AsyncClient, suffix: str = "") -> dict:
    """Register a user and return {token, user, headers}."""
    payload = {
        "email": f"user{suffix}@test.com",
        "username": f"testuser{suffix}",
        "password": "SecurePass123!",
        "full_name": f"Test User {suffix}",
        "trader_style": "swing",
    }
    resp = await client.post("/api/auth/register", json=payload)
    assert resp.status_code == 201, f"Registration failed: {resp.text}"
    data = resp.json()
    token = data["access_token"]
    return {
        "token": token,
        "user": data["user"],
        "headers": {"Authorization": f"Bearer {token}"},
        "credentials": payload,
    }


@pytest_asyncio.fixture
async def auth_user(client):
    """A registered + logged-in user with auth headers."""
    return await _register_user(client, suffix="1")


@pytest_asyncio.fixture
async def auth_user_b(client):
    """A second registered user for isolation tests."""
    return await _register_user(client, suffix="2")


@pytest_asyncio.fixture
async def expired_token():
    """A JWT token that is already expired."""
    return create_access_token(
        data={"sub": "99999"},
        expires_delta=timedelta(minutes=-5),
    )
