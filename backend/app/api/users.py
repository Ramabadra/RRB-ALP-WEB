"""
Users router — current user profile management.

Routes:
  GET   /api/users/me   → return current user profile
  PATCH /api/users/me   → update name / profile_image
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.user import UserResponse, UserUpdateRequest
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Returns the authenticated user's profile information.",
)
async def get_me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
    description="Update editable profile fields (name, profile_image).",
)
async def update_me(
    body: UserUpdateRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> UserResponse:
    service = UserService(db)
    updated_user = await service.update_profile(
        current_user.id,
        name=body.name,
        profile_image=body.profile_image,
    )
    return UserResponse.model_validate(updated_user)
