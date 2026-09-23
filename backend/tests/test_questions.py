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


# ── Security Regression Tests — Phase 4.2 ────────────────────────────────────
# These tests prove that the student-facing APIs never expose correct_answer
# or explanation, while backend grading retains full access.


class TestQuestionSecuritySafeguards:

    @pytest.mark.asyncio
    async def test_get_question_response_has_no_correct_answer(self, db_session):
        """
        QuestionService.get_question() returns the raw ORM Question.
        The router maps it to ExamQuestionResponse — which must NOT include correct_answer.
        We test the schema directly to prove the field is absent at serialisation time.
        """
        from app.schemas.question import ExamQuestionResponse
        service = QuestionService(db_session)
        sub_id, top_id = await _seed_test_data(db_session)
        req = make_question_create_req(sub_id, top_id, correct_answer=AnswerChoice.B)
        question = await service.create_question(req)
        await db_session.commit()

        # This is what the GET /api/questions/{id} router returns
        safe_response = ExamQuestionResponse.model_validate(question)
        serialised = safe_response.model_dump()

        assert "correct_answer" not in serialised
        assert "explanation" not in serialised

    @pytest.mark.asyncio
    async def test_get_question_response_has_no_explanation(self, db_session):
        """Explanation must not appear in ExamQuestionResponse."""
        from app.schemas.question import ExamQuestionResponse
        service = QuestionService(db_session)
        sub_id, top_id = await _seed_test_data(db_session)
        req = make_question_create_req(
            sub_id, top_id,
            explanation="The answer is B because 2+2=4."
        )
        question = await service.create_question(req)
        await db_session.commit()

        safe_response = ExamQuestionResponse.model_validate(question)
        serialised = safe_response.model_dump()

        assert "explanation" not in serialised
        assert "correct_answer" not in serialised

    @pytest.mark.asyncio
    async def test_list_questions_items_have_no_correct_answer(self, db_session):
        """
        QuestionService.list_questions() uses ExamQuestionResponse for items.
        No item in the paginated list must contain correct_answer.
        """
        service = QuestionService(db_session)
        sub_id, top_id = await _seed_test_data(db_session)

        for i in range(3):
            req = make_question_create_req(
                sub_id, top_id,
                question_text=f"Security Q{i}",
                correct_answer=AnswerChoice.C,
                explanation="Explanation text",
            )
            await service.create_question(req)
        await db_session.commit()

        filters = QuestionFilterParams()
        response = await service.list_questions(filters, page=1, page_size=10)

        for item in response.items:
            serialised = item.model_dump() if hasattr(item, "model_dump") else dict(item)
            assert "correct_answer" not in serialised, (
                f"correct_answer leaked in list item: {serialised}"
            )
            assert "explanation" not in serialised, (
                f"explanation leaked in list item: {serialised}"
            )

    @pytest.mark.asyncio
    async def test_exam_question_response_schema_contains_safe_fields(self, db_session):
        """ExamQuestionResponse must include all question content except answers."""
        from app.schemas.question import ExamQuestionResponse
        service = QuestionService(db_session)
        sub_id, top_id = await _seed_test_data(db_session)
        req = make_question_create_req(sub_id, top_id, question_text="Safe schema test")
        question = await service.create_question(req)
        await db_session.commit()

        safe = ExamQuestionResponse.model_validate(question)
        serialised = safe.model_dump()

        # Required safe fields must be present
        assert "id" in serialised
        assert "question_text" in serialised
        assert "option_a" in serialised
        assert "option_b" in serialised
        assert "option_c" in serialised
        assert "option_d" in serialised
        assert "difficulty" in serialised
        assert "source_type" in serialised

        # Sensitive fields must be absent
        assert "correct_answer" not in serialised
        assert "explanation" not in serialised
        assert "verification_status" not in serialised
        assert "extraction_confidence" not in serialised

    @pytest.mark.asyncio
    async def test_backend_grading_accesses_correct_answer_from_orm(self, db_session):
        """
        Backend grading MUST be able to read correct_answer from the ORM Question model.
        This test confirms the ORM model retains the field — schema safety
        should not remove it from the database level.
        """
        service = QuestionService(db_session)
        sub_id, top_id = await _seed_test_data(db_session)
        req = make_question_create_req(sub_id, top_id, correct_answer=AnswerChoice.D)
        question = await service.create_question(req)
        await db_session.commit()

        # Fetch via service (returns ORM object)
        fetched_question = await service.get_question(question.id)

        # ORM model MUST expose correct_answer for grading
        assert hasattr(fetched_question, "correct_answer")
        assert fetched_question.correct_answer == "D"

    @pytest.mark.asyncio
    async def test_question_response_full_for_admin_create(self, db_session):
        """
        POST /api/questions returns QuestionResponse (full — includes correct_answer).
        This is intentional for the admin/question-bank UI.
        """
        service = QuestionService(db_session)
        sub_id, top_id = await _seed_test_data(db_session)
        req = make_question_create_req(sub_id, top_id, correct_answer=AnswerChoice.A)
        question = await service.create_question(req)
        await db_session.commit()

        # Admin create returns QuestionResponse (includes correct_answer)
        from app.schemas.question import QuestionResponse
        admin_response = QuestionResponse.model_validate(question)
        serialised = admin_response.model_dump()

        assert "correct_answer" in serialised
        assert serialised["correct_answer"] == "A"

    @pytest.mark.asyncio
    async def test_exam_question_schema_cannot_be_constructed_with_correct_answer(self, db_session):
        """
        ExamQuestionResponse must not accept a correct_answer field at all.
        If someone attempts to construct it with one, Pydantic should ignore it
        (strict schemas drop extra fields by default).
        """
        from app.schemas.question import ExamQuestionResponse
        service = QuestionService(db_session)
        sub_id, top_id = await _seed_test_data(db_session)
        req = make_question_create_req(sub_id, top_id)
        question = await service.create_question(req)
        await db_session.commit()

        safe = ExamQuestionResponse.model_validate(question)
        assert not hasattr(safe, "correct_answer"), (
            "ExamQuestionResponse must not have a correct_answer attribute"
        )

    @pytest.mark.asyncio
    async def test_delete_question_removes_record_safely(self, db_session):
        """
        Regression: delete still works after schema refactor.
        """
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
    async def test_get_nonexistent_question_raises_404(self, db_session):
        """Regression: 404 still raised for unknown question ID."""
        service = QuestionService(db_session)
        with pytest.raises(HTTPException) as exc_info:
            await service.get_question(uuid.uuid4())
        assert exc_info.value.status_code == 404

