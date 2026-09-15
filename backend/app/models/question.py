"""
Question and QuestionSource models.

Design notes:
- Options A/B/C/D stored as TEXT columns (not a separate table).
  Rationale: MCQ always has exactly 4 options; avoids a join for every question fetch.
- correct_answer stored as VARCHAR(1): 'A', 'B', 'C', or 'D'.
  Rationale: matches PDF answer key format directly; readable in DB.
- Enums implemented as plain string constants with CHECK constraints.
  Rationale: avoids Alembic enum migration pain with PostgreSQL.
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
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ─── String constant groups (used for CHECK constraints + Pydantic enums) ─────
SOURCE_TYPES = ("PYQ", "AI_GENERATED", "REFERENCE")
VERIFICATION_STATUSES = ("VERIFIED", "NEEDS_REVIEW", "REJECTED", "UNVERIFIED")
DIFFICULTIES = ("EASY", "MEDIUM", "HARD")
ANSWER_CHOICES = ("A", "B", "C", "D")
LANGUAGES = ("ENGLISH", "HINDI", "BILINGUAL")


class QuestionSource(Base):
    """
    Represents the origin of a question — a specific PDF exam paper,
    a reference book, or the AI generator.
    """

    __tablename__ = "question_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="REFERENCE",
    )
    exam_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    exam_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exam_shift: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # ─── Relationships ────────────────────────────────────────────────────────
    questions: Mapped[list["Question"]] = relationship(
        "Question", back_populates="source", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<QuestionSource id={self.id} name={self.name}>"


class Question(Base):
    """
    Core question entity.

    Every question — whether from a PYQ PDF, a reference book, or AI-generated —
    lives in this single table. The source_type field distinguishes provenance.

    CRITICAL: AI_GENERATED questions must never have a real source_year.
    PYQ questions must preserve their real exam source and year.
    """

    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint(
            "correct_answer IN ('A', 'B', 'C', 'D')",
            name="ck_questions_correct_answer",
        ),
        CheckConstraint(
            "source_type IN ('PYQ', 'AI_GENERATED', 'REFERENCE')",
            name="ck_questions_source_type",
        ),
        CheckConstraint(
            "verification_status IN ('VERIFIED', 'NEEDS_REVIEW', 'REJECTED', 'UNVERIFIED')",
            name="ck_questions_verification_status",
        ),
        CheckConstraint(
            "difficulty IN ('EASY', 'MEDIUM', 'HARD')",
            name="ck_questions_difficulty",
        ),
        CheckConstraint(
            "language IN ('ENGLISH', 'HINDI', 'BILINGUAL')",
            name="ck_questions_language",
        ),
        # Performance indexes
        Index("ix_questions_subject_id", "subject_id"),
        Index("ix_questions_topic_id", "topic_id"),
        Index("ix_questions_source_type", "source_type"),
        Index("ix_questions_difficulty", "difficulty"),
        Index("ix_questions_verification_status", "verification_status"),
        Index("ix_questions_source_year", "source_year"),
        # Composite index for the most common question-bank query
        Index(
            "ix_questions_subject_topic_difficulty",
            "subject_id",
            "topic_id",
            "difficulty",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ─── Question content ─────────────────────────────────────────────────────
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    option_a: Mapped[str] = mapped_column(Text, nullable=False)
    option_b: Mapped[str] = mapped_column(Text, nullable=False)
    option_c: Mapped[str] = mapped_column(Text, nullable=False)
    option_d: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(1), nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ─── Classification ───────────────────────────────────────────────────────
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="SET NULL"),
        nullable=True,
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="SET NULL"),
        nullable=True,
    )
    subtopic: Mapped[str | None] = mapped_column(String(200), nullable=True)
    difficulty: Mapped[str] = mapped_column(String(10), nullable=False, default="MEDIUM")
    language: Mapped[str] = mapped_column(String(20), nullable=False, default="ENGLISH")

    # ─── Provenance ───────────────────────────────────────────────────────────
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, default="REFERENCE")
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("question_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_exam: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # NULL for AI_GENERATED questions — never invent a year
    source_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ─── Verification ────────────────────────────────────────────────────────
    verification_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="UNVERIFIED"
    )
    extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    answer_mapping_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ─── PDF extraction metadata ─────────────────────────────────────────────
    pdf_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pdf_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    pdf_page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    question_number_in_source: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ─── Timestamps ───────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # ─── Relationships ────────────────────────────────────────────────────────
    subject: Mapped["Subject | None"] = relationship(  # noqa: F821
        "Subject", back_populates="questions", lazy="noload"
    )
    topic: Mapped["Topic | None"] = relationship(  # noqa: F821
        "Topic", back_populates="questions", lazy="noload"
    )
    source: Mapped["QuestionSource | None"] = relationship(
        "QuestionSource", back_populates="questions", lazy="noload"
    )
    pdf_document: Mapped["PdfDocument | None"] = relationship(  # noqa: F821
        "PdfDocument", back_populates="questions", lazy="noload"
    )
    mock_test_entries: Mapped[list["MockTestQuestion"]] = relationship(  # noqa: F821
        "MockTestQuestion", back_populates="question", lazy="noload"
    )
    attempt_answers: Mapped[list["AttemptAnswer"]] = relationship(  # noqa: F821
        "AttemptAnswer", back_populates="question", lazy="noload"
    )
    mistake_entries: Mapped[list["MistakeQuestion"]] = relationship(  # noqa: F821
        "MistakeQuestion", back_populates="question", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Question id={self.id} source_type={self.source_type}>"
