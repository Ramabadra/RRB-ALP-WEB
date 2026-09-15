"""
Attempt and AttemptAnswer schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.schemas.question import AnswerChoice


class AttemptCreateRequest(BaseModel):
    """POST /api/attempts — create a new attempt for a mock test."""

    mock_test_id: UUID


class AttemptResponse(BaseModel):
    """Full attempt response — includes timer info for frontend reconstruction."""

    id: UUID
    user_id: UUID
    mock_test_id: UUID
    status: str
    started_at: datetime | None
    expires_at: datetime | None
    submitted_at: datetime | None
    auto_submitted: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AnswerSaveRequest(BaseModel):
    """
    POST /api/attempts/{id}/answers

    Saves one or more answers in a single call.
    The backend upserts each answer — safe to call repeatedly.
    """

    answers: List["SingleAnswerSave"]


class SingleAnswerSave(BaseModel):
    question_id: UUID
    # None = clear/unanswer the question
    selected_answer: AnswerChoice | None = None
    is_marked: bool = False


class AttemptStatusResponse(BaseModel):
    """
    Returned by GET /api/attempts/{id} during an active exam.
    Includes the server timestamps so the frontend can reconstruct the timer.
    """

    id: UUID
    status: str
    started_at: datetime | None
    expires_at: datetime | None
    # Seconds remaining as computed by backend (convenience field)
    seconds_remaining: int | None
    total_questions: int
    answered_count: int
    marked_count: int

    model_config = {"from_attributes": True}


class SubmitResponse(BaseModel):
    """Response from POST /api/attempts/{id}/submit."""

    attempt_id: UUID
    result_id: UUID
    message: str = "Attempt submitted successfully."
