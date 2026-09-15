"""
ScoringEngine — pure, stateless scoring logic.

This module contains NO database calls. It takes raw Python data
(question answers, correct answers, mock test config) and returns
computed scores and breakdowns.

Keeping it pure makes it:
  - Trivially testable (no mocking needed)
  - Deterministic (same inputs → same outputs every time)
  - Portable (reusable by analytics, re-scoring jobs, etc.)

RRB ALP Scoring Rules:
  - Correct answer:  +marks_per_correct
  - Wrong answer:    -negative_marking (as a fraction of marks_per_correct)
  - Unanswered:      0
  - Score floor:     0 (score cannot go below 0, per RRB convention)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from uuid import UUID


@dataclass
class QuestionResult:
    """Outcome of a single question comparison."""
    question_id: str
    subject_name: Optional[str]
    topic_name: Optional[str]
    selected_answer: Optional[str]
    correct_answer: str
    is_correct: bool
    marks_awarded: float


@dataclass
class ScoreBreakdown:
    attempted: int = 0
    correct: int = 0
    wrong: int = 0
    unanswered: int = 0
    score: float = 0.0
    accuracy: float = 0.0  # 0.0 – 100.0


@dataclass
class ScoringResult:
    """Full output of the scoring engine."""
    total_questions: int
    attempted: int
    correct: int
    wrong: int
    unanswered: int
    score: float
    max_score: float
    accuracy: float  # % of attempted that were correct
    time_spent_seconds: int

    # Per-subject breakdown keyed by subject name
    subject_performance: Dict[str, ScoreBreakdown] = field(default_factory=dict)
    # Per-topic breakdown keyed by topic name
    topic_performance: Dict[str, ScoreBreakdown] = field(default_factory=dict)
    # Per-question detail for review screen
    answer_details: List[dict] = field(default_factory=list)


class ScoringEngine:
    """
    Stateless scoring engine.

    Usage:
        engine = ScoringEngine(
            marks_per_correct=1.0,
            negative_marking=0.3333,
        )
        result = engine.score(
            question_answers=[...],
            user_answers={question_id: selected_answer},
            time_spent_seconds=1200,
        )
    """

    def __init__(self, marks_per_correct: float, negative_marking: float) -> None:
        self.marks_per_correct = marks_per_correct
        self.negative_marking = negative_marking

    def score(
        self,
        question_answers: List[dict],
        user_answers: Dict[str, Optional[str]],
        time_spent_seconds: int,
    ) -> ScoringResult:
        """
        Score a completed attempt.

        Args:
            question_answers: List of dicts with keys:
                question_id (str), correct_answer (str),
                subject_name (str|None), topic_name (str|None)
            user_answers: Mapping of question_id → selected_answer (or None)
            time_spent_seconds: Elapsed exam time in seconds

        Returns:
            ScoringResult with all aggregated and per-question data.
        """
        total = len(question_answers)
        attempted = 0
        correct = 0
        wrong = 0
        raw_score = 0.0
        max_score = total * self.marks_per_correct

        subject_perf: Dict[str, ScoreBreakdown] = {}
        topic_perf: Dict[str, ScoreBreakdown] = {}
        answer_details: List[dict] = []

        for qa in question_answers:
            qid = str(qa["question_id"])
            correct_ans = qa["correct_answer"]
            subject_name = qa.get("subject_name") or "Unknown Subject"
            topic_name = qa.get("topic_name") or "Unknown Topic"
            selected = user_answers.get(qid)

            # ── Per-question scoring ──────────────────────────────────────────
            if selected is None:
                is_correct = False
                marks = 0.0
                unanswered_flag = True
            elif selected == correct_ans:
                is_correct = True
                marks = self.marks_per_correct
                attempted += 1
                correct += 1
                raw_score += marks
                unanswered_flag = False
            else:
                is_correct = False
                marks = -(self.marks_per_correct * self.negative_marking)
                attempted += 1
                wrong += 1
                raw_score += marks
                unanswered_flag = False

            # ── Subject breakdown ─────────────────────────────────────────────
            if subject_name not in subject_perf:
                subject_perf[subject_name] = ScoreBreakdown()
            sb = subject_perf[subject_name]
            if selected is not None:
                sb.attempted += 1
                sb.score += marks
                if is_correct:
                    sb.correct += 1
                else:
                    sb.wrong += 1
            else:
                sb.unanswered += 1

            # ── Topic breakdown ───────────────────────────────────────────────
            if topic_name not in topic_perf:
                topic_perf[topic_name] = ScoreBreakdown()
            tb = topic_perf[topic_name]
            if selected is not None:
                tb.attempted += 1
                tb.score += marks
                if is_correct:
                    tb.correct += 1
                else:
                    tb.wrong += 1
            else:
                tb.unanswered += 1

            # ── Per-question detail ───────────────────────────────────────────
            answer_details.append({
                "question_id": qid,
                "selected_answer": selected,
                "correct_answer": correct_ans,
                "is_correct": is_correct,
            })

        # ── Final aggregation ─────────────────────────────────────────────────
        unanswered = total - attempted
        # Score floor at 0
        final_score = round(max(0.0, raw_score), 4)
        accuracy = round((correct / attempted * 100) if attempted > 0 else 0.0, 2)

        # Compute accuracy on each breakdown
        for bd in list(subject_perf.values()) + list(topic_perf.values()):
            bd.score = round(max(0.0, bd.score), 4)
            bd.accuracy = round(
                (bd.correct / bd.attempted * 100) if bd.attempted > 0 else 0.0, 2
            )

        return ScoringResult(
            total_questions=total,
            attempted=attempted,
            correct=correct,
            wrong=wrong,
            unanswered=unanswered,
            score=final_score,
            max_score=round(max_score, 4),
            accuracy=accuracy,
            time_spent_seconds=time_spent_seconds,
            subject_performance={k: v for k, v in subject_perf.items()},
            topic_performance={k: v for k, v in topic_perf.items()},
            answer_details=answer_details,
        )

    @staticmethod
    def breakdown_to_dict(bd: ScoreBreakdown) -> dict:
        return {
            "attempted": bd.attempted,
            "correct": bd.correct,
            "wrong": bd.wrong,
            "unanswered": bd.unanswered,
            "score": bd.score,
            "accuracy": bd.accuracy,
        }
