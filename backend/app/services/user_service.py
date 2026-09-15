"""
User service — business logic for authentication and user management.

Responsibilities:
- Orchestrate the Google OAuth → User upsert flow
- Issue JWT tokens
- Enforce user-level business rules

Does NOT:
- Touch the DB directly (delegates to UserRepository)
- Know about HTTP requests/responses (that's the router's job)
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import create_access_token
from app.models.user import User
from app.repositories.user_repository import UserRepository

class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = UserRepository(db)

    async def get_or_create_from_google(
        self, google_user_info: Dict[str, Any]
    ) -> tuple[User, bool]:
        """
        Upsert a User from Google OAuth user-info payload.

        Args:
            google_user_info: The dict returned by get_google_user_info()
                              Keys: sub, email, name, picture, email_verified

        Returns:
            (user, created) — created=True if this is a new account.

        Raises:
            HTTPException 400 if the Google email is not verified.
        """
        google_id: str = google_user_info["sub"]
        email: str = google_user_info.get("email", "")
        name: str = google_user_info.get("name", "User")
        picture: str | None = google_user_info.get("picture")
        email_verified: bool = google_user_info.get("email_verified", False)

        if not email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google account email is not verified.",
            )

        # Try by google_id first (primary key for OAuth users)
        user = await self._repo.get_by_google_id(google_id)

        if user is not None:
            await self._repo.update_last_login(user.id)
            return user, False

        # Fallback: check if the email is already registered (edge case)
        user = await self._repo.get_by_email(email)
        if user is not None:
            # Link existing email account to Google
            await self._repo.update_last_login(user.id)
            return user, False

        # Create new user
        user = await self._repo.create(
            google_id=google_id,
            name=name,
            email=email,
            profile_image=picture,
        )
        return user, True

    async def get_user_by_id(self, user_id) -> User:
        """
        Fetch a user by their UUID primary key.
        Raises 404 if not found.
        """
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        return user

    async def update_profile(
        self,
        user_id,
        *,
        name: str | None = None,
        profile_image: str | None = None,
    ) -> User:
        """Update the user's editable profile fields."""
        user = await self._repo.update_profile(
            user_id, name=name, profile_image=profile_image
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        return user

    def issue_token(self, user: User) -> tuple[str, int]:
        """
        Create a signed JWT for the given user.

        Returns:
            (token_string, expires_in_seconds)
        """
        settings = get_settings()
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        token = create_access_token(
            subject=str(user.id),
            expires_delta=expires_delta,
            extra_claims={"email": user.email, "name": user.name},
        )
        expires_in = int(expires_delta.total_seconds())
        return token, expires_in
