"""
SQLAlchemy async engine and session factory.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

# ─── Engine ───────────────────────────────────────────────────────────────────
# pool_size / max_overflow tuned for Supabase's connection limits on free tier.
# Supabase free tier: 60 direct connections max. Use the pooler URL (port 5432)
# which supports up to 200 via PgBouncer.
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=not settings.is_production,       # log SQL in dev
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,                     # recycle connections every 30 min
    pool_pre_ping=True,                    # verify connections before use
)

# ─── Session factory ──────────────────────────────────────────────────────────
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
