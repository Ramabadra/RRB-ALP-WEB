"""
AI Prompts & Schemas — specifies instructions and structured output schemas.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


# ── Validation Schemas ────────────────────────────────────────────────────────

class ValidatedQuestionSchema(BaseModel):
    """Schema for the AI's response when validating a question."""
    is_valid: bool = Field(
        ...,
        description="True if the question is coherent and has a definitive answer. False if the text is completely garbled or unsolvable.",
    )
    question_text: str = Field(
        ...,
        description="Cleaned up question text. Fix OCR errors. Convert math formulas to LaTeX/MathML if applicable.",
    )
    option_a: str = Field(..., description="Cleaned option A text.")
    option_b: str = Field(..., description="Cleaned option B text.")
    option_c: str = Field(..., description="Cleaned option C text.")
    option_d: str = Field(..., description="Cleaned option D text.")
    correct_answer: str = Field(
        ...,
        description="The verified correct option letter: 'A', 'B', 'C', or 'D'.",
    )
    explanation: str = Field(
        ...,
        description="A clear, concise, step-by-step explanation for the correct answer.",
    )
    suggested_subject: str = Field(
        ...,
        description="Categorize this question into one of: MATHEMATICS, GENERAL_INTELLIGENCE, GENERAL_SCIENCE, GENERAL_AWARENESS.",
    )


VALIDATION_PROMPT_TEMPLATE = """
You are an expert examiner for the Indian Railways RRB ALP (Assistant Loco Pilot) exam.

Your task is to review and validate a question that was extracted via OCR from a past exam paper.
The extraction might contain typos, garbled text, or missing mathematical formatting.
The extracted answer key might also be incorrect or missing.

Here is the extracted data:
Question Text: {question_text}
Option A: {option_a}
Option B: {option_b}
Option C: {option_c}
Option D: {option_d}
Extracted Answer: {extracted_answer}

INSTRUCTIONS:
1. Clean up any OCR typos (e.g., 'l' instead of '1', garbled symbols).
2. If there are mathematical equations or symbols, format them using standard MathML or LaTeX conventions where appropriate.
3. Determine the undeniably correct answer based on the cleaned options. If the extracted answer is wrong, correct it.
4. Provide a step-by-step explanation for the correct answer.
5. Categorize the question into the most appropriate RRB ALP subject.

Return the result as a structured JSON object matching the requested schema.
"""


# ── Generation Schemas ────────────────────────────────────────────────────────

class GeneratedQuestion(BaseModel):
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str = Field(..., description="'A', 'B', 'C', or 'D'")
    explanation: str
    difficulty: str = Field(..., description="'EASY', 'MEDIUM', or 'HARD'")
    subtopic: Optional[str] = Field(None, description="Specific subtopic name (e.g., 'Trigonometry')")


class GeneratedQuestionsBatchSchema(BaseModel):
    questions: List[GeneratedQuestion] = Field(..., description="List of generated questions")


GENERATION_PROMPT_TEMPLATE = """
You are an expert examiner for the Indian Railways RRB ALP (Assistant Loco Pilot) exam.

Your task is to generate {count} original, high-quality multiple-choice questions for a mock test.
The questions must strictly follow the RRB ALP exam pattern and difficulty level.

Parameters:
- Subject: {subject}
- Topic: {topic}
- Target Difficulty: {difficulty}
- Language: English

INSTRUCTIONS:
1. Generate exactly {count} distinct questions.
2. The questions must be conceptually accurate and relevant to the RRB ALP syllabus for the given subject and topic.
3. Provide exactly 4 options (A, B, C, D) for each question.
4. Ensure exactly one option is unambiguously correct.
5. Provide a clear step-by-step explanation.
6. Use LaTeX/MathML for any mathematical formulas if applicable.

Return the result as a structured JSON array matching the requested schema.
"""
