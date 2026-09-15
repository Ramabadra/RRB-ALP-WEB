"""
Mistake Book Repository — handles all database queries for the MistakeQuestion model.
"""

from __future__ import annotations

import random
from typing import List, Optional
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mistake import MistakeQuestion
from app.models.question import Question


class MistakeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, mistake_id: UUID, user_id: UUID) -> Optional[MistakeQuestion]:
        """Get a single mistake for a specific user."""
        stmt = select(MistakeQuestion).where(
            MistakeQuestion.id == mistake_id,
            MistakeQuestion.user_id == user_id,
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_question_and_user(self, question_id: UUID, user_id: UUID) -> Optional[MistakeQuestion]:
        """Check if a question is already in the user's mistake book."""
        stmt = select(MistakeQuestion).where(
            MistakeQuestion.question_id == question_id,
            MistakeQuestion.user_id == user_id,
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_paginated(self, user_id: UUID, page: int = 1, page_size: int = 20) -> List[MistakeQuestion]:
        """List mistakes for a user, paginated."""
        offset = (page - 1) * page_size
        stmt = (
            select(MistakeQuestion)
            .where(MistakeQuestion.user_id == user_id)
            .order_by(MistakeQuestion.added_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **kwargs) -> MistakeQuestion:
        """Add a new mistake."""
        mistake = MistakeQuestion(**kwargs)
        self._db.add(mistake)
        await self._db.flush()
        await self._db.refresh(mistake)
        return mistake

    async def update(self, mistake_id: UUID, user_id: UUID, values: dict) -> Optional[MistakeQuestion]:
        """Update user notes."""
        mistake = await self.get_by_id(mistake_id, user_id)
        if not mistake:
            return None
        
        for key, value in values.items():
            setattr(mistake, key, value)
            
        await self._db.flush()
        return mistake

    async def delete(self, mistake_id: UUID, user_id: UUID) -> bool:
        """Remove a mistake from the book."""
        stmt = delete(MistakeQuestion).where(
            MistakeQuestion.id == mistake_id,
            MistakeQuestion.user_id == user_id,
        )
        result = await self._db.execute(stmt)
        return result.rowcount > 0

    async def get_random_practice_questions(self, user_id: UUID, limit: int = 10) -> List[Question]:
        """
        Fetch a random set of questions from the mistake book for practice.
        """
        stmt = (
            select(Question)
            .join(MistakeQuestion, MistakeQuestion.question_id == Question.id)
            .where(MistakeQuestion.user_id == user_id)
            .order_by(func.random())
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())
