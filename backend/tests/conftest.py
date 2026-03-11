"""Shared fixtures for backend tests."""

import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Force test environment
os.environ["DEMO_MODE"] = "true"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"

from main import app  # noqa: E402
from database.engine import engine, Base  # noqa: E402


@pytest_asyncio.fixture
async def db():
    """Create fresh database tables for each test."""
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
