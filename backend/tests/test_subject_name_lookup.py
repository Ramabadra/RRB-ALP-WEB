"""
Focused tests for SubjectRepository.get_by_name case-insensitive lookup.
Proves the ilike() fix works for all ALP subject names sent from the frontend.
"""

from __future__ import annotations

import uuid

import pytest

from app.models.subject import Subject
from app.repositories.subject_repository import SubjectRepository


# ── Seed data that mirrors what is typically in the production DB ─────────────
ALP_SUBJECTS = [
    ("Reasoning", "RSN", 1),
    ("Mathematics", "MATH", 2),
    ("General Science", "SCI", 3),
    ("Physics", "PHY", 4),
    ("Chemistry", "CHEM", 5),
    ("Biology", "BIO", 6),
]


async def _seed(db):
    subjects = []
    for name, code, order in ALP_SUBJECTS:
        s = Subject(id=uuid.uuid4(), name=name, short_code=code, display_order=order)
        db.add(s)
        subjects.append(s)
    await db.flush()
    return subjects


class TestGetByNameCaseInsensitive:

    @pytest.mark.asyncio
    async def test_reasoning_title_case(self, db_session):
        await _seed(db_session)
        repo = SubjectRepository(db_session)
        result = await repo.get_by_name("Reasoning")
        assert result is not None, "Expected to find 'Reasoning' with title-case input"
        assert result.name == "Reasoning"

    @pytest.mark.asyncio
    async def test_reasoning_upper_case(self, db_session):
        await _seed(db_session)
        repo = SubjectRepository(db_session)
        result = await repo.get_by_name("REASONING")
        assert result is not None, "Expected to find 'Reasoning' with UPPER-case input"
        assert result.name == "Reasoning"

    @pytest.mark.asyncio
    async def test_reasoning_lower_case(self, db_session):
        await _seed(db_session)
        repo = SubjectRepository(db_session)
        result = await repo.get_by_name("reasoning")
        assert result is not None, "Expected to find 'Reasoning' with lower-case input"
        assert result.name == "Reasoning"

    @pytest.mark.asyncio
    async def test_mathematics(self, db_session):
        await _seed(db_session)
        repo = SubjectRepository(db_session)
        for variant in ("Mathematics", "MATHEMATICS", "mathematics"):
            result = await repo.get_by_name(variant)
            assert result is not None, f"Expected to find subject with name variant '{variant}'"
            assert result.name == "Mathematics"

    @pytest.mark.asyncio
    async def test_general_science(self, db_session):
        await _seed(db_session)
        repo = SubjectRepository(db_session)
        for variant in ("General Science", "GENERAL SCIENCE", "general science"):
            result = await repo.get_by_name(variant)
            assert result is not None, f"Expected to find subject with name variant '{variant}'"
            assert result.name == "General Science"

    @pytest.mark.asyncio
    async def test_physics(self, db_session):
        await _seed(db_session)
        repo = SubjectRepository(db_session)
        result = await repo.get_by_name("Physics")
        assert result is not None
        assert result.name == "Physics"

    @pytest.mark.asyncio
    async def test_chemistry(self, db_session):
        await _seed(db_session)
        repo = SubjectRepository(db_session)
        result = await repo.get_by_name("Chemistry")
        assert result is not None
        assert result.name == "Chemistry"

    @pytest.mark.asyncio
    async def test_biology(self, db_session):
        await _seed(db_session)
        repo = SubjectRepository(db_session)
        result = await repo.get_by_name("Biology")
        assert result is not None
        assert result.name == "Biology"

    @pytest.mark.asyncio
    async def test_nonexistent_subject_returns_none(self, db_session):
        await _seed(db_session)
        repo = SubjectRepository(db_session)
        result = await repo.get_by_name("Nonexistent Subject")
        assert result is None, "Should return None for a subject that does not exist"

    @pytest.mark.asyncio
    async def test_name_not_permanently_mutated(self, db_session):
        """
        Confirms that passing any case variant does NOT modify the stored name.
        The DB row name must stay as seeded (title-case).
        """
        await _seed(db_session)
        repo = SubjectRepository(db_session)
        result = await repo.get_by_name("REASONING")
        # The stored value must be unchanged — 'Reasoning', not 'REASONING'
        assert result.name == "Reasoning", (
            f"DB value should not be mutated. Expected 'Reasoning', got '{result.name}'"
        )
