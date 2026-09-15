"""
Phase 2 tests: UserService and UserRepository (in-memory SQLite).
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.user_service import UserService
from tests.conftest import make_google_user_info


class TestUserService:

    @pytest.mark.asyncio
    async def test_create_new_user_from_google(self, db_session):
        """New Google login creates a user record."""
        service = UserService(db_session)
        info = make_google_user_info(email="new@example.com", name="New User")

        user, created = await service.get_or_create_from_google(info)
        await db_session.commit()

        assert created is True
        assert user.email == "new@example.com"
        assert user.name == "New User"
        assert user.google_id == info["sub"]
        assert user.id is not None

    @pytest.mark.asyncio
    async def test_existing_user_is_not_duplicated(self, db_session):
        """Logging in twice with the same Google account does not create duplicates."""
        service = UserService(db_session)
        info = make_google_user_info(email="existing@example.com")

        user1, created1 = await service.get_or_create_from_google(info)
        await db_session.commit()

        user2, created2 = await service.get_or_create_from_google(info)

        assert created1 is True
        assert created2 is False
        assert user1.id == user2.id

    @pytest.mark.asyncio
    async def test_unverified_email_is_rejected(self, db_session):
        """Google accounts with unverified emails must be rejected."""
        service = UserService(db_session)
        info = make_google_user_info(email_verified=False)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_or_create_from_google(info)

        assert exc_info.value.status_code == 400
        assert "not verified" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_issue_token_returns_jwt_string(self, db_session):
        """issue_token() returns a valid JWT string and positive expires_in."""
        service = UserService(db_session)
        info = make_google_user_info()
        user, _ = await service.get_or_create_from_google(info)
        await db_session.commit()

        token, expires_in = service.issue_token(user)

        assert isinstance(token, str)
        assert len(token) > 20
        assert expires_in > 0

    @pytest.mark.asyncio
    async def test_issued_token_contains_correct_sub(self, db_session):
        """JWT sub claim must equal the user's UUID."""
        from app.core.security import decode_access_token

        service = UserService(db_session)
        info = make_google_user_info()
        user, _ = await service.get_or_create_from_google(info)
        await db_session.commit()

        token, _ = service.issue_token(user)
        payload = decode_access_token(token)

        assert payload["sub"] == str(user.id)
        assert payload["email"] == user.email

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found_raises_404(self, db_session):
        """get_user_by_id raises 404 for unknown UUIDs."""
        import uuid
        service = UserService(db_session)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_user_by_id(uuid.uuid4())

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_profile_name(self, db_session):
        """update_profile() correctly updates the user's name."""
        service = UserService(db_session)
        info = make_google_user_info(name="Old Name")
        user, _ = await service.get_or_create_from_google(info)
        await db_session.commit()

        updated = await service.update_profile(user.id, name="New Name")
        assert updated is not None
        assert updated.name == "New Name"

    @pytest.mark.asyncio
    async def test_update_profile_no_changes_returns_user(self, db_session):
        """update_profile() with no fields still returns the user."""
        service = UserService(db_session)
        info = make_google_user_info()
        user, _ = await service.get_or_create_from_google(info)
        await db_session.commit()

        result = await service.update_profile(user.id)
        assert result is not None
        assert result.id == user.id
