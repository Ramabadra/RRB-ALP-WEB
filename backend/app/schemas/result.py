"""
Result schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

from pydantic import BaseModel


class SubjectPerformance(BaseModel):
    attempted: int
    correct: int
    wrong: int
    unanswered: int
    score: float
    accuracy: float  # 0.0 – 100.0


class TopicPerformance(BaseModel):
    attempted: int
    correct: int
    wrong: int
    unanswered: int
    score: float
    accuracy: float


class AnswerDetail(BaseModel):
    """Per-question outcome for the review screen."""

    question_id: UUID
    selected_answer: str | None
    correct_answer: str
    is_correct: bool


class ResultResponse(BaseModel):
    """GET /api/results/{attempt_id}"""

    id: UUID
    attempt_id: UUID
    user_id: UUID
    mock_test_id: UUID

    total_questions: int
    attempted: int
    correct: int
    wrong: int
    unanswered: int
    score: float
    max_score: float
    accuracy: float
    time_spent_seconds: int

    subject_performance: Dict[str, SubjectPerformance]
    topic_performance: Dict[str, TopicPerformance]
    answer_details: List[AnswerDetail]

    created_at: datetime

    model_config = {"from_attributes": True}
