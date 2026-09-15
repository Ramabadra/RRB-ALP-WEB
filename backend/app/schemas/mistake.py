"""
Mistake book schemas.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MistakeResponse(BaseModel):
    id: UUID
    user_id: UUID
    question_id: UUID
    attempt_id: UUID | None
    added_at: datetime
    note: str | None

    model_config = {"from_attributes": True}


class MistakeAddRequest(BaseModel):
    """POST /api/mistakes — manually add a question to the mistake book."""

    question_id: UUID
    attempt_id: UUID | None = None
    note: str | None = None


class MistakePracticeRequest(BaseModel):
    """POST /api/mistakes/practice — generate a mock test from mistake questions."""

    question_count: int = 20
    subject_filter: list[str] | None = None
    negative_marking: float = 0.3333
    duration_minutes: int = 20
