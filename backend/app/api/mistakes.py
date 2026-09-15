"""Mistakes router."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.mistake import MistakeAddRequest, MistakePracticeRequest, MistakeResponse
from app.schemas.question import QuestionResponse
from app.services.mistake_service import MistakeService

router = APIRouter(prefix="/mistakes", tags=["Mistake Book"])


@router.get("", response_model=dict)
async def list_mistakes(
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    service = MistakeService(db)
    return await service.list_mistakes(user.id, page, page_size)


@router.post("", response_model=MistakeResponse, status_code=status.HTTP_201_CREATED)
async def add_mistake(
    body: MistakeAddRequest,
    db: DbSession,
    user: CurrentUser,
):
    service = MistakeService(db)
    return await service.add_mistake(user.id, body)


@router.delete("/{mistake_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mistake(
    mistake_id: UUID,
    db: DbSession,
    user: CurrentUser,
):
    service = MistakeService(db)
    await service.delete_mistake(user.id, mistake_id)


@router.post("/practice", response_model=List[QuestionResponse])
async def practice_from_mistakes(
    body: MistakePracticeRequest,
    db: DbSession,
    user: CurrentUser,
):
    service = MistakeService(db)
    return await service.get_practice_questions(user.id, limit=body.question_count)
