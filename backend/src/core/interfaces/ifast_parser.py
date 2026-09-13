"""Port/Interface defining the contract for fast CPU document extraction."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator, List, Union

from src.core.dtos.parser_dtos import (
    DocumentMetadataDTO,
    PageContentDTO,
    ParsedDocumentDTO,
    TOCItemDTO,
)


class IFastParser(ABC):
    """Interface for high-throughput, low-latency CPU document parsing (Tier-1)."""

    @abstractmethod
    def extract_document(self, file_path: Union[str, Path]) -> ParsedDocumentDTO:
        """Extracts all raw page texts, table of contents, and header metadata in bulk.

        Args:
            file_path: Absolute or relative system path to the target PDF file.

        Returns:
            ParsedDocumentDTO containing full text and structural metadata.

        Raises:
            DocumentNotFoundError: If the file does not exist.
            DocumentCorruptedError: If the document is unreadable or malformed.
            DocumentEncryptedError: If the document is password-protected.
            ParserResourceLimitError: If decompression or memory limits are exceeded.
        """
        pass

    @abstractmethod
    def extract_pages_stream(
        self, file_path: Union[str, Path]
    ) -> Iterator[PageContentDTO]:
        """Yields extracted page data page-by-page as a generator to minimize peak memory consumption.

        Args:
            file_path: Absolute or relative system path to the target PDF file.

        Yields:
            PageContentDTO for each processed page sequentially.

        Raises:
            DocumentNotFoundError: If the file does not exist.
            DocumentCorruptedError: If the document structure is invalid.
            PageExtractionError: If an individual page fails to parse mid-stream.
        """
        pass

    @abstractmethod
    def extract_single_page(
        self, file_path: Union[str, Path], page_num: int
    ) -> PageContentDTO:
        """Extracts raw text and metadata for an isolated page.

        Args:
            file_path: Path to the target PDF.
            page_num: 1-indexed target page number.

        Returns:
            PageContentDTO containing extracted page details.

        Raises:
            PageExtractionError: If page_num is out of bounds or extraction fails.
        """
        pass

    @abstractmethod
    def extract_table_of_contents(
        self, file_path: Union[str, Path]
    ) -> List[TOCItemDTO]:
        """Extracts the outline / bookmark tree without reading page body contents.

        Args:
            file_path: Path to the target PDF.

        Returns:
            A list of TOCItemDTO representing hierarchical bookmarks.
        """
        pass

    @abstractmethod
    def extract_metadata(self, file_path: Union[str, Path]) -> DocumentMetadataDTO:
        """Reads fast header-level metadata without parsing body text.

        Args:
            file_path: Path to the target PDF.

        Returns:
            DocumentMetadataDTO with page counts and author/title fields.
        """
        pass

    @abstractmethod
    def render_page(
        self, file_path: Union[str, Path], page_num: int, dpi: int = 150
    ) -> bytes:
        """Renders a single page to image bytes (PNG format).

        Args:
            file_path: Path to the target PDF.
            page_num: 1-indexed target page number.
            dpi: Resolution for rendering the page image.

        Returns:
            Image bytes in PNG format.

        Raises:
            DocumentNotFoundError: If the file does not exist.
            PageExtractionError: If page_num is out of bounds or rendering fails.
        """
        pass

    @abstractmethod
    def extract_chunk_bboxes(
        self, file_path: Union[str, Path], chunks: list[tuple[int, str]]
    ) -> list[list[float]]:
        """Extracts bounding boxes [x0, y0, x1, y1] for a sequence of (page_num, chunk_text) pairs."""
        pass

    @abstractmethod
    def extract_text_bbox(
        self, file_path: Union[str, Path], page_num: int, text: str
    ) -> list[float]:
        """Extracts bounding box [x0, y0, x1, y1] for a text segment on a page."""
        pass
