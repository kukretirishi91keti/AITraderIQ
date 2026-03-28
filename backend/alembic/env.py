"""
Alembic environment configuration for async SQLAlchemy.
Reads DATABASE_URL from environment (via .env) and uses
the same Base metadata as the application.
"""

import asyncio
import os
import sys
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Ensure backend/ is on sys.path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
load_dotenv()

# Alembic Config object
config = context.config

# Override sqlalchemy.url from environment
database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./traderai.db")
config.set_main_option("sqlalchemy.url", database_url)

# Setup loggers
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so metadata is complete
from database.engine import Base  # noqa: E402
import database.models  # noqa: F401, E402

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL without connecting)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migrations."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
