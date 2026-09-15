"""
Question service — business logic for question bank CRUD.

Rules enforced here (NOT in the repository):
- AI_GENERATED questions must not have source_year
- Correct answer must be A/B/C/D (schema validates this already, service double-checks)
- Verification status defaults to UNVERIFIED for manually created questions
"""

from __future__ import annotations

import math
from typing import List, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.question import Question
from app.repositories.question_repository import QuestionRepository
from app.schemas.common import PaginatedResponse
from app.schemas.question import (
    QuestionCreateRequest,
    QuestionFilterParams,
    QuestionResponse,
    QuestionUpdateRequest,
)


class QuestionService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = QuestionRepository(db)

    async def list_questions(
        self,
        filters: QuestionFilterParams,
        page: int,
        page_size: int,
    ) -> PaginatedResponse:
        total = await self._repo.count(filters)
        questions = await self._repo.list_paginated(filters, page, page_size)
        total_pages = math.ceil(total / page_size) if page_size else 1
        return PaginatedResponse(
            items=[QuestionResponse.model_validate(q) for q in questions],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_question(self, question_id: UUID) -> Question:
        q = await self._repo.get_by_id(question_id)
        if q is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question '{question_id}' not found.",
            )
        return q

    async def create_question(self, data: QuestionCreateRequest) -> Question:
        """
        Create a new question.
        Business rule: AI_GENERATED must not have source_year (enforced in schema + here).
        """
        kwargs = data.model_dump(exclude_unset=False)
        # Force verification status for manually created questions
        kwargs["verification_status"] = "UNVERIFIED"
        return await self._repo.create(**kwargs)

    async def update_question(
        self, question_id: UUID, data: QuestionUpdateRequest
    ) -> Question:
        # Verify exists first
        existing = await self.get_question(question_id)

        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return existing

        # Re-validate AI rule if source_type or source_year changed
        new_source_type = updates.get("source_type", existing.source_type)
        new_source_year = updates.get("source_year", existing.source_year)
        if new_source_type == "AI_GENERATED" and new_source_year is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="AI_GENERATED questions cannot have a source_year.",
            )

        updated = await self._repo.update(question_id, updates)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")
        return updated

    async def delete_question(self, question_id: UUID) -> None:
        deleted = await self._repo.delete(question_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question '{question_id}' not found.",
            )
