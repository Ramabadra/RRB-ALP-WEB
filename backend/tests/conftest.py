"""
Test configuration and shared fixtures.

Strategy for DB tests:
- Use async SQLite (aiosqlite) — no external PostgreSQL needed.
- Override all PG-specific types (UUID, JSONB) to SQLite-safe equivalents
  using SQLAlchemy's `with_variant()` on column types.
- Each test function gets an independent DB (function-scoped fixture).
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import String, Text, TypeDecorator

# ─── Set test environment BEFORE importing app ────────────────────────────────
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/rrb_alp_test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-do-not-use-in-production")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-google-client-secret")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("AI_API_KEY", "test-ai-key")
os.environ.setdefault("STORAGE_ENDPOINT", "http://localhost:9000")
os.environ.setdefault("STORAGE_ACCESS_KEY", "test-access-key")
os.environ.setdefault("STORAGE_SECRET_KEY", "test-secret-key")
os.environ.setdefault("ENVIRONMENT", "development")

try:
    from httpx2.testclient import TestClient  # type: ignore[import]
except ImportError:
    from fastapi.testclient import TestClient  # type: ignore[assignment]

# ─── Clear any stale settings cache ──────────────────────────────────────────
# This MUST happen after setting env vars but before importing the app.
from app.core.config import get_settings
get_settings.cache_clear()

from app.main import app as fastapi_app


# ─── SQLite-compatible TypeDecorators ────────────────────────────────────────
class GUIDType(TypeDecorator):
    """Stores UUID as VARCHAR(36). Replaces postgresql.UUID in tests."""
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value: Any, dialect: Any):
        if value is None:
            return None
        return uuid.UUID(str(value))


class JSONType(TypeDecorator):
    """Stores JSON/JSONB as TEXT. Replaces postgresql.JSONB in tests."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        return json.loads(value)


def _patch_table_types(metadata) -> None:
    """
    Walk all columns in SQLAlchemy metadata and replace
    postgresql.UUID → GUIDType and postgresql.JSONB → JSONType.
    This is done in-place and is safe because tests always run
    after the module is imported — we restore nothing (each test process
    uses its own metadata state).
    """
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID
    from sqlalchemy.dialects.postgresql import JSONB

    for table in metadata.tables.values():
        for col in table.columns:
            orig = type(col.type)
            if issubclass(orig, PG_UUID):
                col.type = GUIDType()
            elif issubclass(orig, JSONB):
                col.type = JSONType()


# ─── Import all models so Base.metadata is populated ─────────────────────────
from app.database.base import Base  # noqa: E402
import app.models  # noqa: F401, E402

# Patch once at import time
_patch_table_types(Base.metadata)


# ─── HTTP test client (no real DB connection) ─────────────────────────────────
@pytest.fixture(scope="function")
def client() -> TestClient:
    """
    Function-scoped HTTP test client.
    Does NOT enter the context manager (no lifespan) so no DB connection is needed.
    This is intentional — health/routing tests don't need a running DB.
    """
    return TestClient(fastapi_app, raise_server_exceptions=False)


# ─── Async in-memory SQLite fixtures ─────────────────────────────────────────
@pytest_asyncio.fixture(scope="function")
async def async_db_engine():
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(async_db_engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(
        bind=async_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with factory() as session:
        yield session
        await session.rollback()


# ─── Test data helpers ────────────────────────────────────────────────────────
def make_google_user_info(
    sub: str | None = None,
    email: str = "test@example.com",
    name: str = "Test User",
    picture: str = "https://example.com/pic.jpg",
    email_verified: bool = True,
) -> dict:
    return {
        "sub": sub or str(uuid.uuid4()),
        "email": email,
        "name": name,
        "picture": picture,
        "email_verified": email_verified,
    }
