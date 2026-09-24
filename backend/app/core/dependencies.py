"""
FastAPI dependency injectors.
Import these in route handlers to get DB sessions, current users, etc.
"""

from __future__ import annotations

from typing import Annotated, AsyncGenerator
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import decode_access_token
from app.database.session import AsyncSessionLocal
from app.models.user import User

# ─── Reusable dependency type aliases ─────────────────────────────────────────
SettingsDep = Annotated[Settings, Depends(get_settings)]

bearer_scheme = HTTPBearer(auto_error=False)


# ─── Database session ─────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy session, automatically closed after the request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DbSession = Annotated[AsyncSession, Depends(get_db)]


# ─── Authentication — UUID only ───────────────────────────────────────────────
async def get_current_user_id(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
) -> UUID:
    """
    Extract and validate the JWT Bearer token from the Authorization header.
    Returns the current user's UUID.
    Raises 401 if the token is missing, malformed, or expired.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise ValueError("No subject in token")
        return UUID(user_id_str)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]


async def get_current_user_id_optional(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
) -> UUID | None:
    """Like get_current_user_id but returns None for unauthenticated requests."""
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            return None
        return UUID(user_id_str)
    except (JWTError, ValueError):
        return None


OptionalUserId = Annotated[UUID | None, Depends(get_current_user_id_optional)]


# ─── Authentication — full User object ───────────────────────────────────────
async def get_current_user(
    user_id: CurrentUserId,
    db: DbSession,
) -> "User":  # type: ignore[name-defined]  # noqa: F821
    """
    Resolve the JWT user ID to a full User ORM object.
    Raises 401 if the user no longer exists in the database.
    Use this dependency when you need the full User (e.g. for profile endpoints).
    Use CurrentUserId when you only need the UUID (cheaper — no DB round-trip).
    """
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
