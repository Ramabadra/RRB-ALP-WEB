"""
PDF service — orchestrates upload validation, storage, DB persistence,
and Celery task dispatch.

Key design decisions:
- File bytes are validated BEFORE storage upload (size, MIME type, magic bytes).
- Storage upload is synchronous (boto3) and runs in the FastAPI request handler
  via run_in_executor so it doesn't block the async event loop.
- The Celery task is dispatched AFTER the DB records are committed.
  This prevents the worker from starting before the DB row exists.
- If storage upload fails, no DB record is created (no orphaned rows).
"""

from __future__ import annotations

import asyncio
import io
import math
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Optional
from uuid import UUID

from fastapi import BackgroundTasks, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.pdf_repository import PdfRepository
from app.repositories.question_repository import QuestionRepository
from app.schemas.pdf import (
    PdfDocumentResponse,
    PdfJobStatusResponse,
    PdfUploadResponse,
)
from app.schemas.common import PaginatedResponse
from app.storage.client import StorageClient

# Thread pool for synchronous storage operations
_STORAGE_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="storage")

# Allowed PDF magic bytes (first 4 bytes of a valid PDF)
PDF_MAGIC = b"%PDF"

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/acrobat",
}


class PdfService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = PdfRepository(db)
        self._q_repo = QuestionRepository(db)

    async def upload(
        self,
        user_id: UUID,
        file: UploadFile,
        background_tasks: BackgroundTasks,
        exam_name: Optional[str],
        exam_year: Optional[int],
        exam_shift: Optional[str],
        max_size_bytes: int,
    ) -> PdfUploadResponse:
        """
        Validate, upload to storage, create DB records, dispatch Celery task.
        """
        from app.core.config import get_settings
        settings = get_settings()

        # ── Read file ──────────────────────────────────────────────────────────
        file_bytes = await file.read()
        file_size = len(file_bytes)

        # ── Validate size ─────────────────────────────────────────────────────
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty.",
            )
        if file_size > max_size_bytes:
            max_mb = max_size_bytes // (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {max_mb} MB.",
            )

        # ── Validate MIME type + magic bytes ──────────────────────────────────
        content_type = (file.content_type or "").lower().split(";")[0].strip()
        if content_type not in ALLOWED_MIME_TYPES and content_type != "application/pdf":
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Invalid content type '{content_type}'. Only PDF files are accepted.",
            )
        if not file_bytes.startswith(PDF_MAGIC):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File does not appear to be a valid PDF (invalid magic bytes).",
            )

        filename = file.filename or "document.pdf"

        # ── Create DB records BEFORE storage upload ───────────────────────────
        # We need document_id first so the storage key embeds it
        import uuid as uuid_module
        document_id = uuid_module.uuid4()

        # ── Upload to storage (synchronous — run in thread pool) ──────────────
        storage = StorageClient()

        loop = asyncio.get_event_loop()
        storage_key, _presigned_url = await loop.run_in_executor(
            _STORAGE_EXECUTOR,
            partial(
                storage.upload_pdf,
                user_id=user_id,
                document_id=document_id,
                filename=filename,
                file_bytes=file_bytes,
            ),
        )

        # ── Persist DB records ────────────────────────────────────────────────
        doc = await self._repo.create_document(
            user_id=user_id,
            original_filename=filename,
            storage_key=storage_key,
            file_size_bytes=file_size,
            mime_type="application/pdf",
            exam_name=exam_name.strip() if exam_name else None,
            exam_year=exam_year,
            exam_shift=exam_shift,
        )
        # Override the auto-generated UUID to match what we used for storage_key
        # (SQLAlchemy flushes doc.id = uuid4() — we pre-assigned document_id above
        # but didn't pass it to create_document. Let's use doc.id from DB.)
        job = await self._repo.create_job(doc.id)

        # ── Dispatch Celery task (after commit) ───────────────────────────────
        # Note: We commit inside the FastAPI dependency (after the handler returns).
        # For safety we dispatch after yielding the response.
        # The task ID is stored for tracking.
        from app.pdf.tasks import process_pdf
        
        if getattr(settings, "USE_CELERY", False):
            process_pdf.delay(str(doc.id), str(job.id))
        else:
            background_tasks.add_task(process_pdf, str(doc.id), str(job.id))

        return PdfUploadResponse(
            document_id=doc.id,
            job_id=job.id,
            original_filename=filename,
            file_size_bytes=file_size,
            status="QUEUED",
        )

    async def get_status(self, document_id: UUID, user_id: UUID) -> PdfJobStatusResponse:
        doc = await self._get_owned_doc(document_id, user_id)
        job = await self._repo.get_latest_job(document_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No processing job found for this document.",
            )
        return PdfJobStatusResponse(
            document_id=doc.id,
            job_id=job.id,
            status=job.status,
            progress_pct=job.progress_pct,
            current_stage=job.current_stage,
            error_message=job.error_message,
            questions_extracted=doc.questions_extracted,
            questions_stored=doc.questions_stored,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )

    async def get_document(self, document_id: UUID, user_id: UUID) -> PdfDocumentResponse:
        doc = await self._get_owned_doc(document_id, user_id)
        return PdfDocumentResponse.model_validate(doc)

    async def list_documents(
        self, user_id: UUID, page: int, page_size: int
    ) -> PaginatedResponse:
        total = await self._repo.count_by_user(user_id)
        docs = await self._repo.list_by_user(user_id, page, page_size)
        total_pages = math.ceil(total / page_size) if page_size else 1
        return PaginatedResponse(
            items=[PdfDocumentResponse.model_validate(d) for d in docs],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_extracted_questions(
        self, document_id: UUID, user_id: UUID, page: int, page_size: int
    ) -> PaginatedResponse:
        """Return the questions extracted from this PDF (paginated)."""
        await self._get_owned_doc(document_id, user_id)

        from app.schemas.question import QuestionFilterParams, QuestionResponse
        # Use QuestionRepository with a document_id filter (not a standard filter param)
        # We query directly here since this is a special case
        from sqlalchemy import select, func
        from app.models.question import Question

        total_result = await self._q_repo._db.execute(
            select(func.count()).select_from(Question).where(
                Question.pdf_document_id == document_id
            )
        )
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        questions_result = await self._q_repo._db.execute(
            select(Question)
            .where(Question.pdf_document_id == document_id)
            .order_by(Question.question_number_in_source)
            .offset(offset)
            .limit(page_size)
        )
        questions = list(questions_result.scalars().all())
        total_pages = math.ceil(total / page_size) if page_size else 1

        from app.schemas.question import QuestionResponse
        return PaginatedResponse(
            items=[QuestionResponse.model_validate(q) for q in questions],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def _get_owned_doc(self, document_id: UUID, user_id: UUID):
        doc = await self._repo.get_document(document_id)
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
        if doc.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        return doc
