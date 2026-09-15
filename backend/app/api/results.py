"""
Results router — fetch scoring results.

Routes:
  GET /api/results/{attempt_id}   → full result for a submitted attempt
  GET /api/results                → list user's results (paginated)
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import CurrentUserId, DbSession
from app.repositories.attempt_repository import ResultRepository
from app.schemas.common import PaginatedResponse
from app.schemas.result import ResultResponse

router = APIRouter(prefix="/results", tags=["Results"])


@router.get(
    "/{attempt_id}",
    response_model=ResultResponse,
    summary="Get result for a submitted attempt",
    description=(
        "Returns the full scoring result for a submitted or expired attempt. "
        "Includes per-subject and per-topic breakdowns and per-question answer details "
        "for the review screen."
    ),
)
async def get_result(
    attempt_id: UUID,
    db: DbSession,
    user_id: CurrentUserId,
) -> ResultResponse:
    repo = ResultRepository(db)
    result = await repo.get_by_attempt_id(attempt_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found. Has the attempt been submitted?",
        )
    if result.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    return ResultResponse.model_validate(result)


@router.get(
    "",
    response_model=PaginatedResponse,
    summary="List my results",
    description="Returns the authenticated user's result history, newest first.",
)
async def list_results(
    db: DbSession,
    user_id: CurrentUserId,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse:
    import math
    repo = ResultRepository(db)
    total = await repo.count_by_user(user_id)
    results = await repo.list_by_user(user_id, page, page_size)
    total_pages = math.ceil(total / page_size) if page_size else 1
    return PaginatedResponse(
        items=[ResultResponse.model_validate(r) for r in results],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
