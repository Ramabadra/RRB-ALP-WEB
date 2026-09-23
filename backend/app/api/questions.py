"""
Questions router — full question bank CRUD.

Routes:
  GET    /api/questions              → student-safe paginated list (ExamQuestionResponse)
  GET    /api/questions/{id}         → student-safe single question (ExamQuestionResponse)
  POST   /api/questions              → create manually (QuestionResponse — admin, includes correct_answer)
  PATCH  /api/questions/{id}         → partial update (QuestionResponse — admin)
  DELETE /api/questions/{id}         → delete

Security note:
  GET endpoints use ExamQuestionResponse which NEVER includes correct_answer or explanation.
  QuestionResponse (with correct_answer) is ONLY returned from write endpoints.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentUserId, DbSession
from app.core.config import get_settings
from app.schemas.common import PaginatedResponse
from app.schemas.question import (
    Difficulty,
    ExamQuestionResponse,
    Language,
    QuestionCreateRequest,
    QuestionFilterParams,
    QuestionResponse,
    QuestionUpdateRequest,
    QuestionGenerateRequest,
    QuestionValidateBatchRequest,
    SourceType,
    VerificationStatus,
)
from app.services.question_service import QuestionService
from app.services.ai_service import AIService

router = APIRouter(prefix="/questions", tags=["Questions"])


@router.get(
    "",
    response_model=PaginatedResponse,
    summary="List questions",
    description=(
        "Returns a paginated, filterable list of questions from the question bank. "
        "Response items use ExamQuestionResponse — correct_answer and explanation are NEVER included."
    ),
)
async def list_questions(
    db: DbSession,
    _user_id: CurrentUserId,
    subject_id: UUID | None = Query(None, description="Filter by subject UUID"),
    topic_id: UUID | None = Query(None, description="Filter by topic UUID"),
    source_type: SourceType | None = Query(None, description="PYQ, AI_GENERATED, or REFERENCE"),
    difficulty: Difficulty | None = Query(None, description="EASY, MEDIUM, or HARD"),
    verification_status: VerificationStatus | None = Query(None),
    source_year: int | None = Query(None, description="Filter PYQs by exam year"),
    language: Language | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse:
    filters = QuestionFilterParams(
        subject_id=subject_id,
        topic_id=topic_id,
        source_type=source_type,
        difficulty=difficulty,
        verification_status=verification_status,
        source_year=source_year,
        language=language,
    )
    service = QuestionService(db)
    return await service.list_questions(filters, page, page_size)


@router.get(
    "/{question_id}",
    response_model=ExamQuestionResponse,
    summary="Get a question by ID (student-safe)",
    description=(
        "Returns question text and options. "
        "correct_answer and explanation are NEVER included in this response. "
        "Backend grading accesses correct_answer directly from the database."
    ),
)
async def get_question(
    question_id: UUID,
    db: DbSession,
    _user_id: CurrentUserId,
) -> ExamQuestionResponse:
    service = QuestionService(db)
    question = await service.get_question(question_id)
    return ExamQuestionResponse.model_validate(question)


@router.post(
    "",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a question manually",
    description=(
        "Manually add a question to the bank. "
        "AI_GENERATED questions must have source_year=null. "
        "All manually created questions start with verification_status=UNVERIFIED."
    ),
)
async def create_question(
    body: QuestionCreateRequest,
    db: DbSession,
    _user_id: CurrentUserId,
) -> QuestionResponse:
    service = QuestionService(db)
    question = await service.create_question(body)
    return QuestionResponse.model_validate(question)


@router.patch(
    "/{question_id}",
    response_model=QuestionResponse,
    summary="Partially update a question",
    description="Update any subset of question fields. All fields are optional.",
)
async def update_question(
    question_id: UUID,
    body: QuestionUpdateRequest,
    db: DbSession,
    _user_id: CurrentUserId,
) -> QuestionResponse:
    service = QuestionService(db)
    question = await service.update_question(question_id, body)
    return QuestionResponse.model_validate(question)


@router.delete(
    "/{question_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a question",
)
async def delete_question(
    question_id: UUID,
    db: DbSession,
    _user_id: CurrentUserId,
) -> None:
    service = QuestionService(db)
    await service.delete_question(question_id)


# ── AI Endpoints ─────────────────────────────────────────────────────────────

@router.post(
    "/{question_id}/validate",
    response_model=QuestionResponse,
    summary="Validate a question using AI",
    description="Synchronously validates a single question. Updates text, options, answer, and status.",
)
async def validate_question(
    question_id: UUID,
    db: DbSession,
    _user_id: CurrentUserId,
) -> QuestionResponse:
    service = AIService(db)
    return await service.validate_question(question_id)


@router.post(
    "/validate-batch",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue a batch of questions for validation",
    description="Asynchronously validates a batch of questions using Celery (USE_CELERY=true only).",
)
async def validate_questions_batch(
    body: QuestionValidateBatchRequest,
    db: DbSession,
    _user_id: CurrentUserId,
) -> dict:
    if not get_settings().USE_CELERY:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Batch validation requires Celery. USE_CELERY is disabled in this deployment.",
        )
    from app.pdf.tasks import validate_questions_batch as task
    task.delay([str(q_id) for q_id in body.question_ids])
    return {"message": f"Queued {len(body.question_ids)} questions for validation."}


@router.post(
    "/generate",
    response_model=list[QuestionCreateRequest],
    summary="Generate new mock test questions via AI",
    description="Generates questions and returns them. Does not save them to the database.",
)
async def generate_questions(
    body: QuestionGenerateRequest,
    db: DbSession,
    _user_id: CurrentUserId,
) -> list[QuestionCreateRequest]:
    service = AIService(db)
    return await service.generate_questions(
        subject_id=body.subject_id,
        topic_id=body.topic_id,
        difficulty=body.difficulty,
        count=body.count,
    )
