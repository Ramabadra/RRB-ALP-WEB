"""
Auth schemas.
"""

from __future__ import annotations

from pydantic import BaseModel, HttpUrl


class GoogleAuthInitResponse(BaseModel):
    """Returned by GET /api/auth/google/login — URL to redirect browser to."""

    authorization_url: str


class TokenResponse(BaseModel):
    """Returned after successful OAuth callback."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenRefreshRequest(BaseModel):
    """Not used for Google OAuth (stateless JWT), kept for future extensibility."""

    refresh_token: str


class AuthCallbackParams(BaseModel):
    """Query params Google sends to the callback URL."""

    code: str
    state: str | None = None
