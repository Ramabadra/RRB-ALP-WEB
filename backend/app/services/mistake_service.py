"""
Mistake Book Service — business logic for adding and retrieving mistakes.
"""

from __future__ import annotations

import logging
from typing import List
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.question import Question
from app.repositories.mistake_repository import MistakeRepository
from app.schemas.mistake import MistakeAddRequest, MistakeResponse
from app.schemas.question import QuestionResponse

logger = logging.getLogger(__name__)


class MistakeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = MistakeRepository(db)

    async def list_mistakes(self, user_id: UUID, page: int = 1, page_size: int = 20) -> dict:
        """Returns paginated mistakes with their associated questions if eager loaded."""
        mistakes = await self.repo.list_paginated(user_id, page, page_size)
        return {
            "page": page,
            "page_size": page_size,
            "items": [MistakeResponse.model_validate(m) for m in mistakes],
        }

    async def add_mistake(self, user_id: UUID, req: MistakeAddRequest) -> MistakeResponse:
        """Adds a question to the user's mistake book."""
        # Check if already exists
        existing = await self.repo.get_by_question_and_user(req.question_id, user_id)
        if existing:
            # Maybe update the note
            if req.note:
                existing = await self.repo.update(existing.id, user_id, {"note": req.note})
            return MistakeResponse.model_validate(existing)

        # Create new
        mistake = await self.repo.create(
            user_id=user_id,
            question_id=req.question_id,
            attempt_id=req.attempt_id,
            note=req.note,
        )
        return MistakeResponse.model_validate(mistake)

    async def delete_mistake(self, user_id: UUID, mistake_id: UUID) -> None:
        """Removes a mistake."""
        deleted = await self.repo.delete(mistake_id, user_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mistake not found.",
            )

    async def get_practice_questions(self, user_id: UUID, limit: int = 20) -> List[QuestionResponse]:
        """Returns random unmastered mistakes to practice."""
        questions = await self.repo.get_random_practice_questions(user_id, limit)
        return [QuestionResponse.model_validate(q) for q in questions]
