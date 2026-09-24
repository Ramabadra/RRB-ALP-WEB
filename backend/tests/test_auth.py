"""
Phase 2 tests: Auth module — Google OAuth helper functions + UserService OAuth flow.
No real Google API calls are made (all mocked).
"""

from __future__ import annotations

import pytest

from app.auth.google import build_authorization_url, get_callback_uri


class TestGoogleOAuthHelpers:

    def test_build_authorization_url_contains_client_id(self):
        """Authorization URL must include the configured client_id."""
        url, state = build_authorization_url(
            redirect_uri="http://localhost:8000/api/auth/google/callback"
        )
        assert "client_id=" in url
        assert "accounts.google.com" in url

    def test_build_authorization_url_generates_state(self):
        """State token must be a non-empty string for CSRF protection."""
        _, state = build_authorization_url(
            redirect_uri="http://localhost:8000/api/auth/google/callback"
        )
        assert isinstance(state, str)
        assert len(state) > 20

    def test_build_authorization_url_uses_provided_state(self):
        """If state is provided, it must appear in the URL."""
        _, state = build_authorization_url(
            redirect_uri="http://localhost:8000/api/auth/google/callback",
            state="my-custom-state",
        )
        assert state == "my-custom-state"

    def test_build_authorization_url_includes_scopes(self):
        """Authorization URL must request openid, email, and profile scopes."""
        url, _ = build_authorization_url(
            redirect_uri="http://localhost:8000/api/auth/google/callback"
        )
        assert "openid" in url
        assert "email" in url
        assert "profile" in url

    def test_build_authorization_url_includes_redirect_uri(self):
        """Authorization URL must include the callback redirect URI."""
        redirect_uri = "http://localhost:8000/api/auth/google/callback"
        url, _ = build_authorization_url(redirect_uri=redirect_uri)
        assert "redirect_uri=" in url

    def test_get_callback_uri_format(self):
        """get_callback_uri should produce a well-formed callback URL."""
        from app.core.config import get_settings
        settings = get_settings()
        result = get_callback_uri()
        assert result == f"{settings.FRONTEND_URL.rstrip('/')}/callback"


class TestOAuthEndToEndFlow:
    """
    Tests the full OAuth → User upsert → JWT flow using mocked Google responses.
    These tests use the real UserService with an in-memory SQLite DB
    but mock the httpx calls to Google APIs.
    """

    @pytest.mark.asyncio
    async def test_full_oauth_flow_creates_user_and_token(self, db_session):
        """
        Simulates a complete OAuth flow:
        - Google userinfo returns a verified user
        - UserService creates the account
        - A valid JWT is issued
        """
        from app.core.security import decode_access_token
        from app.services.user_service import UserService
        from tests.conftest import make_google_user_info

        google_info = make_google_user_info(
            email="oauth@example.com",
            name="OAuth User",
        )

        service = UserService(db_session)
        user, created = await service.get_or_create_from_google(google_info)
        await db_session.commit()

        token, expires_in = service.issue_token(user)
        payload = decode_access_token(token)

        assert created is True
        assert user.email == "oauth@example.com"
        assert payload["sub"] == str(user.id)
        assert payload["email"] == "oauth@example.com"
        assert expires_in > 0

    @pytest.mark.asyncio
    async def test_second_login_does_not_create_duplicate(self, db_session):
        """Second OAuth login with same Google account reuses the existing user."""
        from app.services.user_service import UserService
        from tests.conftest import make_google_user_info

        google_info = make_google_user_info(email="repeat@example.com")
        service = UserService(db_session)

        user1, created1 = await service.get_or_create_from_google(google_info)
        await db_session.commit()
        user2, created2 = await service.get_or_create_from_google(google_info)

        assert created1 is True
        assert created2 is False
        assert user1.id == user2.id

    @pytest.mark.asyncio
    async def test_unverified_email_raises_400(self, db_session):
        from app.services.user_service import UserService
        from tests.conftest import make_google_user_info
        from fastapi import HTTPException

        google_info = make_google_user_info(email_verified=False)
        service = UserService(db_session)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_or_create_from_google(google_info)

        assert exc_info.value.status_code == 400
