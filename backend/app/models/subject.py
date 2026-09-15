"""
Subject and Topic models.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    # e.g. MATH, REASON, PHY, CHEM, BIO
    short_code: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # ─── Relationships ────────────────────────────────────────────────────────
    topics: Mapped[list["Topic"]] = relationship(
        "Topic", back_populates="subject", lazy="noload", cascade="all, delete-orphan"
    )
    questions: Mapped[list["Question"]] = relationship(  # noqa: F821
        "Question", back_populates="subject", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Subject id={self.id} name={self.name}>"


class Topic(Base):
    __tablename__ = "topics"
    __table_args__ = (
        UniqueConstraint("subject_id", "name", name="uq_topic_subject_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # ─── Relationships ────────────────────────────────────────────────────────
    subject: Mapped["Subject"] = relationship(
        "Subject", back_populates="topics", lazy="noload"
    )
    questions: Mapped[list["Question"]] = relationship(  # noqa: F821
        "Question", back_populates="topic", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Topic id={self.id} name={self.name}>"
