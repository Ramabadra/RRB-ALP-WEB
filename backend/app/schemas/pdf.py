"""
PDF upload and processing schemas.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PdfUploadResponse(BaseModel):
    """Returned immediately after POST /api/pdfs/upload (before processing starts)."""

    document_id: UUID
    job_id: UUID
    original_filename: str
    file_size_bytes: int
    status: str  # always 'QUEUED' at this point
    message: str = "PDF uploaded. Processing queued."


class PdfDocumentResponse(BaseModel):
    id: UUID
    original_filename: str
    file_size_bytes: int
    mime_type: str
    exam_name: str | None
    exam_year: int | None
    exam_shift: str | None
    page_count: int | None
    questions_extracted: int
    questions_stored: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PdfJobStatusResponse(BaseModel):
    """GET /api/pdfs/{id}/status — polling endpoint."""

    document_id: UUID
    job_id: UUID
    status: str
    progress_pct: float
    current_stage: str | None
    error_message: str | None
    questions_extracted: int
    questions_stored: int
    started_at: datetime | None
    completed_at: datetime | None


class PdfUploadMetadata(BaseModel):
    """Optional metadata the user can provide at upload time."""

    exam_name: str | None = None
    exam_year: int | None = None
    exam_shift: str | None = None
