"""
Phase 3 tests: QuestionService and QuestionRepository.
"""

from __future__ import annotations

import uuid
from typing import List, Tuple

import pytest
from fastapi import HTTPException

from app.models.question import Question
from app.models.subject import Subject, Topic
from app.schemas.question import (
    AnswerChoice,
    Difficulty,
    Language,
    QuestionCreateRequest,
    QuestionFilterParams,
    QuestionUpdateRequest,
    SourceType,
    VerificationStatus,
)
from app.services.question_service import QuestionService


async def _seed_test_data(db_session) -> Tuple[uuid.UUID, uuid.UUID]:
    """Seed subject, topic, and return their IDs for question creation."""
    subject_id = uuid.uuid4()
    topic_id = uuid.uuid4()
    
    sub = Subject(id=subject_id, name="MATH", short_code="MATH", display_order=1)
    top = Topic(id=topic_id, subject_id=subject_id, name="Algebra", display_order=1)
    
    db_session.add_all([sub, top])
    await db_session.flush()
    return subject_id, topic_id


def make_question_create_req(subject_id: uuid.UUID, topic_id: uuid.UUID, **kwargs) -> QuestionCreateRequest:
    defaults = {
        "question_text": "What is 2+2?",
        "option_a": "3",
        "option_b": "4",
        "option_c": "5",
        "option_d": "6",
        "correct_answer": AnswerChoice.B,
        "subject_id": subject_id,
        "topic_id": topic_id,
        "difficulty": Difficulty.EASY,
        "language": Language.ENGLISH,
        "source_type": SourceType.REFERENCE,
    }
    defaults.update(kwargs)
    return QuestionCreateRequest(**defaults)


class TestQuestionService:

    @pytest.mark.asyncio
    async def test_create_question_defaults_to_unverified(self, db_session):
        service = QuestionService(db_session)
        sub_id, top_id = await _seed_test_data(db_session)
        
        req = make_question_create_req(sub_id, top_id)
        # Even if request tries to set VERIFIED, service should force UNVERIFIED for manual creation
        req.verification_status = VerificationStatus.VERIFIED
        
        question = await service.create_question(req)
        await db_session.commit()
        
        assert question.id is not None
        assert question.verification_status == "UNVERIFIED"

    @pytest.mark.asyncio
    async def test_ai_generated_question_rejects_source_year(self, db_session):
        service = QuestionService(db_session)
        sub_id, top_id = await _seed_test_data(db_session)
        
        # Pydantic schema validation should catch this
        with pytest.raises(ValueError, match="must not have a source_year"):
            make_question_create_req(
                sub_id, top_id, 
                source_type=SourceType.AI_GENERATED, 
                source_year=2024
            )

    @pytest.mark.asyncio
    async def test_update_question(self, db_session):
        service = QuestionService(db_session)
        sub_id, top_id = await _seed_test_data(db_session)
        
        req = make_question_create_req(sub_id, top_id)
        question = await service.create_question(req)
        await db_session.commit()
        
        update_req = QuestionUpdateRequest(difficulty=Difficulty.HARD)
        updated = await service.update_question(question.id, update_req)
        
        assert updated.difficulty == "HARD"
        assert updated.question_text == "What is 2+2?" # Unchanged

    @pytest.mark.asyncio
    async def test_update_question_ai_rule_enforced(self, db_session):
        service = QuestionService(db_session)
        sub_id, top_id = await _seed_test_data(db_session)
        
        req = make_question_create_req(sub_id, top_id, source_type=SourceType.REFERENCE, source_year=2020)
        question = await service.create_question(req)
        await db_session.commit()
        
        # Try to change it to AI_GENERATED without dropping the year
        update_req = QuestionUpdateRequest(source_type=SourceType.AI_GENERATED)
        with pytest.raises(HTTPException) as exc_info:
            await service.update_question(question.id, update_req)
            
        assert exc_info.value.status_code == 422
        assert "cannot have a source_year" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_delete_question(self, db_session):
        service = QuestionService(db_session)
        sub_id, top_id = await _seed_test_data(db_session)
        
        req = make_question_create_req(sub_id, top_id)
        question = await service.create_question(req)
        await db_session.commit()
        
        await service.delete_question(question.id)
        
        with pytest.raises(HTTPException) as exc_info:
            await service.get_question(question.id)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_list_paginated_questions(self, db_session):
        service = QuestionService(db_session)
        sub_id, top_id = await _seed_test_data(db_session)
        
        for i in range(5):
            req = make_question_create_req(sub_id, top_id, question_text=f"Q {i}")
            await service.create_question(req)
        await db_session.commit()
        
        filters = QuestionFilterParams()
        response = await service.list_questions(filters, page=1, page_size=3)
        
        assert response.total == 5
        assert len(response.items) == 3
        assert response.total_pages == 2
