from typing import Annotated, List, Optional
import uuid
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from src.services.pdf_service import PDFService
from src.services.chat_service import ChatService
from src.services.citation_service import CitationService


class LangGraphToolFactory:
    def __init__(
        self,
        pdf_service: PDFService,
        chat_service: ChatService,
        citation_service: CitationService,
    ):
        self._pdf_service = pdf_service
        self._chat_service = chat_service
        self._citation_service = citation_service

    def get_all_tools(self) -> list:
        """Returns the complete toolkit bound to the agent."""
        return [
            self._build_hybrid_search_tool(),
            self._build_expand_chunk_context_tool(),
            self._build_get_pages_in_range_tool(),
            self._build_get_toc_tool(),
            self._build_get_metadata_tool(),
            self._build_search_media_chunks_tool(),
            self._build_expand_media_chunk_context_tool(),
        ]

    def _build_hybrid_search_tool(self):
        """Builds the autonomous retrieval and on-the-fly embedding tool."""
        service = self._pdf_service

        @tool("search_documents")
        async def search_documents(
            query: str, state: Annotated[dict, InjectedState]
        ) -> str:
            """
            Search the active document for specific information, context, or keywords.
            Use this tool to find factual answers from the user's PDF.

            Args:
                query: The semantic search query or keywords to look for.
            """
            doc_id = state.get("document_id")
            if not doc_id:
                return "No document_id found in state."

            try:
                # Executes hybrid search and lazily embeds missing vectors
                chunks = await service.hybrid_retrieve(
                    doc_id=doc_id, query=query, limit=3
                )

                if not chunks:
                    return "No relevant information found in the document. Try adjusting your search query."

                # Format the returned DTOs into a structured string for the LLM context window
                return "\n\n".join(
                    f"--- Page {c.page_num} --- [ref: chunk_{self._citation_service.to_short_id(c.chunk_id)}] [Chunk Index: {c.chunk_index}]\n{c.deep_content or c.content}"
                    for c in chunks
                )

            except Exception as e:
                # Prevent the graph from crashing on temporary DB or API failures
                return f"Search failed due to a system error: {str(e)}. Tell the user to try again."

        return search_documents

    def _build_expand_chunk_context_tool(self):
        """Builds the tool to expand reading context around a specific chunk index (semantic navigation)."""
        service = self._pdf_service

        @tool("expand_chunk_context")
        async def expand_chunk_context(
            chunk_index: int,
            state: Annotated[dict, InjectedState],
            radius: int = 2,
        ) -> str:
            """
            Expand the reading context around a specific chunk index to inspect surrounding text.
            Use this tool to fix incomplete answers when a vector search hits the middle of a concept.

            Args:
                chunk_index: The specific chunk index (returned by search_documents) to expand around.
                radius: The number of chunks before and after the target chunk to retrieve (default: 2).
            """
            doc_id = state.get("document_id")
            if not doc_id:
                return "No document_id found in state."

            if radius < 1 or radius > 10:
                return "Invalid radius: radius must be between 1 and 10."

            try:
                chunks = await service.expand_chunk_context(
                    doc_id=doc_id, chunk_index=chunk_index, radius=radius
                )
                if not chunks:
                    return f"No chunks found around chunk index {chunk_index}."

                return "\n\n".join(
                    f"--- Page {c.page_num} --- [ref: chunk_{self._citation_service.to_short_id(c.chunk_id)}] [Chunk Index: {c.chunk_index}]\n{c.deep_content or c.content}"
                    for c in chunks
                )
            except Exception as e:
                return f"Failed to expand chunk context: {str(e)}"

        return expand_chunk_context

    def _build_get_pages_in_range_tool(self):
        """Builds the tool to retrieve sequential document pages by page range."""
        service = self._pdf_service

        @tool("get_pages_in_range")
        async def get_pages_in_range(
            start_page: int, end_page: int, state: Annotated[dict, InjectedState]
        ) -> str:
            """
            Read specific sequential pages of the active document by page range.
            Maximum page range is 10 pages.

            Args:
                start_page: 1-indexed starting page number.
                end_page: 1-indexed ending page number (inclusive).
            """
            doc_id = state.get("document_id")
            if not doc_id:
                return "No document_id found in state."

            if start_page > end_page:
                return "Invalid page range: start_page must be less than end_page."
            if end_page - start_page > 10:
                return "Page range too large: maximum is 10 pages."

            try:
                chunks = await service.get_pages_in_range(
                    doc_id=doc_id, start_page=start_page, end_page=end_page
                )
                if not chunks:
                    return f"No pages found in range {start_page} to {end_page}."

                return "\n\n".join(
                    f"--- Page {c.page_num} --- [ref: chunk_{self._citation_service.to_short_id(c.chunk_id)}]\n{c.deep_content or c.content}"
                    for c in chunks
                )
            except Exception as e:
                return f"Failed to retrieve pages in range: {str(e)}"

        return get_pages_in_range

    def _build_get_toc_tool(self):
        """Builds the tool to retrieve the document table of contents."""
        service = self._pdf_service

        @tool("get_document_toc")
        async def get_document_toc(state: Annotated[dict, InjectedState]) -> str:
            """
            Get the Table of Contents (bookmarks outline) of the active document.
            """
            doc_id = state.get("document_id")
            if not doc_id:
                return "No document_id found in state."

            try:
                toc = await service.get_document_toc(doc_id=doc_id)
                if not toc:
                    return "Document does not have a table of contents."

                lines = [
                    f"- {'  ' * (item.level - 1)}{item.title} (Page {item.page_num})"
                    for item in toc
                ]
                return "\n".join(lines)
            except Exception as e:
                return f"Failed to retrieve table of contents: {str(e)}"

        return get_document_toc

    def _build_get_metadata_tool(self):
        """Builds the tool to retrieve document header metadata."""
        service = self._pdf_service

        @tool("get_document_metadata")
        async def get_document_metadata(state: Annotated[dict, InjectedState]) -> str:
            """
            Get metadata (total pages, title, author, file size) of the active document.
            """
            doc_id = state.get("document_id")
            if not doc_id:
                return "No document_id found in state."

            try:
                meta = await service.get_document_metadata(doc_id=doc_id)
                return (
                    f"Title: {meta.title or 'Unknown'}\n"
                    f"Author: {meta.author or 'Unknown'}\n"
                    f"Total Pages: {meta.total_pages}\n"
                    f"File Size: {meta.file_size_bytes} bytes"
                )
            except Exception as e:
                return f"Failed to retrieve document metadata: {str(e)}"

        return get_document_metadata

    def _build_search_media_chunks_tool(self):
        """Builds the tool to search across media attachment chunks using vector embeddings."""
        chat_service = self._chat_service

        @tool("search_media_chunks")
        async def search_media_chunks(
            query: str,
            state: Annotated[dict, InjectedState],
            media_id: Optional[str] = None,
        ) -> str:
            """
            Search uploaded chat media attachments (text files, code, documents, or attachments)
            for specific information, context, or keywords using semantic vector search.

            Args:
                query: The semantic search query or keywords to look for.
                media_id: Optional UUID string of a specific media attachment to restrict search to.
            """
            target_media_id = None
            if media_id:
                try:
                    target_media_id = uuid.UUID(media_id)
                except (ValueError, TypeError):
                    return f"Invalid media_id format: '{media_id}'. Must be a valid UUID."
            else:
                active_attachments = state.get("active_attachments")
                if active_attachments:
                    target_media_id = active_attachments
            try:
                chunks = await chat_service.search_media_chunks(
                    query=query,
                    media_id=target_media_id,
                    limit=3,
                )
                if not chunks:
                    return "No relevant information found in media attachments. Try adjusting your search query."

                return "\n\n".join(
                    f"--- Media {c.media_id} --- [ref: chunk_{self._citation_service.to_short_id(c.chunk_id)}] [Chunk Index: {c.chunk_index}]\n{c.content}"
                    for c in chunks
                )
            except Exception as e:
                return f"Media chunks search failed due to a system error: {str(e)}."

        return search_media_chunks

    def _build_expand_media_chunk_context_tool(self):
        """Builds the tool to expand context around a specific media chunk index (semantic navigation)."""
        chat_service = self._chat_service

        @tool("expand_media_chunk_context")
        async def expand_media_chunk_context(
            chunk_index: int,
            state: Annotated[dict, InjectedState],
            media_id: Optional[str] = None,
            radius: int = 2,
        ) -> str:
            """
            Expand the reading context around a specific media chunk index to inspect surrounding text.
            Use this tool to fix incomplete answers when a media vector search hits the middle of a concept.

            Args:
                chunk_index: The specific chunk index (returned by search_media_chunks) to expand around.
                media_id: Optional UUID string of the media attachment. If omitted, uses the active attachment from state.
                radius: The number of chunks before and after the target chunk to retrieve (default: 2).
            """
            target_media_id = None
            if media_id:
                try:
                    target_media_id = uuid.UUID(media_id)
                except (ValueError, TypeError):
                    return f"Invalid media_id format: '{media_id}'. Must be a valid UUID."
            else:
                active_attachments = state.get("active_attachments")
                if active_attachments and len(active_attachments) == 1:
                    target_media_id = active_attachments[0]
                elif active_attachments and len(active_attachments) > 1:
                    return "Multiple media attachments found in conversation. Please specify the media_id to expand context."
                else:
                    return "Missing media_id: please specify the media_id for the chunk to expand context."

            if radius < 1 or radius > 10:
                return "Invalid radius: radius must be between 1 and 10."

            try:
                chunks = await chat_service.expand_media_chunk_context(
                    media_id=target_media_id,
                    chunk_index=chunk_index,
                    radius=radius,
                )
                if not chunks:
                    return f"No media chunks found around chunk index {chunk_index} for media {target_media_id}."

                return "\n\n".join(
                    f"--- Media {c.media_id} --- [ref: chunk_{self._citation_service.to_short_id(c.chunk_id)}] [Chunk Index: {c.chunk_index}]\n{c.content}"
                    for c in chunks
                )
            except Exception as e:
                return f"Failed to expand media chunk context: {str(e)}"

        return expand_media_chunk_context

