"""
Tests for AI Service and Validator — testing Phase 6 features.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.ai.prompts import GeneratedQuestion, ValidatedQuestionSchema
from app.models.question import Question
from app.models.subject import Subject
from app.schemas.question import Difficulty


@pytest.fixture
def mock_genai_client():
    with patch("app.ai.client.genai.Client") as mock_client_class:
        mock_instance = mock_client_class.return_value
        
        # Setup the mock to return a fake object with a `.parsed` attribute
        # representing the structured output.
        mock_response = MagicMock()
        mock_instance.models.generate_content.return_value = mock_response
        
        yield mock_instance, mock_response


class TestAIValidator:
    def test_validate_question_success(self, mock_genai_client):
        mock_client, mock_response = mock_genai_client
        
        # Setup the fake parsed return value
        fake_validated = ValidatedQuestionSchema(
            is_valid=True,
            question_text="What is $x$ if $2x = 4$?",
            option_a="1",
            option_b="2",
            option_c="3",
            option_d="4",
            correct_answer="B",
            explanation="Solve for x by dividing by 2.",
            suggested_subject="MATHEMATICS"
        )
        mock_response.parsed = fake_validated

        from app.ai.validator import AIValidator
        validator = AIValidator()
        
        q = Question(
            id=uuid.uuid4(),
            question_text="What is x if 2x = 4?",
            option_a="1", option_b="2", option_c="3", option_d="4",
            correct_answer="B",
        )
        
        result = validator.validate_question(q)
        
        assert result.is_valid is True
        assert "What is $x$" in result.question_text
        assert result.correct_answer == "B"
        
        # Verify the client was called with the right prompt
        mock_client.models.generate_content.assert_called_once()
        kwargs = mock_client.models.generate_content.call_args.kwargs
        assert "What is x if 2x = 4" in kwargs["contents"]


class TestAIGenerator:
    def test_generate_questions_success(self, mock_genai_client):
        mock_client, mock_response = mock_genai_client
        
        # Setup the fake parsed return value
        from app.ai.prompts import GeneratedQuestionsBatchSchema
        fake_generated = GeneratedQuestionsBatchSchema(
            questions=[
                GeneratedQuestion(
                    question_text="Gen Q1", option_a="A", option_b="B", option_c="C", option_d="D",
                    correct_answer="A", explanation="Expl 1", difficulty="EASY"
                )
            ]
        )
        mock_response.parsed = fake_generated

        from app.ai.generator import AIGenerator
        generator = AIGenerator()
        
        result = generator.generate_questions("MATHEMATICS", "Algebra", "EASY", 1)
        
        assert len(result) == 1
        assert result[0].question_text == "Gen Q1"


@pytest.mark.asyncio
class TestAIService:
    async def test_validate_already_verified_raises_400(self, db_session):
        from app.services.ai_service import AIService
        
        q_id = uuid.uuid4()
        q = Question(
            id=q_id,
            question_text="Test",
            option_a="A", option_b="B", option_c="C", option_d="D",
            correct_answer="A",
            verification_status="VERIFIED"
        )
        db_session.add(q)
        await db_session.flush()
        
        service = AIService(db_session)
        
        with pytest.raises(HTTPException) as exc:
            await service.validate_question(q_id)
            
        assert exc.value.status_code == 400
        assert "already verified" in str(exc.value.detail).lower()

    async def test_validate_updates_db(self, db_session, mock_genai_client):
        mock_client, mock_response = mock_genai_client
        mock_response.parsed = ValidatedQuestionSchema(
            is_valid=True,
            question_text="New text",
            option_a="1", option_b="2", option_c="3", option_d="4",
            correct_answer="C",
            explanation="Explanation",
            suggested_subject="MATHEMATICS"
        )
        
        subject = Subject(id=uuid.uuid4(), name="MATHEMATICS", short_code="MATH")
        db_session.add(subject)
        
        q_id = uuid.uuid4()
        q = Question(
            id=q_id,
            question_text="Old text",
            option_a="A", option_b="B", option_c="C", option_d="D",
            correct_answer="A",
            verification_status="NEEDS_REVIEW"
        )
        db_session.add(q)
        await db_session.flush()
        
        from app.services.ai_service import AIService
        service = AIService(db_session)
        updated = await service.validate_question(q_id)
        
        assert updated.verification_status == "VERIFIED"
        assert updated.question_text == "New text"
        assert updated.correct_answer == "C"
        assert updated.subject_id == subject.id

    async def test_generate_questions_endpoint(self, db_session, mock_genai_client):
        mock_client, mock_response = mock_genai_client
        from app.ai.prompts import GeneratedQuestionsBatchSchema
        mock_response.parsed = GeneratedQuestionsBatchSchema(
            questions=[
                GeneratedQuestion(
                    question_text="Gen Q1", option_a="A", option_b="B", option_c="C", option_d="D",
                    correct_answer="A", explanation="Expl 1", difficulty="EASY"
                )
            ]
        )
        
        sub_id = uuid.uuid4()
        top_id = uuid.uuid4()
        
        from app.models.subject import Topic
        db_session.add(Subject(id=sub_id, name="MATH", short_code="M"))
        db_session.add(Topic(id=top_id, subject_id=sub_id, name="Algebra"))
        await db_session.flush()
        
        from app.services.ai_service import AIService
        service = AIService(db_session)
        
        result = await service.generate_questions(sub_id, top_id, Difficulty.EASY, 1)
        
        assert len(result) == 1
        assert result[0].question_text == "Gen Q1"
        assert result[0].source_type == "AI_GENERATED"
        assert result[0].source_year is None
