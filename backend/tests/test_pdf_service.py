"""
Phase 5 integration tests: PdfService — with mocked storage and Celery.

We mock:
- StorageClient.upload_pdf → returns (storage_key, presigned_url)
- process_pdf.delay → no-op (Celery not running in tests)

DB operations use the real in-memory SQLite session.
"""

from __future__ import annotations

import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.services.pdf_service import PdfService


# Minimal valid PDF bytes (just the magic header — enough to pass validation)
VALID_PDF_BYTES = b"%PDF-1.4 minimal test pdf content"
EMPTY_PDF_BYTES = b""
NOT_PDF_BYTES = b"This is not a PDF file at all"


def _make_upload_file(
    filename: str = "test.pdf",
    content: bytes = VALID_PDF_BYTES,
    content_type: str = "application/pdf",
):
    """Create a mock UploadFile for testing."""
    from unittest.mock import AsyncMock, MagicMock
    upload_file = MagicMock()
    upload_file.filename = filename
    upload_file.content_type = content_type
    upload_file.read = AsyncMock(return_value=content)
    return upload_file


class TestPdfServiceValidation:
    """Test upload validation without any real storage calls."""

    @pytest.mark.asyncio
    async def test_empty_file_raises_400(self, db_session):
        service = PdfService(db_session)
        file = _make_upload_file(content=EMPTY_PDF_BYTES)

        with pytest.raises(HTTPException) as exc_info:
            await service.upload(
                user_id=uuid.uuid4(),
                file=file,
                background_tasks=BackgroundTasks(),
                exam_name=None, exam_year=None, exam_shift=None,
                max_size_bytes=50 * 1024 * 1024,
            )
        assert exc_info.value.status_code == 400
        assert "empty" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_file_too_large_raises_413(self, db_session):
        service = PdfService(db_session)
        # 1 byte max but sending 100 bytes
        file = _make_upload_file(content=VALID_PDF_BYTES)

        with pytest.raises(HTTPException) as exc_info:
            await service.upload(
                user_id=uuid.uuid4(),
                file=file,
                background_tasks=BackgroundTasks(),
                exam_name=None, exam_year=None, exam_shift=None,
                max_size_bytes=1,  # 1 byte max
            )
        assert exc_info.value.status_code == 413

    @pytest.mark.asyncio
    async def test_invalid_mime_type_raises_415(self, db_session):
        service = PdfService(db_session)
        file = _make_upload_file(content=VALID_PDF_BYTES, content_type="text/plain")

        with pytest.raises(HTTPException) as exc_info:
            await service.upload(
                user_id=uuid.uuid4(),
                file=file,
                background_tasks=BackgroundTasks(),
                exam_name=None, exam_year=None, exam_shift=None,
                max_size_bytes=50 * 1024 * 1024,
            )
        assert exc_info.value.status_code == 415

    @pytest.mark.asyncio
    async def test_invalid_magic_bytes_raises_400(self, db_session):
        service = PdfService(db_session)
        file = _make_upload_file(content=NOT_PDF_BYTES)  # No %PDF header

        with pytest.raises(HTTPException) as exc_info:
            await service.upload(
                user_id=uuid.uuid4(),
                file=file,
                background_tasks=BackgroundTasks(),
                exam_name=None, exam_year=None, exam_shift=None,
                max_size_bytes=50 * 1024 * 1024,
            )
        assert exc_info.value.status_code == 400
        assert "magic bytes" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_successful_upload_creates_db_records(self, db_session):
        service = PdfService(db_session)
        file = _make_upload_file()
        user_id = uuid.uuid4()

        mock_storage = MagicMock()
        mock_storage.upload_pdf.return_value = (
            f"pdfs/{user_id}/test-doc-id/test.pdf",
            "https://presigned-url.example.com/test.pdf",
        )

        with (
            patch("app.services.pdf_service.StorageClient", return_value=mock_storage),
            patch("app.pdf.tasks.process_pdf") as mock_task,
        ):
            mock_task.delay = MagicMock()

            response = await service.upload(
                user_id=user_id,
                file=file,
                background_tasks=BackgroundTasks(),
                exam_name="RRB ALP 2024",
                exam_year=2024,
                exam_shift="Shift 1",
                max_size_bytes=50 * 1024 * 1024,
            )

        assert response.document_id is not None
        assert response.job_id is not None
        assert response.status == "QUEUED"
        assert response.original_filename == "test.pdf"
        assert response.file_size_bytes == len(VALID_PDF_BYTES)

    @pytest.mark.asyncio
    async def test_upload_calls_storage_client(self, db_session):
        service = PdfService(db_session)
        file = _make_upload_file()
        user_id = uuid.uuid4()

        mock_storage = MagicMock()
        mock_storage.upload_pdf.return_value = ("key", "url")

        with (
            patch("app.services.pdf_service.StorageClient", return_value=mock_storage),
            patch("app.pdf.tasks.process_pdf") as mock_task,
        ):
            mock_task.delay = MagicMock()
            await service.upload(
                user_id=user_id,
                file=file,
                background_tasks=BackgroundTasks(),
                exam_name=None, exam_year=None, exam_shift=None,
                max_size_bytes=50 * 1024 * 1024,
            )

        # Storage must have been called with the right file content
        mock_storage.upload_pdf.assert_called_once()
        call_kwargs = mock_storage.upload_pdf.call_args.kwargs
        assert call_kwargs["file_bytes"] == VALID_PDF_BYTES
        assert call_kwargs["filename"] == "test.pdf"
        assert call_kwargs["user_id"] == user_id

    @pytest.mark.asyncio
    async def test_get_status_raises_403_for_wrong_user(self, db_session):
        """get_status() should raise 403 if user doesn't own the document."""
        from app.models.pdf import PdfDocument, PdfProcessingJob

        # Seed a doc belonging to user1
        user1_id = uuid.uuid4()
        doc = PdfDocument(
            id=uuid.uuid4(),
            user_id=user1_id,
            original_filename="test.pdf",
            storage_key="pdfs/test/key.pdf",
            file_size_bytes=1024,
            mime_type="application/pdf",
        )
        job = PdfProcessingJob(pdf_document_id=doc.id, status="QUEUED")
        db_session.add_all([doc, job])
        await db_session.flush()

        service = PdfService(db_session)
        user2_id = uuid.uuid4()  # Different user

        with pytest.raises(HTTPException) as exc_info:
            await service.get_status(doc.id, user2_id)
        assert exc_info.value.status_code == 403
