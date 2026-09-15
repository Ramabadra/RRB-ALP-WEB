"""
Result model — computed after attempt submission.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Result(Base):
    """
    Computed result for a submitted attempt.

    subject_performance and topic_performance store per-subject/topic breakdowns
    as JSONB so the frontend can render detailed analytics without extra queries.

    answer_details stores the per-question outcome list for the review screen:
    [{"question_id": "...", "selected": "A", "correct": "C", "is_correct": false}, ...]
    """

    __tablename__ = "results"
    __table_args__ = (
        Index("ix_results_user_id", "user_id"),
        Index("ix_results_mock_test_id", "mock_test_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attempts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # one result per attempt
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

    # ─── Aggregate stats ──────────────────────────────────────────────────────
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    attempted: Mapped[int] = mapped_column(Integer, nullable=False)
    correct: Mapped[int] = mapped_column(Integer, nullable=False)
    wrong: Mapped[int] = mapped_column(Integer, nullable=False)
    unanswered: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, nullable=False)
    accuracy: Mapped[float] = mapped_column(Float, nullable=False)       # 0.0 – 100.0
    time_spent_seconds: Mapped[int] = mapped_column(Integer, nullable=False)

    # ─── Breakdowns (stored as JSONB) ─────────────────────────────────────────
    # {"MATHEMATICS": {"attempted": 10, "correct": 7, "wrong": 2, "unanswered": 1, "score": 6.33}}
    subject_performance: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # {"Number System": {"attempted": 3, "correct": 2, ...}}
    topic_performance: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # [{"question_id": "...", "selected_answer": "A", "correct_answer": "C", "is_correct": false}]
    answer_details: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # ─── Relationships ────────────────────────────────────────────────────────
    attempt: Mapped["Attempt"] = relationship(  # noqa: F821
        "Attempt", back_populates="result", lazy="noload"
    )
    user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="results", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Result id={self.id} score={self.score}/{self.max_score}>"
