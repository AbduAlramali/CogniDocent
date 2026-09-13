import asyncio
from typing import List, Sequence, Optional, Dict, Any
import uuid
from src.core.interfaces.ifast_parser import IFastParser
from src.services.embedding_service import EmbeddingService
from src.core.interfaces.idocument_chunk_repository import IDocumentChunkRepository
from src.core.interfaces.idocument_repository import IDocumentRepository
from src.core.interfaces.ivision_provider import IVisionProvider
from src.core.interfaces.ichunker import IChunker
from src.core.interfaces.ilogger import ILogger
from src.core.dtos.parser_dtos import TOCItemDTO, DocumentMetadataDTO
from src.core.dtos.chunk_dto import ChunkDTO
from src.core.enums import UploadStatus
from src.core.exceptions.database import DocumentNotFoundError
from src.core.exceptions.document_exceptions import DocumentNotParsedError
from src.schemas.document_chunk import ChunkUpdateDTO
from src.models.document import Document
from src.models.document_chunk import DocumentChunk


class PDFService:
    """
    Service handling PDF document parsing, page rendering,
    TOC and metadata extraction, hybrid vector retrieval with VLM deep parsing,
    and chunk embeddings generation.
    """

    def __init__(
        self,
        parser: IFastParser,
        embedding_service: EmbeddingService,
        chunk_repo: IDocumentChunkRepository,
        logger: ILogger,
        doc_repo: IDocumentRepository,
        vision_llm: IVisionProvider,
        chunker: IChunker,
    ) -> None:
        self.parser = parser
        self.embedding_service = embedding_service
        self.chunk_repo = chunk_repo
        self.logger = logger
        self.doc_repo = doc_repo
        self.vision_llm = vision_llm
        self.chunker = chunker

    async def _get_file_path(self, doc_id: uuid.UUID) -> Optional[str]:
        try:
            doc = await self.doc_repo.get_by_id(doc_id)
            if doc:
                return doc.file_path
            return None
        except Exception:
            pass

    async def render_page(self, doc_id: uuid.UUID, page_num: int) -> bytes:
        """
        Looks up Document.file_path for doc_id and renders page to image bytes (PNG).
        """
        file_path = await self._get_file_path(doc_id)
        if not file_path:
            self.logger.error(
                "Document not found for rendering", doc_id=doc_id, page_num=page_num
            )
            raise FileNotFoundError(f"Document {doc_id} not found.")

        return await asyncio.to_thread(self.parser.render_page, file_path, page_num)

    async def get_document_toc(self, doc_id: uuid.UUID) -> List[TOCItemDTO]:
        """
        Retrieves TOC for doc_id. If stored in document repository, returns it.
        Otherwise extracts TOC from PDF file using IFastParser, persists it to DB, and returns it.
        """
        try:
            toc_data = await self.doc_repo.get_document_toc(doc_id)
            if toc_data:
                return [
                    TOCItemDTO(
                        title=item["title"],
                        page_num=item["page_num"],
                        level=item.get("level", 1),
                    )
                    for item in toc_data
                ]
        except Exception as e:
            self.logger.warning(
                "Could not retrieve TOC from repository, falling back to file extraction",
                doc_id=doc_id,
                exc_info=e,
            )

        file_path = await self._get_file_path(doc_id)
        if not file_path:
            self.logger.error("Document not found for TOC extraction", doc_id=doc_id)
            raise FileNotFoundError(f"Document {doc_id} not found.")

        toc_items = await asyncio.to_thread(
            self.parser.extract_table_of_contents, file_path
        )

        toc_dicts = [
            {"title": item.title, "page_num": item.page_num, "level": item.level}
            for item in toc_items
        ]
        try:
            await self.doc_repo.update_toc(doc_id, toc_dicts)
        except Exception as e:
            self.logger.warning(
                "Failed to persist extracted TOC to repository",
                doc_id=doc_id,
                exc_info=e,
            )

        return toc_items

    async def get_document_metadata(self, doc_id: uuid.UUID) -> DocumentMetadataDTO:
        """
        Retrieves metadata for doc_id. If stored in document repository, returns it.
        Otherwise extracts metadata from PDF file using IFastParser, persists it to DB, and returns it.
        """
        try:
            meta_data = await self.doc_repo.get_document_metadata(doc_id)
            if meta_data:
                return DocumentMetadataDTO(
                    total_pages=meta_data["total_pages"],
                    file_size_bytes=meta_data.get("file_size_bytes", 0),
                    title=meta_data.get("title"),
                    author=meta_data.get("author"),
                    creator=meta_data.get("creator"),
                    producer=meta_data.get("producer"),
                    custom_metadata=meta_data.get("custom_metadata", {}),
                )
        except Exception as e:
            self.logger.warning(
                "Could not retrieve metadata from repository, falling back to file extraction",
                doc_id=doc_id,
                exc_info=e,
            )

        file_path = await self._get_file_path(doc_id)
        if not file_path:
            self.logger.error(
                "Document not found for metadata extraction", doc_id=doc_id
            )
            raise FileNotFoundError(f"Document {doc_id} not found.")

        metadata_dto = await asyncio.to_thread(self.parser.extract_metadata, file_path)

        meta_dict = {
            "total_pages": metadata_dto.total_pages,
            "file_size_bytes": metadata_dto.file_size_bytes,
            "title": metadata_dto.title,
            "author": metadata_dto.author,
            "creator": metadata_dto.creator,
            "producer": metadata_dto.producer,
            "custom_metadata": metadata_dto.custom_metadata,
        }
        try:
            await self.doc_repo.update_metadata(doc_id, meta_dict)
        except Exception as e:
            self.logger.warning(
                "Failed to persist extracted metadata to repository",
                doc_id=doc_id,
                exc_info=e,
            )

        return metadata_dto

    async def parse_and_embed_document(self, doc_id: uuid.UUID) -> List[DocumentChunk]:
        """
        On project creation: parse document pages, chunk content, compute embeddings,
        and save to document_chunks table. Also populates TOC and metadata in documents table.
        """
        file_path = await self._get_file_path(doc_id)
        if not file_path:
            self.logger.error("Document not found for parsing", doc_id=doc_id)
            raise FileNotFoundError(f"Document {doc_id} not found.")

        parsed_doc = await asyncio.to_thread(self.parser.extract_document, file_path)
        if not parsed_doc.pages:
            self.logger.warning(
                "Document contains no pages", doc_id=doc_id, file_path=file_path
            )
            return []

        # Persist TOC and metadata if doc_repo is present
        if parsed_doc:
            toc_dicts = [
                {"title": item.title, "page_num": item.page_num, "level": item.level}
                for item in parsed_doc.table_of_contents
            ]
            meta_dict = {
                "total_pages": parsed_doc.metadata.total_pages,
                "file_size_bytes": parsed_doc.metadata.file_size_bytes,
                "title": parsed_doc.metadata.title,
                "author": parsed_doc.metadata.author,
                "creator": parsed_doc.metadata.creator,
                "producer": parsed_doc.metadata.producer,
                "custom_metadata": parsed_doc.metadata.custom_metadata,
            }
            try:
                await self.doc_repo.update(
                    doc_id,
                    status=UploadStatus.COMPLETED,
                    toc=toc_dicts,
                    doc_metadata=meta_dict,
                )
            except Exception as e:
                self.logger.warning(
                    "Could not persist TOC and metadata on parse_and_embed",
                    doc_id=doc_id,
                    exc_info=e,
                )

        chunk_dtos = self.chunker.chunk_pages(parsed_doc.pages)

        bboxes = await asyncio.to_thread(
            self.parser.extract_chunk_bboxes,
            file_path,
            [(c.page_num, c.content) for c in chunk_dtos],
        )
        for c, bbox in zip(chunk_dtos, bboxes):
            c.bbox = bbox

        texts = [c.content for c in chunk_dtos]
        embeddings = await self.embedding_service.embed_batch(texts)

        chunks = [
            DocumentChunk(
                doc_id=doc_id,
                chunk_index=c.chunk_index,
                page_num=c.page_num,
                content=c.content,
                content_vector=emb,
                deep_content=None,
                deep_content_vector=None,
                bbox=c.bbox,
            )
            for c, emb in zip(chunk_dtos, embeddings)
        ]

        saved_chunks = list(await self.chunk_repo.bulk_create(chunks))
        self.logger.info(
            "Parsed and embedded document chunks on project creation",
            doc_id=doc_id,
            total_chunks=len(saved_chunks),
        )
        return saved_chunks

    async def get_pages_in_range(
        self, doc_id: uuid.UUID, start_page: int, end_page: int
    ) -> Sequence[DocumentChunk]:
        """
        Retrieves document chunks within [start_page, end_page] (inclusive).
        - If the document does not exist, raises FileNotFoundError.
        - If the document is not parsed yet, raises DocumentNotParsedError.
        - If parsed, returns chunks matching the range from chunk_repo (empty list if none match).
        """
        doc = None
        try:
            doc = await self.doc_repo.get_by_id(doc_id)
        except Exception:
            pass

        if not doc:
            self.logger.error(
                "Document not found for get_pages_in_range", doc_id=doc_id
            )
            raise FileNotFoundError(f"Document {doc_id} not found.")

        if doc.status != UploadStatus.COMPLETED:
            self.logger.warning(
                "Document has not been parsed yet",
                doc_id=doc_id,
                status=doc.status,
            )
            raise DocumentNotParsedError(
                doc_id=doc_id,
                reason=f"Document status is '{doc.status}', parsing is not completed.",
            )

        chunks = list(
            await self.chunk_repo.get_chunks_in_page_range(doc_id, start_page, end_page)
        )
        return chunks

    async def expand_chunk_context(
        self, doc_id: uuid.UUID, chunk_index: int, radius: int = 2
    ) -> Sequence[DocumentChunk]:
        """
        Retrieves sequential chunks surrounding target chunk_index within radius.
        Used for semantic navigation when a vector search hits the middle of a concept.
        """
        chunks = list(
            await self.chunk_repo.get_chunks_in_context_window(
                doc_id=doc_id, target_chunk_index=chunk_index, radius=radius
            )
        )
        return chunks

    async def hybrid_retrieve(
        self,
        doc_id: uuid.UUID,
        query: str,
        limit: int = 3,
    ) -> List[DocumentChunk]:
        """
        Use case: Unified vector retrieval with on-demand VLM deep parsing.
        1. Embed the search query.
        2. Execute unified vector search across all document chunks: evaluates
           deep_content_vector per chunk, falling back to content_vector if deep_content_vector is missing.
        3. If no results found, fallback to initial document chunks.
        4. For any returned chunks lacking deep parsing, concurrently fetch images,
           call Vision LLM to extract markdown into deep_content, compute deep embeddings,
           and save updates to Postgres.
        """
        # 1. Always embed the query first
        query_vector = await self.embedding_service.embed_text(query)

        # 2. Unified vector search evaluating deep_content_vector falling back to content_vector per chunk
        chunks = list(
            await self.chunk_repo.search_chunks_vector(
                doc_id=doc_id, query_vector=query_vector, limit=limit
            )
        )

        # If no results found from vector search
        if not chunks:
            chunks = list(
                await self.chunk_repo.get_fallback_chunks(doc_id=doc_id, limit=limit)
            )

        # 3. Concurrently fetch images and call Vision LLM (Crucial for speed)
        needs_parsing = [c for c in chunks if c.deep_content is None]

        if needs_parsing:

            async def parse_chunk(chunk: DocumentChunk) -> DocumentChunk:
                image_bytes = await self.render_page(doc_id, chunk.page_num)
                markdown = await self.vision_llm.extract_markdown(image_bytes)
                chunk.deep_content = markdown
                return chunk

            await asyncio.gather(*(parse_chunk(c) for c in needs_parsing))

            texts = [c.deep_content for c in needs_parsing]
            embeddings = await self.embedding_service.embed_batch(texts)

            updates: List[ChunkUpdateDTO] = []
            for c, emb in zip(needs_parsing, embeddings):
                c.deep_content_vector = emb
                updates.append(
                    ChunkUpdateDTO(
                        chunk_id=c.chunk_id,
                        deep_content=c.deep_content,
                        deep_content_vector=emb,
                    )
                )

            # Save the Markdown and Embeddings to Postgres
            await self.chunk_repo.update_chunks(updates)

        return chunks

    async def get_page_description(self, doc_id: uuid.UUID, page_num: int) -> str:
        """
        Renders the page to image bytes, calls Vision LLM to generate a rich description
        of the page (text, visuals, charts, tables), and returns the description.
        """
        image_bytes = await self.render_page(doc_id, page_num)
        return await self.vision_llm.extract_markdown(image_bytes)

