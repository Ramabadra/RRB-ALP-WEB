"""
MistakeQuestion model — user's personal mistake book.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MistakeQuestion(Base):
    """
    A question the user got wrong, saved to their personal mistake book.

    Unique constraint (user_id, question_id) prevents duplicate entries —
    if the user gets the same question wrong multiple times,
    the existing entry is preserved (not duplicated).

    attempt_id is nullable: mistakes can also be manually added.
    """

    __tablename__ = "mistake_questions"
    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_mistake_user_question"),
        Index("ix_mistake_questions_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attempts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ─── Relationships ────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="mistake_questions", lazy="noload"
    )
    question: Mapped["Question"] = relationship(  # noqa: F821
        "Question", back_populates="mistake_entries", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<MistakeQuestion user_id={self.user_id} question_id={self.question_id}>"
