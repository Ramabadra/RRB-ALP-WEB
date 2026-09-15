"""
Phase 4 tests: ScoringEngine — pure unit tests, no DB needed.
"""

from __future__ import annotations

import pytest

from app.services.scoring_engine import ScoringEngine


QUESTIONS = [
    {"question_id": "q1", "correct_answer": "A", "subject_name": "Math", "topic_name": "Algebra"},
    {"question_id": "q2", "correct_answer": "B", "subject_name": "Math", "topic_name": "Algebra"},
    {"question_id": "q3", "correct_answer": "C", "subject_name": "Physics", "topic_name": "Mechanics"},
    {"question_id": "q4", "correct_answer": "D", "subject_name": "Physics", "topic_name": "Mechanics"},
    {"question_id": "q5", "correct_answer": "A", "subject_name": "Math", "topic_name": "Numbers"},
]


class TestScoringEngine:

    def _engine(self, marks=1.0, neg=0.3333):
        return ScoringEngine(marks_per_correct=marks, negative_marking=neg)

    def test_all_correct(self):
        engine = self._engine()
        user_ans = {"q1": "A", "q2": "B", "q3": "C", "q4": "D", "q5": "A"}
        result = engine.score(QUESTIONS, user_ans, time_spent_seconds=600)

        assert result.correct == 5
        assert result.wrong == 0
        assert result.unanswered == 0
        assert result.score == 5.0
        assert result.max_score == 5.0
        assert result.accuracy == 100.0

    def test_all_wrong(self):
        engine = self._engine()
        user_ans = {"q1": "B", "q2": "C", "q3": "D", "q4": "A", "q5": "B"}
        result = engine.score(QUESTIONS, user_ans, time_spent_seconds=600)

        assert result.correct == 0
        assert result.wrong == 5
        assert result.score == 0.0  # Floor at 0 — raw score is negative
        assert result.accuracy == 0.0

    def test_all_unanswered(self):
        engine = self._engine()
        result = engine.score(QUESTIONS, {}, time_spent_seconds=600)

        assert result.attempted == 0
        assert result.unanswered == 5
        assert result.score == 0.0
        assert result.accuracy == 0.0

    def test_mixed_answers(self):
        engine = self._engine(marks=1.0, neg=0.3333)
        # q1: correct (+1), q2: wrong (-0.3333), q3: unanswered (0), q4: correct (+1), q5: wrong (-0.3333)
        user_ans = {"q1": "A", "q2": "C", "q4": "D", "q5": "B"}
        result = engine.score(QUESTIONS, user_ans, time_spent_seconds=300)

        assert result.correct == 2
        assert result.wrong == 2
        assert result.unanswered == 1
        assert result.attempted == 4
        # raw = 2 * 1.0 - 2 * 0.3333 = 2.0 - 0.6666 = 1.3334
        assert abs(result.score - round(2.0 - 2 * 0.3333, 4)) < 0.001
        assert result.time_spent_seconds == 300

    def test_score_floor_does_not_go_negative(self):
        engine = self._engine(marks=1.0, neg=1.0)  # 1 wrong cancels 1 correct
        # All wrong  → raw score = -5, should be floored at 0
        user_ans = {"q1": "B", "q2": "C", "q3": "D", "q4": "A", "q5": "B"}
        result = engine.score(QUESTIONS, user_ans, time_spent_seconds=600)
        assert result.score == 0.0

    def test_subject_breakdown(self):
        engine = self._engine()
        # All correct
        user_ans = {"q1": "A", "q2": "B", "q3": "C", "q4": "D", "q5": "A"}
        result = engine.score(QUESTIONS, user_ans, time_spent_seconds=600)

        math_perf = result.subject_performance["Math"]
        assert math_perf.correct == 3  # q1, q2, q5
        assert math_perf.wrong == 0

        physics_perf = result.subject_performance["Physics"]
        assert physics_perf.correct == 2  # q3, q4

    def test_topic_breakdown(self):
        engine = self._engine()
        user_ans = {"q1": "A", "q2": "B", "q3": "D"}  # q3 wrong
        result = engine.score(QUESTIONS, user_ans, time_spent_seconds=600)

        algebra = result.topic_performance["Algebra"]
        assert algebra.correct == 2
        assert algebra.wrong == 0

        mechanics = result.topic_performance["Mechanics"]
        assert mechanics.correct == 0
        assert mechanics.wrong == 1
        assert mechanics.unanswered == 1

    def test_answer_details_included(self):
        engine = self._engine()
        user_ans = {"q1": "A", "q2": "C"}
        result = engine.score(QUESTIONS, user_ans, time_spent_seconds=60)

        assert len(result.answer_details) == 5
        q1_detail = next(d for d in result.answer_details if d["question_id"] == "q1")
        assert q1_detail["is_correct"] is True
        q2_detail = next(d for d in result.answer_details if d["question_id"] == "q2")
        assert q2_detail["is_correct"] is False
        assert q2_detail["selected_answer"] == "C"
        assert q2_detail["correct_answer"] == "B"

    def test_accuracy_calculation(self):
        engine = self._engine()
        # 3 correct, 1 wrong, 1 unanswered → accuracy = 3/4 = 75%
        user_ans = {"q1": "A", "q2": "B", "q3": "D", "q4": "D"}  # q3 wrong, q5 unanswered
        result = engine.score(QUESTIONS, user_ans, time_spent_seconds=600)

        assert result.correct == 3
        assert result.wrong == 1
        assert result.attempted == 4
        assert result.accuracy == 75.0

    def test_no_negative_marking_mode(self):
        """When negative_marking=0, wrong answers score 0."""
        engine = ScoringEngine(marks_per_correct=1.0, negative_marking=0.0)
        user_ans = {"q1": "B", "q2": "C", "q3": "D", "q4": "A", "q5": "B"}  # all wrong
        result = engine.score(QUESTIONS, user_ans, time_spent_seconds=600)
        assert result.score == 0.0
        assert result.wrong == 5
