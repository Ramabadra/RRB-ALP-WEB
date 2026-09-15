"""
Phase 1 tests: settings loading and validation.
"""

from __future__ import annotations

import pytest


def test_settings_load_from_env() -> None:
    """Settings should load correctly from the env vars set in conftest."""
    from app.core.config import get_settings
    settings = get_settings()
    assert settings.DATABASE_URL.startswith("postgresql")
    assert len(settings.SECRET_KEY) > 10
    assert settings.GOOGLE_CLIENT_ID != ""
    assert settings.ENVIRONMENT == "development"


def test_settings_allowed_origins_single() -> None:
    """Single FRONTEND_URL should produce a single-item list."""
    from app.core.config import get_settings
    settings = get_settings()
    origins = settings.allowed_origins
    assert isinstance(origins, list)
    assert len(origins) >= 1
    assert all(o.startswith("http") for o in origins)


def test_settings_max_pdf_size_bytes() -> None:
    from app.core.config import get_settings
    settings = get_settings()
    assert settings.max_pdf_size_bytes == settings.MAX_PDF_SIZE_MB * 1024 * 1024


def test_settings_not_production() -> None:
    from app.core.config import get_settings
    settings = get_settings()
    assert settings.is_production is False
