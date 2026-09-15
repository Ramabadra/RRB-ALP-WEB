"""
Subject service — business logic for subjects and topics.
"""

from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subject import Subject, Topic
from app.repositories.subject_repository import SubjectRepository, TopicRepository


class SubjectService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = SubjectRepository(db)

    async def list_subjects(self) -> List[Subject]:
        return await self._repo.get_all()

    async def get_subject(self, subject_id: UUID) -> Subject:
        subject = await self._repo.get_by_id(subject_id)
        if subject is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subject '{subject_id}' not found.",
            )
        return subject


class TopicService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = TopicRepository(db)
        self._subject_repo = SubjectRepository(db)

    async def list_topics(self, subject_id: UUID | None = None) -> List[Topic]:
        # If subject_id provided, verify it exists first
        if subject_id is not None:
            subject = await self._subject_repo.get_by_id(subject_id)
            if subject is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Subject '{subject_id}' not found.",
                )
        return await self._repo.get_all(subject_id=subject_id)

    async def get_topic(self, topic_id: UUID) -> Topic:
        topic = await self._repo.get_by_id(topic_id)
        if topic is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Topic '{topic_id}' not found.",
            )
        return topic
