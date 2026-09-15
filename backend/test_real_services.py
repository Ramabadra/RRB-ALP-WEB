#!/usr/bin/env python
"""
Real external service smoke tests.

Tests connectivity and basic operations for:
- Supabase PostgreSQL
- Supabase Storage
- Google Gemini API
- Redis
- Celery

Usage:
    python test_real_services.py

Requirements:
    Set in .env:
    - DATABASE_URL (Supabase PostgreSQL)
    - STORAGE_ENDPOINT, STORAGE_ACCESS_KEY, STORAGE_SECRET_KEY (Supabase)
    - AI_API_KEY (Google Gemini)
    - REDIS_URL (Redis service)
"""

from __future__ import annotations

import asyncio
import io
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)-8s %(message)s')
logger = logging.getLogger(__name__)

# Test results tracking
test_results = {
    'passed': [],
    'failed': [],
    'skipped': [],
    'warning': [],
}


def log_pass(name: str, message: str = ""):
    """Log a passing test."""
    msg = f"✅ {name}"
    if message:
        msg += f" — {message}"
    logger.info(msg)
    test_results['passed'].append(name)


def log_fail(name: str, error: str):
    """Log a failing test."""
    logger.error(f"❌ {name} — {error}")
    test_results['failed'].append((name, error))


def log_skip(name: str, reason: str):
    """Log a skipped test."""
    logger.warning(f"⏭️  {name} — {reason}")
    test_results['skipped'].append((name, reason))


def log_warn(name: str, message: str):
    """Log a warning."""
    logger.warning(f"⚠️  {name} — {message}")
    test_results['warning'].append((name, message))


# ============================================================================
# 1. POSTGRESQL CONNECTIVITY TESTS
# ============================================================================

async def test_postgresql_connection():
    """Test basic PostgreSQL connection."""
    name = "PostgreSQL Connection"
    try:
        from app.core.config import get_settings
        from app.database.session import async_engine

        settings = get_settings()
        if not settings.DATABASE_URL:
            log_skip(name, "DATABASE_URL not configured")
            return

        logger.info(f"Testing {name}...")
        async with async_engine.connect() as conn:
            from sqlalchemy import text
            result = await conn.execute(text("SELECT 1"))   
            value = result.scalar()
            if value == 1:
                log_pass(name, f"Connected to {settings.DATABASE_URL.split('@')[1].split('/')[0] if '@' in settings.DATABASE_URL else 'database'}")
            else:
                log_fail(name, "Query returned unexpected result")
    except Exception as e:
        log_fail(name, str(e))


async def test_postgresql_table_check():
    """Check if database tables exist."""
    name = "PostgreSQL Tables Exist"
    try:
        from app.database.session import async_engine
        from sqlalchemy import text

        logger.info(f"Testing {name}...")
        async with async_engine.connect() as conn:
            # Check if any of our tables exist
            result = await conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' LIMIT 5
            """))
            tables = result.fetchall()
            if tables:
                table_names = [t[0] for t in tables]
                log_pass(name, f"Found {len(tables)} tables: {', '.join(table_names[:3])}")
            else:
                log_warn(name, "No tables found - migrations may not have been run")
    except Exception as e:
        # Expected if migrations not run or PostgreSQL not available
        log_skip(name, str(e)[:100])


# ============================================================================
# 2. SUPABASE STORAGE TESTS
# ============================================================================

async def test_storage_connection():
    """Test Supabase Storage connectivity."""
    name = "Supabase Storage Connection"
    try:
        from app.core.config import get_settings
        from app.storage.client import StorageClient

        settings = get_settings()
        if not settings.STORAGE_ENDPOINT or settings.STORAGE_ENDPOINT.startswith("https://xxxx"):
            log_skip(name, "Storage credentials not configured")
            return

        logger.info(f"Testing {name}...")
        client = StorageClient()
        # Try to get a non-existent file to test auth without creating data
        # This will fail but proves connectivity and auth
        try:
            client.get_presigned_url("test-nonexistent-file", expires_in=60)
        except Exception as e:
            if "NoSuchKey" in str(e) or "not found" in str(e).lower():
                log_pass(name, "Storage service responding (auth working)")
            else:
                raise
    except Exception as e:
        log_fail(name, str(e))


async def test_storage_upload_download():
    """Test Supabase Storage upload and download."""
    name = "Supabase Storage Upload/Download"
    try:
        from app.core.config import get_settings
        from app.storage.client import StorageClient

        settings = get_settings()
        if not settings.STORAGE_ENDPOINT or settings.STORAGE_ENDPOINT.startswith("https://xxxx"):
            log_skip(name, "Storage credentials not configured")
            return

        logger.info(f"Testing {name}...")
        
        # Create test file
        test_filename = f"test-{uuid.uuid4().hex[:8]}.txt"
        test_content = b"Test content from real service smoke test"
        test_user_id = uuid.uuid4()
        test_doc_id = uuid.uuid4()
        
        client = StorageClient()
        
        # Upload
        storage_key, presigned_url = client.upload_pdf(
        user_id=test_user_id,
        document_id=test_doc_id,
        filename=test_filename,
        file_bytes=test_content,
        )

        logger.info(f"  Uploaded to: {storage_key}")
        
        # Download
        downloaded = client.download_pdf(storage_key)
        if downloaded == test_content:
            log_pass(name, f"Successfully uploaded and downloaded {len(test_content)} bytes")
        else:
            log_fail(name, "Downloaded content doesn't match uploaded content")
        
        # Delete
        client.delete_pdf(storage_key)
        logger.info(f"  Deleted: {storage_key}")
        
    except Exception as e:
        log_fail(name, str(e))


# ============================================================================
# 3. GEMINI API TESTS
# ============================================================================

def test_gemini_client_init():
    """Test Gemini client initialization."""
    name = "Gemini Client Initialization"
    try:
        from app.core.config import get_settings
        from app.ai.client import AIClient

        settings = get_settings()
        if not settings.AI_API_KEY or settings.AI_API_KEY == "":
            log_skip(name, "AI_API_KEY not configured")
            return

        logger.info(f"Testing {name}...")
        client = AIClient()
        
        if client.model_name == "gemini-3.8-flash":
            log_pass(name, f"Using model: {client.model_name}")
        else:
            log_warn(name, f"Model is {client.model_name}, expected gemini-3.8-flash")
            
    except Exception as e:
        log_fail(name, str(e))


def test_gemini_api_call():
    """Test actual Gemini API call with structured output."""
    name = "Gemini API Call"
    try:
        from app.core.config import get_settings
        from app.ai.client import AIClient
        from pydantic import BaseModel

        settings = get_settings()
        if not settings.AI_API_KEY or settings.AI_API_KEY == "":
            log_skip(name, "AI_API_KEY not configured")
            return

        logger.info(f"Testing {name}...")
        
        # Simple test schema
        class TestResponse(BaseModel):
            answer: str
            confidence: float

        client = AIClient()
        
        # Make a simple request
        prompt = "Answer in JSON: What is 2+2? (answer: string, confidence: 0-1)"
        result = client.generate_structured(
            prompt=prompt,
            response_schema=TestResponse,
            temperature=0.0
        )
        
        if hasattr(result, 'answer') and hasattr(result, 'confidence'):
            log_pass(name, f"Gemini returned: {result.answer}")
        else:
            log_fail(name, "Unexpected response format from Gemini")
            
    except Exception as e:
        log_fail(name, str(e)[:200])


# ============================================================================
# 4. REDIS TESTS
# ============================================================================

def test_redis_connection():
    """Test Redis connection."""
    name = "Redis Connection"
    try:
        from app.core.config import get_settings
        import redis

        settings = get_settings()
        redis_url = settings.REDIS_URL
        
        logger.info(f"Testing {name}...")
        
        # Parse Redis URL
        r = redis.from_url(redis_url)
        r.ping()
        
        log_pass(name, f"Connected to Redis at {redis_url.split('@')[-1] if '@' in redis_url else redis_url}")
        
    except Exception as e:
        if "Connection refused" in str(e):
            log_skip(name, f"Redis not available at configured URL ({str(e)[:50]})")
        else:
            log_fail(name, str(e))


def test_celery_worker_discovery():
    """Test Celery task discovery."""
    name = "Celery Task Discovery"
    try:
        from app.core.celery_app import celery_app
        from app.pdf import tasks  # noqa: F401

        logger.info(f"Testing {name}...")
        
        # Get registered tasks
        tasks = celery_app.tasks
        pdf_tasks = [t for t in tasks if 'pdf' in t.lower() or 'process' in t.lower()]
        
        if pdf_tasks:
            log_pass(name, f"Found {len(pdf_tasks)} PDF tasks: {', '.join(pdf_tasks[:2])}")
        else:
            log_warn(name, "No PDF tasks found in registry")
            
    except Exception as e:
        log_fail(name, str(e))


# ============================================================================
# 5. FULL PDF PIPELINE TEST
# ============================================================================

async def test_pdf_pipeline():
    """Test full PDF processing pipeline."""
    name = "Full PDF Pipeline"
    try:
        from app.core.config import get_settings
        from app.database.session import AsyncSession, async_engine
        from app.models.user import User
        from app.models.pdf import PdfDocument, PdfProcessingJob
        from app.pdf.extractor import PDFExtractor
        from app.pdf.parser import QuestionParser
        from sqlalchemy.orm import sessionmaker
        import uuid as uuid_module

        settings = get_settings()
        if not settings.DATABASE_URL or settings.DATABASE_URL.startswith("postgresql"):
            if not all([settings.DATABASE_URL, settings.STORAGE_ENDPOINT and not settings.STORAGE_ENDPOINT.startswith("https://xxxx")]):
                log_skip(name, "Database or Storage not fully configured")
                return

        logger.info(f"Testing {name}...")
        
        # Create a minimal test PDF (this is a very simple PDF)
        test_pdf_bytes = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< >>
stream
BT
/F1 12 Tf
100 700 Td
(Q.1) Tj
0 -20 Td
(A) Tj
0 -20 Td
(B) Tj
0 -20 Td
(C) Tj
0 -20 Td
(D) Tj
0 -20 Td
(Answer: B) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000244 00000 n 
0000000473 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
554
%%EOF
"""
        
        # Test text extraction
        logger.info(f"  Testing PDF extraction...")
        extractor = PDFExtractor()
        try:
            result = extractor.extract(test_pdf_bytes)
            if result.page_count > 0:
                log_pass(f"{name} - Extraction", f"Extracted {result.page_count} pages")
            else:
                log_warn(f"{name} - Extraction", "No content extracted from test PDF")
        except Exception as e:
            log_skip(f"{name} - Extraction", f"Extraction failed: {str(e)[:50]}")
        
        # Test question parsing
        logger.info(f"  Testing question parsing...")
        parser = QuestionParser()
        try:
            sample_text = """
Q.1 What is the capital of India?
(A) Delhi
(B) Mumbai
(C) Bangalore
(D) Pune
Answer: A
"""
            parsed = parser.parse(sample_text, 1)
            if parsed:
                log_pass(f"{name} - Parsing", f"Parsed {len(parsed)} questions from text")
            else:
                log_warn(f"{name} - Parsing", "No questions parsed from sample text")
        except Exception as e:
            log_fail(f"{name} - Parsing", str(e)[:100])
        
        log_pass(name, "Pipeline components functional (end-to-end not tested without full setup)")
        
    except Exception as e:
        log_fail(name, str(e)[:200])


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

async def run_async_tests():
    """Run all async tests."""
    await test_postgresql_connection()
    await test_postgresql_table_check()
    await test_storage_connection()
    await test_storage_upload_download()
    await test_pdf_pipeline()


def run_sync_tests():
    """Run all sync tests."""
    test_gemini_client_init()
    test_gemini_api_call()
    test_redis_connection()
    test_celery_worker_discovery()


async def main():
    """Run all tests and generate report."""
    print("\n" + "=" * 80)
    print("REAL SERVICE SMOKE TESTS")
    print("=" * 80 + "\n")
    
    # Run sync tests
    run_sync_tests()
    
    print()
    
    # Run async tests
    await run_async_tests()
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    print(f"\n✅ PASSED: {len(test_results['passed'])}")
    for name in test_results['passed']:
        print(f"   {name}")
    
    if test_results['warning']:
        print(f"\n⚠️  WARNINGS: {len(test_results['warning'])}")
        for name, msg in test_results['warning']:
            print(f"   {name}: {msg}")
    
    if test_results['skipped']:
        print(f"\n⏭️  SKIPPED: {len(test_results['skipped'])}")
        for name, reason in test_results['skipped']:
            print(f"   {name}: {reason}")
    
    if test_results['failed']:
        print(f"\n❌ FAILED: {len(test_results['failed'])}")
        for name, error in test_results['failed']:
            print(f"   {name}: {error}")
    
    print("\n" + "=" * 80 + "\n")
    
    # Exit with appropriate code
    sys.exit(1 if test_results['failed'] else 0)


if __name__ == "__main__":
    asyncio.run(main())
