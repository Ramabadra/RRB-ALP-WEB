"""
Phase 4 integration tests: AttemptService — full exam lifecycle.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import List
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.models.mock_test import MockTest, MockTestQuestion
from app.models.question import Question
from app.models.subject import Subject, Topic
from app.models.user import User
from app.schemas.attempt import AnswerSaveRequest, SingleAnswerSave
from app.schemas.question import AnswerChoice
from app.services.attempt_service import AttemptService


def _utcnow():
    return datetime.now(timezone.utc)


async def _seed_exam(db_session, question_count: int = 5):
    """Seed a complete exam: user, subject, topic, questions, mock_test."""
    user = User(id=uuid.uuid4(), email="exam@test.com", name="Exam User", google_id="exam_g")
    db_session.add(user)

    sub = Subject(id=uuid.uuid4(), name="MATH", short_code="MATH", display_order=1)
    top = Topic(id=uuid.uuid4(), subject_id=sub.id, name="Algebra", display_order=1)
    db_session.add_all([sub, top])

    questions = []
    for i in range(question_count):
        q = Question(
            id=uuid.uuid4(),
            question_text=f"Q{i}",
            option_a="A", option_b="B", option_c="C", option_d="D",
            correct_answer="A",
            subject_id=sub.id, topic_id=top.id,
            difficulty="EASY", language="ENGLISH",
            source_type="REFERENCE", verification_status="VERIFIED",
        )
        questions.append(q)
    db_session.add_all(questions)

    mock_test = MockTest(
        id=uuid.uuid4(),
        user_id=user.id,
        title="Test Exam",
        question_count=question_count,
        duration_minutes=30,
        negative_marking=0.3333,
        marks_per_correct=1.0,
        source_type="REFERENCE",
        difficulty="EASY",
    )
    db_session.add(mock_test)
    await db_session.flush()

    for i, q in enumerate(questions, start=1):
        entry = MockTestQuestion(mock_test_id=mock_test.id, question_id=q.id, position=i)
        db_session.add(entry)

    await db_session.flush()
    return user, mock_test, questions


class TestAttemptService:

    @pytest.mark.asyncio
    async def test_create_attempt_success(self, db_session):
        user, mock_test, _ = await _seed_exam(db_session)
        service = AttemptService(db_session)

        attempt = await service.create_attempt(user.id, mock_test.id)
        await db_session.commit()

        assert attempt.id is not None
        assert attempt.status == "NOT_STARTED"
        assert attempt.user_id == user.id

    @pytest.mark.asyncio
    async def test_create_attempt_wrong_owner_raises_403(self, db_session):
        user, mock_test, _ = await _seed_exam(db_session)
        service = AttemptService(db_session)
        other_user_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.create_attempt(other_user_id, mock_test.id)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_start_attempt_sets_timer(self, db_session):
        user, mock_test, _ = await _seed_exam(db_session)
        service = AttemptService(db_session)

        attempt = await service.create_attempt(user.id, mock_test.id)
        await db_session.commit()

        started = await service.start_attempt(attempt.id, user.id)
        await db_session.commit()

        assert started.status == "IN_PROGRESS"
        assert started.started_at is not None
        assert started.expires_at is not None
        # expires_at should be ~30 minutes after started_at
        delta = started.expires_at - started.started_at
        assert abs(delta.total_seconds() - 30 * 60) < 5

    @pytest.mark.asyncio
    async def test_start_attempt_is_idempotent(self, db_session):
        user, mock_test, _ = await _seed_exam(db_session)
        service = AttemptService(db_session)

        attempt = await service.create_attempt(user.id, mock_test.id)
        await db_session.commit()

        started1 = await service.start_attempt(attempt.id, user.id)
        started2 = await service.start_attempt(attempt.id, user.id)  # Call again

        assert started1.started_at == started2.started_at  # Unchanged

    @pytest.mark.asyncio
    async def test_save_answers_upserts_correctly(self, db_session):
        user, mock_test, questions = await _seed_exam(db_session)
        service = AttemptService(db_session)

        attempt = await service.create_attempt(user.id, mock_test.id)
        await service.start_attempt(attempt.id, user.id)
        await db_session.commit()

        body = AnswerSaveRequest(answers=[
            SingleAnswerSave(question_id=questions[0].id, selected_answer=AnswerChoice.A),
            SingleAnswerSave(question_id=questions[1].id, selected_answer=AnswerChoice.B, is_marked=True),
        ])
        status_resp = await service.save_answers(attempt.id, user.id, body)

        assert status_resp.answered_count == 2
        assert status_resp.marked_count == 1

    @pytest.mark.asyncio
    async def test_save_answers_blocks_wrong_question(self, db_session):
        user, mock_test, _ = await _seed_exam(db_session)
        service = AttemptService(db_session)

        attempt = await service.create_attempt(user.id, mock_test.id)
        await service.start_attempt(attempt.id, user.id)
        await db_session.commit()

        # Use a question UUID not in this mock test
        foreign_qid = uuid.uuid4()
        body = AnswerSaveRequest(answers=[
            SingleAnswerSave(question_id=foreign_qid, selected_answer=AnswerChoice.A),
        ])
        with pytest.raises(HTTPException) as exc_info:
            await service.save_answers(attempt.id, user.id, body)
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_full_lifecycle_submit_creates_result(self, db_session):
        user, mock_test, questions = await _seed_exam(db_session)
        service = AttemptService(db_session)

        attempt = await service.create_attempt(user.id, mock_test.id)
        await service.start_attempt(attempt.id, user.id)
        await db_session.commit()

        # Answer all questions correctly
        body = AnswerSaveRequest(answers=[
            SingleAnswerSave(question_id=q.id, selected_answer=AnswerChoice.A)
            for q in questions
        ])
        await service.save_answers(attempt.id, user.id, body)
        await db_session.commit()

        submit_resp = await service.submit(attempt.id, user.id)
        await db_session.commit()

        assert submit_resp.result_id is not None
        assert "submitted successfully" in submit_resp.message.lower()

    @pytest.mark.asyncio
    async def test_submit_is_idempotent(self, db_session):
        user, mock_test, questions = await _seed_exam(db_session)
        service = AttemptService(db_session)

        attempt = await service.create_attempt(user.id, mock_test.id)
        await service.start_attempt(attempt.id, user.id)
        await db_session.commit()

        resp1 = await service.submit(attempt.id, user.id)
        await db_session.commit()
        resp2 = await service.submit(attempt.id, user.id)  # Second call

        assert resp1.result_id == resp2.result_id  # Same result returned

    @pytest.mark.asyncio
    async def test_correct_score_is_calculated(self, db_session):
        """All correct answers → score = question_count * marks_per_correct."""
        user, mock_test, questions = await _seed_exam(db_session, question_count=5)
        service = AttemptService(db_session)

        attempt = await service.create_attempt(user.id, mock_test.id)
        await service.start_attempt(attempt.id, user.id)
        await db_session.commit()

        # All correct (correct_answer == "A" for all seeded questions)
        body = AnswerSaveRequest(answers=[
            SingleAnswerSave(question_id=q.id, selected_answer=AnswerChoice.A)
            for q in questions
        ])
        await service.save_answers(attempt.id, user.id, body)
        await db_session.commit()

        submit_resp = await service.submit(attempt.id, user.id)
        await db_session.commit()

        from app.repositories.attempt_repository import ResultRepository
        result = await ResultRepository(db_session).get_by_attempt_id(attempt.id)

        assert result.correct == 5
        assert result.wrong == 0
        assert result.score == 5.0  # 5 * 1.0

    @pytest.mark.asyncio
    async def test_save_answers_blocked_when_not_started(self, db_session):
        user, mock_test, questions = await _seed_exam(db_session)
        service = AttemptService(db_session)

        attempt = await service.create_attempt(user.id, mock_test.id)
        await db_session.commit()
        # Do NOT call start_attempt

        body = AnswerSaveRequest(answers=[
            SingleAnswerSave(question_id=questions[0].id, selected_answer=AnswerChoice.A),
        ])
        with pytest.raises(HTTPException) as exc_info:
            await service.save_answers(attempt.id, user.id, body)
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_get_status_returns_seconds_remaining(self, db_session):
        user, mock_test, _ = await _seed_exam(db_session)
        service = AttemptService(db_session)

        attempt = await service.create_attempt(user.id, mock_test.id)
        await service.start_attempt(attempt.id, user.id)
        await db_session.commit()

        status_resp = await service.get_status(attempt.id, user.id)

        assert status_resp.status == "IN_PROGRESS"
        assert status_resp.seconds_remaining is not None
        assert status_resp.seconds_remaining > 0
        assert status_resp.seconds_remaining <= 30 * 60

    # ── New tests: Phase 4.1 — status response enrichment ─────────────────────

    @pytest.mark.asyncio
    async def test_status_includes_mock_test_id(self, db_session):
        """AttemptStatusResponse must contain mock_test_id for frontend reload."""
        user, mock_test, _ = await _seed_exam(db_session)
        service = AttemptService(db_session)

        attempt = await service.create_attempt(user.id, mock_test.id)
        await service.start_attempt(attempt.id, user.id)
        await db_session.commit()

        status_resp = await service.get_status(attempt.id, user.id)

        assert status_resp.mock_test_id == mock_test.id

    @pytest.mark.asyncio
    async def test_status_answers_empty_before_any_save(self, db_session):
        """answers list must be [] when the user has not answered anything yet."""
        user, mock_test, _ = await _seed_exam(db_session)
        service = AttemptService(db_session)

        attempt = await service.create_attempt(user.id, mock_test.id)
        await service.start_attempt(attempt.id, user.id)
        await db_session.commit()

        status_resp = await service.get_status(attempt.id, user.id)

        assert status_resp.answers == []

    @pytest.mark.asyncio
    async def test_status_answers_restored_after_save(self, db_session):
        """After saving, get_status() must return answers for UI restoration."""
        user, mock_test, questions = await _seed_exam(db_session)
        service = AttemptService(db_session)

        attempt = await service.create_attempt(user.id, mock_test.id)
        await service.start_attempt(attempt.id, user.id)
        await db_session.commit()

        body = AnswerSaveRequest(answers=[
            SingleAnswerSave(question_id=questions[0].id, selected_answer=AnswerChoice.C),
            SingleAnswerSave(question_id=questions[1].id, selected_answer=AnswerChoice.D, is_marked=True),
        ])
        await service.save_answers(attempt.id, user.id, body)
        await db_session.commit()

        # Simulate browser refresh
        status_resp = await service.get_status(attempt.id, user.id)
        answer_map = {str(a.question_id): a for a in status_resp.answers}

        assert len(status_resp.answers) == 2
        assert answer_map[str(questions[0].id)].selected_answer == AnswerChoice.C
        assert answer_map[str(questions[0].id)].is_marked is False
        assert answer_map[str(questions[1].id)].selected_answer == AnswerChoice.D
        assert answer_map[str(questions[1].id)].is_marked is True

    @pytest.mark.asyncio
    async def test_mark_for_review_persists(self, db_session):
        """is_marked flag must survive a round-trip through the DB."""
        user, mock_test, questions = await _seed_exam(db_session)
        service = AttemptService(db_session)

        attempt = await service.create_attempt(user.id, mock_test.id)
        await service.start_attempt(attempt.id, user.id)
        await db_session.commit()

        body = AnswerSaveRequest(answers=[
            SingleAnswerSave(question_id=questions[2].id, is_marked=True),
        ])
        await service.save_answers(attempt.id, user.id, body)
        await db_session.commit()

        status_resp = await service.get_status(attempt.id, user.id)
        answer_map = {str(a.question_id): a for a in status_resp.answers}

        marked = answer_map[str(questions[2].id)]
        assert marked.is_marked is True
        assert marked.selected_answer is None

    @pytest.mark.asyncio
    async def test_clear_answer_persists_as_none(self, db_session):
        """selected_answer=null clears the answer; answered_count must drop to 0."""
        user, mock_test, questions = await _seed_exam(db_session)
        service = AttemptService(db_session)

        attempt = await service.create_attempt(user.id, mock_test.id)
        await service.start_attempt(attempt.id, user.id)
        await db_session.commit()

        body1 = AnswerSaveRequest(answers=[
            SingleAnswerSave(question_id=questions[0].id, selected_answer=AnswerChoice.A),
        ])
        await service.save_answers(attempt.id, user.id, body1)
        await db_session.commit()

        body2 = AnswerSaveRequest(answers=[
            SingleAnswerSave(question_id=questions[0].id, selected_answer=None),
        ])
        await service.save_answers(attempt.id, user.id, body2)
        await db_session.commit()

        status_resp = await service.get_status(attempt.id, user.id)
        answer_map = {str(a.question_id): a for a in status_resp.answers}

        assert str(questions[0].id) in answer_map
        assert answer_map[str(questions[0].id)].selected_answer is None
        assert status_resp.answered_count == 0

    @pytest.mark.asyncio
    async def test_status_response_has_no_correct_answer_field(self, db_session):
        """AttemptStatusResponse and PersistedAnswer must NOT expose correct_answer."""
        user, mock_test, questions = await _seed_exam(db_session)
        service = AttemptService(db_session)

        attempt = await service.create_attempt(user.id, mock_test.id)
        await service.start_attempt(attempt.id, user.id)
        await db_session.commit()

        body = AnswerSaveRequest(answers=[
            SingleAnswerSave(question_id=questions[0].id, selected_answer=AnswerChoice.A),
        ])
        await service.save_answers(attempt.id, user.id, body)

        status_resp = await service.get_status(attempt.id, user.id)
        status_dict = status_resp.model_dump()

        assert "correct_answer" not in status_dict
        for ans in status_dict.get("answers", []):
            assert "correct_answer" not in ans

    @pytest.mark.asyncio
    async def test_get_status_unauthorized_raises_403(self, db_session):
        """A different user cannot read another user's attempt status."""
        user, mock_test, _ = await _seed_exam(db_session)
        service = AttemptService(db_session)

        attempt = await service.create_attempt(user.id, mock_test.id)
        await service.start_attempt(attempt.id, user.id)
        await db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await service.get_status(attempt.id, uuid.uuid4())
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_not_started_attempt_has_no_timer(self, db_session):
        """NOT_STARTED attempt must return seconds_remaining=None."""
        user, mock_test, _ = await _seed_exam(db_session)
        service = AttemptService(db_session)

        attempt = await service.create_attempt(user.id, mock_test.id)
        await db_session.commit()

        status_resp = await service.get_status(attempt.id, user.id)

        assert status_resp.status == "NOT_STARTED"
        assert status_resp.seconds_remaining is None

    @pytest.mark.asyncio
    async def test_expired_attempt_auto_submits_on_status(self, db_session):
        """When expires_at is past, get_status() auto-submits and returns EXPIRED."""
        from sqlalchemy import update
        from app.models.attempt import Attempt as AttemptModel

        user, mock_test, _ = await _seed_exam(db_session)
        service = AttemptService(db_session)

        attempt = await service.create_attempt(user.id, mock_test.id)
        await service.start_attempt(attempt.id, user.id)
        await db_session.commit()

        past = _utcnow() - timedelta(seconds=10)
        await db_session.execute(
            update(AttemptModel)
            .where(AttemptModel.id == attempt.id)
            .values(expires_at=past)
        )
        await db_session.commit()

        status_resp = await service.get_status(attempt.id, user.id)

        assert status_resp.status == "EXPIRED"
        assert status_resp.seconds_remaining is None

    @pytest.mark.asyncio
    async def test_submit_returns_result_id(self, db_session):
        """submit() must return SubmitResponse with attempt_id + result_id."""
        user, mock_test, questions = await _seed_exam(db_session)
        service = AttemptService(db_session)

        attempt = await service.create_attempt(user.id, mock_test.id)
        await service.start_attempt(attempt.id, user.id)
        await db_session.commit()

        body = AnswerSaveRequest(answers=[
            SingleAnswerSave(question_id=questions[0].id, selected_answer=AnswerChoice.A),
        ])
        await service.save_answers(attempt.id, user.id, body)
        await db_session.commit()

        submit_resp = await service.submit(attempt.id, user.id)
        await db_session.commit()

        assert submit_resp.attempt_id == attempt.id
        assert submit_resp.result_id is not None
        assert "submitted successfully" in submit_resp.message.lower()

    @pytest.mark.asyncio
    async def test_save_answers_blocks_unauthorized(self, db_session):
        """A different user cannot save answers to another user's attempt."""
        user, mock_test, questions = await _seed_exam(db_session)
        service = AttemptService(db_session)

        attempt = await service.create_attempt(user.id, mock_test.id)
        await service.start_attempt(attempt.id, user.id)
        await db_session.commit()

        body = AnswerSaveRequest(answers=[
            SingleAnswerSave(question_id=questions[0].id, selected_answer=AnswerChoice.A),
        ])
        with pytest.raises(HTTPException) as exc_info:
            await service.save_answers(attempt.id, uuid.uuid4(), body)
        assert exc_info.value.status_code == 403

