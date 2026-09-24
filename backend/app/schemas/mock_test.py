"""
MockTest schemas.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class MockTestSourceType(str, Enum):
    PYQ = "PYQ"
    AI_GENERATED = "AI_GENERATED"
    REFERENCE = "REFERENCE"
    MIXED = "MIXED"


class MockTestDifficulty(str, Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    MIXED = "MIXED"


ALLOWED_QUESTION_COUNTS = {20, 30, 40, 50, 75}


class MockTestGenerateRequest(BaseModel):
    """Request body for POST /api/mock-tests."""

    question_count: int = Field(
        30, description="Number of questions. Allowed: 20, 30, 40, 50, 75"
    )
    subjects: List[str] = Field(
        default_factory=list,
        description="Subject names to include. Empty = all subjects.",
    )
    topics: List[UUID] = Field(
        default_factory=list,
        description="Topic UUIDs to include. Empty = all topics.",
    )
    difficulty: MockTestDifficulty = MockTestDifficulty.MIXED
    source_type: MockTestSourceType = MockTestSourceType.MIXED
    negative_marking: float = Field(
        0.3333,
        ge=0.0,
        le=1.0,
        description="Marks deducted per wrong answer (as a fraction of marks_per_correct).",
    )
    marks_per_correct: float = Field(1.0, gt=0.0)
    duration_minutes: int = Field(30, gt=0, le=180)
    title: str | None = Field(None, max_length=300)

    @field_validator("question_count")
    @classmethod
    def validate_question_count(cls, v: int) -> int:
        if v not in ALLOWED_QUESTION_COUNTS:
            raise ValueError(
                f"question_count must be one of {sorted(ALLOWED_QUESTION_COUNTS)}"
            )
        return v


class MockTestResponse(BaseModel):
    """Full mock test response including question IDs."""

    id: UUID
    title: str
    user_id: UUID
    question_count: int
    duration_minutes: int
    negative_marking: float
    marks_per_correct: float
    source_type: str
    difficulty: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MockTestSummary(BaseModel):
    """Lightweight mock test listing."""

    id: UUID
    title: str
    question_count: int
    duration_minutes: int
    difficulty: str
    source_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MockTestDetailResponse(BaseModel):
    """Full mock test details including ordered question UUIDs."""

    id: UUID
    title: str
    user_id: UUID
    question_count: int
    duration_minutes: int
    negative_marking: float
    marks_per_correct: float
    source_type: str
    difficulty: str
    created_at: datetime
    question_ids: List[UUID] = Field(
        default_factory=list,
        description="Ordered question UUIDs. Use these to start an attempt."
    )

    model_config = {"from_attributes": True}
