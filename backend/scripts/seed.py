"""
Seed script — populates subjects and topics into the database.

Usage:
    cd backend/
    python -m scripts.seed

This script is idempotent: running it multiple times is safe.
It uses INSERT ... ON CONFLICT DO NOTHING so existing data is preserved.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import uuid
from typing import List, Tuple

# Add backend root to path so app imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database.session import AsyncSessionLocal, async_engine
from app.models.subject import Subject, Topic

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ─── Seed data ────────────────────────────────────────────────────────────────
# Format: (subject_name, short_code, display_order, topics_list)
SUBJECTS_AND_TOPICS: List[Tuple[str, str, int, List[str]]] = [
    (
        "MATHEMATICS",
        "MATH",
        1,
        [
            "Number System",
            "LCM and HCF",
            "Ratio and Proportion",
            "Percentage",
            "Profit and Loss",
            "Time and Work",
            "Time and Distance",
            "Simple Interest",
            "Compound Interest",
            "Algebra",
            "Geometry",
            "Mensuration",
            "Statistics",
        ],
    ),
    (
        "REASONING",
        "REASON",
        2,
        [
            "Analogy",
            "Classification",
            "Series",
            "Coding-Decoding",
            "Blood Relations",
            "Direction and Distance",
            "Venn Diagram",
            "Syllogism",
            "Statement and Conclusion",
            "Puzzle",
        ],
    ),
    (
        "PHYSICS",
        "PHY",
        3,
        [
            "Units and Measurements",
            "Motion",
            "Force and Laws of Motion",
            "Work and Energy",
            "Heat and Temperature",
            "Sound",
            "Light and Optics",
            "Electricity",
            "Magnetism",
        ],
    ),
    (
        "CHEMISTRY",
        "CHEM",
        4,
        [
            "Atomic Structure",
            "Elements and Compounds",
            "Acids, Bases and Salts",
            "Metals and Non-metals",
            "Chemical Reactions",
            "Periodic Table",
            "Carbon and Its Compounds",
        ],
    ),
    (
        "BIOLOGY",
        "BIO",
        5,
        [
            "Cell Structure and Function",
            "Human Body Systems",
            "Nutrition and Digestion",
            "Respiration",
            "Blood and Circulatory System",
            "Diseases and Prevention",
            "Plant Kingdom",
            "Genetics and Heredity",
            "Ecology and Environment",
        ],
    ),
]


async def seed_subjects_and_topics() -> None:
    logger.info("Starting database seed...")

    async with AsyncSessionLocal() as session:
        # Verify connection
        await session.execute(text("SELECT 1"))
        logger.info("Database connection OK")

        seeded_subjects = 0
        seeded_topics = 0

        for subject_name, short_code, display_order, topic_names in SUBJECTS_AND_TOPICS:
            # ── Upsert subject ──────────────────────────────────────────────
            stmt = (
                pg_insert(Subject)
                .values(
                    id=uuid.uuid4(),
                    name=subject_name,
                    short_code=short_code,
                    display_order=display_order,
                )
                .on_conflict_do_nothing(index_elements=["name"])
                .returning(Subject.id, Subject.name)
            )
            result = await session.execute(stmt)
            row = result.fetchone()

            if row:
                subject_id = row[0]
                seeded_subjects += 1
                logger.info("  ✓ Seeded subject: %s", subject_name)
            else:
                # Subject already exists — fetch its ID
                existing = await session.execute(
                    select(Subject).where(Subject.name == subject_name)
                )
                subject_obj = existing.scalar_one()
                subject_id = subject_obj.id
                logger.info("  → Subject already exists: %s", subject_name)

            # ── Upsert topics ───────────────────────────────────────────────
            for idx, topic_name in enumerate(topic_names):
                topic_stmt = (
                    pg_insert(Topic)
                    .values(
                        id=uuid.uuid4(),
                        subject_id=subject_id,
                        name=topic_name,
                        display_order=idx + 1,
                    )
                    .on_conflict_do_nothing(
                        constraint="uq_topic_subject_name"
                    )
                )
                topic_result = await session.execute(topic_stmt)
                if topic_result.rowcount > 0:
                    seeded_topics += 1
                    logger.info("      ✓ Topic: %s", topic_name)
                else:
                    logger.info("      → Already exists: %s", topic_name)

        await session.commit()

    logger.info(
        "\nSeed complete — %d subjects, %d topics inserted.",
        seeded_subjects,
        seeded_topics,
    )


async def main() -> None:
    try:
        await seed_subjects_and_topics()
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
