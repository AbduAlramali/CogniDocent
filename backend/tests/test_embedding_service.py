import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.core.dtos.llm_provider_dtos import EmbeddingConfigDTO
from src.core.enums import EmbeddingProvider
from src.core.interfaces.idocument_chunk_repository import IDocumentChunkRepository
from src.core.interfaces.iembedding_provider import IEmbeddingProvider
from src.core.interfaces.ivision_provider import IVisionProvider
from src.core.interfaces.ilogger import ILogger
from src.models.document_chunk import DocumentChunk
from src.schemas.document_chunk import DocumentChunkResponse, ChunkUpdateDTO
from src.services.embedding_service import EmbeddingService
from src.services.pdf_service import PDFService


@pytest.fixture
def mock_repo():
    repo = AsyncMock(spec=IDocumentChunkRepository)
    repo.get_embedding_metadata = AsyncMock()
    repo.alter_embedding_dimensions = AsyncMock()
    repo.nullify_project_embeddings = AsyncMock()
    repo.upsert_embedding_metadata = AsyncMock()
    repo.count_populated_embeddings = AsyncMock()
    repo.search_chunks_vector = AsyncMock()
    repo.get_fallback_chunks = AsyncMock()
    repo.get_chunks_missing_embeddings = AsyncMock()
    repo.update_chunks = AsyncMock()
    return repo


@pytest.fixture
def mock_provider():
    provider = AsyncMock(spec=IEmbeddingProvider)
    provider.embed_text = AsyncMock(return_value=[0.1, 0.2, 0.3])
    provider.embed_batch = AsyncMock(return_value=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
    return provider


@pytest.fixture
def mock_logger():
    return MagicMock(spec=ILogger)


@pytest.fixture
def mock_pdf_service():
    pdf_svc = AsyncMock(spec=PDFService)
    pdf_svc.render_page = AsyncMock(return_value=b"fake_image_bytes")
    return pdf_svc


@pytest.fixture
def mock_vision_llm():
    vision = AsyncMock(spec=IVisionProvider)
    vision.extract_markdown = AsyncMock(return_value="# Extracted Markdown")
    return vision


@pytest.fixture
def service(mock_repo, mock_provider, mock_logger):
    return EmbeddingService(
        document_chunk_repo=mock_repo,
        embedding_provider=mock_provider,
        logger=mock_logger,
    )


@pytest.mark.asyncio
async def test_update_project_embedding_model_dimension_change(service, mock_repo):
    project_id = uuid.uuid4()
    mock_repo.get_embedding_metadata.return_value = ("nomic-embed-text-v2-moe", 768)

    new_config = EmbeddingConfigDTO(
        provider=EmbeddingProvider.OPENAI,
        model_name="text-embedding-3-small",
        dimensions=1536,
    )

    await service.update_project_embedding_model(project_id, new_config)

    # Verifies service decided to alter dimensions via DDL and upsert metadata
    mock_repo.alter_embedding_dimensions.assert_called_once_with(1536)
    mock_repo.nullify_project_embeddings.assert_not_called()
    mock_repo.upsert_embedding_metadata.assert_called_once_with(
        project_id=project_id,
        active_model="text-embedding-3-small",
        dimensions=1536,
    )


@pytest.mark.asyncio
async def test_update_project_embedding_model_same_dimension_different_model(service, mock_repo):
    project_id = uuid.uuid4()
    mock_repo.get_embedding_metadata.return_value = ("nomic-embed-text-v2-moe", 768)

    new_config = EmbeddingConfigDTO(
        provider=EmbeddingProvider.OLLAMA,
        model_name="bge-base-en-v1.5",
        dimensions=768,
    )

    await service.update_project_embedding_model(project_id, new_config)

    # Verifies service decided to nullify project embeddings and upsert metadata
    mock_repo.alter_embedding_dimensions.assert_not_called()
    mock_repo.nullify_project_embeddings.assert_called_once_with(project_id)
    mock_repo.upsert_embedding_metadata.assert_called_once_with(
        project_id=project_id,
        active_model="bge-base-en-v1.5",
        dimensions=768,
    )


@pytest.mark.asyncio
async def test_update_project_embedding_model_skip_when_same(service, mock_repo):
    project_id = uuid.uuid4()
    mock_repo.get_embedding_metadata.return_value = ("nomic-embed-text-v2-moe", 768)

    same_config = EmbeddingConfigDTO(
        provider=EmbeddingProvider.OLLAMA,
        model_name="nomic-embed-text-v2-moe",
        dimensions=768,
    )

    await service.update_project_embedding_model(project_id, same_config)

    mock_repo.alter_embedding_dimensions.assert_not_called()
    mock_repo.nullify_project_embeddings.assert_not_called()
    mock_repo.upsert_embedding_metadata.assert_not_called()


@pytest.mark.asyncio
async def test_reembed_project_chunks(service, mock_repo, mock_provider):
    project_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    mock_chunk = DocumentChunkResponse(
        chunk_id=chunk_id,
        doc_id=doc_id,
        chunk_index=0,
        page_num=1,
        content="Test chunk content",
    )
    mock_repo.get_chunks_missing_embeddings.return_value = [mock_chunk]

    count = await service.reembed_project_chunks(project_id=project_id, batch_size=10)

    assert count == 1
    mock_provider.embed_batch.assert_called_once_with(["Test chunk content"])
    mock_repo.update_chunks.assert_called_once_with(
        [ChunkUpdateDTO(chunk_id=chunk_id, content_vector=[0.1, 0.2, 0.3])]
    )


@pytest.mark.asyncio
async def test_embed_batch(service, mock_provider):
    texts = ["hello", "world"]
    result = await service.embed_batch(texts)
    assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    mock_provider.embed_batch.assert_called_once_with(texts)


@pytest.mark.asyncio
async def test_embed_batch_empty(service, mock_provider):
    result = await service.embed_batch([])
    assert result == []
    mock_provider.embed_batch.assert_not_called()


@pytest.mark.asyncio
async def test_embed_text(service, mock_provider):
    result = await service.embed_text("sample text")
    assert result == [0.1, 0.2, 0.3]
    mock_provider.embed_text.assert_called_once_with("sample text")

