"""
Attempts router — exam session lifecycle.

Routes:
  POST /api/attempts                      → create attempt (pre-start)
  POST /api/attempts/{id}/start           → start timer (NOT_STARTED → IN_PROGRESS)
  GET  /api/attempts/{id}/status          → live status + seconds_remaining
  POST /api/attempts/{id}/answers         → upsert answers (autosave)
  POST /api/attempts/{id}/submit          → submit → triggers scoring
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from app.core.dependencies import CurrentUserId, DbSession
from app.schemas.attempt import (
    AnswerSaveRequest,
    AttemptCreateRequest,
    AttemptResponse,
    AttemptStatusResponse,
    SubmitResponse,
)
from app.services.attempt_service import AttemptService

router = APIRouter(prefix="/attempts", tags=["Attempts"])


@router.post(
    "",
    response_model=AttemptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new attempt",
    description=(
        "Creates an attempt record in NOT_STARTED state. "
        "Call POST /attempts/{id}/start to begin the timer."
    ),
)
async def create_attempt(
    body: AttemptCreateRequest,
    db: DbSession,
    user_id: CurrentUserId,
) -> AttemptResponse:
    service = AttemptService(db)
    attempt = await service.create_attempt(user_id, body.mock_test_id)
    return AttemptResponse.model_validate(attempt)


@router.post(
    "/{attempt_id}/start",
    response_model=AttemptResponse,
    summary="Start the exam timer",
    description=(
        "Transitions the attempt from NOT_STARTED to IN_PROGRESS. "
        "Sets started_at and expires_at on the server. "
        "Safe to call again if already started (idempotent)."
    ),
)
async def start_attempt(
    attempt_id: UUID,
    db: DbSession,
    user_id: CurrentUserId,
) -> AttemptResponse:
    service = AttemptService(db)
    attempt = await service.start_attempt(attempt_id, user_id)
    return AttemptResponse.model_validate(attempt)


@router.get(
    "/{attempt_id}/status",
    response_model=AttemptStatusResponse,
    summary="Get live exam status",
    description=(
        "Returns the current attempt status. "
        "seconds_remaining is computed by the server from expires_at. "
        "If the timer has expired, the attempt is auto-submitted and status=EXPIRED is returned."
    ),
)
async def get_attempt_status(
    attempt_id: UUID,
    db: DbSession,
    user_id: CurrentUserId,
) -> AttemptStatusResponse:
    service = AttemptService(db)
    return await service.get_status(attempt_id, user_id)


@router.post(
    "/{attempt_id}/answers",
    response_model=AttemptStatusResponse,
    summary="Save answers (autosave)",
    description=(
        "Upserts one or more answers in a single call. "
        "Safe to call repeatedly — the backend replaces stale rows. "
        "Returns the updated live status after saving. "
        "Raises 409 if the attempt is not IN_PROGRESS or the timer has expired."
    ),
)
async def save_answers(
    attempt_id: UUID,
    body: AnswerSaveRequest,
    db: DbSession,
    user_id: CurrentUserId,
) -> AttemptStatusResponse:
    service = AttemptService(db)
    return await service.save_answers(attempt_id, user_id, body)


@router.post(
    "/{attempt_id}/submit",
    response_model=SubmitResponse,
    summary="Submit the attempt",
    description=(
        "Submits the attempt and triggers synchronous scoring. "
        "If the timer has already expired, the attempt is marked EXPIRED instead of SUBMITTED. "
        "Returns the result_id which you can use to fetch the full result."
    ),
)
async def submit_attempt(
    attempt_id: UUID,
    db: DbSession,
    user_id: CurrentUserId,
) -> SubmitResponse:
    service = AttemptService(db)
    return await service.submit(attempt_id, user_id)
