"""
test_pdf_background_tasks.py
Real execution-path tests for the FastAPI BackgroundTasks PDF pipeline.

Tests the ACTUAL execution of process_pdf() without Celery, without Redis,
without real storage — using in-memory SQLite and mocked storage/extractor.

Covers:
  1. Happy path: BackgroundTasks registers + executes process_pdf → COMPLETED
  2. bind=True self-injection: Celery injects self; doc_id is NOT confused with self
  3. Failure path: storage failure → job FAILED in DB, error recorded
  4. Extraction failure → job FAILED with error_message
  5. Idempotency: COMPLETED job skipped, FAILED job retryable, in-flight blocked
  6. No duplicate questions when triggered twice on same job
"""

from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi import BackgroundTasks
from sqlalchemy import String, Text, TypeDecorator, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models.pdf import PdfDocument, PdfProcessingJob


# ─── SQLite-compatible TypeDecorators (mirrors conftest.py) ───────────────────

class GUIDType(TypeDecorator):
    impl = String(36)
    cache_ok = True
    def process_bind_param(self, v, d): return str(v) if v is not None else None
    def process_result_value(self, v, d): return uuid.UUID(str(v)) if v else None


class JSONType(TypeDecorator):
    impl = Text
    cache_ok = True
    def process_bind_param(self, v, d): return json.dumps(v) if v is not None else None
    def process_result_value(self, v, d): return json.loads(v) if v else None


def _patch_metadata_types():
    """Replace PG-specific column types with SQLite-safe ones (in-place, idempotent)."""
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
    for table in Base.metadata.tables.values():
        for col in table.columns:
            if isinstance(col.type, PG_UUID):
                col.type = GUIDType()
            elif isinstance(col.type, JSONB):
                col.type = JSONType()


_patch_metadata_types()


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def sync_engine():
    engine = create_engine(
        "sqlite:///:memory:", 
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def sync_session(sync_engine):
    factory = sessionmaker(bind=sync_engine, autocommit=False, autoflush=True)
    session = factory()
    yield session
    session.rollback()
    session.close()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _seed_doc_and_job(session: Session, job_status: str = "QUEUED"):
    doc = PdfDocument(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        original_filename="test.pdf",
        storage_key=f"pdfs/test/{uuid.uuid4()}/test.pdf",
        file_size_bytes=1024,
        mime_type="application/pdf",
    )
    job = PdfProcessingJob(
        id=uuid.uuid4(),
        pdf_document_id=doc.id,
        status=job_status,
    )
    session.add_all([doc, job])
    session.commit()
    return doc, job


def _refresh(session: Session, obj):
    session.expire(obj)
    session.refresh(obj)
    return obj


def _make_extraction(used_ocr: bool = False):
    page = MagicMock()
    page.page_number = 1
    page.text = "Q1. Sample? A)a B)b C)c D)d\nAnswer: A"
    extraction = MagicMock()
    extraction.pages = [page]
    extraction.full_text = page.text
    extraction.page_count = 1
    extraction.used_ocr = used_ocr
    return extraction


def _make_parse_result(n: int = 2):
    pqs = []
    for i in range(n):
        pq = MagicMock()
        pq.question_text = f"Q{i+1}?"
        pq.option_a, pq.option_b, pq.option_c, pq.option_d = "A", "B", "C", "D"
        pq.correct_answer = "A"
        pq.confidence = 0.9
        pq.page_number = 1
        pq.source_number = i + 1
        pqs.append(pq)
    result = MagicMock()
    result.questions = pqs
    result.total_extracted = n
    result.total_with_answers = n
    result.parse_warnings = []
    return result


def _fake_session_factory(session: Session):
    """Return a fake get_sync_db_session that yields the given session."""
    @contextmanager
    def _ctx():
        yield session
        session.flush()
    return _ctx


def _run_bt(bt: BackgroundTasks):
    """Run BackgroundTasks synchronously (works on Python 3.14)."""
    asyncio.run(bt())


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestBackgroundTasksExecutionPath:

    def test_happy_path_queued_to_completed(self, sync_session):
        """
        PROVES: BackgroundTasks.add_task(process_pdf, doc_id, job_id) executes
        process_pdf end-to-end and leaves the job in COMPLETED state with
        questions saved and result_json populated.
        """
        doc, job = _seed_doc_and_job(sync_session, "QUEUED")

        mock_storage = MagicMock()
        mock_storage.download_pdf.return_value = b"%PDF-1.4 fake"

        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = _make_extraction()

        mock_parser = MagicMock()
        mock_parser.parse.return_value = _make_parse_result(n=2)

        from app.pdf.tasks import process_pdf

        with (
            patch("app.pdf.tasks.get_sync_db_session", _fake_session_factory(sync_session)),
            patch("app.pdf.tasks.StorageClient", return_value=mock_storage),
            patch("app.pdf.tasks.PDFExtractor", return_value=mock_extractor),
            patch("app.pdf.tasks.QuestionParser", return_value=mock_parser),
        ):
            bt = BackgroundTasks()
            bt.add_task(process_pdf, str(doc.id), str(job.id))
            _run_bt(bt)

        _refresh(sync_session, job)
        assert job.status == "COMPLETED"
        assert job.progress_pct == 100.0
        assert job.result_json["total_stored"] == 2
        assert job.started_at is not None
        assert job.completed_at is not None

    def test_bind_true_self_injection_is_not_confused_with_doc_id(self):
        """
        PROVES: Celery's bind=True machinery injects `self` automatically.
        BackgroundTasks passes (doc_id, job_id) as positional args — these
        must NOT be shifted into self, which would silently corrupt the call.
        """
        from celery import shared_task

        received = {}

        @shared_task(bind=True)
        def probe(self, doc_id: str, job_id: str):
            received["self_is_str"] = isinstance(self, str)
            received["doc_id"] = doc_id
            received["job_id"] = job_id

        bt = BackgroundTasks()
        bt.add_task(probe, "doc-111", "job-222")
        _run_bt(bt)

        assert received["doc_id"] == "doc-111", "doc_id was not received"
        assert received["job_id"] == "job-222", "job_id was not received"
        assert not received["self_is_str"], (
            "CRITICAL: self received the doc_id string — "
            "bind=True injection broken, process_pdf will call uuid.UUID() on "
            "a task instance and crash at runtime"
        )


class TestFailurePath:

    def test_storage_failure_sets_job_to_failed_with_error_message(self, sync_session):
        """
        PROVES: When storage download raises, the job is updated to FAILED
        in the DB with the error message recorded. The DB state is correct
        even though the exception propagates out of the background thread.
        """
        doc, job = _seed_doc_and_job(sync_session, "QUEUED")

        mock_storage = MagicMock()
        mock_storage.download_pdf.side_effect = ConnectionError("Supabase Storage unreachable")

        from app.pdf.tasks import process_pdf

        with (
            patch("app.pdf.tasks.get_sync_db_session", _fake_session_factory(sync_session)),
            patch("app.pdf.tasks.StorageClient", return_value=mock_storage),
        ):
            bt = BackgroundTasks()
            bt.add_task(process_pdf, str(doc.id), str(job.id))
            try:
                _run_bt(bt)
            except Exception:
                # asyncio.run re-raises the exception in unit-test context.
                # In production Starlette logs it and moves on — server stays alive.
                pass

        _refresh(sync_session, job)
        assert job.status == "FAILED", f"Expected FAILED, got {job.status}"
        assert job.error_message is not None
        assert "Supabase Storage unreachable" in job.error_message
        assert len(job.error_message) <= 500

    def test_extraction_failure_sets_failed_with_descriptive_error(self, sync_session):
        """Extraction errors are recorded with a descriptive message, not a stack trace."""
        doc, job = _seed_doc_and_job(sync_session, "QUEUED")

        mock_storage = MagicMock()
        mock_storage.download_pdf.return_value = b"%PDF-1.4 ok"

        mock_extractor = MagicMock()
        mock_extractor.extract.side_effect = ValueError("PDF is encrypted and cannot be parsed")

        from app.pdf.tasks import process_pdf

        with (
            patch("app.pdf.tasks.get_sync_db_session", _fake_session_factory(sync_session)),
            patch("app.pdf.tasks.StorageClient", return_value=mock_storage),
            patch("app.pdf.tasks.PDFExtractor", return_value=mock_extractor),
        ):
            try:
                process_pdf(str(doc.id), str(job.id))
            except Exception:
                pass

        _refresh(sync_session, job)
        assert job.status == "FAILED"
        assert "encrypted" in (job.error_message or "")


class TestIdempotency:

    def test_completed_job_is_skipped_without_touching_storage(self, sync_session):
        """COMPLETED jobs must be short-circuited before any storage call."""
        doc, job = _seed_doc_and_job(sync_session, "COMPLETED")

        call_counts = {"storage": 0}
        mock_storage = MagicMock()
        mock_storage.download_pdf.side_effect = lambda k: (
            call_counts.__setitem__("storage", call_counts["storage"] + 1) or b"%PDF"
        )

        from app.pdf.tasks import process_pdf

        with (
            patch("app.pdf.tasks.get_sync_db_session", _fake_session_factory(sync_session)),
            patch("app.pdf.tasks.StorageClient", return_value=mock_storage),
        ):
            result = process_pdf(str(doc.id), str(job.id))

        assert result == {"status": "skipped", "reason": "already COMPLETED"}
        assert call_counts["storage"] == 0

    def test_failed_job_is_retryable_not_blocked(self, sync_session):
        """
        FAILED jobs must NOT be in the skip list.
        An admin re-triggering a failed job must be able to re-process it.
        This is the corrected behaviour after removing FAILED from the guard.
        """
        doc, job = _seed_doc_and_job(sync_session, "FAILED")

        mock_storage = MagicMock()
        mock_storage.download_pdf.return_value = b"%PDF-1.4 ok"

        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = _make_extraction()

        mock_parser = MagicMock()
        mock_parser.parse.return_value = _make_parse_result(n=1)

        from app.pdf.tasks import process_pdf

        with (
            patch("app.pdf.tasks.get_sync_db_session", _fake_session_factory(sync_session)),
            patch("app.pdf.tasks.StorageClient", return_value=mock_storage),
            patch("app.pdf.tasks.PDFExtractor", return_value=mock_extractor),
            patch("app.pdf.tasks.QuestionParser", return_value=mock_parser),
        ):
            result = process_pdf(str(doc.id), str(job.id))

        _refresh(sync_session, job)
        assert job.status == "COMPLETED", (
            f"FAILED job should be retryable and finish as COMPLETED, got {job.status}"
        )

    @pytest.mark.parametrize("in_flight_status", [
        "PROCESSING", "EXTRACTING", "OCR", "PARSING", "VALIDATING"
    ])
    def test_in_flight_job_is_blocked(self, sync_session, in_flight_status):
        """Jobs already in an active pipeline stage must not be started again."""
        doc, job = _seed_doc_and_job(sync_session, in_flight_status)

        from app.pdf.tasks import process_pdf

        with patch("app.pdf.tasks.get_sync_db_session", _fake_session_factory(sync_session)):
            result = process_pdf(str(doc.id), str(job.id))

        assert result["status"] == "skipped", (
            f"In-flight status {in_flight_status} should be skipped, got {result}"
        )

    def test_no_duplicate_questions_on_double_invocation(self, sync_session):
        """
        Calling process_pdf twice on the same job must not create duplicate questions.
        The first call moves status → COMPLETED; the second call sees COMPLETED and skips.
        """
        from app.models.question import Question

        doc, job = _seed_doc_and_job(sync_session, "QUEUED")

        mock_storage = MagicMock()
        mock_storage.download_pdf.return_value = b"%PDF-1.4 ok"

        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = _make_extraction()

        mock_parser = MagicMock()
        mock_parser.parse.return_value = _make_parse_result(n=3)

        from app.pdf.tasks import process_pdf

        with (
            patch("app.pdf.tasks.get_sync_db_session", _fake_session_factory(sync_session)),
            patch("app.pdf.tasks.StorageClient", return_value=mock_storage),
            patch("app.pdf.tasks.PDFExtractor", return_value=mock_extractor),
            patch("app.pdf.tasks.QuestionParser", return_value=mock_parser),
        ):
            process_pdf(str(doc.id), str(job.id))   # First: QUEUED → COMPLETED
            process_pdf(str(doc.id), str(job.id))   # Second: sees COMPLETED → skipped

        q_count = sync_session.query(Question).filter(
            Question.pdf_document_id == doc.id
        ).count()
        assert q_count == 3, (
            f"Expected exactly 3 questions (no duplicates), got {q_count}"
        )
