"""
Phase 1 tests: Pydantic schema validation.
Tests that schemas accept valid data and reject invalid data correctly.
No database required.
"""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from app.schemas.question import (
    AnswerChoice,
    Difficulty,
    Language,
    QuestionCreateRequest,
    SourceType,
)
from app.schemas.mock_test import MockTestGenerateRequest
from app.schemas.attempt import AnswerSaveRequest, SingleAnswerSave
from app.schemas.common import PaginatedResponse
from app.schemas.result import ResultResponse, SubjectPerformance


# ─── QuestionCreateRequest ────────────────────────────────────────────────────

def test_question_create_valid() -> None:
    """Valid question data should pass schema validation."""
    q = QuestionCreateRequest(
        question_text="What is 2 + 2?",
        option_a="2",
        option_b="3",
        option_c="4",
        option_d="5",
        correct_answer=AnswerChoice.C,
        source_type=SourceType.REFERENCE,
    )
    assert q.correct_answer == AnswerChoice.C
    assert q.difficulty == Difficulty.MEDIUM  # default
    assert q.language == Language.ENGLISH     # default


def test_question_ai_generated_no_year() -> None:
    """AI_GENERATED questions with a source_year must be rejected."""
    with pytest.raises(ValidationError) as exc_info:
        QuestionCreateRequest(
            question_text="AI question",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_answer=AnswerChoice.A,
            source_type=SourceType.AI_GENERATED,
            source_year=2023,  # Must NOT be set for AI questions
        )
    assert "source_year" in str(exc_info.value) or "AI_GENERATED" in str(exc_info.value)


def test_question_pyq_with_year() -> None:
    """PYQ questions may have a source_year."""
    q = QuestionCreateRequest(
        question_text="PYQ question",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        correct_answer=AnswerChoice.B,
        source_type=SourceType.PYQ,
        source_year=2021,
        source_exam="RRB ALP",
    )
    assert q.source_year == 2021


def test_question_invalid_correct_answer() -> None:
    """Correct answer must be A/B/C/D only."""
    with pytest.raises(ValidationError):
        QuestionCreateRequest(
            question_text="Test",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_answer="E",  # type: ignore[arg-type]
            source_type=SourceType.REFERENCE,
        )


# ─── MockTestGenerateRequest ──────────────────────────────────────────────────

def test_mock_test_valid() -> None:
    req = MockTestGenerateRequest(question_count=30, duration_minutes=30)
    assert req.question_count == 30
    assert req.negative_marking == pytest.approx(0.3333, abs=0.001)


def test_mock_test_invalid_question_count() -> None:
    """question_count must be in {20, 30, 40, 50, 75}."""
    with pytest.raises(ValidationError):
        MockTestGenerateRequest(question_count=25)  # not in allowed set


def test_mock_test_negative_marking_out_of_range() -> None:
    with pytest.raises(ValidationError):
        MockTestGenerateRequest(question_count=30, negative_marking=1.5)


# ─── AnswerSaveRequest ────────────────────────────────────────────────────────

def test_answer_save_valid() -> None:
    req = AnswerSaveRequest(
        answers=[
            SingleAnswerSave(question_id=uuid.uuid4(), selected_answer=AnswerChoice.A),
            SingleAnswerSave(question_id=uuid.uuid4(), selected_answer=None, is_marked=True),
        ]
    )
    assert len(req.answers) == 2
    assert req.answers[1].selected_answer is None
    assert req.answers[1].is_marked is True


def test_answer_invalid_choice() -> None:
    with pytest.raises(ValidationError):
        AnswerSaveRequest(
            answers=[
                SingleAnswerSave(
                    question_id=uuid.uuid4(),
                    selected_answer="Z",  # type: ignore[arg-type]
                )
            ]
        )


# ─── PaginatedResponse ────────────────────────────────────────────────────────

def test_paginated_response_generic() -> None:
    resp = PaginatedResponse[str](
        items=["a", "b", "c"],
        total=3,
        page=1,
        page_size=10,
        total_pages=1,
    )
    assert resp.total == 3
    assert resp.items == ["a", "b", "c"]
