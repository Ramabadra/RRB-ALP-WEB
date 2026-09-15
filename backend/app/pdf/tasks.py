"""
PDF processing Celery task — the full pipeline for one uploaded document.

Pipeline stages (matches PDF_JOB_STATUSES in the model):
  QUEUED → PROCESSING → EXTRACTING → [OCR] → PARSING → VALIDATING → COMPLETED
                                                                       ↓ on error
                                                                     FAILED

Each stage updates progress_pct and current_stage in the DB so the frontend
can poll GET /api/pdfs/{id}/status to show a real-time progress bar.

IMPORTANT: This task runs in a Celery worker (sync), not in the async FastAPI
process. It uses a synchronous SQLAlchemy session (not AsyncSession).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy.orm import Session

from app.database.sync_session import get_sync_db_session
from app.models.pdf import PdfDocument, PdfProcessingJob
from app.models.question import Question
from app.pdf.extractor import PDFExtractor
from app.pdf.parser import QuestionParser
from app.storage.client import StorageClient

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _update_job(
    session: Session,
    job: PdfProcessingJob,
    *,
    status: str | None = None,
    progress_pct: float | None = None,
    current_stage: str | None = None,
    error_message: str | None = None,
    result_json: dict | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> None:
    """Update a processing job row in one call."""
    if status is not None:
        job.status = status
    if progress_pct is not None:
        job.progress_pct = progress_pct
    if current_stage is not None:
        job.current_stage = current_stage
    if error_message is not None:
        job.error_message = error_message
    if result_json is not None:
        job.result_json = result_json
    if started_at is not None:
        job.started_at = started_at
    if completed_at is not None:
        job.completed_at = completed_at
    session.commit()


@shared_task(
    name="app.pdf.tasks.process_pdf",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
)
def process_pdf(
    self,
    document_id: str,
    job_id: str,
) -> dict:
    """
    Process an uploaded PDF end-to-end.

    Args:
        document_id: UUID string of the PdfDocument record.
        job_id: UUID string of the PdfProcessingJob record.

    Returns:
        Summary dict with extracted/stored counts.
    """
    doc_uuid = uuid.UUID(document_id)
    job_uuid = uuid.UUID(job_id)

    with get_sync_db_session() as session:
        job = session.get(PdfProcessingJob, job_uuid)
        doc = session.get(PdfDocument, doc_uuid)

        if job is None or doc is None:
            logger.error("Missing DB records: job=%s doc=%s", job_id, document_id)
            return {"error": "DB records not found"}

        try:
            # ── Stage: PROCESSING ──────────────────────────────────────────────
            _update_job(
                session, job,
                status="PROCESSING",
                started_at=_utcnow(),
                progress_pct=5.0,
                current_stage="Downloading from storage",
            )

            storage = StorageClient()
            pdf_bytes = storage.download_pdf(doc.storage_key)
            logger.info("Downloaded %d bytes for doc %s", len(pdf_bytes), document_id)

            # ── Stage: EXTRACTING ─────────────────────────────────────────────
            _update_job(session, job, status="EXTRACTING", progress_pct=15.0, current_stage="Extracting text")

            extractor = PDFExtractor()
            extraction = extractor.extract(pdf_bytes)

            # Update page count
            doc.page_count = extraction.page_count
            session.commit()

            if extraction.used_ocr:
                _update_job(session, job, status="OCR", progress_pct=40.0, current_stage="OCR processing")
                logger.info("Used OCR for doc %s", document_id)

            # ── Stage: PARSING ────────────────────────────────────────────────
            _update_job(session, job, status="PARSING", progress_pct=60.0, current_stage="Parsing questions")

            parser = QuestionParser()
            page_texts = [(p.page_number, p.text) for p in extraction.pages]
            parse_result = parser.parse(extraction.full_text, page_texts)

            doc.questions_extracted = parse_result.total_extracted
            session.commit()

            logger.info(
                "Parsed %d questions, %d with answers for doc %s",
                parse_result.total_extracted,
                parse_result.total_with_answers,
                document_id,
            )

            # ── Stage: VALIDATING ─────────────────────────────────────────────
            _update_job(session, job, status="VALIDATING", progress_pct=75.0, current_stage="Storing questions")

            stored_count = 0
            skipped_count = 0

            for pq in parse_result.questions:
                # Skip very low confidence questions
                if pq.confidence < 0.3:
                    skipped_count += 1
                    continue

                # Skip questions with no correct answer unless it's a reference
                if pq.correct_answer is None:
                    skipped_count += 1
                    continue

                q = Question(
                    question_text=pq.question_text,
                    option_a=pq.option_a,
                    option_b=pq.option_b,
                    option_c=pq.option_c,
                    option_d=pq.option_d,
                    correct_answer=pq.correct_answer,
                    source_type="PYQ",
                    source_exam=doc.exam_name,
                    source_year=doc.exam_year,
                    verification_status="NEEDS_REVIEW",
                    extraction_confidence=pq.confidence,
                    pdf_document_id=doc_uuid,
                    pdf_page_number=pq.page_number,
                    question_number_in_source=pq.source_number,
                )
                session.add(q)
                stored_count += 1

            session.commit()

            doc.questions_stored = stored_count
            session.commit()

            # ── Stage: COMPLETED ──────────────────────────────────────────────
            result_summary = {
                "total_extracted": parse_result.total_extracted,
                "total_stored": stored_count,
                "total_skipped": skipped_count,
                "total_with_answers": parse_result.total_with_answers,
                "used_ocr": extraction.used_ocr,
                "page_count": extraction.page_count,
                "parse_warnings": parse_result.parse_warnings[:50],  # Cap at 50 warnings
            }

            _update_job(
                session, job,
                status="COMPLETED",
                progress_pct=100.0,
                current_stage="Done",
                completed_at=_utcnow(),
                result_json=result_summary,
            )

            logger.info(
                "PDF processing COMPLETED: doc=%s stored=%d skipped=%d",
                document_id, stored_count, skipped_count,
            )
            return result_summary

        except Exception as exc:
            logger.exception("PDF processing FAILED for doc %s: %s", document_id, exc)

            try:
                # Best-effort — update job to FAILED status
                _update_job(
                    session, job,
                    status="FAILED",
                    progress_pct=0.0,
                    current_stage=None,
                    error_message=str(exc)[:500],  # Truncate to avoid huge error strings
                    completed_at=_utcnow(),
                )
            except Exception:
                pass  # If DB is down, we can't do much

            # Retry up to max_retries times
            raise self.retry(exc=exc)


@shared_task(
    name="app.pdf.tasks.validate_questions_batch",
    bind=True,
    max_retries=2,
)
def validate_questions_batch(self, question_ids: list[str]) -> dict:
    """
    Background task to validate a batch of questions using the AIValidator.
    """
    from app.ai.validator import AIValidator
    from app.models.subject import Subject
    
    success_count = 0
    fail_count = 0
    validator = AIValidator()
    
    with get_sync_db_session() as session:
        for q_id_str in question_ids:
            try:
                q_uuid = uuid.UUID(q_id_str)
                q = session.get(Question, q_uuid)
                if not q or q.verification_status == "VERIFIED":
                    continue
                
                ai_result = validator.validate_question(q)
                
                if not ai_result.is_valid:
                    q.verification_status = "REJECTED"
                    q.explanation = "AI marked this question as invalid or unreadable."
                else:
                    q.question_text = ai_result.question_text
                    q.option_a = ai_result.option_a
                    q.option_b = ai_result.option_b
                    q.option_c = ai_result.option_c
                    q.option_d = ai_result.option_d
                    q.correct_answer = ai_result.correct_answer
                    q.explanation = ai_result.explanation
                    q.verification_status = "VERIFIED"
                    
                    if ai_result.suggested_subject:
                        # Case-insensitive match for the subject
                        sub = session.query(Subject).filter(
                            Subject.name.ilike(ai_result.suggested_subject)
                        ).first()
                        if sub:
                            q.subject_id = sub.id

                session.commit()
                success_count += 1
                
            except Exception as e:
                logger.error("Failed to validate question %s: %s", q_id_str, e)
                session.rollback()
                fail_count += 1
                
    return {"success": success_count, "failed": fail_count}
