"""
RRB ALP Subject Seed — idempotent startup data initialization.

This module inserts the canonical RRB ALP subjects into the production database
if they do not already exist. It is safe to run on every deployment:
  - Uses INSERT ... ON CONFLICT DO NOTHING (upsert by name)
  - Never deletes existing rows
  - Never modifies existing data

Run:
  Automatically called during FastAPI lifespan startup.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import uuid as uuid_module

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

logger = logging.getLogger(__name__)

# ─── Canonical RRB ALP subjects ───────────────────────────────────────────────
# These are the official CBT-1/CBT-2 subject areas for RRB ALP.
# short_code must be unique; display_order controls UI ordering.
CANONICAL_SUBJECTS = [
    {"name": "Mathematics",     "short_code": "MATH",  "display_order": 1},
    {"name": "Reasoning",       "short_code": "RSN",   "display_order": 2},
    {"name": "General Science", "short_code": "SCI",   "display_order": 3},
    {"name": "Physics",         "short_code": "PHY",   "display_order": 4},
    {"name": "Chemistry",       "short_code": "CHEM",  "display_order": 5},
    {"name": "Biology",         "short_code": "BIO",   "display_order": 6},
    {"name": "Current Affairs", "short_code": "CA",    "display_order": 7},
]


async def seed_subjects(conn: AsyncConnection) -> None:
    """
    Insert canonical RRB ALP subjects if they do not already exist.
    Idempotent: safe to call on every startup/redeploy.
    Does NOT modify or delete any existing subject rows.
    """
    now = datetime.now(timezone.utc)
    inserted = 0
    skipped = 0

    for subj in CANONICAL_SUBJECTS:
        # Check by name (case-insensitive) to avoid duplicates even if casing differs
        result = await conn.execute(
            text("SELECT id FROM subjects WHERE LOWER(name) = LOWER(:name)"),
            {"name": subj["name"]},
        )
        existing = result.fetchone()

        if existing:
            skipped += 1
            logger.debug("Subject already exists, skipping: %s", subj["name"])
            continue

        # Also check by short_code to avoid unique-constraint violations
        result2 = await conn.execute(
            text("SELECT id FROM subjects WHERE short_code = :code"),
            {"code": subj["short_code"]},
        )
        existing_code = result2.fetchone()

        if existing_code:
            skipped += 1
            logger.debug(
                "Subject with code '%s' already exists, skipping: %s",
                subj["short_code"], subj["name"],
            )
            continue

        new_id = uuid_module.uuid4()
        await conn.execute(
            text(
                """
                INSERT INTO subjects (id, name, short_code, description, display_order, created_at, updated_at)
                VALUES (:id, :name, :short_code, NULL, :display_order, :now, :now)
                """
            ),
            {
                "id": str(new_id),
                "name": subj["name"],
                "short_code": subj["short_code"],
                "display_order": subj["display_order"],
                "now": now,
            },
        )
        inserted += 1
        logger.info("Seeded subject: %s (id=%s)", subj["name"], new_id)

    if inserted:
        logger.info("Subject seed complete: %d inserted, %d skipped.", inserted, skipped)
    else:
        logger.info("Subject seed: all %d subjects already present, nothing inserted.", skipped)
