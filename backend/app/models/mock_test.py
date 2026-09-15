"""
MockTest and MockTestQuestion models.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MockTest(Base):
    """
    A generated mock test. Contains configuration and references questions
    via the MockTestQuestion junction table.
    """

    __tablename__ = "mock_tests"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('PYQ', 'AI_GENERATED', 'REFERENCE', 'MIXED')",
            name="ck_mock_tests_source_type",
        ),
        CheckConstraint(
            "difficulty IN ('EASY', 'MEDIUM', 'HARD', 'MIXED')",
            name="ck_mock_tests_difficulty",
        ),
        Index("ix_mock_tests_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    negative_marking: Mapped[float] = mapped_column(Float, nullable=False, default=0.3333)
    marks_per_correct: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, default="MIXED")
    difficulty: Mapped[str] = mapped_column(String(10), nullable=False, default="MIXED")
    # Full generation request parameters stored for auditing
    config_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # ─── Relationships ────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="mock_tests", lazy="noload"
    )
    mock_test_questions: Mapped[list["MockTestQuestion"]] = relationship(
        "MockTestQuestion",
        back_populates="mock_test",
        lazy="noload",
        cascade="all, delete-orphan",
        order_by="MockTestQuestion.position",
    )
    attempts: Mapped[list["Attempt"]] = relationship(  # noqa: F821
        "Attempt", back_populates="mock_test", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<MockTest id={self.id} title={self.title}>"


class MockTestQuestion(Base):
    """
    Junction table linking MockTest to Questions, preserving question order.
    """

    __tablename__ = "mock_test_questions"
    __table_args__ = (
        UniqueConstraint("mock_test_id", "position", name="uq_mtq_mock_test_position"),
        UniqueConstraint("mock_test_id", "question_id", name="uq_mtq_mock_test_question"),
        Index("ix_mock_test_questions_mock_test_id", "mock_test_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mock_test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mock_tests.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    # ─── Relationships ────────────────────────────────────────────────────────
    mock_test: Mapped["MockTest"] = relationship(
        "MockTest", back_populates="mock_test_questions", lazy="noload"
    )
    question: Mapped["Question"] = relationship(  # noqa: F821
        "Question", back_populates="mock_test_entries", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<MockTestQuestion mock_test_id={self.mock_test_id} position={self.position}>"
