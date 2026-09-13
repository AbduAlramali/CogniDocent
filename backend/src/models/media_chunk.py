from __future__ import annotations
import uuid
from typing import TYPE_CHECKING
from sqlalchemy import Integer, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from src.infra.postgres_adapter import Base

if TYPE_CHECKING:
    from src.models.media import Media


class MediaChunk(Base):
    """
    SQLAlchemy Model representing the 'media_chunks' table.
    Stores chunked content extracted from media files with vector search indexing.
    """
    __tablename__ = "media_chunks"

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Unique identifier for the media chunk",
    )
    media_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("media.media_id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to the parent media file",
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Sequence index of the chunk within the media file",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Text content extracted from the media chunk",
    )
    content_vector: Mapped[list[float] | None] = mapped_column(
        Vector(768),
        nullable=True,
        comment="Vector embedding of the chunk content",
    )
    chunk_metadata: Mapped[dict | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        comment="Metadata associated with the media chunk stored as JSONB",
    )

    # Relationships
    media: Mapped[Media] = relationship(
        "Media",
        back_populates="chunks",
    )

    # HNSW index for vector cosine similarity
    __table_args__ = (
        Index(
            "idx_media_chunks_content_vector",
            "content_vector",
            postgresql_using="hnsw",
            postgresql_ops={"content_vector": "vector_cosine_ops"},
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<MediaChunk(chunk_id={self.chunk_id}, media_id={self.media_id}, "
            f"chunk_index={self.chunk_index})>"
        )
