"""
MockTest repository — DB queries for MockTest and MockTestQuestion.
"""

from __future__ import annotations

import uuid
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mock_test import MockTest, MockTestQuestion


class MockTestRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        *,
        user_id: UUID,
        title: str,
        question_count: int,
        duration_minutes: int,
        negative_marking: float,
        marks_per_correct: float,
        source_type: str,
        difficulty: str,
        config_json: dict | None = None,
    ) -> MockTest:
        mock_test = MockTest(
            user_id=user_id,
            title=title,
            question_count=question_count,
            duration_minutes=duration_minutes,
            negative_marking=negative_marking,
            marks_per_correct=marks_per_correct,
            source_type=source_type,
            difficulty=difficulty,
            config_json=config_json,
        )
        self._db.add(mock_test)
        await self._db.flush()
        return mock_test

    async def add_questions(
        self, mock_test_id: UUID, question_ids: List[UUID]
    ) -> None:
        """Insert MockTestQuestion rows (ordered by position = list index + 1)."""
        for position, qid in enumerate(question_ids, start=1):
            entry = MockTestQuestion(
                mock_test_id=mock_test_id,
                question_id=qid,
                position=position,
            )
            self._db.add(entry)
        await self._db.flush()

    async def get_by_id(self, mock_test_id: UUID) -> Optional[MockTest]:
        result = await self._db.execute(
            select(MockTest).where(MockTest.id == mock_test_id)
        )
        return result.scalar_one_or_none()

    async def get_question_ids(self, mock_test_id: UUID) -> List[UUID]:
        """Return ordered question UUIDs for a mock test."""
        result = await self._db.execute(
            select(MockTestQuestion.question_id)
            .where(MockTestQuestion.mock_test_id == mock_test_id)
            .order_by(MockTestQuestion.position)
        )
        return [row[0] for row in result.all()]

    async def list_by_user(
        self, user_id: UUID, page: int = 1, page_size: int = 20
    ) -> List[MockTest]:
        offset = (page - 1) * page_size
        result = await self._db.execute(
            select(MockTest)
            .where(MockTest.user_id == user_id)
            .order_by(MockTest.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        return list(result.scalars().all())

    async def count_by_user(self, user_id: UUID) -> int:
        from sqlalchemy import func
        result = await self._db.execute(
            select(func.count())
            .select_from(MockTest)
            .where(MockTest.user_id == user_id)
        )
        return result.scalar_one()
