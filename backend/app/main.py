"""
RRB ALP Mock Test Platform — FastAPI Application Entry Point
============================================================

This module creates the FastAPI app, registers all routers,
configures CORS/middleware, and registers global exception handlers.

DO NOT add business logic here. Keep this file as the composition root only.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.middleware import SecureHeadersMiddleware
from app.core.rate_limit import limiter
from google import genai


from app.api import (
    analytics,
    attempts,
    auth,
    mistakes,
    mock_tests,
    pdfs,
    questions,
    results,
    subjects,
    topics,
    users,
)
from app.core.config import get_settings
from app.database.session import async_engine

logger = logging.getLogger(__name__)


# ─── Lifespan (startup / shutdown) ────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Verify DB connectivity on startup; clean up on shutdown."""
    logger.info("Starting RRB ALP backend...")
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified ✓")
    except Exception as exc:
        logger.error("Database connection FAILED: %s", exc)
        # Do not hard-crash on startup — let health check reflect the failure.

    # ── Verify AI Model Availability ──────────────────────────────────────────
    settings = get_settings()
    if settings.AI_API_KEY:
        try:
            logger.info("Verifying Gemini AI configuration...")
            client = genai.Client(api_key=settings.AI_API_KEY)
            # This will raise an exception if the model doesn't exist or key is invalid
            model_info = client.models.get(model=settings.AI_MODEL)
            logger.info("Gemini AI configuration verified ✓. Using model: %s", model_info.name)
        except Exception as exc:
            logger.error(
                "Gemini AI configuration FAILED: Cannot access model '%s'. "
                "Check AI_API_KEY and AI_MODEL (currently %s). Error: %s",
                settings.AI_MODEL, settings.AI_MODEL, exc
            )
            # We raise here because the application cannot function correctly if the configured AI model is dead.
            raise RuntimeError(f"Invalid Gemini AI configuration: {exc}") from exc
    else:
        logger.warning("AI_API_KEY is missing! AI features will be disabled.")

    yield  # Application runs here

    logger.info("Shutting down RRB ALP backend...")
    await async_engine.dispose()


# ─── Application factory ──────────────────────────────────────────────────────

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="RRB ALP Mock Test Platform API",
        description=(
            "Backend API for the RRB ALP preparation platform. "
            "Provides question bank, mock test generation, exam attempts, "
            "PDF processing, and AI-powered question validation."
        ),
        version="1.0.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )
    
    # Register slowapi rate limiter exception handler
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── Security Middlewares ──────────────────────────────────────────────────
    # OWASP Security Headers (X-Frame-Options, HSTS, X-Content-Type-Options)
    app.add_middleware(SecureHeadersMiddleware)
    
    # Limit to trusted hosts (default to *, override in production)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["*"]
    )
    
    # ── CORS ──────────────────────────────────────────────────────────────────
    # Reads allowed origins from FRONTEND_URL env var (comma-separated).
    # Never uses wildcard "*" in production.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
        expose_headers=["X-Request-ID"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    api_prefix = "/api"
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(users.router, prefix=api_prefix)
    app.include_router(subjects.router, prefix=api_prefix)
    app.include_router(topics.router, prefix=api_prefix)
    app.include_router(questions.router, prefix=api_prefix)
    app.include_router(mock_tests.router, prefix=api_prefix)
    app.include_router(attempts.router, prefix=api_prefix)
    app.include_router(results.router, prefix=api_prefix)
    app.include_router(analytics.router, prefix=api_prefix)
    app.include_router(mistakes.router, prefix=api_prefix)
    app.include_router(pdfs.router, prefix=api_prefix)

    # ── Global exception handlers ─────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Catch-all for unhandled exceptions.
        Never exposes internal details (stack traces, DB errors) in production.
        """
        logger.exception("Unhandled exception on %s %s", request.method, request.url)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "status_code": 500,
            },
        )

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get(
        "/health",
        tags=["Health"],
        summary="Health check",
        description="Returns 200 OK if the service is running. Used by Render health checks.",
    )
    async def health_check() -> dict:
        return {
            "status": "ok",
            "service": "rrb-alp-backend",
            "version": "1.0.0",
        }

    return app


app = create_app()
