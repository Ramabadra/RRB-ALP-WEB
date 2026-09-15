"""
Question schemas.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, field_validator


class AnswerChoice(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class SourceType(str, Enum):
    PYQ = "PYQ"
    AI_GENERATED = "AI_GENERATED"
    REFERENCE = "REFERENCE"


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    REJECTED = "REJECTED"
    UNVERIFIED = "UNVERIFIED"


class Difficulty(str, Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class Language(str, Enum):
    ENGLISH = "ENGLISH"
    HINDI = "HINDI"
    BILINGUAL = "BILINGUAL"


class QuestionResponse(BaseModel):
    """Full question response — used in question bank and review screens."""

    id: UUID
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: AnswerChoice
    explanation: str | None

    subject_id: UUID | None
    topic_id: UUID | None
    subtopic: str | None
    difficulty: Difficulty
    language: Language

    source_type: SourceType
    source_exam: str | None
    source_year: int | None

    verification_status: VerificationStatus
    extraction_confidence: float | None

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuestionSummary(BaseModel):
    """Lightweight question representation for lists — no correct answer exposed during exam."""

    id: UUID
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    subject_id: UUID | None
    topic_id: UUID | None
    difficulty: Difficulty
    source_type: SourceType

    model_config = {"from_attributes": True}


class QuestionCreateRequest(BaseModel):
    """Used to manually create a question via the API."""

    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: AnswerChoice
    explanation: str | None = None
    subject_id: UUID | None = None
    topic_id: UUID | None = None
    subtopic: str | None = None
    difficulty: Difficulty = Difficulty.MEDIUM
    language: Language = Language.ENGLISH
    source_type: SourceType = SourceType.REFERENCE
    source_exam: str | None = None
    # Must be None if source_type == AI_GENERATED
    source_year: int | None = None
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED

    @field_validator("source_year")
    @classmethod
    def ai_questions_have_no_year(cls, v: int | None, info: object) -> int | None:
        # Access values via info.data in Pydantic v2
        data = getattr(info, "data", {})
        if data.get("source_type") == SourceType.AI_GENERATED and v is not None:
            raise ValueError(
                "AI_GENERATED questions must not have a source_year. "
                "Do not invent exam years."
            )
        return v


class QuestionUpdateRequest(BaseModel):
    """Partial update for a question."""

    question_text: str | None = None
    option_a: str | None = None
    option_b: str | None = None
    option_c: str | None = None
    option_d: str | None = None
    correct_answer: AnswerChoice | None = None
    explanation: str | None = None
    subject_id: UUID | None = None
    topic_id: UUID | None = None
    subtopic: str | None = None
    difficulty: Difficulty | None = None
    language: Language | None = None
    source_type: SourceType | None = None
    source_year: int | None = None
    verification_status: VerificationStatus | None = None


class QuestionFilterParams(BaseModel):
    """Query parameters for GET /api/questions."""

    subject_id: UUID | None = None
    topic_id: UUID | None = None
    source_type: SourceType | None = None
    difficulty: Difficulty | None = None
    verification_status: VerificationStatus | None = None
    source_year: int | None = None
    language: Language | None = None
    page: int = 1
    page_size: int = 20

    @field_validator("page_size")
    @classmethod
    def cap_page_size(cls, v: int) -> int:
        return min(v, 100)


class QuestionGenerateRequest(BaseModel):
    subject_id: UUID
    topic_id: UUID
    difficulty: Difficulty
    count: int = 5


class QuestionValidateBatchRequest(BaseModel):
    question_ids: list[UUID]
