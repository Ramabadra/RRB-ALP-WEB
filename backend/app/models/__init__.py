"""
app/models/__init__.py
Re-exports all ORM models so Alembic can discover them via metadata.
"""

from app.models.attempt import Attempt, AttemptAnswer
from app.models.mistake import MistakeQuestion
from app.models.mock_test import MockTest, MockTestQuestion
from app.models.pdf import PdfDocument, PdfProcessingJob
from app.models.question import Question, QuestionSource
from app.models.result import Result
from app.models.subject import Subject, Topic
from app.models.user import User

__all__ = [
    "User",
    "Subject",
    "Topic",
    "QuestionSource",
    "Question",
    "MockTest",
    "MockTestQuestion",
    "Attempt",
    "AttemptAnswer",
    "Result",
    "PdfDocument",
    "PdfProcessingJob",
    "MistakeQuestion",
]
