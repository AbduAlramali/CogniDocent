from __future__ import annotations
from datetime import datetime, timezone
import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from src.infra.postgres_adapter import Base
from src.core.enums import UploadStatus

if TYPE_CHECKING:
    from src.models.message import Message
    from src.models.media_chunk import MediaChunk


class Media(Base):
    """
    SQLAlchemy Model representing the 'media' table.
    """

    __tablename__ = "media"

    media_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Unique identifier for the media file",
    )
    message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("messages.message_id", ondelete="CASCADE"),
        nullable=True,
        comment="Reference to the associated message",
    )

    filename: Mapped[str] = mapped_column(
        String, nullable=False, comment="Original filename of the media attachment"
    )
    file_path: Mapped[str] = mapped_column(
        String, nullable=False, comment="Physical path where the file is stored"
    )
    file_size_bytes: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Size of the file in bytes"
    )
    file_hash: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="Hash of the file content for duplicate checking",
    )
    content_type: Mapped[str] = mapped_column(
        String, nullable=False, comment="MIME/Content type of the media file"
    )
    status: Mapped[UploadStatus] = mapped_column(
        Enum(UploadStatus),
        nullable=False,
        default=UploadStatus.PROCESSING,
        server_default=UploadStatus.PROCESSING.value,
        comment="Processing/Upload status of the media",
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Timestamp when the media file was uploaded",
    )
    thumbnails: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    caption: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Caption for images"
    )
    has_chunks: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        comment="Indicates whether this media entry has linked entries in media_chunks",
    )

    # Relationships
    message: Mapped[Message] = relationship("Message", back_populates="media")
    chunks: Mapped[list[MediaChunk]] = relationship(
        "MediaChunk",
        back_populates="media",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Media(media_id={self.media_id}, filename={self.filename}, status={self.status}, has_chunks={self.has_chunks})>"

