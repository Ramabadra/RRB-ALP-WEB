"""
app/schemas/__init__.py
"""
from app.schemas.analytics import AnalyticsResponse
from app.schemas.attempt import (
    AnswerSaveRequest,
    AttemptCreateRequest,
    AttemptResponse,
    AttemptStatusResponse,
    SingleAnswerSave,
    SubmitResponse,
)
from app.schemas.auth import AuthCallbackParams, GoogleAuthInitResponse, TokenResponse
from app.schemas.common import ErrorResponse, MessageResponse, PaginatedResponse
from app.schemas.mistake import MistakeAddRequest, MistakePracticeRequest, MistakeResponse
from app.schemas.mock_test import MockTestGenerateRequest, MockTestResponse, MockTestSummary
from app.schemas.pdf import (
    PdfDocumentResponse,
    PdfJobStatusResponse,
    PdfUploadMetadata,
    PdfUploadResponse,
)
from app.schemas.question import (
    AnswerChoice,
    Difficulty,
    Language,
    QuestionCreateRequest,
    QuestionFilterParams,
    QuestionResponse,
    QuestionSummary,
    QuestionUpdateRequest,
    SourceType,
    VerificationStatus,
)
from app.schemas.result import ResultResponse
from app.schemas.subject import SubjectResponse, TopicResponse, TopicWithSubjectResponse
from app.schemas.user import UserResponse, UserUpdateRequest

__all__ = [
    # Common
    "PaginatedResponse", "MessageResponse", "ErrorResponse",
    # Auth
    "GoogleAuthInitResponse", "TokenResponse", "AuthCallbackParams",
    # User
    "UserResponse", "UserUpdateRequest",
    # Subject/Topic
    "SubjectResponse", "TopicResponse", "TopicWithSubjectResponse",
    # Question
    "QuestionResponse", "QuestionSummary", "QuestionCreateRequest",
    "QuestionUpdateRequest", "QuestionFilterParams",
    "AnswerChoice", "SourceType", "VerificationStatus", "Difficulty", "Language",
    # MockTest
    "MockTestGenerateRequest", "MockTestResponse", "MockTestSummary",
    # Attempt
    "AttemptCreateRequest", "AttemptResponse", "AttemptStatusResponse",
    "AnswerSaveRequest", "SingleAnswerSave", "SubmitResponse",
    # Result
    "ResultResponse",
    # Analytics
    "AnalyticsResponse",
    # Mistakes
    "MistakeResponse", "MistakeAddRequest", "MistakePracticeRequest",
    # PDF
    "PdfUploadResponse", "PdfDocumentResponse", "PdfJobStatusResponse", "PdfUploadMetadata",
]
