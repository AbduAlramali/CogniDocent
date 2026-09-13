from __future__ import annotations
import uuid
from typing import TYPE_CHECKING
from sqlalchemy import Integer, ForeignKey, Text, Index, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from src.infra.postgres_adapter import Base

if TYPE_CHECKING:
    from src.models.document import Document


class DocumentChunk(Base):
    """
    SQLAlchemy Model representing the 'document_chunks' table.
    Stores extracted chunk-level content with vector search indexing.
    """

    __tablename__ = "document_chunks"

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Uniquely identifies this specific text segment. Replaces page_id.",
    )

    doc_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.doc_id", ondelete="CASCADE"),
        nullable=False,
        comment="Links back to the main document.",
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="The absolute sequential order of the chunk across the entire document (1, 2, 3...). Essential for reconstructing flow.",
    )
    page_num: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Retained from your old schema. Multiple rows will now share the same page_num and doc_id.",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The 500-token chunk.",
    )
    content_vector: Mapped[list[float] | None] = mapped_column(
        Vector(768),
        nullable=True,
        comment="The embedding for this specific chunk.",
    )
    deep_content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Retained for your advanced processing logic.",
    )
    deep_content_vector: Mapped[list[float] | None] = mapped_column(
        Vector(768),
        nullable=True,
        comment="Retained for your advanced processing logic.",
    )
    bbox: Mapped[list[float] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Bounding box coordinates [x0, y0, x1, y1] for PDF highlighting.",
    )

    # Relationships
    document: Mapped[Document] = relationship(
        "Document",
        back_populates="chunks",
    )

    # Constraints and HNSW indexes for vector cosine similarity
    __table_args__ = (
        UniqueConstraint(
            "doc_id", "chunk_index", name="uq_document_chunks_doc_id_chunk_index"
        ),
        Index(
            "idx_document_chunks_content_vector",
            "content_vector",
            postgresql_using="hnsw",
            postgresql_ops={"content_vector": "vector_cosine_ops"},
        ),
        Index(
            "idx_document_chunks_deep_content_vector",
            "deep_content_vector",
            postgresql_using="hnsw",
            postgresql_ops={"deep_content_vector": "vector_cosine_ops"},
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentChunk(chunk_id={self.chunk_id}, doc_id={self.doc_id}, "
            f"chunk_index={self.chunk_index}, page_num={self.page_num})>"
        )
