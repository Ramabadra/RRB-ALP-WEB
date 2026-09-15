"""
SQLAlchemy declarative base shared by all ORM models.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    All ORM models inherit from this base.
    Provides the metadata registry used by Alembic autogenerate.
    """
    pass
