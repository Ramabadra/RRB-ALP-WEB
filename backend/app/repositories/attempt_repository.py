"""
Attempt + Result repositories — all DB queries for the exam engine.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attempt import Attempt, AttemptAnswer
from app.models.result import Result


# ─── Attempt Repository ────────────────────────────────────────────────────────

class AttemptRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, *, user_id: UUID, mock_test_id: UUID) -> Attempt:
        attempt = Attempt(user_id=user_id, mock_test_id=mock_test_id, status="NOT_STARTED")
        self._db.add(attempt)
        await self._db.flush()
        return attempt

    async def get_by_id(self, attempt_id: UUID) -> Optional[Attempt]:
        result = await self._db.execute(
            select(Attempt).where(Attempt.id == attempt_id)
        )
        return result.scalar_one_or_none()

    async def start(
        self, attempt_id: UUID, started_at: datetime, expires_at: datetime
    ) -> None:
        await self._db.execute(
            update(Attempt)
            .where(Attempt.id == attempt_id)
            .values(status="IN_PROGRESS", started_at=started_at, expires_at=expires_at)
        )
        await self._db.flush()

    async def mark_submitted(
        self,
        attempt_id: UUID,
        submitted_at: datetime,
        auto_submitted: bool = False,
    ) -> None:
        status = "EXPIRED" if auto_submitted else "SUBMITTED"
        await self._db.execute(
            update(Attempt)
            .where(Attempt.id == attempt_id)
            .values(
                status=status,
                submitted_at=submitted_at,
                auto_submitted=auto_submitted,
            )
        )
        await self._db.flush()

    async def upsert_answers(
        self,
        attempt_id: UUID,
        answers: List[dict],
        answered_at: datetime,
    ) -> None:
        """
        Upsert multiple answers in one call.

        Each dict: {"question_id": UUID, "selected_answer": str|None, "is_marked": bool}

        Strategy: INSERT OR REPLACE (SQLite) / ON CONFLICT DO UPDATE (Postgres).
        We use dialect-agnostic approach — delete existing rows then re-insert —
        because the test suite uses SQLite and production uses PostgreSQL.
        The `uq_attempt_answers_attempt_question` unique constraint protects us.
        """
        if not answers:
            return

        question_ids = [a["question_id"] for a in answers]

        # Delete existing rows for these question_ids in this attempt
        from sqlalchemy import delete as sql_delete
        await self._db.execute(
            sql_delete(AttemptAnswer).where(
                AttemptAnswer.attempt_id == attempt_id,
                AttemptAnswer.question_id.in_(question_ids),
            )
        )

        # Re-insert with new values
        for ans in answers:
            row = AttemptAnswer(
                attempt_id=attempt_id,
                question_id=ans["question_id"],
                selected_answer=ans.get("selected_answer"),
                is_marked=ans.get("is_marked", False),
                answered_at=answered_at if ans.get("selected_answer") else None,
            )
            self._db.add(row)

        await self._db.flush()

    async def get_answers(self, attempt_id: UUID) -> List[AttemptAnswer]:
        result = await self._db.execute(
            select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt_id)
        )
        return list(result.scalars().all())

    async def count_answers(self, attempt_id: UUID) -> dict:
        """Return dict with answered_count and marked_count for the status endpoint."""
        rows = await self.get_answers(attempt_id)
        return {
            "answered_count": sum(1 for r in rows if r.selected_answer is not None),
            "marked_count": sum(1 for r in rows if r.is_marked),
        }


# ─── Result Repository ─────────────────────────────────────────────────────────

class ResultRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        *,
        attempt_id: UUID,
        user_id: UUID,
        mock_test_id: UUID,
        total_questions: int,
        attempted: int,
        correct: int,
        wrong: int,
        unanswered: int,
        score: float,
        max_score: float,
        accuracy: float,
        time_spent_seconds: int,
        subject_performance: dict,
        topic_performance: dict,
        answer_details: list,
    ) -> Result:
        result = Result(
            attempt_id=attempt_id,
            user_id=user_id,
            mock_test_id=mock_test_id,
            total_questions=total_questions,
            attempted=attempted,
            correct=correct,
            wrong=wrong,
            unanswered=unanswered,
            score=score,
            max_score=max_score,
            accuracy=accuracy,
            time_spent_seconds=time_spent_seconds,
            subject_performance=subject_performance,
            topic_performance=topic_performance,
            answer_details=answer_details,
        )
        self._db.add(result)
        await self._db.flush()
        return result

    async def get_by_attempt_id(self, attempt_id: UUID) -> Optional[Result]:
        res = await self._db.execute(
            select(Result).where(Result.attempt_id == attempt_id)
        )
        return res.scalar_one_or_none()

    async def get_by_id(self, result_id: UUID) -> Optional[Result]:
        res = await self._db.execute(
            select(Result).where(Result.id == result_id)
        )
        return res.scalar_one_or_none()

    async def list_by_user(
        self, user_id: UUID, page: int = 1, page_size: int = 20
    ) -> List[Result]:
        from sqlalchemy import func
        offset = (page - 1) * page_size
        res = await self._db.execute(
            select(Result)
            .where(Result.user_id == user_id)
            .order_by(Result.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        return list(res.scalars().all())

    async def count_by_user(self, user_id: UUID) -> int:
        from sqlalchemy import func
        res = await self._db.execute(
            select(func.count()).select_from(Result).where(Result.user_id == user_id)
        )
        return res.scalar_one()
