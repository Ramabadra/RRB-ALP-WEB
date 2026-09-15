"""
Analytics schemas.
"""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel


class ScoreDataPoint(BaseModel):
    """Single point in a score/accuracy trend series."""

    attempt_id: str
    date: str  # ISO 8601
    score: float
    max_score: float
    accuracy: float


class WeakArea(BaseModel):
    name: str
    accuracy: float
    attempted: int
    correct: int
    wrong: int


class AnalyticsResponse(BaseModel):
    """GET /api/analytics — aggregated user performance summary."""

    # Overall stats
    total_attempts: int
    total_questions_attempted: int
    total_correct: int
    total_wrong: int
    total_unanswered: int

    average_score: float
    best_score: float
    latest_score: float | None
    average_accuracy: float

    # Trend series (most recent 10 attempts)
    score_trend: List[ScoreDataPoint]
    accuracy_trend: List[ScoreDataPoint]

    # Per-subject and per-topic aggregated performance
    subject_performance: Dict[str, "SubjectAnalytics"]
    topic_performance: Dict[str, "TopicAnalytics"]

    # Ranked weak areas (lowest accuracy first)
    weak_subjects: List[WeakArea]
    weak_topics: List[WeakArea]


class SubjectAnalytics(BaseModel):
    attempted: int
    correct: int
    wrong: int
    unanswered: int
    accuracy: float


class TopicAnalytics(BaseModel):
    subject_name: str
    attempted: int
    correct: int
    wrong: int
    unanswered: int
    accuracy: float
