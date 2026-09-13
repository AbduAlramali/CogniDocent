import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.core.dtos.llm_provider_dtos import CitationMetadata
from src.core.interfaces.idocument_chunk_repository import IDocumentChunkRepository
from src.core.interfaces.idocument_repository import IDocumentRepository
from src.core.interfaces.ilogger import ILogger
from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.services.citation_service import CitationService


@pytest.fixture
def mock_chunk_repo():
    return AsyncMock(spec=IDocumentChunkRepository)


@pytest.fixture
def mock_doc_repo():
    return AsyncMock(spec=IDocumentRepository)


@pytest.fixture
def mock_logger():
    return MagicMock(spec=ILogger)


@pytest.fixture
def citation_service(mock_chunk_repo, mock_doc_repo, mock_logger):
    return CitationService(
        chunk_repo=mock_chunk_repo,
        doc_repo=mock_doc_repo,
        logger=mock_logger,
    )


def test_to_short_id_deterministic(citation_service):
    chunk_id = uuid.uuid4()
    short1 = citation_service.to_short_id(chunk_id)
    short2 = citation_service.to_short_id(chunk_id)

    assert short1 == short2
    assert len(short1) == 6
    assert citation_service.get_chunk_id(short1) == chunk_id


def test_extract_ref_tags(citation_service):
    text = "Here is fact one [ref: chunk_a1b2c3] and fact two [ref: chunk_d4e5f6] and repeated [ref: chunk_a1b2c3]."
    tags = citation_service.extract_ref_tags(text)
    assert tags == ["chunk_a1b2c3", "chunk_d4e5f6"]


@pytest.mark.asyncio
async def test_build_citations_no_tags(citation_service):
    doc_id = uuid.uuid4()
    text = "A response with no citations at all."
    swapped_text, citations = await citation_service.build_citations(text, doc_id)

    assert swapped_text == text
    assert citations == []


@pytest.mark.asyncio
async def test_build_citations_swaps_short_ids_and_fetches_metadata(
    citation_service, mock_chunk_repo, mock_doc_repo
):
    doc_id = uuid.uuid4()
    chunk_uuid_1 = uuid.uuid4()
    chunk_uuid_2 = uuid.uuid4()

    short_1 = citation_service.to_short_id(chunk_uuid_1)
    short_2 = citation_service.to_short_id(chunk_uuid_2)

    doc = MagicMock(spec=Document)
    doc.primary_name = "Neural_Networks_Architecture.pdf"
    mock_doc_repo.get_by_id.return_value = doc

    chunk_1 = MagicMock(spec=DocumentChunk)
    chunk_1.chunk_id = chunk_uuid_1
    chunk_1.page_num = 3
    chunk_1.bbox = [50.0, 100.0, 450.0, 140.0]

    chunk_2 = MagicMock(spec=DocumentChunk)
    chunk_2.chunk_id = chunk_uuid_2
    chunk_2.page_num = 7
    chunk_2.bbox = [80.0, 200.0, 500.0, 260.0]

    async def fake_get_chunk(cid):
        if cid == chunk_uuid_1:
            return chunk_1
        if cid == chunk_uuid_2:
            return chunk_2
        return None

    mock_chunk_repo.get_by_id.side_effect = fake_get_chunk

    llm_output = (
        f"Transformers use self-attention [ref: chunk_{short_1}]. "
        f"Residual connections help training deep layers [ref: chunk_{short_2}]."
    )

    swapped_text, citations = await citation_service.build_citations(llm_output, doc_id)

    expected_db_ref_1 = f"chunk_{chunk_uuid_1}"
    expected_db_ref_2 = f"chunk_{chunk_uuid_2}"

    # Check raw text has literal markers swapped to DB chunk IDs
    assert f"[ref: {expected_db_ref_1}]" in swapped_text
    assert f"[ref: {expected_db_ref_2}]" in swapped_text
    assert f"[ref: chunk_{short_1}]" not in swapped_text

    # Check isolated metadata objects
    assert len(citations) == 2
    assert citations[0] == CitationMetadata(
        ref_id=expected_db_ref_1,
        page=3,
        bbox=[50.0, 100.0, 450.0, 140.0],
        source_name="Neural_Networks_Architecture.pdf",
    )
    assert citations[1] == CitationMetadata(
        ref_id=expected_db_ref_2,
        page=7,
        bbox=[80.0, 200.0, 500.0, 260.0],
        source_name="Neural_Networks_Architecture.pdf",
    )
