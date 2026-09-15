"""
User repository — all DB queries for the User model.

Rules:
- Never contains business logic; that lives in UserService.
- All methods accept an AsyncSession and return ORM objects or None.
- All SQL is parameterized via SQLAlchemy — no string formatting.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        result = await self._db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_google_id(self, google_id: str) -> Optional[User]:
        result = await self._db.execute(
            select(User).where(User.google_id == google_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self._db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        google_id: str,
        name: str,
        email: str,
        profile_image: str | None = None,
    ) -> User:
        user = User(
            google_id=google_id,
            name=name,
            email=email,
            profile_image=profile_image,
        )
        self._db.add(user)
        await self._db.flush()   # get the generated UUID without committing
        await self._db.refresh(user)
        return user

    async def update_last_login(self, user_id: UUID) -> None:
        await self._db.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_login=datetime.now(timezone.utc))
        )

    async def update_profile(
        self,
        user_id: UUID,
        *,
        name: str | None = None,
        profile_image: str | None = None,
    ) -> Optional[User]:
        values: dict = {}
        if name is not None:
            values["name"] = name
        if profile_image is not None:
            values["profile_image"] = profile_image

        if not values:
            return await self.get_by_id(user_id)

        await self._db.execute(
            update(User).where(User.id == user_id).values(**values)
        )
        await self._db.flush()
        return await self.get_by_id(user_id)
