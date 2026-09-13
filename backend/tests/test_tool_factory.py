import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.pdf_service import PDFService
from src.services.chat_service import ChatService
from src.models.document_chunk import DocumentChunk
from src.models.media_chunk import MediaChunk
from src.core.dtos.parser_dtos import TOCItemDTO, DocumentMetadataDTO
from src.infra.orchestrators.langgraph.tools.tool_factory import LangGraphToolFactory


@pytest.fixture
def mock_pdf_service():
    service = AsyncMock(spec=PDFService)
    service.hybrid_retrieve = AsyncMock()
    service.expand_chunk_context = AsyncMock()
    service.get_pages_in_range = AsyncMock()
    service.get_document_toc = AsyncMock()
    service.get_document_metadata = AsyncMock()
    return service


@pytest.fixture
def mock_chat_service():
    service = AsyncMock(spec=ChatService)
    service.search_media_chunks = AsyncMock()
    service.expand_media_chunk_context = AsyncMock()
    return service


from src.services.citation_service import CitationService


@pytest.fixture
def mock_citation_service():
    service = MagicMock(spec=CitationService)
    service.to_short_id = MagicMock(side_effect=lambda cid: str(cid))
    return service


@pytest.fixture
def tool_factory(mock_pdf_service, mock_chat_service, mock_citation_service):
    return LangGraphToolFactory(
        pdf_service=mock_pdf_service,
        chat_service=mock_chat_service,
        citation_service=mock_citation_service,
    )


def test_get_all_tools(tool_factory):
    tools = tool_factory.get_all_tools()
    assert len(tools) == 7
    tool_names = [t.name for t in tools]
    assert "search_documents" in tool_names
    assert "expand_chunk_context" in tool_names
    assert "get_pages_in_range" in tool_names
    assert "get_document_toc" in tool_names
    assert "get_document_metadata" in tool_names
    assert "search_media_chunks" in tool_names
    assert "expand_media_chunk_context" in tool_names


@pytest.mark.asyncio
async def test_search_documents_tool(tool_factory, mock_pdf_service):
    tools = {t.name: t for t in tool_factory.get_all_tools()}
    doc_id = uuid.uuid4()
    chunk = DocumentChunk(chunk_id=uuid.uuid4(), doc_id=doc_id, chunk_index=0, page_num=1, content="Hello World")
    mock_pdf_service.hybrid_retrieve.return_value = [chunk]

    search_tool = tools["search_documents"]
    result = await search_tool.ainvoke({"query": "greeting", "state": {"document_id": doc_id}})

    assert "--- Page 1 ---" in result
    assert "Hello World" in result
    assert "[Chunk Index: 0]" in result
    mock_pdf_service.hybrid_retrieve.assert_called_once_with(doc_id=doc_id, query="greeting", limit=3)


@pytest.mark.asyncio
async def test_expand_chunk_context_tool(tool_factory, mock_pdf_service):
    tools = {t.name: t for t in tool_factory.get_all_tools()}
    doc_id = uuid.uuid4()
    chunk1 = DocumentChunk(chunk_id=uuid.uuid4(), doc_id=doc_id, chunk_index=1, page_num=1, content="Context before")
    chunk2 = DocumentChunk(chunk_id=uuid.uuid4(), doc_id=doc_id, chunk_index=2, page_num=1, content="Target chunk")
    chunk3 = DocumentChunk(chunk_id=uuid.uuid4(), doc_id=doc_id, chunk_index=3, page_num=2, content="Context after")
    mock_pdf_service.expand_chunk_context.return_value = [chunk1, chunk2, chunk3]

    expand_tool = tools["expand_chunk_context"]
    result = await expand_tool.ainvoke({"chunk_index": 2, "radius": 1, "state": {"document_id": doc_id}})

    assert "Context before" in result
    assert "Target chunk" in result
    assert "Context after" in result
    assert "--- Page 1 ---" in result
    assert "[Chunk Index: 2]" in result
    mock_pdf_service.expand_chunk_context.assert_called_once_with(doc_id=doc_id, chunk_index=2, radius=1)


@pytest.mark.asyncio
async def test_get_pages_in_range_tool(tool_factory, mock_pdf_service):
    tools = {t.name: t for t in tool_factory.get_all_tools()}
    doc_id = uuid.uuid4()
    chunk = DocumentChunk(chunk_id=uuid.uuid4(), doc_id=doc_id, chunk_index=2, page_num=2, content="Page 2 text")
    mock_pdf_service.get_pages_in_range.return_value = [chunk]

    range_tool = tools["get_pages_in_range"]
    result = await range_tool.ainvoke({"start_page": 2, "end_page": 2, "state": {"document_id": doc_id}})

    assert "--- Page 2 ---" in result
    assert "Page 2 text" in result
    mock_pdf_service.get_pages_in_range.assert_called_once_with(doc_id=doc_id, start_page=2, end_page=2)


@pytest.mark.asyncio
async def test_get_document_toc_tool(tool_factory, mock_pdf_service):
    tools = {t.name: t for t in tool_factory.get_all_tools()}
    doc_id = uuid.uuid4()
    mock_pdf_service.get_document_toc.return_value = [
        TOCItemDTO(title="Introduction", page_num=1, level=1),
        TOCItemDTO(title="Deep Dive", page_num=5, level=2),
    ]

    toc_tool = tools["get_document_toc"]
    result = await toc_tool.ainvoke({"state": {"document_id": doc_id}})

    assert "- Introduction (Page 1)" in result
    assert "-   Deep Dive (Page 5)" in result
    mock_pdf_service.get_document_toc.assert_called_once_with(doc_id=doc_id)


@pytest.mark.asyncio
async def test_get_document_metadata_tool(tool_factory, mock_pdf_service):
    tools = {t.name: t for t in tool_factory.get_all_tools()}
    doc_id = uuid.uuid4()
    mock_pdf_service.get_document_metadata.return_value = DocumentMetadataDTO(
        total_pages=20,
        file_size_bytes=5000,
        title="Sample Book",
        author="John Doe",
    )

    meta_tool = tools["get_document_metadata"]
    result = await meta_tool.ainvoke({"state": {"document_id": doc_id}})

    assert "Title: Sample Book" in result
    assert "Author: John Doe" in result
    assert "Total Pages: 20" in result
    mock_pdf_service.get_document_metadata.assert_called_once_with(doc_id=doc_id)


@pytest.mark.asyncio
async def test_search_media_chunks_tool(tool_factory, mock_chat_service):
    tools = {t.name: t for t in tool_factory.get_all_tools()}
    media_id = uuid.uuid4()
    chunk = MediaChunk(
        chunk_id=uuid.uuid4(),
        media_id=media_id,
        chunk_index=0,
        content="Sample code chunk",
        content_vector=[0.1, 0.2],
    )
    mock_chat_service.search_media_chunks.return_value = [chunk]

    search_tool = tools["search_media_chunks"]
    result = await search_tool.ainvoke({
        "query": "code logic",
        "state": {"active_attachments": [media_id]},
    })

    assert f"--- Media {media_id} ---" in result
    assert "Sample code chunk" in result
    assert "[Chunk Index: 0]" in result
    mock_chat_service.search_media_chunks.assert_called_once_with(
        query="code logic",
        media_id=[media_id],
        limit=3,
    )


@pytest.mark.asyncio
async def test_expand_media_chunk_context_tool(tool_factory, mock_chat_service):
    tools = {t.name: t for t in tool_factory.get_all_tools()}
    media_id = uuid.uuid4()
    c1 = MediaChunk(chunk_id=uuid.uuid4(), media_id=media_id, chunk_index=1, content="Context before")
    c2 = MediaChunk(chunk_id=uuid.uuid4(), media_id=media_id, chunk_index=2, content="Target code")
    mock_chat_service.expand_media_chunk_context.return_value = [c1, c2]

    expand_tool = tools["expand_media_chunk_context"]
    result = await expand_tool.ainvoke({
        "chunk_index": 2,
        "media_id": str(media_id),
        "radius": 1,
        "state": {},
    })

    assert "Context before" in result
    assert "Target code" in result
    mock_chat_service.expand_media_chunk_context.assert_called_once_with(
        media_id=media_id,
        chunk_index=2,
        radius=1,
    )
