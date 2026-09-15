"""
Subjects router — list and retrieve RRB ALP exam subjects.

Routes:
  GET /api/subjects          → list all subjects
  GET /api/subjects/{id}     → get one subject by UUID
"""

from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter

from app.core.dependencies import DbSession
from app.schemas.subject import SubjectResponse
from app.services.subject_service import SubjectService

router = APIRouter(prefix="/subjects", tags=["Subjects"])


@router.get(
    "",
    response_model=List[SubjectResponse],
    summary="List all subjects",
    description=(
        "Returns all exam subjects in display order. "
        "No authentication required — used to populate filters and navigation."
    ),
)
async def list_subjects(db: DbSession) -> List[SubjectResponse]:
    service = SubjectService(db)
    subjects = await service.list_subjects()
    return [SubjectResponse.model_validate(s) for s in subjects]


@router.get(
    "/{subject_id}",
    response_model=SubjectResponse,
    summary="Get a subject by ID",
    description="Returns a single subject by its UUID.",
)
async def get_subject(subject_id: UUID, db: DbSession) -> SubjectResponse:
    service = SubjectService(db)
    subject = await service.get_subject(subject_id)
    return SubjectResponse.model_validate(subject)
