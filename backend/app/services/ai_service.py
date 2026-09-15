"""
AI Service — orchestrates DB interactions and AI generation/validation calls.
"""

from __future__ import annotations

import logging
from typing import List, Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.generator import AIGenerator
from app.ai.validator import AIValidator
from app.repositories.question_repository import QuestionRepository
from app.repositories.subject_repository import SubjectRepository, TopicRepository
from app.schemas.question import (
    Difficulty,
    QuestionCreateRequest,
    QuestionResponse,
    SourceType,
    VerificationStatus,
)

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.q_repo = QuestionRepository(db)
        self.subject_repo = SubjectRepository(db)
        self.topic_repo = TopicRepository(db)
        self.validator = AIValidator()
        self.generator = AIGenerator()

    async def validate_question(self, question_id: UUID) -> QuestionResponse:
        """
        Validates a single question using AI.
        Fetches question, calls Gemini, updates DB, returns updated Question.
        """
        question = await self.q_repo.get_by_id(question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

        if question.verification_status == VerificationStatus.VERIFIED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question is already verified.",
            )

        # Call AI validation
        try:
            ai_result = self.validator.validate_question(question)
        except Exception as e:
            logger.error("AI validation failed for question %s: %s", question_id, str(e))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI Validation service error: {str(e)}",
            )

        # If the AI thinks it's complete garbage, mark as rejected
        if not ai_result.is_valid:
            updated = await self.q_repo.update(
                question_id,
                values={
                    "verification_status": VerificationStatus.REJECTED,
                    "explanation": "AI marked this question as invalid or unreadable."
                }
            )
            return QuestionResponse.model_validate(updated)

        # Find the best subject matching the AI's suggestion
        subject_id = question.subject_id
        if ai_result.suggested_subject:
            subjects = await self.subject_repo.get_all()
            for sub in subjects:
                # Basic string match
                if sub.name.upper() == ai_result.suggested_subject.upper():
                    subject_id = sub.id
                    break

        # Apply updates
        updated = await self.q_repo.update(
            question_id,
            values={
                "question_text": ai_result.question_text,
                "option_a": ai_result.option_a,
                "option_b": ai_result.option_b,
                "option_c": ai_result.option_c,
                "option_d": ai_result.option_d,
                "correct_answer": ai_result.correct_answer,
                "explanation": ai_result.explanation,
                "subject_id": subject_id,
                "verification_status": VerificationStatus.VERIFIED,
            }
        )

        return QuestionResponse.model_validate(updated)

    async def generate_questions(
        self, subject_id: UUID, topic_id: UUID, difficulty: Difficulty, count: int = 5
    ) -> List[QuestionCreateRequest]:
        """
        Generates new questions and returns them as CreateRequests.
        Does NOT automatically save them to the database (allows frontend to preview).
        """
        if count > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 questions can be generated at once.")

        subject = await self.subject_repo.get_by_id(subject_id)
        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found.")

        topic = await self.topic_repo.get_by_id(topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found.")

        try:
            generated = self.generator.generate_questions(
                subject=subject.name,
                topic=topic.name,
                difficulty=difficulty.value,
                count=count,
            )
        except Exception as e:
            logger.error("AI generation failed: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI Generation service error: {str(e)}",
            )

        # Map to QuestionCreateRequest so the frontend can display them and optionally save them
        return [
            QuestionCreateRequest(
                question_text=q.question_text,
                option_a=q.option_a,
                option_b=q.option_b,
                option_c=q.option_c,
                option_d=q.option_d,
                correct_answer=q.correct_answer,
                explanation=q.explanation,
                subject_id=subject_id,
                topic_id=topic_id,
                subtopic=q.subtopic,
                difficulty=Difficulty(q.difficulty.upper()),
                source_type=SourceType.AI_GENERATED,
                language="ENGLISH",
            )
            for q in generated
        ]
