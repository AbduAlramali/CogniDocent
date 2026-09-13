import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.interfaces.ilogger import ILogger
from src.infra.repositories.document_chunk_repository import DocumentChunkRepository
from src.models.document_chunk import DocumentChunk
from src.models.embedding_index_metadata import EmbeddingIndexMetadata
from src.schemas.document_chunk import ChunkUpdateDTO


@pytest.fixture
def mock_session():
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_logger():
    return MagicMock(spec=ILogger)


@pytest.fixture
def repo(mock_session, mock_logger):
    return DocumentChunkRepository(session=mock_session, logger=mock_logger)


@pytest.mark.asyncio
async def test_get_embedding_metadata(repo, mock_session):
    project_id = uuid.uuid4()
    mock_record = EmbeddingIndexMetadata(
        project_id=project_id,
        active_model="nomic-embed-text-v2-moe",
        dimensions=768,
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_record
    mock_session.execute.return_value = mock_result

    metadata = await repo.get_embedding_metadata(project_id)
    assert metadata == ("nomic-embed-text-v2-moe", 768)


@pytest.mark.asyncio
async def test_upsert_embedding_metadata_update_existing(repo, mock_session):
    project_id = uuid.uuid4()
    existing = EmbeddingIndexMetadata(
        project_id=project_id,
        active_model="old-model",
        dimensions=768,
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing
    mock_session.execute.return_value = mock_result

    await repo.upsert_embedding_metadata(project_id, "new-model", 1536)
    assert existing.active_model == "new-model"
    assert existing.dimensions == 1536
    assert mock_session.commit.called


@pytest.mark.asyncio
async def test_alter_embedding_dimensions(repo, mock_session):
    await repo.alter_embedding_dimensions(1536)
    executed_sqls = [
        str(call.args[0]) for call in mock_session.execute.call_args_list if len(call.args) > 0
    ]
    assert any("DROP INDEX IF EXISTS idx_document_chunks_content_vector" in sql for sql in executed_sqls)
    assert any("DROP INDEX IF EXISTS idx_document_chunks_deep_content_vector" in sql for sql in executed_sqls)
    assert any("ALTER TABLE document_chunks ALTER COLUMN content_vector TYPE vector(1536) USING NULL" in sql for sql in executed_sqls)
    assert any("ALTER TABLE document_chunks ALTER COLUMN deep_content_vector TYPE vector(1536) USING NULL" in sql for sql in executed_sqls)
    assert any("CREATE INDEX idx_document_chunks_content_vector" in sql for sql in executed_sqls)
    assert any("CREATE INDEX idx_document_chunks_deep_content_vector" in sql for sql in executed_sqls)
    assert mock_session.commit.called


@pytest.mark.asyncio
async def test_nullify_project_embeddings(repo, mock_session):
    project_id = uuid.uuid4()
    await repo.nullify_project_embeddings(project_id)
    assert mock_session.execute.called
    assert mock_session.commit.called


@pytest.mark.asyncio
async def test_count_populated_embeddings(repo, mock_session):
    doc_id = uuid.uuid4()
    mock_result = MagicMock()
    mock_result.scalar.return_value = 5
    mock_session.execute.return_value = mock_result

    count = await repo.count_populated_embeddings(doc_id)
    assert count == 5


@pytest.mark.asyncio
async def test_bulk_create(repo, mock_session):
    doc_id = uuid.uuid4()
    chunks = [
        DocumentChunk(chunk_id=uuid.uuid4(), doc_id=doc_id, chunk_index=0, page_num=1, content="C1"),
        DocumentChunk(chunk_id=uuid.uuid4(), doc_id=doc_id, chunk_index=1, page_num=2, content="C2"),
    ]
    result = await repo.bulk_create(chunks)
    assert result == chunks
    assert mock_session.add_all.called
    assert mock_session.commit.called


@pytest.mark.asyncio
async def test_search_chunks_vector(repo, mock_session):
    doc_id = uuid.uuid4()
    chunk = DocumentChunk(
        chunk_id=uuid.uuid4(),
        doc_id=doc_id,
        chunk_index=0,
        page_num=1,
        content="test",
        content_vector=[0.1, 0.2],
        deep_content=None,
        deep_content_vector=None,
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [chunk]
    mock_session.execute.return_value = mock_result

    chunks = await repo.search_chunks_vector(doc_id=doc_id, query_vector=[0.1, 0.2], limit=3)
    assert len(chunks) == 1
    assert chunks[0] == chunk


@pytest.mark.asyncio
async def test_search_chunks_vector_db_error(repo, mock_session):
    from sqlalchemy.exc import SQLAlchemyError
    from src.core.exceptions.database import RepositoryError

    doc_id = uuid.uuid4()
    mock_session.execute.side_effect = SQLAlchemyError("DB failure")

    with pytest.raises(RepositoryError, match="Vector search failed"):
        await repo.search_chunks_vector(doc_id=doc_id, query_vector=[0.1, 0.2], limit=3)


@pytest.mark.asyncio
async def test_update_chunks(repo, mock_session):
    chunk_id = uuid.uuid4()
    await repo.update_chunks(
        [ChunkUpdateDTO(chunk_id=chunk_id, deep_content="# Markdown", deep_content_vector=[0.1, 0.2])]
    )
    assert mock_session.execute.called
    assert mock_session.commit.called


@pytest.mark.asyncio
async def test_get_chunks_in_page_range(repo, mock_session):
    doc_id = uuid.uuid4()
    chunk1 = DocumentChunk(chunk_id=uuid.uuid4(), doc_id=doc_id, chunk_index=0, page_num=1, content="Page 1")
    chunk2 = DocumentChunk(chunk_id=uuid.uuid4(), doc_id=doc_id, chunk_index=1, page_num=2, content="Page 2")

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [chunk1, chunk2]
    mock_session.execute.return_value = mock_result

    chunks = await repo.get_chunks_in_page_range(doc_id, start_page=1, end_page=2)
    assert len(chunks) == 2
    assert chunks[0] == chunk1
    assert chunks[1] == chunk2


@pytest.mark.asyncio
async def test_get_chunks_in_context_window(repo, mock_session):
    doc_id = uuid.uuid4()
    c1 = DocumentChunk(chunk_id=uuid.uuid4(), doc_id=doc_id, chunk_index=3, page_num=1, content="Before")
    c2 = DocumentChunk(chunk_id=uuid.uuid4(), doc_id=doc_id, chunk_index=4, page_num=1, content="Target")
    c3 = DocumentChunk(chunk_id=uuid.uuid4(), doc_id=doc_id, chunk_index=5, page_num=2, content="After")

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [c1, c2, c3]
    mock_session.execute.return_value = mock_result

    chunks = await repo.get_chunks_in_context_window(doc_id, target_chunk_index=4, radius=1)
    assert len(chunks) == 3
    assert chunks[0] == c1
    assert chunks[1] == c2
    assert chunks[2] == c3
