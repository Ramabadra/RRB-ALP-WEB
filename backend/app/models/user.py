"""
User model — Google OAuth users only.
Passwords are never stored.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    google_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    profile_image: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    last_login: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # ─── Relationships ────────────────────────────────────────────────────────
    mock_tests: Mapped[list["MockTest"]] = relationship(  # noqa: F821
        "MockTest", back_populates="user", lazy="noload"
    )
    attempts: Mapped[list["Attempt"]] = relationship(  # noqa: F821
        "Attempt", back_populates="user", lazy="noload"
    )
    results: Mapped[list["Result"]] = relationship(  # noqa: F821
        "Result", back_populates="user", lazy="noload"
    )
    pdf_documents: Mapped[list["PdfDocument"]] = relationship(  # noqa: F821
        "PdfDocument", back_populates="user", lazy="noload"
    )
    mistake_questions: Mapped[list["MistakeQuestion"]] = relationship(  # noqa: F821
        "MistakeQuestion", back_populates="user", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
