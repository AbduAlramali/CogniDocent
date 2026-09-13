import uuid
from typing import Sequence, Optional, List, Tuple
from sqlalchemy import select, update, func, text, or_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.core.interfaces.ilogger import ILogger
from src.core.interfaces.idocument_chunk_repository import IDocumentChunkRepository
from src.schemas.document_chunk import DocumentChunkResponse, ChunkUpdateDTO
from src.core.exceptions.database import (
    RepositoryError,
    DocumentChunkNotFoundError,
    DuplicateChunkError,
)
from src.models.document_chunk import DocumentChunk
from src.models.project import Project
from src.models.embedding_index_metadata import EmbeddingIndexMetadata


class DocumentChunkRepository(IDocumentChunkRepository):
    """
    SQLAlchemy implementation of IDocumentChunkRepository (PostgreSQL Adapter).
    Contains purely database access operations without business logic or orchestration.
    """

    def __init__(self, session: AsyncSession, logger: ILogger) -> None:
        self.session = session
        self.logger = logger

    async def get_by_id(self, chunk_id: uuid.UUID) -> DocumentChunk | None:
        try:
            stmt = select(DocumentChunk).where(DocumentChunk.chunk_id == chunk_id)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            self.logger.error("Database error retrieving chunk by ID", chunk_id=chunk_id, exc_info=e)
            raise RepositoryError(f"Failed to retrieve chunk: {str(e)}") from e

    async def get_by_chunk_index(self, doc_id: uuid.UUID, chunk_index: int) -> DocumentChunk | None:
        try:
            stmt = select(DocumentChunk).where(
                DocumentChunk.doc_id == doc_id,
                DocumentChunk.chunk_index == chunk_index,
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            self.logger.error(
                "Database error retrieving chunk by index",
                doc_id=doc_id,
                chunk_index=chunk_index,
                exc_info=e,
            )
            raise RepositoryError(f"Failed to retrieve chunk: {str(e)}") from e

    async def list_by_document(self, doc_id: uuid.UUID) -> Sequence[DocumentChunk]:
        try:
            stmt = (
                select(DocumentChunk)
                .where(DocumentChunk.doc_id == doc_id)
                .order_by(DocumentChunk.chunk_index.asc())
            )
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            self.logger.error("Database error listing chunks for document", doc_id=doc_id, exc_info=e)
            raise RepositoryError(f"Failed to list chunks: {str(e)}") from e

    async def get_chunks_in_page_range(
        self, doc_id: uuid.UUID, start_page: int, end_page: int
    ) -> Sequence[DocumentChunk]:
        try:
            stmt = (
                select(DocumentChunk)
                .where(
                    DocumentChunk.doc_id == doc_id,
                    DocumentChunk.page_num >= start_page,
                    DocumentChunk.page_num <= end_page,
                )
                .order_by(DocumentChunk.chunk_index.asc())
            )
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            self.logger.error(
                "Database error retrieving chunks in page range",
                doc_id=doc_id,
                start_page=start_page,
                end_page=end_page,
                exc_info=e,
            )
            raise RepositoryError(f"Failed to retrieve chunks in page range: {str(e)}") from e

    async def get_chunks_in_context_window(
        self, doc_id: uuid.UUID, target_chunk_index: int, radius: int = 2
    ) -> Sequence[DocumentChunk]:
        try:
            min_index = max(0, target_chunk_index - radius)
            max_index = target_chunk_index + radius
            stmt = (
                select(DocumentChunk)
                .where(
                    DocumentChunk.doc_id == doc_id,
                    DocumentChunk.chunk_index >= min_index,
                    DocumentChunk.chunk_index <= max_index,
                )
                .order_by(DocumentChunk.chunk_index.asc())
            )
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            self.logger.error(
                "Database error expanding chunk context",
                doc_id=doc_id,
                target_chunk_index=target_chunk_index,
                radius=radius,
                exc_info=e,
            )
            raise RepositoryError(f"Failed to expand chunk context: {str(e)}") from e

    async def create(self, chunk: DocumentChunk) -> DocumentChunk:
        try:
            self.session.add(chunk)
            await self.session.commit()
            await self.session.refresh(chunk)
            return chunk
        except IntegrityError as e:
            await self.session.rollback()
            self.logger.warning(
                "DocumentChunk integrity violation on create",
                doc_id=chunk.doc_id,
                chunk_index=chunk.chunk_index,
                exc_info=e,
            )
            raise DuplicateChunkError("doc_id and chunk_index combo", f"doc_id={chunk.doc_id}, chunk_index={chunk.chunk_index}") from e
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error(
                "Database error creating document chunk",
                doc_id=chunk.doc_id,
                chunk_index=chunk.chunk_index,
                exc_info=e,
            )
            raise RepositoryError(f"Failed to create chunk: {str(e)}") from e

    async def bulk_create(self, chunks: Sequence[DocumentChunk]) -> Sequence[DocumentChunk]:
        try:
            self.session.add_all(chunks)
            await self.session.commit()
            return chunks
        except IntegrityError as e:
            await self.session.rollback()
            self.logger.warning("DocumentChunk integrity violation on bulk_create", exc_info=e)
            raise DuplicateChunkError("chunks", "Duplicate chunk entries detected") from e
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error("Database error bulk creating document chunks", count=len(chunks), exc_info=e)
            raise RepositoryError(f"Failed to bulk create chunks: {str(e)}") from e

    async def update(self, chunk_id: uuid.UUID, **kwargs) -> DocumentChunk:
        try:
            chunk = await self.get_by_id(chunk_id)
            if not chunk:
                raise DocumentChunkNotFoundError(chunk_id)

            for key, value in kwargs.items():
                if hasattr(chunk, key):
                    setattr(chunk, key, value)

            await self.session.commit()
            await self.session.refresh(chunk)
            return chunk
        except DocumentChunkNotFoundError:
            raise
        except IntegrityError as e:
            await self.session.rollback()
            self.logger.warning("DocumentChunk integrity violation on update", chunk_id=chunk_id, exc_info=e)
            raise DuplicateChunkError("fields", str(kwargs)) from e
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error("Database error updating chunk", chunk_id=chunk_id, exc_info=e)
            raise RepositoryError(f"Failed to update chunk: {str(e)}") from e

    async def delete(self, chunk_id: uuid.UUID) -> bool:
        try:
            chunk = await self.get_by_id(chunk_id)
            if not chunk:
                return False

            await self.session.delete(chunk)
            await self.session.commit()
            return True
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error("Database error deleting chunk", chunk_id=chunk_id, exc_info=e)
            raise RepositoryError(f"Failed to delete chunk: {str(e)}") from e

    async def get_embedding_metadata(self, project_id: uuid.UUID) -> Optional[Tuple[str, int]]:
        try:
            stmt = select(EmbeddingIndexMetadata).where(
                EmbeddingIndexMetadata.project_id == project_id
            )
            result = await self.session.execute(stmt)
            record = result.scalar_one_or_none()
            if record:
                return (record.active_model, record.dimensions)
            return None
        except SQLAlchemyError as e:
            self.logger.error("Database error retrieving embedding metadata", project_id=project_id, exc_info=e)
            raise RepositoryError(f"Failed to retrieve embedding metadata: {str(e)}") from e

    async def upsert_embedding_metadata(
        self, project_id: uuid.UUID, active_model: str, dimensions: int
    ) -> None:
        try:
            stmt = select(EmbeddingIndexMetadata).where(
                EmbeddingIndexMetadata.project_id == project_id
            )
            result = await self.session.execute(stmt)
            meta_row = result.scalar_one_or_none()
            if meta_row:
                meta_row.active_model = active_model
                meta_row.dimensions = dimensions
                meta_row.updated_at = func.now()
            else:
                new_meta = EmbeddingIndexMetadata(
                    project_id=project_id,
                    active_model=active_model,
                    dimensions=dimensions,
                )
                self.session.add(new_meta)
            await self.session.commit()
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error("Database error upserting embedding metadata", project_id=project_id, exc_info=e)
            raise RepositoryError(f"Failed to upsert embedding metadata: {str(e)}") from e

    async def alter_embedding_dimensions(self, new_dimensions: int) -> None:
        try:
            # 1. Drop existing HNSW indexes
            await self.session.execute(
                text("DROP INDEX IF EXISTS idx_document_chunks_content_vector;")
            )
            await self.session.execute(
                text("DROP INDEX IF EXISTS idx_document_chunks_deep_content_vector;")
            )
            # 2. Alter column types to new vector dimensions with USING NULL
            await self.session.execute(
                text(
                    f"ALTER TABLE document_chunks ALTER COLUMN content_vector TYPE vector({new_dimensions}) USING NULL;"
                )
            )
            await self.session.execute(
                text(
                    f"ALTER TABLE document_chunks ALTER COLUMN deep_content_vector TYPE vector({new_dimensions}) USING NULL;"
                )
            )
            # 3. Recreate HNSW indexes for cosine distance
            await self.session.execute(
                text(
                    "CREATE INDEX idx_document_chunks_content_vector ON document_chunks USING hnsw (content_vector vector_cosine_ops);"
                )
            )
            await self.session.execute(
                text(
                    "CREATE INDEX idx_document_chunks_deep_content_vector ON document_chunks USING hnsw (deep_content_vector vector_cosine_ops);"
                )
            )
            await self.session.commit()
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error("Database error altering embedding dimensions DDL", new_dimensions=new_dimensions, exc_info=e)
            raise RepositoryError(f"Failed to alter embedding dimensions: {str(e)}") from e

    async def nullify_project_embeddings(self, project_id: uuid.UUID) -> None:
        try:
            doc_subquery = select(Project.doc_id).where(Project.project_id == project_id).scalar_subquery()
            await self.session.execute(
                update(DocumentChunk)
                .where(DocumentChunk.doc_id == doc_subquery)
                .values(content_vector=None, deep_content_vector=None)
            )
            await self.session.commit()
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error("Database error nullifying project embeddings", project_id=project_id, exc_info=e)
            raise RepositoryError(f"Failed to nullify project embeddings: {str(e)}") from e

    async def count_populated_embeddings(self, doc_id: uuid.UUID) -> int:
        try:
            stmt = select(func.count(DocumentChunk.chunk_id)).where(
                DocumentChunk.doc_id == doc_id,
                or_(
                    DocumentChunk.content_vector.isnot(None),
                    DocumentChunk.deep_content_vector.isnot(None),
                ),
            )
            result = await self.session.execute(stmt)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            self.logger.error("Database error counting populated embeddings", doc_id=doc_id, exc_info=e)
            raise RepositoryError(f"Failed to count populated embeddings: {str(e)}") from e

    async def search_chunks_vector(
        self, doc_id: uuid.UUID, query_vector: List[float], limit: int = 3
    ) -> Sequence[DocumentChunk]:
        try:
            effective_vector = case(
                (DocumentChunk.deep_content_vector.isnot(None), DocumentChunk.deep_content_vector),
                else_=DocumentChunk.content_vector,
            )
            stmt = (
                select(DocumentChunk)
                .where(
                    DocumentChunk.doc_id == doc_id,
                    or_(
                        DocumentChunk.deep_content_vector.isnot(None),
                        DocumentChunk.content_vector.isnot(None),
                    ),
                )
                .order_by(effective_vector.cosine_distance(query_vector))
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            self.logger.error("Database error during unified vector search", doc_id=doc_id, exc_info=e)
            raise RepositoryError(f"Vector search failed: {str(e)}") from e

    async def get_fallback_chunks(
        self, doc_id: uuid.UUID, limit: int = 3
    ) -> Sequence[DocumentChunk]:
        try:
            stmt = (
                select(DocumentChunk)
                .where(DocumentChunk.doc_id == doc_id)
                .order_by(DocumentChunk.chunk_index.asc())
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            self.logger.error("Database error fetching fallback chunks", doc_id=doc_id, exc_info=e)
            raise RepositoryError(f"Fallback fetch failed: {str(e)}") from e

    async def get_chunks_missing_embeddings(
        self,
        project_id: uuid.UUID,
        batch_size: int = 100,
    ) -> List[DocumentChunkResponse]:
        try:
            stmt = (
                select(DocumentChunk)
                .join(Project, Project.doc_id == DocumentChunk.doc_id)
                .where(
                    Project.project_id == project_id,
                    DocumentChunk.content_vector.is_(None),
                )
                .order_by(DocumentChunk.chunk_index.asc())
                .limit(batch_size)
            )
            result = await self.session.execute(stmt)
            chunks = result.scalars().all()
            return [DocumentChunkResponse.model_validate(c) for c in chunks]
        except SQLAlchemyError as e:
            self.logger.error("Database error fetching chunks missing embeddings", project_id=project_id, exc_info=e)
            raise RepositoryError(f"Failed to fetch chunks missing embeddings: {str(e)}") from e

    async def update_chunks(
        self, updates: Sequence[ChunkUpdateDTO]
    ) -> None:
        if not updates:
            return
        try:
            for item in updates:
                values = {}
                if item.deep_content is not None:
                    values["deep_content"] = item.deep_content
                if item.deep_content_vector is not None:
                    values["deep_content_vector"] = item.deep_content_vector
                if item.content is not None:
                    values["content"] = item.content
                if item.content_vector is not None:
                    values["content_vector"] = item.content_vector

                if values:
                    await self.session.execute(
                        update(DocumentChunk)
                        .where(DocumentChunk.chunk_id == item.chunk_id)
                        .values(**values)
                    )
            await self.session.commit()
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error("Database error updating chunks", count=len(updates), exc_info=e)
            raise RepositoryError(f"Failed to update chunks: {str(e)}") from e
