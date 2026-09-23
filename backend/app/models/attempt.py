"""
Attempt and AttemptAnswer models.

The server is the authoritative timer source.
started_at and expires_at are set on the server at attempt creation time.
The frontend reconstructs its countdown from these backend timestamps.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.mock_test import MockTest
    from app.models.result import Result
    from app.models.question import Question

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


ATTEMPT_STATUSES = ("NOT_STARTED", "IN_PROGRESS", "SUBMITTED", "EXPIRED")


class Attempt(Base):
    """
    A user's exam session for a specific MockTest.

    Timer rules:
    - started_at is set when the user begins the attempt (server time).
    - expires_at = started_at + mock_test.duration_minutes (server calculated).
    - The backend checks expires_at on every answer save and submission.
    - If expires_at has passed, the backend auto-submits and marks status=EXPIRED.
    """

    __tablename__ = "attempts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('NOT_STARTED', 'IN_PROGRESS', 'SUBMITTED', 'EXPIRED')",
            name="ck_attempts_status",
        ),
        Index("ix_attempts_user_id", "user_id"),
        Index("ix_attempts_mock_test_id", "mock_test_id"),
        Index("ix_attempts_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    mock_test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mock_tests.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="NOT_STARTED")
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    auto_submitted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # ─── Relationships ────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="attempts", lazy="noload"
    )
    mock_test: Mapped["MockTest"] = relationship(  # noqa: F821
        "MockTest", back_populates="attempts", lazy="noload"
    )
    answers: Mapped[list["AttemptAnswer"]] = relationship(
        "AttemptAnswer",
        back_populates="attempt",
        lazy="noload",
        cascade="all, delete-orphan",
    )
    result: Mapped["Result | None"] = relationship(  # noqa: F821
        "Result", back_populates="attempt", uselist=False, lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Attempt id={self.id} status={self.status}>"


class AttemptAnswer(Base):
    """
    One row per question per attempt — autosaved as the user selects answers.

    Upserted on POST /api/attempts/{id}/answers.
    unique(attempt_id, question_id) prevents duplicate rows.
    selected_answer=NULL means the question was seen but not answered.
    is_marked=True means the user flagged it for review.
    """

    __tablename__ = "attempt_answers"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_attempt_answers_attempt_question"),
        CheckConstraint(
            "selected_answer IS NULL OR selected_answer IN ('A', 'B', 'C', 'D')",
            name="ck_attempt_answers_selected_answer",
        ),
        Index("ix_attempt_answers_attempt_id", "attempt_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attempts.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    # NULL = unanswered; 'A'|'B'|'C'|'D' = user's selection
    selected_answer: Mapped[str | None] = mapped_column(String(1), nullable=True)
    is_marked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    answered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # ─── Relationships ────────────────────────────────────────────────────────
    attempt: Mapped["Attempt"] = relationship(
        "Attempt", back_populates="answers", lazy="noload"
    )
    question: Mapped["Question"] = relationship(  # noqa: F821
        "Question", back_populates="attempt_answers", lazy="noload"
    )

    def __repr__(self) -> str:
        return (
            f"<AttemptAnswer attempt_id={self.attempt_id} "
            f"question_id={self.question_id} answer={self.selected_answer}>"
        )
