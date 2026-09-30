"""
Mock test generation service.

Source-type behaviour:
- VERIFIED / PYQ / REFERENCE:
    Pull exclusively from the verified question bank.
    Raise 400 if insufficient questions are available.

- AI_GENERATED:
    Generate ALL required questions via Gemini.
    Zero dependency on the verified bank.

- MIXED:
    Pull as many verified questions as available (up to `question_count`).
    Generate the deficit via Gemini.
    Result always contains exactly `question_count` questions.
"""

from __future__ import annotations

import logging
import math
import uuid as _uuid
from typing import List
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mock_test import MockTest
from app.models.question import Question
from app.repositories.mock_test_repository import MockTestRepository
from app.repositories.question_repository import QuestionRepository
from app.repositories.subject_repository import SubjectRepository
from app.schemas.mock_test import MockTestGenerateRequest, MockTestResponse, MockTestSummary
from app.schemas.common import PaginatedResponse

logger = logging.getLogger(__name__)


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

        Dispatches to the correct strategy based on source_type:
        - VERIFIED / PYQ / REFERENCE -> bank-only
        - AI_GENERATED               -> Gemini-only
        - MIXED                      -> bank first, Gemini for deficit
        """
        # ── Resolve subject names -> UUIDs ────────────────────────────────────
        subject_ids: List[UUID] = []
        if request.subjects:
            for name in request.subjects:
                subject = await self._sub_repo.get_by_name(name)
                if subject is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Subject '{name}' not found. "
                            "Check /api/subjects for valid names."
                        ),
                    )
                subject_ids.append(subject.id)

        source_type = request.source_type.value if hasattr(request.source_type, "value") else str(request.source_type)

        # ── Route to the right strategy ───────────────────────────────────────
        if source_type == "AI_GENERATED":
            questions = await self._generate_ai_questions(request, subject_ids)
        elif source_type == "MIXED":
            questions = await self._generate_mixed_questions(request, subject_ids)
        else:
            # VERIFIED / PYQ / REFERENCE — bank-only
            questions = await self._select_from_bank(request, subject_ids, source_type)
            if len(questions) < request.question_count:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Not enough verified questions available. "
                        f"Requested {request.question_count}, "
                        f"found {len(questions)}. "
                        "Try broadening your filters or uploading more PDFs."
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
            source_type=source_type,
            difficulty=request.difficulty if isinstance(request.difficulty, str) else request.difficulty.value,
            config_json=request.model_dump(exclude={"title"}),
        )

        # ── Link questions (ordered) ──────────────────────────────────────────
        await self._repo.add_questions(
            mock_test.id, [q.id for q in questions]
        )

        return mock_test

    # ── Bank-only strategy ────────────────────────────────────────────────────

    async def _select_from_bank(
        self,
        request: MockTestGenerateRequest,
        subject_ids: List[UUID],
        source_type: str | None,
    ) -> List[Question]:
        """Select questions from the verified question bank."""
        effective_source_type = (
            source_type if source_type not in ("MIXED", "AI_GENERATED") else None
        )
        return await self._q_repo.select_for_mock_test(
            count=request.question_count,
            subject_ids=subject_ids or None,
            topic_ids=request.topics or None,
            source_type=effective_source_type,
            difficulty=(
                request.difficulty.value
                if hasattr(request.difficulty, "value")
                else str(request.difficulty)
            ) if (request.difficulty and str(request.difficulty) != "MIXED") else None,
        )

    # ── AI-only strategy ──────────────────────────────────────────────────────

    async def _generate_ai_questions(
        self,
        request: MockTestGenerateRequest,
        subject_ids: List[UUID],
    ) -> List[Question]:
        """
        Generate `question_count` questions using Gemini and persist them.

        Batched: generates in chunks of up to 10 to stay within prompt limits.
        """
        subject_name = request.subjects[0] if request.subjects else "General Science"
        difficulty = (
            request.difficulty.value
            if hasattr(request.difficulty, "value")
            else str(request.difficulty)
        )
        if difficulty == "MIXED":
            difficulty = "MEDIUM"

        needed = request.question_count
        generated_questions: List[Question] = []

        logger.info(
            "[AI_MOCK] Generating %d AI questions: subject=%s difficulty=%s",
            needed, subject_name, difficulty,
        )

        remaining = needed
        MAX_RETRIES = 2
        attempt = 0

        while remaining > 0 and attempt <= MAX_RETRIES:
            batch_size = min(remaining, 10)
            attempt += 1
            try:
                batch = await self._call_gemini_batch(
                    subject=subject_name,
                    topic="RRB ALP Syllabus",
                    difficulty=difficulty,
                    count=batch_size,
                    subject_ids=subject_ids,
                )
                generated_questions.extend(batch)
                remaining -= len(batch)
                logger.info(
                    "[AI_MOCK] Batch generated %d questions. "
                    "Total so far: %d / %d",
                    len(batch), len(generated_questions), needed,
                )
            except Exception as exc:
                logger.error(
                    "[AI_MOCK] Gemini batch failed (attempt %d/%d): %s",
                    attempt, MAX_RETRIES + 1, exc,
                )
                if attempt > MAX_RETRIES:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=(
                            f"AI question generation failed after {MAX_RETRIES + 1} "
                            f"attempts: {exc}"
                        ),
                    )

        if len(generated_questions) < needed:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    f"AI generated only {len(generated_questions)} of "
                    f"{needed} requested questions. Try again."
                ),
            )

        return generated_questions[:needed]

    # ── MIXED strategy ────────────────────────────────────────────────────────

    async def _generate_mixed_questions(
        self,
        request: MockTestGenerateRequest,
        subject_ids: List[UUID],
    ) -> List[Question]:
        """
        Fill from bank first, generate the deficit via Gemini.
        """
        bank_questions = await self._select_from_bank(request, subject_ids, source_type=None)
        verified_count = len(bank_questions)
        deficit = request.question_count - verified_count

        logger.info(
            "[MIXED_MOCK] bank=%d deficit=%d total_needed=%d",
            verified_count, deficit, request.question_count,
        )

        if deficit <= 0:
            return bank_questions[: request.question_count]

        # Generate the deficit via AI
        ai_request = request.model_copy(update={"question_count": deficit})
        # question_count validation: override directly since deficit might not
        # be in ALLOWED_QUESTION_COUNTS — we bypass the validator for internal use
        object.__setattr__(ai_request, "question_count", deficit)

        ai_questions = await self._generate_ai_questions(ai_request, subject_ids)
        combined = bank_questions + ai_questions
        logger.info(
            "[MIXED_MOCK] Combined: verified=%d ai_generated=%d total=%d",
            verified_count, len(ai_questions), len(combined),
        )
        return combined[: request.question_count]

    # ── Internal: call Gemini and persist returned questions ──────────────────

    async def _call_gemini_batch(
        self,
        *,
        subject: str,
        topic: str,
        difficulty: str,
        count: int,
        subject_ids: List[UUID],
    ) -> List[Question]:
        """
        Call AIGenerator.generate_questions() and persist returned questions
        to the DB so they can be linked to the mock test.

        Runs in a thread pool because AIGenerator uses the synchronous
        google-genai SDK.
        """
        import asyncio
        from app.ai.generator import AIGenerator

        generator = AIGenerator()

        logger.info(
            "[AI_MOCK] Calling Gemini: subject=%s topic=%s difficulty=%s count=%d",
            subject, topic, difficulty, count,
        )

        # Run sync Gemini SDK call in thread pool to avoid blocking event loop
        generated = await asyncio.to_thread(
            generator.generate_questions,
            subject=subject,
            topic=topic,
            difficulty=difficulty,
            count=count,
        )

        logger.info(
            "[AI_MOCK] Gemini returned %d questions (requested %d)",
            len(generated), count,
        )

        # Persist generated questions to DB and return ORM objects
        persisted: List[Question] = []
        for gq in generated:
            # Validate correct_answer is one of A B C D
            answer = (gq.correct_answer or "").strip().upper()
            if answer not in ("A", "B", "C", "D"):
                logger.warning(
                    "[AI_MOCK] Skipping question with invalid answer=%r", gq.correct_answer
                )
                continue

            # Validate all options are non-empty
            if not all([
                gq.question_text.strip(),
                gq.option_a.strip(),
                gq.option_b.strip(),
                gq.option_c.strip(),
                gq.option_d.strip(),
            ]):
                logger.warning("[AI_MOCK] Skipping question with empty fields")
                continue

            q_difficulty = (gq.difficulty or difficulty).strip().upper()
            if q_difficulty not in ("EASY", "MEDIUM", "HARD"):
                q_difficulty = difficulty.upper()
                if q_difficulty not in ("EASY", "MEDIUM", "HARD"):
                    q_difficulty = "MEDIUM"

            q = await self._q_repo.create(
                question_text=gq.question_text.strip(),
                option_a=gq.option_a.strip(),
                option_b=gq.option_b.strip(),
                option_c=gq.option_c.strip(),
                option_d=gq.option_d.strip(),
                correct_answer=answer,
                explanation=getattr(gq, "explanation", None),
                source_type="AI_GENERATED",
                difficulty=q_difficulty,
                verification_status="VERIFIED",  # AI-generated, trusted for mock use
                subtopic=getattr(gq, "subtopic", None),
                subject_id=subject_ids[0] if subject_ids else None,
            )
            persisted.append(q)

        logger.info(
            "[AI_MOCK] Persisted %d / %d generated questions",
            len(persisted), len(generated),
        )
        return persisted

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def get_mock_test(self, mock_test_id: UUID, user_id: UUID) -> dict:
        mock_test = await self._repo.get_by_id(mock_test_id)
        if mock_test is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mock test not found.",
            )
        if mock_test.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied.",
            )
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
        parts = []
        if request.subjects:
            parts.append(" + ".join(s.title() for s in request.subjects[:2]))
            if len(request.subjects) > 2:
                parts[-1] += f" +{len(request.subjects) - 2} more"
        else:
            parts.append("Full Syllabus")

        diff = request.difficulty
        diff_str = diff.value if hasattr(diff, "value") else str(diff)
        if diff_str != "MIXED":
            parts.append(diff_str.title())

        src = request.source_type
        src_str = src.value if hasattr(src, "value") else str(src)
        if src_str == "AI_GENERATED":
            parts.append("AI")

        parts.append(f"{request.question_count}Q")
        parts.append(f"{request.duration_minutes}min")
        return " · ".join(parts) + " Practice Test"
