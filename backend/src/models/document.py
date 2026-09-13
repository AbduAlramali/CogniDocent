from __future__ import annotations
from datetime import datetime, timezone
import uuid
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.infra.postgres_adapter import Base

if TYPE_CHECKING:
    from src.models.project import Project
    from src.models.document_chunk import DocumentChunk


class Document(Base):
    """
    SQLAlchemy Model representing the 'documents' table.
    """

    __tablename__ = "documents"

    doc_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Unique identifier for the document",
    )
    file_path: Mapped[str] = mapped_column(
        String, nullable=False, comment="Physical path where the file is stored"
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Timestamp when the file was uploaded",
    )
    file_size_bytes: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Size of the file in bytes"
    )
    file_hash: Mapped[str] = mapped_column(
        String,
        nullable=False,
        unique=True,
        comment="Hash of the file content for duplicate checking",
    )
    content_type: Mapped[str] = mapped_column(
        String, nullable=False, comment="MIME/Content type of the file"
    )
    status: Mapped[str] = mapped_column(
        String, nullable=False, comment="Processing status of the document"
    )
    primary_name: Mapped[str] = mapped_column(
        String, nullable=False, comment="Original name of the uploaded file"
    )
    toc: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Extracted table of contents / bookmarks stored as JSON",
    )
    doc_metadata: Mapped[dict | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
        comment="Document header metadata stored as JSON",
    )
    thumbnails: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Generated thumbnails stored as JSON",
    )

    # Relationships
    # One-to-One relationship back to Project
    project: Mapped[Project | None] = relationship(
        "Project",
        back_populates="document",
        uselist=False,
        cascade="all, delete-orphan",
    )
    chunks: Mapped[list[DocumentChunk]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Document(doc_id={self.doc_id}, primary_name={self.primary_name}, status={self.status})>"
