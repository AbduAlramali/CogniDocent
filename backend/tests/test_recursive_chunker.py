from unittest.mock import MagicMock
import pytest

from src.core.dtos.parser_dtos import PageContentDTO
from src.core.interfaces.ilogger import ILogger
from src.infra.chunkers.recursive_chunker import RecursiveChunkerAdapter


@pytest.fixture
def mock_logger():
    logger = MagicMock(spec=ILogger)
    logger.info = MagicMock()
    return logger


def test_recursive_chunker_basic_splitting(mock_logger):
    chunker = RecursiveChunkerAdapter(logger=mock_logger, chunk_size=20, chunk_overlap=5)

    pages = [
        PageContentDTO(
            page_num=1,
            raw_text="This is a long sentence that will be split into multiple chunks.",
            char_count=65,
        ),
        PageContentDTO(
            page_num=2,
            raw_text="Second page with more text to split.",
            char_count=36,
        ),
    ]

    chunks = chunker.chunk_pages(pages)

    assert len(chunks) > 2
    # Verify global indexing
    for idx, chunk in enumerate(chunks):
        assert chunk.chunk_index == idx
        assert chunk.content

    # First chunks belong to page 1, subsequent to page 2
    page1_chunks = [c for c in chunks if c.page_num == 1]
    page2_chunks = [c for c in chunks if c.page_num == 2]
    assert len(page1_chunks) > 0
    assert len(page2_chunks) > 0
    assert page1_chunks[-1].chunk_index < page2_chunks[0].chunk_index

    # Check logger called
    assert mock_logger.info.call_count >= 2


def test_recursive_chunker_skips_empty_pages(mock_logger):
    chunker = RecursiveChunkerAdapter(logger=mock_logger, chunk_size=100, chunk_overlap=10)

    pages = [
        PageContentDTO(page_num=1, raw_text="   \n\t  ", char_count=0),
        PageContentDTO(page_num=2, raw_text="Valid page content.", char_count=19),
        PageContentDTO(page_num=3, raw_text="", char_count=0),
    ]

    chunks = chunker.chunk_pages(pages)

    assert len(chunks) == 1
    assert chunks[0].page_num == 2
    assert chunks[0].chunk_index == 0
    assert chunks[0].content == "Valid page content."


def test_recursive_chunker_empty_pages_list(mock_logger):
    chunker = RecursiveChunkerAdapter(logger=mock_logger)
    chunks = chunker.chunk_pages([])
    assert chunks == []
