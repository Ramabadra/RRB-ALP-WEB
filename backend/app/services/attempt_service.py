"""
AttemptService — orchestrates the full exam session lifecycle.

State Machine:
  NOT_STARTED  →  start()  →  IN_PROGRESS
  IN_PROGRESS  →  save_answers()   (stays IN_PROGRESS)
  IN_PROGRESS  →  submit()  →  SUBMITTED
  IN_PROGRESS  →  timer expired during submit  →  EXPIRED

Rules enforced here:
  1. Only one active attempt per user per mock test at a time.
  2. Only the owner of the attempt can interact with it.
  3. Timer is server-authoritative: expires_at is set at start time.
  4. If the timer has expired when submit is called, the attempt is marked EXPIRED.
  5. Answers can only be saved while attempt is IN_PROGRESS and timer is valid.
  6. Submission triggers synchronous scoring and Result creation.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attempt import Attempt
from app.models.result import Result
from app.repositories.attempt_repository import AttemptRepository, ResultRepository
from app.repositories.mock_test_repository import MockTestRepository
from app.repositories.question_repository import QuestionRepository
from app.schemas.attempt import (
    AnswerSaveRequest,
    AttemptStatusResponse,
    SubmitResponse,
)
from app.services.scoring_engine import ScoringEngine


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AttemptService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = AttemptRepository(db)
        self._result_repo = ResultRepository(db)
        self._mt_repo = MockTestRepository(db)
        self._q_repo = QuestionRepository(db)

    # ── Create ────────────────────────────────────────────────────────────────

    async def create_attempt(self, user_id: UUID, mock_test_id: UUID) -> Attempt:
        """
        Create a new attempt for a mock test.
        Validates that the mock test exists and belongs to this user.
        """
        mock_test = await self._mt_repo.get_by_id(mock_test_id)
        if mock_test is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mock test not found.",
            )
        if mock_test.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only attempt your own mock tests.",
            )
        return await self._repo.create(user_id=user_id, mock_test_id=mock_test_id)

    # ── Start ─────────────────────────────────────────────────────────────────

    async def start_attempt(self, attempt_id: UUID, user_id: UUID) -> Attempt:
        """
        Begin the exam timer. Transitions NOT_STARTED → IN_PROGRESS.
        Sets server-authoritative started_at and expires_at.
        """
        attempt = await self._get_owned_attempt(attempt_id, user_id)

        if attempt.status == "IN_PROGRESS":
            # Idempotent: already started — return as-is
            return attempt

        if attempt.status not in ("NOT_STARTED",):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot start an attempt with status='{attempt.status}'.",
            )

        mock_test = await self._mt_repo.get_by_id(attempt.mock_test_id)
        now = _utcnow()
        expires_at = now + timedelta(minutes=mock_test.duration_minutes)

        await self._repo.start(attempt_id, started_at=now, expires_at=expires_at)
        return await self._repo.get_by_id(attempt_id)

    # ── Status ────────────────────────────────────────────────────────────────

    async def get_status(self, attempt_id: UUID, user_id: UUID) -> AttemptStatusResponse:
        """
        Return live exam status including server-computed seconds_remaining.
        If the timer has expired, the attempt is auto-submitted.
        """
        attempt = await self._get_owned_attempt(attempt_id, user_id)

        # Auto-expire if timer has run out and not yet submitted
        if attempt.status == "IN_PROGRESS" and attempt.expires_at:
            now = _utcnow()
            if now >= attempt.expires_at:
                await self._auto_submit(attempt, user_id)
                attempt = await self._repo.get_by_id(attempt_id)

        counts = await self._repo.count_answers(attempt_id)
        mock_test = await self._mt_repo.get_by_id(attempt.mock_test_id)

        # Compute seconds remaining
        seconds_remaining: Optional[int] = None
        if attempt.status == "IN_PROGRESS" and attempt.expires_at:
            remaining = (attempt.expires_at - _utcnow()).total_seconds()
            seconds_remaining = max(0, int(remaining))

        return AttemptStatusResponse(
            id=attempt.id,
            status=attempt.status,
            started_at=attempt.started_at,
            expires_at=attempt.expires_at,
            seconds_remaining=seconds_remaining,
            total_questions=mock_test.question_count,
            answered_count=counts["answered_count"],
            marked_count=counts["marked_count"],
        )

    # ── Save Answers ──────────────────────────────────────────────────────────

    async def save_answers(
        self, attempt_id: UUID, user_id: UUID, body: AnswerSaveRequest
    ) -> AttemptStatusResponse:
        """
        Upsert answers. Safe to call repeatedly — the backend replaces stale rows.
        Returns updated live status.
        """
        attempt = await self._get_owned_attempt(attempt_id, user_id)

        if attempt.status != "IN_PROGRESS":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot save answers for attempt with status='{attempt.status}'. Start the attempt first.",
            )

        # Check timer
        now = _utcnow()
        if attempt.expires_at and now >= attempt.expires_at:
            await self._auto_submit(attempt, user_id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Time expired. Your attempt was auto-submitted.",
            )

        # Validate all question IDs belong to this mock test
        question_ids = await self._mt_repo.get_question_ids(attempt.mock_test_id)
        valid_qids = {str(qid) for qid in question_ids}

        for ans in body.answers:
            if str(ans.question_id) not in valid_qids:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Question '{ans.question_id}' does not belong to this mock test.",
                )

        answer_dicts = [
            {
                "question_id": ans.question_id,
                "selected_answer": ans.selected_answer.value if ans.selected_answer else None,
                "is_marked": ans.is_marked,
            }
            for ans in body.answers
        ]
        await self._repo.upsert_answers(attempt_id, answer_dicts, answered_at=now)

        return await self.get_status(attempt_id, user_id)

    # ── Submit ────────────────────────────────────────────────────────────────

    async def submit(
        self, attempt_id: UUID, user_id: UUID
    ) -> SubmitResponse:
        """
        Submit the attempt. Triggers synchronous scoring.
        If timer has already expired, marks EXPIRED instead of SUBMITTED.
        """
        attempt = await self._get_owned_attempt(attempt_id, user_id)

        if attempt.status in ("SUBMITTED", "EXPIRED"):
            # Idempotent — return the existing result
            existing_result = await self._result_repo.get_by_attempt_id(attempt_id)
            if existing_result:
                return SubmitResponse(
                    attempt_id=attempt_id,
                    result_id=existing_result.id,
                    message="Already submitted.",
                )

        if attempt.status not in ("IN_PROGRESS", "SUBMITTED", "EXPIRED"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot submit attempt with status='{attempt.status}'.",
            )

        now = _utcnow()
        auto_submitted = bool(attempt.expires_at and now >= attempt.expires_at)

        await self._repo.mark_submitted(attempt_id, submitted_at=now, auto_submitted=auto_submitted)

        result = await self._compute_and_save_result(attempt, user_id, now)

        return SubmitResponse(
            attempt_id=attempt_id,
            result_id=result.id,
            message="Time expired. Attempt auto-submitted." if auto_submitted else "Attempt submitted successfully.",
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _get_owned_attempt(self, attempt_id: UUID, user_id: UUID) -> Attempt:
        attempt = await self._repo.get_by_id(attempt_id)
        if attempt is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attempt not found.",
            )
        if attempt.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied.",
            )
        return attempt

    async def _auto_submit(self, attempt: Attempt, user_id: UUID) -> None:
        """Internal: silently auto-submit an expired attempt."""
        if attempt.status in ("SUBMITTED", "EXPIRED"):
            return
        now = _utcnow()
        await self._repo.mark_submitted(attempt.id, submitted_at=now, auto_submitted=True)
        await self._compute_and_save_result(attempt, user_id, now)

    async def _compute_and_save_result(
        self, attempt: Attempt, user_id: UUID, submitted_at: datetime
    ) -> Result:
        """Score the attempt and persist a Result row."""
        # Check if already scored
        existing = await self._result_repo.get_by_attempt_id(attempt.id)
        if existing:
            return existing

        mock_test = await self._mt_repo.get_by_id(attempt.mock_test_id)
        question_ids = await self._mt_repo.get_question_ids(attempt.mock_test_id)
        questions = await self._q_repo.get_by_ids(question_ids)

        # Load all user answers as a dict
        raw_answers = await self._repo.get_answers(attempt.id)
        user_answers = {str(a.question_id): a.selected_answer for a in raw_answers}

        # Build question_answers payload for scoring engine
        question_answers = []
        for q in questions:
            question_answers.append({
                "question_id": str(q.id),
                "correct_answer": q.correct_answer,
                "subject_name": None,  # Populated in Phase 6 analytics with join
                "topic_name": None,
            })

        engine = ScoringEngine(
            marks_per_correct=mock_test.marks_per_correct,
            negative_marking=mock_test.negative_marking,
        )

        time_spent_seconds = 0
        if attempt.started_at and submitted_at:
            time_spent_seconds = max(
                0, int((submitted_at - attempt.started_at).total_seconds())
            )

        scored = engine.score(
            question_answers=question_answers,
            user_answers=user_answers,
            time_spent_seconds=time_spent_seconds,
        )

        result = await self._result_repo.create(
            attempt_id=attempt.id,
            user_id=user_id,
            mock_test_id=attempt.mock_test_id,
            total_questions=scored.total_questions,
            attempted=scored.attempted,
            correct=scored.correct,
            wrong=scored.wrong,
            unanswered=scored.unanswered,
            score=scored.score,
            max_score=scored.max_score,
            accuracy=scored.accuracy,
            time_spent_seconds=scored.time_spent_seconds,
            subject_performance={
                k: ScoringEngine.breakdown_to_dict(v)
                for k, v in scored.subject_performance.items()
            },
            topic_performance={
                k: ScoringEngine.breakdown_to_dict(v)
                for k, v in scored.topic_performance.items()
            },
            answer_details=scored.answer_details,
        )

        return result
