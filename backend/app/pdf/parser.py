"""
Question parser — converts raw PDF text into structured question objects.

RRB ALP paper format:
  Q.1 / 1. / Q1.  — question number prefix
  (A) / (a) / A.  — option labels
  Answer key appears as:  Answer: B  /  Ans: (C)  /  Ans. A

The parser uses a multi-pass regex strategy:
  Pass 1: Detect answer key section (usually at the end of the PDF)
  Pass 2: Split text into individual question blocks
  Pass 3: Extract options from each block
  Pass 4: Match each question to its answer from the key

Design principles:
  - Never crash on bad input — log warnings and skip malformed questions
  - confidence score on each extracted question (0.0 – 1.0)
  - Always preserve the raw question number from the source paper
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Regex patterns ─────────────────────────────────────────────────────────────

# Question start: "Q.1", "Q. 1", "Q1." prefix OR bare "1." "1)" ONLY when followed
# by at least 3 non-space chars (prevents matching answer key lines like "1) B").
QUESTION_START_RE = re.compile(
    r"""(?:^|\n)\s*(?:
        Q\.?\s*(?P<qnum1>\d{1,3})[.)\s]   # Q.1 / Q1. / Q. 1
        |(?P<qnum2>\d{1,3})[.)]\s+(?=\S{3})  # bare 1. / 1) only if ≥3 non-space chars follow
    )""",
    re.VERBOSE | re.MULTILINE,
)

# Option label: "(A)", "(a)", "A.", "a.", "A)", "a)"
# Captures label letter + everything until next option or end
OPTION_LABEL_RE = re.compile(
    r"^\s*\(?([AaBbCcDd])[.)]\s*(.+?)$",
    re.MULTILINE,
)

# Answer key line patterns
# Format 1: "1. B", "1) B", "1: B"
ANSWER_KEY_NUMBERED_RE = re.compile(
    r"(?:^|\n)\s*(\d{1,3})[.):\s]\s*\(?([AaBbCcDd])\)?(?:\s|$)",
    re.MULTILINE,
)

# Format 2: "Ans: B", "Answer: (C)", "Ans. A"
ANSWER_INLINE_RE = re.compile(
    r"Ans(?:wer)?\.?\s*[:.]?\s*\(?([AaBbCcDd])\)?",
    re.IGNORECASE,
)

# Answer key section header — text after this is treated as answer key
ANSWER_SECTION_RE = re.compile(
    r"\n\s*(?:Answer\s*Key|Answers?|Solutions?|Ans(?:wer)?\s*Key)\s*[:\n]",
    re.IGNORECASE,
)


@dataclass
class ParsedQuestion:
    """A question extracted from a PDF page."""
    source_number: int            # Original question number in the paper
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: Optional[str]  # "A", "B", "C", or "D" — None if not found
    confidence: float              # 0.0 – 1.0
    page_number: int               # Source page (1-indexed)


@dataclass
class ParseResult:
    """Full result of parsing a PDF's extracted text."""
    questions: List[ParsedQuestion]
    answer_key: Dict[int, str]    # question_number → "A"|"B"|"C"|"D"
    parse_warnings: List[str]
    total_extracted: int
    total_with_answers: int


class QuestionParser:
    """
    Converts raw text extracted from an RRB ALP PDF into structured
    ParsedQuestion objects.

    Usage:
        parser = QuestionParser()
        result = parser.parse(full_text, page_texts)
    """

    def parse(self, full_text: str, page_texts: List[Tuple[int, str]]) -> ParseResult:
        """
        Parse the full text of a PDF into structured questions.

        Args:
            full_text: Concatenated text of all pages
            page_texts: List of (page_number, page_text) tuples

        Returns:
            ParseResult with parsed questions, answer key, and warnings
        """
        warnings: List[str] = []

        # ── Pass 1: Extract answer key ─────────────────────────────────────────
        answer_key = self._extract_answer_key(full_text)
        logger.info("Extracted %d answers from answer key", len(answer_key))

        # ── Pass 2: Extract question blocks per page ───────────────────────────
        questions: List[ParsedQuestion] = []
        for page_num, page_text in page_texts:
            # Strip the answer key section from parsing to avoid false matches
            clean_text = self._strip_answer_section(page_text)
            page_questions = self._parse_page(clean_text, page_num, answer_key, warnings)
            questions.extend(page_questions)

        # Deduplicate by source_number (same question may appear on page overlap)
        seen: set = set()
        unique_questions: List[ParsedQuestion] = []
        for q in questions:
            if q.source_number not in seen:
                seen.add(q.source_number)
                unique_questions.append(q)

        total_with_answers = sum(1 for q in unique_questions if q.correct_answer is not None)
        logger.info(
            "Parsing complete: %d questions, %d with answers",
            len(unique_questions), total_with_answers,
        )

        return ParseResult(
            questions=unique_questions,
            answer_key=answer_key,
            parse_warnings=warnings,
            total_extracted=len(unique_questions),
            total_with_answers=total_with_answers,
        )

    def _strip_answer_section(self, text: str) -> str:
        """Remove the answer key section from text before parsing questions."""
        match = ANSWER_SECTION_RE.search(text)
        if match:
            return text[:match.start()]
        # Also strip inline "Ans:" lines for cleaner question text
        return ANSWER_INLINE_RE.sub("", text)

    def _extract_answer_key(self, text: str) -> Dict[int, str]:
        """
        Locate and parse the answer key section.

        Tries to find a dedicated answer key block first.
        Falls back to scanning for inline "Ans: X" patterns.
        """
        answer_key: Dict[int, str] = {}

        # Check for dedicated answer section
        section_match = ANSWER_SECTION_RE.search(text)
        if section_match:
            ans_section = text[section_match.end():]
            for match in ANSWER_KEY_NUMBERED_RE.finditer(ans_section):
                try:
                    q_num = int(match.group(1))
                    ans = match.group(2).upper()
                    answer_key[q_num] = ans
                except (ValueError, IndexError):
                    pass
            if answer_key:
                return answer_key

        # Fallback: scan whole text for numbered answers
        for match in ANSWER_KEY_NUMBERED_RE.finditer(text):
            try:
                q_num = int(match.group(1))
                ans = match.group(2).upper()
                # Only include if it's in a plausible range (1-200)
                if 1 <= q_num <= 200:
                    answer_key[q_num] = ans
            except (ValueError, IndexError):
                pass

        return answer_key

    def _parse_page(
        self,
        page_text: str,
        page_num: int,
        answer_key: Dict[int, str],
        warnings: List[str],
    ) -> List[ParsedQuestion]:
        """Parse a single page's text into question objects."""
        questions: List[ParsedQuestion] = []

        # Find all question start positions
        q_starts = list(QUESTION_START_RE.finditer(page_text))
        if not q_starts:
            return questions

        for i, match in enumerate(q_starts):
            # Get the captured question number from either named group
            q_num_str = match.group("qnum1") or match.group("qnum2")
            if q_num_str is None:
                continue
            q_num = int(q_num_str)
            start = match.end()
            end = q_starts[i + 1].start() if i + 1 < len(q_starts) else len(page_text)
            block = page_text[start:end].strip()

            parsed = self._parse_question_block(
                block=block,
                source_number=q_num,
                page_num=page_num,
                answer_key=answer_key,
                warnings=warnings,
            )
            if parsed is not None:
                questions.append(parsed)

        return questions

    def _parse_question_block(
        self,
        block: str,
        source_number: int,
        page_num: int,
        answer_key: Dict[int, str],
        warnings: List[str],
    ) -> Optional[ParsedQuestion]:
        """Parse one question block into a ParsedQuestion."""
        if not block.strip():
            return None

        lines = block.split("\n")
        options: Dict[str, str] = {}
        question_lines: List[str] = []
        in_options = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            opt_match = OPTION_LABEL_RE.match(stripped)
            if opt_match:
                letter = opt_match.group(1).upper()
                opt_text = opt_match.group(2).strip()
                if letter in ("A", "B", "C", "D"):
                    options[letter] = opt_text
                    in_options = True
            elif not in_options:
                # Still reading question text (before options)
                question_lines.append(stripped)
            else:
                # After first option, multi-line option continuation
                # Append to the last option
                if options:
                    last_letter = list(options.keys())[-1]
                    options[last_letter] += " " + stripped

        q_text = " ".join(question_lines).strip()
        q_text = re.sub(r"\s+", " ", q_text).strip()

        if not q_text:
            warnings.append(f"Q{source_number} (page {page_num}): Empty question text — skipped.")
            return None

        # Validate all 4 options present
        opt_a = options.get("A", "")
        opt_b = options.get("B", "")
        opt_c = options.get("C", "")
        opt_d = options.get("D", "")

        missing = [k for k, v in {"A": opt_a, "B": opt_b, "C": opt_c, "D": opt_d}.items() if not v]
        if missing:
            warnings.append(
                f"Q{source_number} (page {page_num}): Missing options {missing}. "
                "Included with empty options — needs manual review."
            )

        confidence = self._compute_confidence(q_text, opt_a, opt_b, opt_c, opt_d)
        correct_answer = answer_key.get(source_number)

        return ParsedQuestion(
            source_number=source_number,
            question_text=q_text,
            option_a=opt_a or "—",
            option_b=opt_b or "—",
            option_c=opt_c or "—",
            option_d=opt_d or "—",
            correct_answer=correct_answer,
            confidence=confidence,
            page_number=page_num,
        )

    @staticmethod
    def _compute_confidence(q_text: str, a: str, b: str, c: str, d: str) -> float:
        """
        Heuristic confidence score (0.0 – 1.0).

        Factors:
          - All 4 options present: +0.4
          - Question text > 15 chars: +0.3
          - Options are all distinct: +0.2
          - No OCR artefacts (garbled chars): +0.1
        """
        score = 0.0
        opts = [a, b, c, d]
        all_present = all(o and o != "—" for o in opts)

        if all_present:
            score += 0.4
        if len(q_text) > 15:
            score += 0.3
        if all_present and len(set(opts)) == 4:
            score += 0.2
        non_ascii = sum(1 for ch in q_text if ord(ch) > 127)
        if len(q_text) > 0 and non_ascii / len(q_text) < 0.3:
            score += 0.1

        return round(min(score, 1.0), 2)
