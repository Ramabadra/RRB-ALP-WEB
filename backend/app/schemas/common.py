"""
Common shared schemas: pagination, errors, generic responses.
"""

from __future__ import annotations

from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper used by all list endpoints."""

    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageResponse(BaseModel):
    """Simple success message response."""

    message: str


class ErrorDetail(BaseModel):
    """Machine-readable error detail."""

    field: str | None = None
    message: str


class ErrorResponse(BaseModel):
    """Standard error envelope returned for all 4xx/5xx responses."""

    error: str
    details: List[ErrorDetail] | None = None
    status_code: int
