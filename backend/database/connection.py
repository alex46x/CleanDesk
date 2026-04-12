"""
database/connection.py — Async SQLAlchemy engine + session factory.

Supports:
  • SQLite  (default, zero-config)
  • PostgreSQL (set DATABASE_URL env var)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, StaticPool

from backend.config import DATABASE_URL

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
_is_sqlite = DATABASE_URL.startswith("sqlite")

_engine_kwargs: dict = {
    "echo": False,          # set True to trace SQL in dev
    "future": True,
}

if _is_sqlite:
    # SQLite needs a single shared connection in async mode
    _engine_kwargs.update(
        {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }
    )
else:
    # PostgreSQL: use NullPool so connections are not cached between requests
    _engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(DATABASE_URL, **_engine_kwargs)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# Dependency — FastAPI compatible
# ---------------------------------------------------------------------------
@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Yield a session and guarantee cleanup."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency injection target."""
    async with get_db_context() as session:
        yield session


# ---------------------------------------------------------------------------
# Initialise schema (called at startup)
# ---------------------------------------------------------------------------
async def init_db() -> None:
    """Create all tables if they don't exist."""
    from backend.database.models import Base  # local import avoids circular

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialised at %s", DATABASE_URL)
