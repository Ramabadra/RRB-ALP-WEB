"""
Auth router — Google OAuth 2.0 + JWT issuance.

Routes:
  GET  /api/auth/google/login     → returns authorization URL
  GET  /api/auth/google/callback  → handles code, returns JWT
  POST /api/auth/logout           → stateless logout
"""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.auth.google import (
    build_authorization_url,
    exchange_code_for_token,
    get_callback_uri,
    get_google_user_info,
)
from app.core.config import get_settings
from app.core.dependencies import CurrentUser, DbSession
from app.schemas.auth import GoogleAuthInitResponse, TokenResponse
from app.schemas.common import MessageResponse
from app.services.user_service import UserService
from app.core.rate_limit import limiter


router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger(__name__)


@router.get(
    "/google/login",
    response_model=GoogleAuthInitResponse,
    summary="Initiate Google OAuth login",
    description=(
        "Returns the Google OAuth authorization URL. "
        "The frontend should redirect the user's browser to this URL."
    ),
)
@limiter.limit("5/minute")
async def google_login(request: Request) -> GoogleAuthInitResponse:
    """
    Step 1 of Google OAuth.
    Returns the URL the frontend must redirect the browser to.
    """
    redirect_uri = get_callback_uri()
    authorization_url, _state = build_authorization_url(redirect_uri)
    return GoogleAuthInitResponse(authorization_url=authorization_url)


@router.get(
    "/google/callback",
    response_model=TokenResponse,
    summary="Google OAuth callback",
    description=(
        "Google redirects here after the user grants consent. "
        "Exchanges the authorization code for a JWT access token."
    ),
)
async def google_callback(
    request: Request,
    db: DbSession,
    code: str | None = None,
    error: str | None = None,
) -> TokenResponse:
    """
    Step 2 of Google OAuth.
    Receives ?code=xxx from Google, exchanges it for tokens,
    fetches user info, upserts the user record, and returns a JWT.
    """
    # Google sends ?error=access_denied if user cancelled
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google OAuth error: {error}",
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code from Google.",
        )

    redirect_uri = get_callback_uri()

    # ── Exchange code for Google tokens ──────────────────────────────────────
    try:
        token_response = await exchange_code_for_token(code, redirect_uri)
    except httpx.HTTPStatusError as exc:
        logger.error("Google token exchange failed: %s", exc.response.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to exchange authorization code with Google.",
        )

    access_token: str | None = token_response.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google did not return an access token.",
        )

    # ── Fetch user info ───────────────────────────────────────────────────────
    try:
        google_user = await get_google_user_info(access_token)
    except httpx.HTTPStatusError as exc:
        logger.error("Google userinfo fetch failed: %s", exc.response.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch user info from Google.",
        )

    # ── Upsert user + issue JWT ───────────────────────────────────────────────
    service = UserService(db)
    user, _created = await service.get_or_create_from_google(google_user)
    jwt_token, expires_in = service.issue_token(user)

    logger.info("User %s (%s) authenticated via Google.", user.id, user.email)

    return TokenResponse(
        access_token=jwt_token,
        token_type="bearer",
        expires_in=expires_in,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout",
    description=(
        "Stateless JWT logout — the backend does not maintain a session. "
        "The frontend must discard the stored access token."
    ),
)
async def logout(current_user: CurrentUser) -> MessageResponse:
    """
    Logout endpoint. Since JWTs are stateless, this just confirms the
    token was valid and tells the frontend to discard it.
    For a full blocklist-based logout, a Redis token denylist can be added in Phase 7.
    """
    logger.info("User %s logged out.", current_user.id)
    return MessageResponse(message="Logged out successfully.")
