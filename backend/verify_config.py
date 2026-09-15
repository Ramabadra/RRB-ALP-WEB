#!/usr/bin/env python
"""Verify application configuration."""
from app.core.config import get_settings

s = get_settings()
print("=" * 60)
print("CONFIGURATION VERIFICATION")
print("=" * 60)
print(f"DATABASE_URL configured: {bool(s.DATABASE_URL)}")
if s.DATABASE_URL:
    print(f"  - Starts with postgresql+asyncpg: {s.DATABASE_URL.startswith('postgresql+asyncpg')}")
    # Mask the connection string
    masked = s.DATABASE_URL.replace(s.DATABASE_URL.split('@')[0], 'postgresql+asyncpg://****') if '@' in s.DATABASE_URL else s.DATABASE_URL
    print(f"  - Masked URL: {masked}")

print(f"\nAI Configuration:")
print(f"  - AI_API_KEY configured: {bool(s.AI_API_KEY)}")
print(f"  - AI_MODEL: {s.AI_MODEL}")

print(f"\nRedis/Celery:")
print(f"  - REDIS_URL: {s.REDIS_URL}")

print(f"\nStorage:")
print(f"  - STORAGE_ENDPOINT configured: {bool(s.STORAGE_ENDPOINT)}")
print(f"  - STORAGE_BUCKET: {s.STORAGE_BUCKET}")
print(f"  - STORAGE_REGION: {s.STORAGE_REGION}")

print(f"\nOther:")
print(f"  - ENVIRONMENT: {s.ENVIRONMENT}")
print(f"  - is_production: {s.is_production}")
print(f"  - MAX_PDF_SIZE_MB: {s.MAX_PDF_SIZE_MB}")
print(f"  - FRONTEND_URL: {s.FRONTEND_URL}")
print(f"  - Allowed origins: {s.allowed_origins}")
print("=" * 60)
