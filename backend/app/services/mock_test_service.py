"""
Mock test generation service.

The generation algorithm:
1. Validate request parameters.
2. Resolve subject/topic filters to UUIDs.
3. Call QuestionRepository.select_for_mock_test() to pick questions randomly.
4. Check we have enough questions (raise 400 if not).
5. Auto-generate a descriptive title if not provided.
6. Persist MockTest + MockTestQuestion rows.
7. Return the created MockTest ORM object.
"""

from __future__ import annotations

import math
from typing import List
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mock_test import MockTest
from app.repositories.mock_test_repository import MockTestRepository
from app.repositories.question_repository import QuestionRepository
from app.repositories.subject_repository import SubjectRepository
from app.schemas.mock_test import MockTestGenerateRequest, MockTestResponse, MockTestSummary
from app.schemas.common import PaginatedResponse


class MockTestService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = MockTestRepository(db)
        self._q_repo = QuestionRepository(db)
        self._sub_repo = SubjectRepository(db)

    async def generate(
        self, user_id: UUID, request: MockTestGenerateRequest
    ) -> MockTest:
        """
        Generate a new randomised mock test for the user.
        """
        # ── Resolve subject names → UUIDs ────────────────────────────────────
        subject_ids: List[UUID] = []
        if request.subjects:
            for name in request.subjects:
                subject = await self._sub_repo.get_by_name(name.upper())
                if subject is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Subject '{name}' not found. Check /api/subjects for valid names.",
                    )
                subject_ids.append(subject.id)

        # ── Select questions from question bank ───────────────────────────────
        questions = await self._q_repo.select_for_mock_test(
            count=request.question_count,
            subject_ids=subject_ids or None,
            topic_ids=request.topics or None,
            source_type=request.source_type if request.source_type != "MIXED" else None,
            difficulty=request.difficulty if request.difficulty != "MIXED" else None,
        )

        if len(questions) < request.question_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Not enough verified questions available. "
                    f"Requested {request.question_count}, found {len(questions)}. "
                    f"Try broadening your filters or adding more questions to the bank."
                ),
            )

        # ── Auto-generate title ───────────────────────────────────────────────
        title = request.title or self._auto_title(request)

        # ── Persist MockTest ──────────────────────────────────────────────────
        mock_test = await self._repo.create(
            user_id=user_id,
            title=title,
            question_count=request.question_count,
            duration_minutes=request.duration_minutes,
            negative_marking=request.negative_marking,
            marks_per_correct=request.marks_per_correct,
            source_type=request.source_type,
            difficulty=request.difficulty,
            config_json=request.model_dump(exclude={"title"}),
        )

        # ── Link questions (ordered) ──────────────────────────────────────────
        await self._repo.add_questions(
            mock_test.id, [q.id for q in questions]
        )

        return mock_test

    async def get_mock_test(self, mock_test_id: UUID, user_id: UUID) -> dict:
        """
        Return a mock test with its ordered question_ids list.
        Raises 404 / 403 as appropriate.
        """
        mock_test = await self._repo.get_by_id(mock_test_id)
        if mock_test is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mock test not found.")
        if mock_test.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

        question_ids = await self._repo.get_question_ids(mock_test_id)
        return {"mock_test": mock_test, "question_ids": question_ids}

    async def list_mock_tests(
        self, user_id: UUID, page: int, page_size: int
    ) -> PaginatedResponse:
        total = await self._repo.count_by_user(user_id)
        mock_tests = await self._repo.list_by_user(user_id, page, page_size)
        total_pages = math.ceil(total / page_size) if page_size else 1
        return PaginatedResponse(
            items=[MockTestSummary.model_validate(mt) for mt in mock_tests],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def _auto_title(request: MockTestGenerateRequest) -> str:
        """Generate a descriptive test title from the request parameters."""
        parts = []
        if request.subjects:
            parts.append(" + ".join(s.title() for s in request.subjects[:2]))
            if len(request.subjects) > 2:
                parts[-1] += f" +{len(request.subjects) - 2} more"
        else:
            parts.append("Full Syllabus")

        diff = request.difficulty
        if diff != "MIXED":
            parts.append(diff.title())

        parts.append(f"{request.question_count}Q")
        parts.append(f"{request.duration_minutes}min")
        return " · ".join(parts) + " Practice Test"
