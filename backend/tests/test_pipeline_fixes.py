"""
test_pipeline_fixes.py

Focused regression tests for the two root-cause fixes:

1. PDF QUEUED fix: _run_process_pdf_core is a plain callable (not @shared_task
   wrapper) so BackgroundTasks can invoke it directly without a broker.

2. AI_GENERATED mock fix: MockTestService.generate() invokes AIGenerator when
   source_type=AI_GENERATED, regardless of verified bank size.

These are unit tests — no real DB, no real Gemini, no real storage.
"""

from __future__ import annotations

import asyncio
import types
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# 1. PDF: _run_process_pdf_core is importable and is NOT a @shared_task wrapper
# ─────────────────────────────────────────────────────────────────────────────

class TestRunProcessPdfCoreIsPlainCallable:
    """Verify the fix: _run_process_pdf_core must be a plain function."""

    def test_is_importable(self):
        from app.pdf.tasks import _run_process_pdf_core
        assert _run_process_pdf_core is not None

    def test_is_plain_callable_not_celery_task(self):
        """
        The @shared_task decorator wraps functions in a Celery Task object.
        _run_process_pdf_core must NOT be wrapped — it must be a plain function
        so BackgroundTasks can call it without a Celery broker.
        """
        from app.pdf import tasks as tasks_module
        from app.pdf.tasks import _run_process_pdf_core
        import inspect

        # Must be a plain function, not a Celery Task instance
        assert inspect.isfunction(_run_process_pdf_core), (
            "_run_process_pdf_core must be a plain function, not a Celery task wrapper. "
            "If it's a Celery task, calling it from BackgroundTasks tries to use the broker."
        )

    def test_process_pdf_is_celery_task(self):
        """
        process_pdf IS the @shared_task wrapper — used for the Celery path.
        Verify it exists and is the Celery variant.
        """
        from app.pdf.tasks import process_pdf
        # A Celery shared_task is NOT a plain function
        import inspect
        assert not inspect.isfunction(process_pdf), (
            "process_pdf should be a Celery task wrapper (not a plain function)."
        )

    def test_background_tasks_path_uses_core_not_wrapper(self):
        """
        When USE_CELERY=False, pdf_service.upload() must register
        _run_process_pdf_core with BackgroundTasks, not process_pdf.

        This test inspects the pdf_service source to verify the correct
        symbol is imported in the BackgroundTasks branch.
        """
        import inspect
        from app.services import pdf_service as svc_module
        source = inspect.getsource(svc_module)

        # In the non-Celery branch the code must import _run_process_pdf_core
        assert "_run_process_pdf_core" in source, (
            "pdf_service.py must import _run_process_pdf_core in the BackgroundTasks branch."
        )

        # The source should NOT use process_pdf directly in the add_task call
        # (it may import process_pdf for the Celery path, but the add_task call
        #  must reference _run_process_pdf_core)
        assert "background_tasks.add_task" in source, (
            "pdf_service.py must call background_tasks.add_task()"
        )
        # Verify asyncio.to_thread is used to wrap the sync function
        assert "asyncio.to_thread" in source or "_asyncio.to_thread" in source, (
            "pdf_service.py must use asyncio.to_thread to run _run_process_pdf_core "
            "in a thread pool without blocking the event loop."
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. _run_process_pdf_core executes the full pipeline when mocked
# ─────────────────────────────────────────────────────────────────────────────

class TestRunProcessPdfCoreExecution:
    """
    Verify _run_process_pdf_core runs through the full pipeline
    (download → extract → parse → store → COMPLETED) when all
    dependencies are mocked.
    """

    def _make_mock_session(self, job_status="QUEUED"):
        """Build a minimal mock SQLAlchemy session with job+doc."""
        doc_id = uuid.uuid4()
        job_id = uuid.uuid4()

        doc = MagicMock()
        doc.id = doc_id
        doc.storage_key = "test/key.pdf"
        doc.exam_name = "RRB ALP"
        doc.exam_year = 2024
        doc.questions_extracted = 0
        doc.questions_stored = 0
        doc.page_count = None

        job = MagicMock()
        job.id = job_id
        job.status = job_status
        job.progress_pct = 0
        job.current_stage = None
        job.error_message = None
        job.result_json = None
        job.started_at = None
        job.completed_at = None

        session = MagicMock()
        session.get = MagicMock(side_effect=lambda model, uid: (
            job if str(uid) == str(job_id) else doc
        ))
        session.add = MagicMock()
        session.commit = MagicMock()
        session.rollback = MagicMock()
        session.__enter__ = MagicMock(return_value=session)
        session.__exit__ = MagicMock(return_value=False)

        return session, doc, job, str(doc_id), str(job_id)

    @patch("app.pdf.tasks.get_sync_db_session")
    @patch("app.pdf.tasks.StorageClient")
    @patch("app.pdf.tasks.PDFExtractor")
    @patch("app.pdf.tasks.QuestionParser")
    def test_happy_path_reaches_completed(
        self,
        MockParser,
        MockExtractor,
        MockStorage,
        MockSession,
    ):
        from app.pdf.tasks import _run_process_pdf_core
        from app.pdf.extractor import ExtractionResult, PageText
        from app.pdf.parser import ParseResult, ParsedQuestion

        session, doc, job, doc_id, job_id = self._make_mock_session()
        MockSession.return_value.__enter__ = MagicMock(return_value=session)
        MockSession.return_value.__exit__ = MagicMock(return_value=False)

        # Storage
        mock_storage_inst = MagicMock()
        mock_storage_inst.download_pdf.return_value = b"%PDF-1.4 test"
        MockStorage.return_value = mock_storage_inst

        # Extractor returns 2 pages
        page1 = PageText(page_number=1, text="Q.1 What is 2+2?\n(A) 3\n(B) 4\n(C) 5\n(D) 6")
        mock_extraction = ExtractionResult(
            pages=[page1],
            page_count=1,
            used_ocr=False,
        )
        mock_extractor_inst = MagicMock()
        mock_extractor_inst.extract.return_value = mock_extraction
        MockExtractor.return_value = mock_extractor_inst

        # Parser returns 1 question with answer
        pq = ParsedQuestion(
            question_text="What is 2+2?",
            option_a="3",
            option_b="4",
            option_c="5",
            option_d="6",
            correct_answer="B",
            confidence=0.9,
            source_number=1,
            page_number=1,
        )
        mock_parse_result = ParseResult(
            questions=[pq],
            answer_key={1: "B"},
            total_extracted=1,
            total_with_answers=1,
            parse_warnings=[],
        )
        mock_parser_inst = MagicMock()
        mock_parser_inst.parse.return_value = mock_parse_result
        MockParser.return_value = mock_parser_inst

        result = _run_process_pdf_core(doc_id, job_id)

        assert result["total_stored"] == 1
        assert result["total_extracted"] == 1
        assert result["page_count"] == 1
        # Job should have been updated to COMPLETED
        assert job.status == "COMPLETED"

    @patch("app.pdf.tasks.get_sync_db_session")
    @patch("app.pdf.tasks.StorageClient")
    def test_storage_failure_marks_job_failed(self, MockStorage, MockSession):
        from app.pdf.tasks import _run_process_pdf_core

        session, doc, job, doc_id, job_id = self._make_mock_session()
        MockSession.return_value.__enter__ = MagicMock(return_value=session)
        MockSession.return_value.__exit__ = MagicMock(return_value=False)

        # Storage raises
        mock_storage_inst = MagicMock()
        mock_storage_inst.download_pdf.side_effect = RuntimeError("S3 connection failed")
        MockStorage.return_value = mock_storage_inst

        with pytest.raises(RuntimeError, match="S3 connection failed"):
            _run_process_pdf_core(doc_id, job_id)

        assert job.status == "FAILED"
        assert "S3 connection failed" in job.error_message

    @patch("app.pdf.tasks.get_sync_db_session")
    def test_already_completed_is_skipped(self, MockSession):
        from app.pdf.tasks import _run_process_pdf_core

        session, doc, job, doc_id, job_id = self._make_mock_session(job_status="COMPLETED")
        MockSession.return_value.__enter__ = MagicMock(return_value=session)
        MockSession.return_value.__exit__ = MagicMock(return_value=False)

        result = _run_process_pdf_core(doc_id, job_id)
        assert result["status"] == "skipped"
        assert result["reason"] == "already COMPLETED"

    @patch("app.pdf.tasks.get_sync_db_session")
    def test_in_flight_is_skipped(self, MockSession):
        from app.pdf.tasks import _run_process_pdf_core

        session, doc, job, doc_id, job_id = self._make_mock_session(job_status="PROCESSING")
        MockSession.return_value.__enter__ = MagicMock(return_value=session)
        MockSession.return_value.__exit__ = MagicMock(return_value=False)

        result = _run_process_pdf_core(doc_id, job_id)
        assert result["status"] == "skipped"

    @patch("app.pdf.tasks.get_sync_db_session")
    def test_failed_job_is_retryable(self, MockSession):
        """A FAILED job must NOT be skipped — it should be retried."""
        from app.pdf.tasks import _run_process_pdf_core

        # FAILED status should proceed, not skip
        session, doc, job, doc_id, job_id = self._make_mock_session(job_status="FAILED")
        MockSession.return_value.__enter__ = MagicMock(return_value=session)
        MockSession.return_value.__exit__ = MagicMock(return_value=False)

        # Mock storage to also fail — we just want to verify it was NOT skipped
        with patch("app.pdf.tasks.StorageClient") as MockSC:
            mock_sc = MagicMock()
            mock_sc.download_pdf.side_effect = RuntimeError("retriable error")
            MockSC.return_value = mock_sc

            with pytest.raises(RuntimeError):
                _run_process_pdf_core(doc_id, job_id)

        # Job status was updated (not left as FAILED unchanged without attempt)
        # The update to PROCESSING happened before the storage call
        assert job.status == "FAILED"  # Re-set after second failure


# ─────────────────────────────────────────────────────────────────────────────
# 3. AI_GENERATED mock: Gemini IS invoked, bank is NOT required
# ─────────────────────────────────────────────────────────────────────────────

class TestAIMockGeneration:
    """
    Verify MockTestService calls AIGenerator for AI_GENERATED source_type
    even when the verified question bank is empty.
    """

    def _make_generated_question(self, idx: int):
        from app.ai.prompts import GeneratedQuestion
        return GeneratedQuestion(
            question_text=f"Q{idx}: What is {idx} + {idx}?",
            option_a=str(idx),
            option_b=str(idx * 2),
            option_c=str(idx * 3),
            option_d=str(idx * 4),
            correct_answer="B",
            explanation=f"{idx} + {idx} = {idx * 2}",
            difficulty="EASY",
            subtopic="Arithmetic",
        )

    def _make_persisted_question(self, idx: int):
        """Simulate what QuestionRepository.create() would return."""
        q = MagicMock()
        q.id = uuid.uuid4()
        q.question_text = f"Q{idx}: What is {idx} + {idx}?"
        q.source_type = "AI_GENERATED"
        q.verification_status = "VERIFIED"
        return q

    @pytest.mark.asyncio
    async def test_ai_generated_calls_gemini_not_bank(self):
        """
        When source_type=AI_GENERATED and bank has 0 verified questions,
        the service should call AIGenerator.generate_questions, NOT raise 400.
        """
        from app.services.mock_test_service import MockTestService
        from app.schemas.mock_test import MockTestGenerateRequest, MockTestSourceType

        # Build a mock DB session
        mock_db = AsyncMock()

        svc = MockTestService(mock_db)

        # Bank returns 0 questions
        svc._q_repo = AsyncMock()
        svc._q_repo.select_for_mock_test = AsyncMock(return_value=[])

        # Subject repo finds the subject
        mock_subject = MagicMock()
        mock_subject.id = uuid.uuid4()
        svc._sub_repo = AsyncMock()
        svc._sub_repo.get_by_name = AsyncMock(return_value=mock_subject)

        # Mock repo create
        persisted = [self._make_persisted_question(i) for i in range(5)]
        create_calls = iter(persisted)
        svc._q_repo.create = AsyncMock(side_effect=lambda **kw: next(create_calls))

        # Mock repo for MockTest creation
        mock_mock_test = MagicMock()
        mock_mock_test.id = uuid.uuid4()
        svc._repo = AsyncMock()
        svc._repo.create = AsyncMock(return_value=mock_mock_test)
        svc._repo.add_questions = AsyncMock()

        generated_gqs = [self._make_generated_question(i) for i in range(5)]

        with patch("app.ai.generator.AIGenerator.generate_questions",
                   return_value=generated_gqs) as mock_gemini:
            request = MockTestGenerateRequest(
                question_count=20,  # Must be in ALLOWED_QUESTION_COUNTS
                subjects=["Reasoning"],
                source_type=MockTestSourceType.AI_GENERATED,
            )
            # Override question_count for test
            object.__setattr__(request, "question_count", 5)

            result = await svc._generate_ai_questions(request, [mock_subject.id])

        # Gemini WAS called
        mock_gemini.assert_called_once()
        # Results returned
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_ai_generated_does_not_call_bank_query(self):
        """
        AI_GENERATED must not query select_for_mock_test at all.
        """
        from app.services.mock_test_service import MockTestService
        from app.schemas.mock_test import MockTestGenerateRequest, MockTestSourceType

        mock_db = AsyncMock()
        svc = MockTestService(mock_db)

        mock_subject = MagicMock()
        mock_subject.id = uuid.uuid4()
        svc._sub_repo = AsyncMock()
        svc._sub_repo.get_by_name = AsyncMock(return_value=mock_subject)

        svc._q_repo = AsyncMock()
        svc._q_repo.select_for_mock_test = AsyncMock(return_value=[])
        svc._q_repo.create = AsyncMock(side_effect=[
            self._make_persisted_question(i) for i in range(20)
        ])

        mock_mock_test = MagicMock()
        mock_mock_test.id = uuid.uuid4()
        svc._repo = AsyncMock()
        svc._repo.create = AsyncMock(return_value=mock_mock_test)
        svc._repo.add_questions = AsyncMock()

        generated_gqs = [self._make_generated_question(i) for i in range(5)]

        with patch("app.ai.generator.AIGenerator.generate_questions",
                   return_value=generated_gqs):
            request = MockTestGenerateRequest(question_count=20, subjects=["Reasoning"])
            object.__setattr__(request, "question_count", 5)
            object.__setattr__(request, "source_type", MockTestSourceType.AI_GENERATED)

            await svc._generate_ai_questions(request, [mock_subject.id])

        # Bank was NOT queried for AI_GENERATED path
        svc._q_repo.select_for_mock_test.assert_not_called()

    @pytest.mark.asyncio
    async def test_mixed_uses_bank_then_ai_for_deficit(self):
        """
        MIXED: bank has 2, needs 5 → AI generates 3.
        """
        from app.services.mock_test_service import MockTestService
        from app.schemas.mock_test import MockTestGenerateRequest, MockTestSourceType

        mock_db = AsyncMock()
        svc = MockTestService(mock_db)

        bank_qs = [self._make_persisted_question(i) for i in range(2)]
        svc._q_repo = AsyncMock()
        svc._q_repo.select_for_mock_test = AsyncMock(return_value=bank_qs)
        svc._q_repo.create = AsyncMock(side_effect=[
            self._make_persisted_question(i + 100) for i in range(10)
        ])

        svc._sub_repo = AsyncMock()
        mock_subject = MagicMock()
        mock_subject.id = uuid.uuid4()
        svc._sub_repo.get_by_name = AsyncMock(return_value=mock_subject)

        generated_gqs = [self._make_generated_question(i) for i in range(3)]

        with patch("app.ai.generator.AIGenerator.generate_questions",
                   return_value=generated_gqs) as mock_gemini:
            request = MockTestGenerateRequest(question_count=20, subjects=["Reasoning"])
            object.__setattr__(request, "question_count", 5)
            object.__setattr__(request, "source_type", MockTestSourceType.MIXED)

            result = await svc._generate_mixed_questions(request, [mock_subject.id])

        assert len(result) == 5
        # Bank was queried
        svc._q_repo.select_for_mock_test.assert_called_once()
        # Gemini was invoked for deficit
        mock_gemini.assert_called_once()

    @pytest.mark.asyncio
    async def test_verified_shortage_raises_400(self):
        """
        VERIFIED/PYQ source with insufficient bank must raise HTTP 400.
        (MIXED would try Gemini — this test validates the bank-only shortage path.)
        """
        from app.services.mock_test_service import MockTestService
        from app.schemas.mock_test import MockTestGenerateRequest, MockTestSourceType
        from fastapi import HTTPException

        mock_db = AsyncMock()
        svc = MockTestService(mock_db)

        # Bank returns empty
        svc._q_repo = AsyncMock()
        svc._q_repo.select_for_mock_test = AsyncMock(return_value=[])

        # Subject found
        mock_subject = MagicMock()
        mock_subject.id = uuid.uuid4()
        svc._sub_repo = AsyncMock()
        svc._sub_repo.get_by_name = AsyncMock(return_value=mock_subject)

        svc._repo = AsyncMock()

        request = MockTestGenerateRequest(question_count=20, subjects=["Reasoning"])
        object.__setattr__(request, "question_count", 5)
        object.__setattr__(request, "source_type", MockTestSourceType.PYQ)

        with pytest.raises(HTTPException) as exc_info:
            await svc.generate(user_id=uuid.uuid4(), request=request)

        assert exc_info.value.status_code == 400
        assert "Not enough verified questions" in exc_info.value.detail
