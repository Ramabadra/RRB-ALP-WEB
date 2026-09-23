"""
Attempt and AttemptAnswer schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

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


class PersistedAnswer(BaseModel):
    """
    A single answer row returned inside AttemptStatusResponse.

    Deliberately mirrors SingleAnswerSave so the frontend can seed its local
    answer state directly.  This schema MUST NOT include correct_answer,
    explanation, or any scoring information — the status endpoint is called
    during active exams.
    """

    question_id: UUID
    selected_answer: AnswerChoice | None = None
    is_marked: bool = False

    model_config = {"from_attributes": True}


class AttemptStatusResponse(BaseModel):
    """
    Returned by GET /api/attempts/{attempt_id}/status.

    Contains everything the frontend needs to reconstruct the exam after a
    browser refresh, reconnect, or tab switch:
      - Server-computed seconds_remaining (authoritative timer)
      - mock_test_id to reload the question list
      - answers list with the user's persisted selections and mark-for-review flags

    IMPORTANT: correct_answer is never included.  This endpoint is safe to
    call during an active exam session.
    """

    id: UUID
    mock_test_id: UUID
    status: str
    started_at: datetime | None
    expires_at: datetime | None
    # Seconds remaining as computed by the server from expires_at.
    # None when the attempt is NOT_STARTED or already SUBMITTED/EXPIRED.
    seconds_remaining: Optional[int]
    total_questions: int
    answered_count: int
    marked_count: int
    # Persisted answer state — used to restore the exam UI on refresh.
    answers: List[PersistedAnswer] = []

    model_config = {"from_attributes": True}


class SubmitResponse(BaseModel):
    """Response from POST /api/attempts/{id}/submit."""

    attempt_id: UUID
    result_id: UUID
    message: str = "Attempt submitted successfully."
