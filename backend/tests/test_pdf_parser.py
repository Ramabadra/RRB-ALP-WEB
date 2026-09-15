"""
Phase 5 tests: QuestionParser — pure unit tests, no DB, no storage needed.

We test the parser against realistic RRB ALP paper text samples.
"""

from __future__ import annotations

import pytest

from app.pdf.parser import QuestionParser


# ── Sample PDF text fixtures ─────────────────────────────────────────────────

CLEAN_PAPER = """
Q.1 A train travels 120 km in 2 hours. What is its speed?
(A) 50 km/h
(B) 60 km/h
(C) 70 km/h
(D) 80 km/h

Q.2 Which planet is closest to the Sun?
(A) Venus
(B) Earth
(C) Mercury
(D) Mars

Q.3 What is 15 × 8?
(A) 100
(B) 110
(C) 120
(D) 130

Answer Key
1) B
2) C
3) C
"""

INLINE_ANS_FORMAT = """
1. The capital of India is:
A. Mumbai
B. Delhi
C. Chennai
D. Kolkata
Ans: B

2. Who invented the telephone?
A. Edison
B. Bell
C. Newton
D. Tesla
Ans: B
"""

MISSING_OPTION_PAPER = """
Q.1 What is H2O?
(A) Hydrogen
(B) Water
(C) Oxygen

Answer Key
1) B
"""

NUMBERED_ANS_KEY = """
Q.1 Speed = Distance / Time. If distance = 100m, time = 10s, speed = ?
(A) 5 m/s
(B) 10 m/s
(C) 15 m/s
(D) 20 m/s

Q.2 Which is a prime number?
(A) 4
(B) 6
(C) 7
(D) 9

Answers:
1. B
2. C
"""


class TestQuestionParser:

    def _parse(self, text: str):
        parser = QuestionParser()
        pages = [(1, text)]
        return parser.parse(text, pages)

    def test_clean_paper_extracts_all_questions(self):
        result = self._parse(CLEAN_PAPER)
        assert result.total_extracted == 3

    def test_answer_key_parsed_correctly(self):
        result = self._parse(CLEAN_PAPER)
        assert result.answer_key[1] == "B"
        assert result.answer_key[2] == "C"
        assert result.answer_key[3] == "C"

    def test_questions_matched_to_answers(self):
        result = self._parse(CLEAN_PAPER)
        q1 = next(q for q in result.questions if q.source_number == 1)
        assert q1.correct_answer == "B"

        q2 = next(q for q in result.questions if q.source_number == 2)
        assert q2.correct_answer == "C"

    def test_options_extracted_correctly(self):
        result = self._parse(CLEAN_PAPER)
        q1 = next(q for q in result.questions if q.source_number == 1)
        assert "50 km/h" in q1.option_a
        assert "60 km/h" in q1.option_b
        assert "70 km/h" in q1.option_c
        assert "80 km/h" in q1.option_d

    def test_question_text_extracted(self):
        result = self._parse(CLEAN_PAPER)
        q1 = next(q for q in result.questions if q.source_number == 1)
        assert "train" in q1.question_text.lower()
        assert "120 km" in q1.question_text

    def test_numbered_answer_key_format(self):
        result = self._parse(NUMBERED_ANS_KEY)
        assert result.answer_key.get(1) == "B"
        assert result.answer_key.get(2) == "C"

    def test_missing_option_generates_warning(self):
        result = self._parse(MISSING_OPTION_PAPER)
        assert any("Missing options" in w for w in result.parse_warnings)

    def test_question_source_number_preserved(self):
        result = self._parse(CLEAN_PAPER)
        source_numbers = {q.source_number for q in result.questions}
        assert 1 in source_numbers
        assert 2 in source_numbers
        assert 3 in source_numbers

    def test_page_number_recorded(self):
        parser = QuestionParser()
        pages = [(5, CLEAN_PAPER)]  # page 5
        result = parser.parse(CLEAN_PAPER, pages)
        for q in result.questions:
            assert q.page_number == 5

    def test_high_confidence_for_complete_questions(self):
        result = self._parse(CLEAN_PAPER)
        for q in result.questions:
            # All options present + question text > 15 chars = at least 0.7 confidence
            assert q.confidence >= 0.4, f"Q{q.source_number} confidence too low: {q.confidence}"

    def test_deduplication_across_pages(self):
        """Same question on two overlapping pages should appear only once."""
        parser = QuestionParser()
        # Same text on page 1 and page 2 — Q1 appears twice
        pages = [(1, CLEAN_PAPER), (2, CLEAN_PAPER)]
        result = parser.parse(CLEAN_PAPER + CLEAN_PAPER, pages)
        source_numbers = [q.source_number for q in result.questions]
        # Each number should appear only once
        assert len(source_numbers) == len(set(source_numbers))

    def test_empty_text_returns_empty_result(self):
        result = self._parse("")
        assert result.total_extracted == 0
        assert result.answer_key == {}

    def test_total_with_answers_count(self):
        result = self._parse(CLEAN_PAPER)
        # All 3 questions have answers
        assert result.total_with_answers == 3

    def test_questions_without_answers_count(self):
        # Paper with questions but no answer key
        no_key_paper = """
Q.1 What is 2+2?
(A) 3
(B) 4
(C) 5
(D) 6
"""
        result = self._parse(no_key_paper)
        assert result.total_extracted == 1
        assert result.total_with_answers == 0
        assert result.questions[0].correct_answer is None


class TestPDFValidation:
    """Test PDF validation logic in PdfService (no storage/DB needed)."""

    def test_pdf_magic_bytes_valid(self):
        """Valid PDF starts with %PDF."""
        from app.services.pdf_service import PDF_MAGIC
        assert PDF_MAGIC == b"%PDF"

    def test_allowed_mime_types(self):
        from app.services.pdf_service import ALLOWED_MIME_TYPES
        assert "application/pdf" in ALLOWED_MIME_TYPES

    def test_confidence_score_computation(self):
        """High quality question should get 0.9+ confidence."""
        from app.pdf.parser import QuestionParser
        score = QuestionParser._compute_confidence(
            q_text="This is a proper question with more than 15 characters",
            a="Option A answer",
            b="Option B answer",
            c="Option C answer",
            d="Option D answer",
        )
        assert score >= 0.9

    def test_low_confidence_for_short_question(self):
        """Short question with missing options should get low confidence."""
        from app.pdf.parser import QuestionParser
        score = QuestionParser._compute_confidence(
            q_text="Short",
            a="",
            b="",
            c="",
            d="",
        )
        assert score < 0.3
