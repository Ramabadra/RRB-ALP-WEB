"""
RRB ALP Mock Test Platform — Backend Configuration
===================================================
All settings are loaded exclusively from environment variables.
Never hardcode secrets. Never commit .env files.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ─── Database ────────────────────────────────────────────────────────────
    DATABASE_URL: str  
    # ─── Security ────────────────────────────────────────────────────────────
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ─── Google OAuth ────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    # ─── CORS ────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins
    FRONTEND_URL: str = "http://localhost:3000"

    # ─── AI — Google Gemini ──────────────────────────────────────────────────
    AI_API_KEY: str = ""
    AI_MODEL: str = "gemini-3.8-flash"

    # ─── Object Storage — Supabase Storage (S3-compatible) ───────────────────
    STORAGE_ENDPOINT: str = ""
    STORAGE_ACCESS_KEY: str = ""
    STORAGE_SECRET_KEY: str = ""
    STORAGE_BUCKET: str = "rrb-alp-pdfs"
    STORAGE_REGION: str = "ap-south-1"

    # ─── PDF Processing ──────────────────────────────────────────────────────
    MAX_PDF_SIZE_MB: int = 50

    # ─── Redis / Celery ──────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ─── Environment ─────────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"

    # ─── Derived helpers ─────────────────────────────────────────────────────
    @property
    def allowed_origins(self) -> List[str]:
        """Parse comma-separated FRONTEND_URL into a list of allowed origins."""
        return [url.strip() for url in self.FRONTEND_URL.split(",") if url.strip()]

    @property
    def max_pdf_size_bytes(self) -> int:
        return self.MAX_PDF_SIZE_MB * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v.startswith("postgresql"):
            raise ValueError(
                "DATABASE_URL must be a PostgreSQL connection string "
                "(e.g. postgresql+asyncpg://...)"
            )
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings. Use this as a FastAPI dependency."""
    return Settings()
