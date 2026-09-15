"""
PdfDocument and PdfProcessingJob models.

Design notes:
- PDF binary files are NEVER stored in PostgreSQL.
- The actual file lives in Supabase Storage. storage_key is the object key.
- PdfDocument = metadata + storage reference.
- PdfProcessingJob = background job state machine for the processing pipeline.
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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


PDF_JOB_STATUSES = (
    "QUEUED",
    "PROCESSING",
    "EXTRACTING",
    "OCR",
    "PARSING",
    "VALIDATING",
    "COMPLETED",
    "FAILED",
)


class PdfDocument(Base):
    """
    Metadata record for an uploaded PDF file.

    The physical file is stored in Supabase Storage.
    storage_key is the object key used to retrieve/delete it.
    """

    __tablename__ = "pdf_documents"
    __table_args__ = (
        Index("ix_pdf_documents_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    # S3 object key in Supabase Storage bucket
    storage_key: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # ─── Exam metadata (may be filled by user or auto-detected) ──────────────
    exam_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    exam_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exam_shift: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ─── Processing results ───────────────────────────────────────────────────
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    questions_extracted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    questions_stored: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # ─── Relationships ────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="pdf_documents", lazy="noload"
    )
    processing_jobs: Mapped[list["PdfProcessingJob"]] = relationship(
        "PdfProcessingJob",
        back_populates="pdf_document",
        lazy="noload",
        cascade="all, delete-orphan",
        order_by="PdfProcessingJob.created_at",
    )
    questions: Mapped[list["Question"]] = relationship(  # noqa: F821
        "Question", back_populates="pdf_document", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<PdfDocument id={self.id} filename={self.original_filename}>"


class PdfProcessingJob(Base):
    """
    Background processing job state machine.

    The pipeline moves through these stages:
    QUEUED → PROCESSING → EXTRACTING → (OCR if needed) → PARSING → VALIDATING → COMPLETED
                                                                                 ↓ on error
                                                                               FAILED

    progress_pct: 0.0 – 100.0, updated as each stage completes.
    result_json: final report of extracted/rejected question counts, errors, etc.
    """

    __tablename__ = "pdf_processing_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('QUEUED','PROCESSING','EXTRACTING','OCR','PARSING','VALIDATING','COMPLETED','FAILED')",
            name="ck_pdf_jobs_status",
        ),
        Index("ix_pdf_jobs_pdf_document_id", "pdf_document_id"),
        Index("ix_pdf_jobs_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pdf_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pdf_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="QUEUED")
    progress_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Human-readable error description — never expose stack traces
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Final processing report
    result_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # ─── Relationships ────────────────────────────────────────────────────────
    pdf_document: Mapped["PdfDocument"] = relationship(
        "PdfDocument", back_populates="processing_jobs", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<PdfProcessingJob id={self.id} status={self.status}>"
