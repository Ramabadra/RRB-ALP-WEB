"""
Phase 3 tests: MockTestService and MockTestRepository.
"""

from __future__ import annotations

import uuid
from typing import List, Tuple

import pytest
from fastapi import HTTPException

from app.models.question import Question
from app.models.subject import Subject, Topic
from app.models.user import User
from app.schemas.mock_test import MockTestDifficulty, MockTestGenerateRequest, MockTestSourceType
from app.services.mock_test_service import MockTestService


async def _seed_test_data(db_session) -> Tuple[User, Subject, Topic, List[Question]]:
    """Seed user, subject, topic, and a pool of VERIFIED questions."""
    # User
    user = User(id=uuid.uuid4(), email="test@example.com", name="Test User", google_id="test_google")
    db_session.add(user)
    
    # Subject/Topic
    sub = Subject(id=uuid.uuid4(), name="MATH", short_code="MATH", display_order=1)
    top = Topic(id=uuid.uuid4(), subject_id=sub.id, name="Algebra", display_order=1)
    db_session.add_all([sub, top])
    
    # 25 Verified Questions (Enough to generate a 20-question mock test)
    questions = []
    for i in range(25):
        q = Question(
            id=uuid.uuid4(),
            question_text=f"Q {i}",
            option_a="A", option_b="B", option_c="C", option_d="D",
            correct_answer="A",
            subject_id=sub.id,
            topic_id=top.id,
            difficulty="MEDIUM",
            language="ENGLISH",
            source_type="REFERENCE",
            verification_status="VERIFIED"
        )
        questions.append(q)
    db_session.add_all(questions)
    
    await db_session.flush()
    return user, sub, top, questions


class TestMockTestService:

    @pytest.mark.asyncio
    async def test_generate_mock_test_success(self, db_session):
        user, sub, top, _ = await _seed_test_data(db_session)
        service = MockTestService(db_session)
        
        req = MockTestGenerateRequest(
            question_count=20,
            subjects=["MATH"],
            difficulty=MockTestDifficulty.MEDIUM,
            source_type=MockTestSourceType.REFERENCE
        )
        
        mock_test = await service.generate(user.id, req)
        await db_session.commit()
        
        assert mock_test.id is not None
        assert mock_test.question_count == 20
        assert mock_test.user_id == user.id
        
        # Verify auto-title
        assert "Math" in mock_test.title
        assert "20Q" in mock_test.title
        assert "Medium" in mock_test.title

    @pytest.mark.asyncio
    async def test_generate_not_enough_questions_raises_400(self, db_session):
        user, sub, top, _ = await _seed_test_data(db_session)
        service = MockTestService(db_session)
        
        # We only seeded 25 questions, asking for 30 should fail
        req = MockTestGenerateRequest(
            question_count=30,
            subjects=["MATH"]
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await service.generate(user.id, req)
            
        assert exc_info.value.status_code == 400
        assert "Not enough verified questions available" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_generate_invalid_subject_raises_400(self, db_session):
        user, sub, top, _ = await _seed_test_data(db_session)
        service = MockTestService(db_session)
        
        req = MockTestGenerateRequest(
            question_count=20,
            subjects=["HISTORY"] # Does not exist
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await service.generate(user.id, req)
            
        assert exc_info.value.status_code == 400
        assert "Subject 'HISTORY' not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_mock_test_includes_ordered_questions(self, db_session):
        user, sub, top, _ = await _seed_test_data(db_session)
        service = MockTestService(db_session)
        
        req = MockTestGenerateRequest(question_count=20)
        mock_test = await service.generate(user.id, req)
        await db_session.commit()
        
        data = await service.get_mock_test(mock_test.id, user.id)
        assert data["mock_test"].id == mock_test.id
        assert len(data["question_ids"]) == 20

    @pytest.mark.asyncio
    async def test_get_mock_test_enforces_user_isolation(self, db_session):
        user, sub, top, _ = await _seed_test_data(db_session)
        service = MockTestService(db_session)
        
        req = MockTestGenerateRequest(question_count=20)
        mock_test = await service.generate(user.id, req)
        await db_session.commit()
        
        other_user_id = uuid.uuid4()
        
        with pytest.raises(HTTPException) as exc_info:
            await service.get_mock_test(mock_test.id, other_user_id)
            
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_list_mock_tests(self, db_session):
        user, sub, top, _ = await _seed_test_data(db_session)
        service = MockTestService(db_session)
        
        # Generate 2 mock tests
        for _ in range(2):
            req = MockTestGenerateRequest(question_count=20)
            await service.generate(user.id, req)
        await db_session.commit()
        
        response = await service.list_mock_tests(user.id, page=1, page_size=10)
        
        assert response.total == 2
        assert len(response.items) == 2
