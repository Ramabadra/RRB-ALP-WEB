"""
Topics router — list and retrieve topics within subjects.

Routes:
  GET /api/topics              → list all topics (optional ?subject_id= filter)
  GET /api/topics/{id}         → get one topic by UUID
"""

from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.dependencies import DbSession
from app.schemas.subject import TopicResponse
from app.services.subject_service import TopicService

router = APIRouter(prefix="/topics", tags=["Topics"])


@router.get(
    "",
    response_model=List[TopicResponse],
    summary="List topics",
    description=(
        "Returns topics, optionally filtered by subject. "
        "Pass ?subject_id=<uuid> to get topics for a specific subject only."
    ),
)
async def list_topics(
    db: DbSession,
    subject_id: UUID | None = Query(
        default=None, description="Filter by subject UUID"
    ),
) -> List[TopicResponse]:
    service = TopicService(db)
    topics = await service.list_topics(subject_id=subject_id)
    return [TopicResponse.model_validate(t) for t in topics]


@router.get(
    "/{topic_id}",
    response_model=TopicResponse,
    summary="Get a topic by ID",
    description="Returns a single topic by its UUID.",
)
async def get_topic(topic_id: UUID, db: DbSession) -> TopicResponse:
    service = TopicService(db)
    topic = await service.get_topic(topic_id)
    return TopicResponse.model_validate(topic)
