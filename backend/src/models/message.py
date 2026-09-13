from __future__ import annotations
from datetime import datetime, timezone
import uuid
from typing import TYPE_CHECKING, Any
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.infra.postgres_adapter import Base
from src.core.enums import ChatProvider

if TYPE_CHECKING:
    from src.models.chat import Chat
    from src.models.media import Media


class Message(Base):
    """
    SQLAlchemy Model representing the 'messages' table.
    """

    __tablename__ = "messages"

    message_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Unique identifier for the message",
    )
    chat_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chats.chat_id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to the associated chat session",
    )
    role: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="Role of the sender (e.g. system, user, assistant)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Timestamp when the message was created",
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Text content of the message"
    )
    citations: Mapped[Any | None] = mapped_column(
        JSONB, nullable=True, comment="Citations or source references stored as JSONB"
    )
    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Optional response generation latency in milliseconds",
    )
    token_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Optional token count of the message"
    )
    ai_provider: Mapped[ChatProvider | None] = mapped_column(
        SQLEnum(ChatProvider, name="ai_provider", native_enum=True),
        nullable=True,
        default=None,
        comment="AI Provider used for this message (if assistant role)",
    )
    ai_model: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        comment="AI Model version used for this message (if assistant role)",
    )

    # Relationships
    chat: Mapped[Chat] = relationship("Chat", back_populates="messages")
    media: Mapped[list[Media]] = relationship(
        "Media", back_populates="message", cascade="all, delete-orphan"
    )

    @property
    def image_captions(self) -> list[str]:
        """
        Captions of associated image media files that do not have entries in media_chunks.
        """
        if not self.media:
            return []
        return [
            m.caption
            for m in self.media
            if m.caption and not getattr(m, "has_chunks", False)
        ]

    @property
    def image_attachments(self) -> list[Media]:
        """
        Image media attachments that do not have entries in media_chunks.
        """
        if not self.media:
            return []
        return [
            m
            for m in self.media
            if (m.content_type or "").startswith("image/") and not getattr(m, "has_chunks", False)
        ]

    @property
    def doc_attachments(self) -> list[Media]:
        """
        Document, text, or chunked media attachments.
        """
        if not self.media:
            return []
        return [
            m
            for m in self.media
            if not ((m.content_type or "").startswith("image/") and not getattr(m, "has_chunks", False))
        ]

    def __repr__(self) -> str:
        return f"<Message(message_id={self.message_id}, chat_id={self.chat_id}, role={self.role})>"


