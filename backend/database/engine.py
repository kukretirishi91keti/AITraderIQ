"""
Database engine configuration.
Uses SQLite for simplicity (easy to swap to PostgreSQL for production).
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

_raw_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./traderai.db")

# Neon / Render / Heroku all provide postgresql:// or postgres:// — asyncpg needs +asyncpg
DATABASE_URL = _raw_url
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Connection args vary by database type
_connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    # timeout=20: retry for up to 20s when DB is locked (test teardown races)
    _connect_args = {"check_same_thread": False, "timeout": 20}

# Async engine for FastAPI
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
    connect_args=_connect_args,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """Dependency that provides a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """
    Initialize database tables.

    In production (DEMO_MODE != true), logs a reminder to use Alembic migrations.
    In development/demo mode, uses create_all for convenience.
    """
    import database.models  # noqa: F401 - registers User, WatchlistItem, etc.
    try:
        from services.backtest_engine import SignalRecord  # noqa: F401
    except ImportError:
        pass

    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
    if not demo_mode:
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info(
            "Production mode: use 'alembic upgrade head' to manage schema migrations. "
            "Falling back to create_all for any missing tables."
        )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database engine."""
    await engine.dispose()
