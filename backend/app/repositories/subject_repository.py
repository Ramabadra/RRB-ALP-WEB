"""
Subject and Topic repository — all DB queries for Subject and Topic models.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subject import Subject, Topic


class SubjectRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_all(self) -> List[Subject]:
        result = await self._db.execute(
            select(Subject).order_by(Subject.display_order, Subject.name)
        )
        return list(result.scalars().all())

    async def get_by_id(self, subject_id: UUID) -> Optional[Subject]:
        result = await self._db.execute(
            select(Subject).where(Subject.id == subject_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Subject]:
        result = await self._db.execute(
            select(Subject).where(Subject.name == name.upper())
        )
        return result.scalar_one_or_none()


class TopicRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_all(self, subject_id: UUID | None = None) -> List[Topic]:
        stmt = select(Topic).order_by(Topic.display_order, Topic.name)
        if subject_id is not None:
            stmt = stmt.where(Topic.subject_id == subject_id)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, topic_id: UUID) -> Optional[Topic]:
        result = await self._db.execute(
            select(Topic).where(Topic.id == topic_id)
        )
        return result.scalar_one_or_none()

    async def get_by_subject(self, subject_id: UUID) -> List[Topic]:
        result = await self._db.execute(
            select(Topic)
            .where(Topic.subject_id == subject_id)
            .order_by(Topic.display_order, Topic.name)
        )
        return list(result.scalars().all())
