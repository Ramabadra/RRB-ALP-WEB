"""
Subject and Topic schemas.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SubjectResponse(BaseModel):
    id: UUID
    name: str
    short_code: str
    description: str | None
    display_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TopicResponse(BaseModel):
    id: UUID
    subject_id: UUID
    name: str
    display_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TopicWithSubjectResponse(TopicResponse):
    """Topic response that also includes the parent subject name."""

    subject_name: str | None = None
