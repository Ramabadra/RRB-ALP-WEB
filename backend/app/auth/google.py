"""
Google OAuth 2.0 client.

Implements the Authorization Code flow using httpx for token exchange
and user-info fetching. Authlib is used only for token verification helpers.

Flow:
  1. build_authorization_url()  →  redirect browser here
  2. exchange_code_for_token()  →  POST to Google with the code
  3. get_google_user_info()     →  GET /userinfo with the access token
  4. Caller creates/updates User in DB, issues JWT
"""

from __future__ import annotations

import secrets
from typing import Any, Dict
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

SCOPES = "openid email profile"


def build_authorization_url(redirect_uri: str, state: str | None = None) -> tuple[str, str]:
    """
    Build the Google OAuth authorization URL.

    Returns:
        (authorization_url, state_token)
        The state_token must be stored in the session/cookie and
        verified when Google redirects back.
    """
    settings = get_settings()
    state = state or secrets.token_urlsafe(32)
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return url, state


async def exchange_code_for_token(code: str, redirect_uri: str) -> Dict[str, Any]:
    """
    Exchange the authorization code for Google tokens.

    Returns the raw token response dict (contains access_token, id_token, etc.)
    Raises httpx.HTTPStatusError on failure.
    """
    settings = get_settings()
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        return response.json()


async def get_google_user_info(access_token: str) -> Dict[str, Any]:
    """
    Fetch the authenticated user's profile from Google.

    Returns a dict with keys: sub, email, name, picture, email_verified.
    Raises httpx.HTTPStatusError on failure.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()


def get_callback_uri() -> str:
    """Construct the OAuth callback URL pointing to the frontend application."""
    settings = get_settings()
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    return f"{frontend_url}/callback"
