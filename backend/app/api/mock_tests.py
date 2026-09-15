"""
Mock tests router — generation and retrieval.

Routes:
  POST /api/mock-tests              → generate a new mock test
  GET  /api/mock-tests              → list user's mock tests (paginated)
  GET  /api/mock-tests/{id}         → get mock test details + question_ids
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentUserId, DbSession
from app.schemas.common import PaginatedResponse
from app.schemas.mock_test import MockTestDetailResponse, MockTestGenerateRequest, MockTestSummary
from app.services.mock_test_service import MockTestService

router = APIRouter(prefix="/mock-tests", tags=["Mock Tests"])


@router.post(
    "",
    response_model=MockTestDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a mock test",
    description=(
        "Generates a new randomised mock test from the question bank. "
        "Questions are randomly selected from VERIFIED questions matching the filters. "
        "Returns a 400 if the question bank doesn't have enough matching questions."
    ),
)
async def generate_mock_test(
    body: MockTestGenerateRequest,
    db: DbSession,
    user_id: CurrentUserId,
) -> MockTestDetailResponse:
    service = MockTestService(db)
    result = await service.generate(user_id, body)
    # Return the mock test with empty question_ids list
    # The detail endpoint provides question_ids for the exam engine
    return MockTestDetailResponse(
        id=result.id,
        title=result.title,
        user_id=result.user_id,
        question_count=result.question_count,
        duration_minutes=result.duration_minutes,
        negative_marking=result.negative_marking,
        marks_per_correct=result.marks_per_correct,
        source_type=result.source_type,
        difficulty=result.difficulty,
        created_at=result.created_at,
        question_ids=[],  # populated by GET /{id}
    )


@router.get(
    "",
    response_model=PaginatedResponse,
    summary="List my mock tests",
    description="Returns the authenticated user's mock tests, newest first.",
)
async def list_mock_tests(
    db: DbSession,
    user_id: CurrentUserId,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse:
    service = MockTestService(db)
    return await service.list_mock_tests(user_id, page, page_size)


@router.get(
    "/{mock_test_id}",
    response_model=MockTestDetailResponse,
    summary="Get mock test with question list",
    description=(
        "Returns full mock test details including the ordered list of question_ids. "
        "The frontend uses this to start the exam — question_ids are passed to "
        "the attempt engine which fetches questions individually."
    ),
)
async def get_mock_test(
    mock_test_id: UUID,
    db: DbSession,
    user_id: CurrentUserId,
) -> MockTestDetailResponse:
    service = MockTestService(db)
    data = await service.get_mock_test(mock_test_id, user_id)
    mt = data["mock_test"]
    qids = data["question_ids"]
    return MockTestDetailResponse(
        id=mt.id,
        title=mt.title,
        user_id=mt.user_id,
        question_count=mt.question_count,
        duration_minutes=mt.duration_minutes,
        negative_marking=mt.negative_marking,
        marks_per_correct=mt.marks_per_correct,
        source_type=mt.source_type,
        difficulty=mt.difficulty,
        created_at=mt.created_at,
        question_ids=qids,
    )
