"""
Question repository — all DB queries for the Question model.

Provides:
- Paginated, filtered list with composite WHERE clauses
- Single question fetch
- Create / update / soft-delete
- Question selection engine for mock test generation
"""

from __future__ import annotations

import random
import uuid
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.question import Question
from app.schemas.question import QuestionFilterParams


class QuestionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    def _apply_filters(self, stmt, filters: QuestionFilterParams):
        """Apply all optional filter params to a SELECT statement."""
        if filters.subject_id:
            stmt = stmt.where(Question.subject_id == filters.subject_id)
        if filters.topic_id:
            stmt = stmt.where(Question.topic_id == filters.topic_id)
        if filters.source_type:
            stmt = stmt.where(Question.source_type == filters.source_type)
        if filters.difficulty:
            stmt = stmt.where(Question.difficulty == filters.difficulty)
        if filters.verification_status:
            stmt = stmt.where(Question.verification_status == filters.verification_status)
        if filters.source_year:
            stmt = stmt.where(Question.source_year == filters.source_year)
        if filters.language:
            stmt = stmt.where(Question.language == filters.language)
        return stmt

    async def count(self, filters: QuestionFilterParams) -> int:
        stmt = select(func.count()).select_from(Question)
        stmt = self._apply_filters(stmt, filters)
        result = await self._db.execute(stmt)
        return result.scalar_one()

    async def list_paginated(
        self,
        filters: QuestionFilterParams,
        page: int = 1,
        page_size: int = 20,
    ) -> List[Question]:
        offset = (page - 1) * page_size
        stmt = (
            select(Question)
            .order_by(Question.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        stmt = self._apply_filters(stmt, filters)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, question_id: UUID) -> Optional[Question]:
        result = await self._db.execute(
            select(Question).where(Question.id == question_id)
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> Question:
        question = Question(**kwargs)
        self._db.add(question)
        await self._db.flush()
        await self._db.refresh(question)
        return question

    async def update(self, question_id: UUID, values: dict) -> Optional[Question]:
        if not values:
            return await self.get_by_id(question_id)
        await self._db.execute(
            update(Question).where(Question.id == question_id).values(**values)
        )
        await self._db.flush()
        return await self.get_by_id(question_id)

    async def delete(self, question_id: UUID) -> bool:
        result = await self._db.execute(
            delete(Question).where(Question.id == question_id)
        )
        return result.rowcount > 0

    async def select_for_mock_test(
        self,
        *,
        count: int,
        subject_ids: List[UUID] | None = None,
        topic_ids: List[UUID] | None = None,
        source_type: str | None = None,
        difficulty: str | None = None,
        exclude_ids: List[UUID] | None = None,
    ) -> List[Question]:
        """
        Randomly select `count` questions for mock test generation.

        Strategy:
        1. Build a filtered query (verified questions only).
        2. Fetch up to 3× count candidates (to enable random shuffle).
        3. Shuffle and take exactly `count` questions.
        4. If not enough questions exist, return all available (caller handles shortfall).
        """
        stmt = select(Question).where(
            Question.verification_status == "VERIFIED"
        )

        if subject_ids:
            stmt = stmt.where(Question.subject_id.in_(subject_ids))
        if topic_ids:
            stmt = stmt.where(Question.topic_id.in_(topic_ids))
        if source_type and source_type != "MIXED":
            stmt = stmt.where(Question.source_type == source_type)
        if difficulty and difficulty != "MIXED":
            stmt = stmt.where(Question.difficulty == difficulty)
        if exclude_ids:
            stmt = stmt.where(Question.id.notin_(exclude_ids))

        # Fetch a pool of candidates to randomise from
        pool_size = min(count * 3, 500)
        stmt = stmt.limit(pool_size)

        result = await self._db.execute(stmt)
        candidates = list(result.scalars().all())

        if not candidates:
            return []

        random.shuffle(candidates)
        return candidates[:count]

    async def get_by_ids(self, ids: List[UUID]) -> List[Question]:
        """Fetch questions by a list of UUIDs, preserving the input order."""
        if not ids:
            return []
        result = await self._db.execute(
            select(Question).where(Question.id.in_(ids))
        )
        questions = {q.id: q for q in result.scalars().all()}
        return [questions[qid] for qid in ids if qid in questions]
