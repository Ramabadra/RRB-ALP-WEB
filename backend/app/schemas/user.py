"""
User schemas.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    """Public user profile — returned by /api/users/me."""

    id: UUID
    name: str
    email: EmailStr
    profile_image: str | None
    created_at: datetime
    last_login: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    """Fields the user can update on their profile."""

    name: str | None = None
    profile_image: str | None = None
