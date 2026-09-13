from typing import Optional, List, Any
import uuid

from src.core.dtos.llm_provider_dtos import EmbeddingConfigDTO
from src.schemas.document_chunk import ChunkUpdateDTO
from src.core.interfaces.idocument_chunk_repository import IDocumentChunkRepository
from src.core.interfaces.iembedding_provider import IEmbeddingProvider
from src.core.interfaces.ilogger import ILogger


class EmbeddingService:
    """
    Use cases orchestrating project embedding model changes and background re-embedding routines.
    """

    def __init__(
        self,
        document_chunk_repo: IDocumentChunkRepository,
        embedding_provider: IEmbeddingProvider,
        logger: ILogger,
    ) -> None:
        self.repo = document_chunk_repo
        self.embedding_provider = embedding_provider
        self.logger = logger

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Compute vector embeddings for a batch of text strings."""
        if not texts:
            return []
        return await self.embedding_provider.embed_batch(texts)

    async def embed_text(self, text: str) -> List[float]:
        """Compute vector embedding for a single text string."""
        return await self.embedding_provider.embed_text(text)

    async def update_project_embedding_model(
        self, project_id: uuid.UUID, config: EmbeddingConfigDTO
    ) -> None:
        """
        Use case: updates the embedding model for a project.
        Business rules:
        - Reads metadata from DB.
        - If metadata is empty or active_model != config.model_name or dimensions changed:
          - If dimensions differ: executes DDL routine to alter pgvector column and rebuild HNSW index.
          - If dimensions are identical: nullifies embeddings only for the related document.
          - Upserts embedding_index_metadata for project_id.
        """
        current_meta = await self.repo.get_embedding_metadata(project_id)
        current_model = current_meta[0] if current_meta else None
        current_dim = current_meta[1] if current_meta else 768

        if current_model != config.model_name or current_dim != config.dimensions:
            self.logger.info(
                "Project embedding model change detected. Executing reset routine.",
                project_id=project_id,
                current_model=current_model,
                new_model=config.model_name,
                current_dim=current_dim,
                new_dim=config.dimensions,
            )

            # Check if dimension change requires table column alteration
            if current_dim != config.dimensions:
                self.logger.info(
                    "Altering pgvector column dimension and rebuilding index",
                    old_dim=current_dim,
                    new_dim=config.dimensions,
                )
                await self.repo.alter_embedding_dimensions(config.dimensions)
            else:
                self.logger.info(
                    "Nullifying embeddings for project document",
                    project_id=project_id,
                )
                await self.repo.nullify_project_embeddings(project_id)

            await self.repo.upsert_embedding_metadata(
                project_id=project_id,
                active_model=config.model_name,
                dimensions=config.dimensions,
            )
        else:
            self.logger.info(
                "Project embedding model unchanged. No reset needed.",
                project_id=project_id,
                active_model=config.model_name,
            )

    async def reembed_project_chunks(
        self,
        project_id: uuid.UUID,
        batch_size: int = 50,
    ) -> int:
        """
        Use case: batch embedding routine for project chunks missing content embeddings.
        """
        missing_chunks = await self.repo.get_chunks_missing_embeddings(
            project_id=project_id,
            batch_size=batch_size,
        )
        if not missing_chunks:
            return 0

        texts = [c.content for c in missing_chunks]
        embeddings = await self.embedding_provider.embed_batch(texts)

        updates: List[ChunkUpdateDTO] = [
            ChunkUpdateDTO(chunk_id=chunk.chunk_id, content_vector=emb)
            for chunk, emb in zip(missing_chunks, embeddings)
        ]
        await self.repo.update_chunks(updates)
        self.logger.info(
            "Populated missing embeddings for project chunks",
            count=len(updates),
            project_id=project_id,
        )
        return len(updates)
