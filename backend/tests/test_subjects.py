"""
Phase 2 tests: SubjectService and TopicService (in-memory SQLite with seeded data).
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from app.models.subject import Subject, Topic
from app.services.subject_service import SubjectService, TopicService


async def _seed_subjects(db_session):
    """Insert test subjects and topics into the test DB."""
    math = Subject(
        id=uuid.uuid4(),
        name="MATHEMATICS",
        short_code="MATH",
        display_order=1,
    )
    physics = Subject(
        id=uuid.uuid4(),
        name="PHYSICS",
        short_code="PHY",
        display_order=3,
    )
    db_session.add_all([math, physics])
    await db_session.flush()

    topics = [
        Topic(id=uuid.uuid4(), subject_id=math.id, name="Number System", display_order=1),
        Topic(id=uuid.uuid4(), subject_id=math.id, name="Percentage", display_order=2),
        Topic(id=uuid.uuid4(), subject_id=physics.id, name="Motion", display_order=1),
    ]
    db_session.add_all(topics)
    await db_session.flush()

    return math, physics, topics


class TestSubjectService:

    @pytest.mark.asyncio
    async def test_list_subjects_returns_all(self, db_session):
        await _seed_subjects(db_session)
        service = SubjectService(db_session)

        subjects = await service.list_subjects()

        assert len(subjects) == 2
        names = {s.name for s in subjects}
        assert "MATHEMATICS" in names
        assert "PHYSICS" in names

    @pytest.mark.asyncio
    async def test_list_subjects_ordered_by_display_order(self, db_session):
        await _seed_subjects(db_session)
        service = SubjectService(db_session)

        subjects = await service.list_subjects()

        assert subjects[0].display_order <= subjects[1].display_order

    @pytest.mark.asyncio
    async def test_get_subject_valid_id(self, db_session):
        math, _, _ = await _seed_subjects(db_session)
        service = SubjectService(db_session)

        result = await service.get_subject(math.id)
        assert result.name == "MATHEMATICS"

    @pytest.mark.asyncio
    async def test_get_subject_not_found(self, db_session):
        service = SubjectService(db_session)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_subject(uuid.uuid4())

        assert exc_info.value.status_code == 404


class TestTopicService:

    @pytest.mark.asyncio
    async def test_list_all_topics(self, db_session):
        await _seed_subjects(db_session)
        service = TopicService(db_session)

        topics = await service.list_topics()
        assert len(topics) == 3

    @pytest.mark.asyncio
    async def test_list_topics_filtered_by_subject(self, db_session):
        math, _, _ = await _seed_subjects(db_session)
        service = TopicService(db_session)

        topics = await service.list_topics(subject_id=math.id)

        assert len(topics) == 2
        assert all(t.subject_id == math.id for t in topics)

    @pytest.mark.asyncio
    async def test_list_topics_invalid_subject_raises_404(self, db_session):
        """Filtering by a non-existent subject_id must raise 404."""
        service = TopicService(db_session)

        with pytest.raises(HTTPException) as exc_info:
            await service.list_topics(subject_id=uuid.uuid4())

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_topic_valid_id(self, db_session):
        math, _, topics = await _seed_subjects(db_session)
        service = TopicService(db_session)

        result = await service.get_topic(topics[0].id)
        assert result.name == "Number System"

    @pytest.mark.asyncio
    async def test_get_topic_not_found(self, db_session):
        service = TopicService(db_session)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_topic(uuid.uuid4())

        assert exc_info.value.status_code == 404
