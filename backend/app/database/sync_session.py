"""
Synchronous SQLAlchemy session — used ONLY by Celery workers.

FastAPI uses AsyncSession. Celery workers are synchronous, so they need
a regular sync Session. Never use this in async FastAPI request handlers.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def _get_sync_engine():
    settings = get_settings()
    # Convert asyncpg URL to psycopg2 URL for synchronous use
    url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    return create_engine(url, pool_pre_ping=True)


def _get_sync_session_factory() -> sessionmaker:
    engine = _get_sync_engine()
    return sessionmaker(bind=engine, autocommit=False, autoflush=True)


@contextmanager
def get_sync_db_session() -> Generator[Session, None, None]:
    """Context manager providing a synchronous SQLAlchemy session for Celery tasks."""
    factory = _get_sync_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
