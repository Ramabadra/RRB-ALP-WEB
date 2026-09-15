"""
PDF repository — DB queries for PdfDocument and PdfProcessingJob.
"""

from __future__ import annotations

import uuid
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pdf import PdfDocument, PdfProcessingJob


class PdfRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_document(
        self,
        *,
        user_id: UUID,
        original_filename: str,
        storage_key: str,
        file_size_bytes: int,
        mime_type: str,
        exam_name: str | None = None,
        exam_year: int | None = None,
        exam_shift: str | None = None,
    ) -> PdfDocument:
        doc = PdfDocument(
            user_id=user_id,
            original_filename=original_filename,
            storage_key=storage_key,
            file_size_bytes=file_size_bytes,
            mime_type=mime_type,
            exam_name=exam_name,
            exam_year=exam_year,
            exam_shift=exam_shift,
        )
        self._db.add(doc)
        await self._db.flush()
        return doc

    async def create_job(self, pdf_document_id: UUID) -> PdfProcessingJob:
        job = PdfProcessingJob(pdf_document_id=pdf_document_id, status="QUEUED")
        self._db.add(job)
        await self._db.flush()
        return job

    async def get_document(self, document_id: UUID) -> Optional[PdfDocument]:
        result = await self._db.execute(
            select(PdfDocument).where(PdfDocument.id == document_id)
        )
        return result.scalar_one_or_none()

    async def get_latest_job(self, document_id: UUID) -> Optional[PdfProcessingJob]:
        result = await self._db.execute(
            select(PdfProcessingJob)
            .where(PdfProcessingJob.pdf_document_id == document_id)
            .order_by(PdfProcessingJob.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self, user_id: UUID, page: int = 1, page_size: int = 20
    ) -> List[PdfDocument]:
        offset = (page - 1) * page_size
        result = await self._db.execute(
            select(PdfDocument)
            .where(PdfDocument.user_id == user_id)
            .order_by(PdfDocument.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        return list(result.scalars().all())

    async def count_by_user(self, user_id: UUID) -> int:
        from sqlalchemy import func
        result = await self._db.execute(
            select(func.count()).select_from(PdfDocument).where(PdfDocument.user_id == user_id)
        )
        return result.scalar_one()
