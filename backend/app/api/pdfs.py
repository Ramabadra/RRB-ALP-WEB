"""
PDFs router — upload, status polling, document listing, question review.

Routes:
  POST /api/pdfs/upload              → upload a PDF, get document_id + job_id
  GET  /api/pdfs                     → list user's uploaded PDFs (paginated)
  GET  /api/pdfs/{id}                → get document metadata
  GET  /api/pdfs/{id}/status         → poll processing job progress (0-100%)
  GET  /api/pdfs/{id}/questions      → list questions extracted from this PDF
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, File, Form, Query, UploadFile, status

from app.core.dependencies import CurrentUserId, DbSession
from app.core.config import get_settings
from app.schemas.common import PaginatedResponse
from app.schemas.pdf import (
    PdfDocumentResponse,
    PdfJobStatusResponse,
    PdfUploadResponse,
)
from app.services.pdf_service import PdfService

router = APIRouter(prefix="/pdfs", tags=["PDFs"])


@router.post(
    "/upload",
    response_model=PdfUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a PDF for processing",
    description=(
        "Uploads a PDF file (max 50 MB) to Supabase Storage, creates metadata "
        "records, and queues a background processing job.\n\n"
        "The response includes `document_id` and `job_id`. "
        "Poll `GET /api/pdfs/{id}/status` to track extraction progress.\n\n"
        "Optional metadata (`exam_name`, `exam_year`, `exam_shift`) helps the "
        "parser label extracted questions correctly."
    ),
)
async def upload_pdf(
    db: DbSession,
    user_id: CurrentUserId,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF file to upload"),
    exam_name: str | None = Form(None, description="e.g. 'RRB ALP 2024'"),
    exam_year: int | None = Form(None, description="e.g. 2024"),
    exam_shift: str | None = Form(None, description="e.g. 'Shift 1'"),
) -> PdfUploadResponse:
    settings = get_settings()
    service = PdfService(db)
    return await service.upload(
        user_id=user_id,
        file=file,
        background_tasks=background_tasks,
        exam_name=exam_name,
        exam_year=exam_year,
        exam_shift=exam_shift,
        max_size_bytes=settings.max_pdf_size_bytes,
    )


@router.get(
    "",
    response_model=PaginatedResponse,
    summary="List my uploaded PDFs",
)
async def list_pdfs(
    db: DbSession,
    user_id: CurrentUserId,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse:
    service = PdfService(db)
    return await service.list_documents(user_id, page, page_size)


@router.get(
    "/{pdf_id}",
    response_model=PdfDocumentResponse,
    summary="Get PDF document metadata",
)
async def get_pdf(
    pdf_id: UUID,
    db: DbSession,
    user_id: CurrentUserId,
) -> PdfDocumentResponse:
    service = PdfService(db)
    return await service.get_document(pdf_id, user_id)


@router.get(
    "/{pdf_id}/status",
    response_model=PdfJobStatusResponse,
    summary="Poll processing job status",
    description=(
        "Poll this endpoint to track PDF processing progress.\n\n"
        "`progress_pct`: 0–100 completion percentage.\n"
        "`current_stage`: human-readable current pipeline stage.\n"
        "`status`: one of QUEUED, PROCESSING, EXTRACTING, OCR, PARSING, "
        "VALIDATING, COMPLETED, FAILED.\n\n"
        "Recommended polling interval: 2 seconds while status != COMPLETED|FAILED."
    ),
)
async def get_pdf_status(
    pdf_id: UUID,
    db: DbSession,
    user_id: CurrentUserId,
) -> PdfJobStatusResponse:
    service = PdfService(db)
    return await service.get_status(pdf_id, user_id)


@router.get(
    "/{pdf_id}/questions",
    response_model=PaginatedResponse,
    summary="List questions extracted from this PDF",
    description=(
        "Returns the questions that were extracted and stored from this PDF. "
        "Ordered by their original question number in the source paper. "
        "All questions start with verification_status=NEEDS_REVIEW."
    ),
)
async def get_pdf_questions(
    pdf_id: UUID,
    db: DbSession,
    user_id: CurrentUserId,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse:
    service = PdfService(db)
    return await service.get_extracted_questions(pdf_id, user_id, page, page_size)
