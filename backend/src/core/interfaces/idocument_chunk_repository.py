from abc import ABC, abstractmethod
import uuid
from typing import Sequence, Optional, List, Tuple
from src.models.document_chunk import DocumentChunk
from src.schemas.document_chunk import DocumentChunkResponse, ChunkUpdateDTO


class IDocumentChunkRepository(ABC):
    """
    Interface for DocumentChunk repository operations (Port).
    Provides database access primitives for DocumentChunks and embedding metadata.
    Contains no business logic or orchestration.
    """

    @abstractmethod
    async def get_by_id(self, chunk_id: uuid.UUID) -> DocumentChunk | None:
        """Retrieve a chunk by its ID."""
        pass

    @abstractmethod
    async def get_by_chunk_index(self, doc_id: uuid.UUID, chunk_index: int) -> DocumentChunk | None:
        """Retrieve a specific chunk of a document by sequential chunk index."""
        pass

    @abstractmethod
    async def list_by_document(self, doc_id: uuid.UUID) -> Sequence[DocumentChunk]:
        """Retrieve all chunks for a specific document, ordered by chunk_index."""
        pass

    @abstractmethod
    async def get_chunks_in_page_range(
        self, doc_id: uuid.UUID, start_page: int, end_page: int
    ) -> Sequence[DocumentChunk]:
        """Retrieve document chunks where page_num is within [start_page, end_page] inclusive, ordered by chunk_index."""
        pass

    @abstractmethod
    async def get_chunks_in_context_window(
        self, doc_id: uuid.UUID, target_chunk_index: int, radius: int = 2
    ) -> Sequence[DocumentChunk]:
        """
        Retrieve chunks surrounding target_chunk_index within [target - radius, target + radius]
        ordered by chunk_index ASC.
        """
        pass

    @abstractmethod
    async def create(self, chunk: DocumentChunk) -> DocumentChunk:
        """Save a new document chunk."""
        pass

    @abstractmethod
    async def bulk_create(self, chunks: Sequence[DocumentChunk]) -> Sequence[DocumentChunk]:
        """Bulk save document chunks."""
        pass

    @abstractmethod
    async def update(self, chunk_id: uuid.UUID, **kwargs) -> DocumentChunk:
        """Update an existing chunk."""
        pass

    @abstractmethod
    async def delete(self, chunk_id: uuid.UUID) -> bool:
        """Delete a chunk by its ID."""
        pass

    @abstractmethod
    async def get_embedding_metadata(self, project_id: uuid.UUID) -> Optional[Tuple[str, int]]:
        """Retrieve active embedding model name and dimensions for a project."""
        pass

    @abstractmethod
    async def upsert_embedding_metadata(
        self, project_id: uuid.UUID, active_model: str, dimensions: int
    ) -> None:
        """Upsert embedding metadata record for a project."""
        pass

    @abstractmethod
    async def alter_embedding_dimensions(self, new_dimensions: int) -> None:
        """
        Execute DDL routine to alter pgvector column dimensions for content_vector and deep_content_vector:
        1. DROP INDEX IF EXISTS idx_document_chunks_content_vector;
        2. DROP INDEX IF EXISTS idx_document_chunks_deep_content_vector;
        3. ALTER TABLE document_chunks ALTER COLUMN content_vector TYPE vector(:new_dimensions) USING NULL;
        4. ALTER TABLE document_chunks ALTER COLUMN deep_content_vector TYPE vector(:new_dimensions) USING NULL;
        5. Rebuild HNSW indexes.
        """
        pass

    @abstractmethod
    async def nullify_project_embeddings(self, project_id: uuid.UUID) -> None:
        """
        Execute DML update setting content_vector = NULL and deep_content_vector = NULL for chunks of the document belonging to project_id.
        """
        pass

    @abstractmethod
    async def count_populated_embeddings(self, doc_id: uuid.UUID) -> int:
        """Count how many chunks for doc_id have non-null content_vector or deep_content_vector."""
        pass

    @abstractmethod
    async def search_chunks_vector(
        self, doc_id: uuid.UUID, query_vector: List[float], limit: int = 3
    ) -> Sequence[DocumentChunk]:
        """
        Execute unified vector search across all chunks: evaluates deep_content_vector per chunk,
        falling back to content_vector if deep_content_vector is not present.
        """
        pass

    @abstractmethod
    async def get_fallback_chunks(
        self, doc_id: uuid.UUID, limit: int = 3
    ) -> Sequence[DocumentChunk]:
        """Fetch the first N chunks of a document ordered by chunk_index."""
        pass

    @abstractmethod
    async def get_chunks_missing_embeddings(
        self,
        project_id: uuid.UUID,
        batch_size: int = 100,
    ) -> List[DocumentChunkResponse]:
        """Fetches chunk rows where content_vector IS NULL for the specified project."""
        pass

    @abstractmethod
    async def update_chunks(
        self, updates: Sequence[ChunkUpdateDTO]
    ) -> None:
        """Batch update document chunks with deep_content and deep_content_vector."""
        pass
