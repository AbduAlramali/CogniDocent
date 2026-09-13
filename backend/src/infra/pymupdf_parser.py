"""Adapter implementation using PyMuPDF and injected structured ILogger for Tier-1 fast document parsing."""

from pathlib import Path
from typing import Any, Iterator, List, Union

from src.core.dtos.parser_dtos import (
    DocumentMetadataDTO,
    PageContentDTO,
    ParsedDocumentDTO,
    TOCItemDTO,
)
from src.core.exceptions.fast_parser_exceptions import (
    FastParserError,
    DocumentCorruptedError,
    DocumentEncryptedError,
    DocumentNotFoundError,
    PageExtractionError,
    ParserResourceLimitError,
)
from src.core.interfaces.ifast_parser import IFastParser
from src.core.interfaces.ilogger import ILogger


class PyMuPDFParser(IFastParser):
    def __init__(self, mupdf_client: Any, logger: ILogger) -> None:
        """
        Args:
            mupdf_client: Injected pymupdf / fitz module or factory client.
            logger: Injected ILogger implementation supporting structured kwargs.
        """
        self._mupdf = mupdf_client
        self._logger = logger

    def _open_doc(self, file_path: Union[str, Path]) -> Any:
        """Opens a PDF document with validated existence and exception handling."""
        path_str = str(file_path)
        if not Path(path_str).exists():
            self._logger.error("Document file not found", file_path=path_str)
            raise DocumentNotFoundError(path_str)

        try:
            doc = self._mupdf.open(path_str)
        except getattr(self._mupdf, "FileDataError", Exception) as e:
            self._logger.error(
                "Corrupted document detected",
                exc_info=e,
                file_path=path_str,
                reason=str(e),
            )
            raise DocumentCorruptedError(path_str, reason=str(e)) from e
        except Exception as e:
            self._logger.error(
                "Unexpected error opening document",
                exc_info=e,
                file_path=path_str,
                reason=str(e),
            )
            raise DocumentCorruptedError(
                path_str, reason=f"Unexpected error: {e}"
            ) from e

        if doc.needs_pass:
            doc.close()
            self._logger.warning("Encrypted document encountered", file_path=path_str)
            raise DocumentEncryptedError(path_str)

        return doc

    def extract_document(self, file_path: Union[str, Path]) -> ParsedDocumentDTO:
        path_str = str(file_path)
        self._logger.info("Starting bulk document extraction", file_path=path_str)

        doc = self._open_doc(file_path)
        try:
            metadata = self._extract_metadata(doc, file_path)
            toc = self._extract_toc(doc)
            pages = list(self._extract_pages(doc, file_path))

            self._logger.info(
                "Bulk document extraction completed successfully",
                file_path=path_str,
                total_pages=len(pages),
                toc_entries_count=len(toc),
            )
            return ParsedDocumentDTO(
                metadata=metadata,
                table_of_contents=toc,
                pages=pages,
            )
        except MemoryError as e:
            self._logger.critical(
                "Memory limit exceeded during bulk extraction",
                exc_info=e,
                file_path=path_str,
            )
            raise ParserResourceLimitError(path_str, "Memory Exceeded") from e
        except Exception as e:
            self._logger.error(
                "Unexpected error during bulk extraction",
                exc_info=e,
                file_path=path_str,
                reason=str(e),
            )
            raise FastParserError(
                f"Unexpected error during bulk extraction: {e}"
            ) from e
        finally:
            doc.close()

    def extract_pages_stream(
        self, file_path: Union[str, Path]
    ) -> Iterator[PageContentDTO]:
        doc = self._open_doc(file_path)
        try:
            yield from self._extract_pages(doc, file_path)
        except Exception as e:
            self._logger.error(
                "Unexpected error during page stream extraction",
                exc_info=e,
                file_path=file_path,
                reason=str(e),
            )
            raise FastParserError(
                f"Unexpected error during page stream extraction: {e}"
            ) from e
        finally:
            doc.close()

    def extract_single_page(
        self, file_path: Union[str, Path], page_num: int
    ) -> PageContentDTO:
        path_str = str(file_path)
        doc = self._open_doc(file_path)
        try:
            if page_num < 1 or page_num > len(doc):
                self._logger.warning(
                    "Requested page number out of bounds",
                    file_path=path_str,
                    requested_page=page_num,
                    total_pages=len(doc),
                )
                raise PageExtractionError(
                    path_str, page_num, "Page number out of bounds."
                )

            page = doc[page_num - 1]
            return self._parse_single_page(page, page_num, path_str)
        finally:
            doc.close()

    def extract_table_of_contents(
        self, file_path: Union[str, Path]
    ) -> List[TOCItemDTO]:
        doc = self._open_doc(file_path)
        try:
            return self._extract_toc(doc)
        except Exception as e:
            self._logger.error(
                "Unexpected error during TOC extraction",
                exc_info=e,
                file_path=file_path,
                reason=str(e),
            )
            raise FastParserError(f"Unexpected error during TOC extraction: {e}") from e
        finally:
            doc.close()

    def extract_metadata(self, file_path: Union[str, Path]) -> DocumentMetadataDTO:
        doc = self._open_doc(file_path)
        try:
            return self._extract_metadata(doc, file_path)
        except Exception as e:
            self._logger.error(
                "Unexpected error during metadata extraction",
                exc_info=e,
                file_path=file_path,
                reason=str(e),
            )
            raise FastParserError(
                f"Unexpected error during metadata extraction: {e}"
            ) from e
        finally:
            doc.close()

    def render_page(
        self, file_path: Union[str, Path], page_num: int, dpi: int = 150
    ) -> bytes:
        path_str = str(file_path)
        doc = self._open_doc(file_path)
        try:
            if page_num < 1 or page_num > len(doc):
                self._logger.warning(
                    "Requested page number out of bounds for rendering",
                    file_path=path_str,
                    requested_page=page_num,
                    total_pages=len(doc),
                )
                raise PageExtractionError(
                    path_str, page_num, "Page number out of bounds."
                )

            page = doc[page_num - 1]
            pix = page.get_pixmap(dpi=dpi)
            return pix.tobytes("png")
        except PageExtractionError:
            raise
        except Exception as e:
            self._logger.error(
                "Unexpected error during page rendering",
                exc_info=e,
                file_path=path_str,
                page_num=page_num,
                reason=str(e),
            )
            raise PageExtractionError(
                path_str, page_num, f"Failed to render page: {e}"
            ) from e
        finally:
            doc.close()

    def _locate_bbox_on_page(self, page: Any, text: str) -> list[float]:
        clean_text = " ".join(text.split())
        rects = page.search_for(clean_text)
        if rects:
            return [
                min(r.x0 for r in rects),
                min(r.y0 for r in rects),
                max(r.x1 for r in rects),
                max(r.y1 for r in rects),
            ]
        words = clean_text.split()
        prefix = " ".join(words[:4])
        suffix = " ".join(words[-4:])
        all_rects = page.search_for(prefix) + page.search_for(suffix)
        if all_rects:
            return [
                min(r.x0 for r in all_rects),
                min(r.y0 for r in all_rects),
                max(r.x1 for r in all_rects),
                max(r.y1 for r in all_rects),
            ]
        return [0.0, 0.0, 0.0, 0.0]

    def extract_chunk_bboxes(
        self, file_path: Union[str, Path], chunks: list[tuple[int, str]]
    ) -> list[list[float]]:
        doc = self._open_doc(file_path)
        try:
            results: list[list[float]] = []
            for page_num, text in chunks:
                page = doc[page_num - 1]
                bbox = self._locate_bbox_on_page(page, text)
                results.append(bbox)
            return results
        finally:
            doc.close()

    def extract_text_bbox(
        self, file_path: Union[str, Path], page_num: int, text: str
    ) -> list[float]:
        doc = self._open_doc(file_path)
        try:
            page = doc[page_num - 1]
            return self._locate_bbox_on_page(page, text)
        finally:
            doc.close()

    # --- Internal Extraction Helpers ---

    def _extract_metadata(
        self, doc: Any, file_path: Union[str, Path]
    ) -> DocumentMetadataDTO:
        meta = doc.metadata or {}
        file_size = Path(file_path).stat().st_size if Path(file_path).exists() else 0

        return DocumentMetadataDTO(
            total_pages=doc.page_count,
            file_size_bytes=file_size,
            title=meta.get("title"),
            author=meta.get("author"),
            creator=meta.get("creator"),
            producer=meta.get("producer"),
            custom_metadata={
                k: v
                for k, v in meta.items()
                if k not in ["title", "author", "creator", "producer"] and v
            },
        )

    def _extract_toc(self, doc: Any) -> List[TOCItemDTO]:
        raw_toc = doc.get_toc() or []
        toc_items = []
        for item in raw_toc:
            if len(item) >= 3:
                toc_items.append(
                    TOCItemDTO(
                        level=item[0],
                        title=item[1],
                        page_num=item[2],
                    )
                )
        return toc_items

    def _extract_pages(
        self, doc: Any, file_path: Union[str, Path]
    ) -> Iterator[PageContentDTO]:
        for page_index in range(len(doc)):
            page = doc[page_index]
            yield self._parse_single_page(page, page_index + 1, str(file_path))

    def _parse_single_page(
        self, page: Any, page_num: int, file_path: str
    ) -> PageContentDTO:
        try:
            raw_text = page.get_text()
            char_count = len(raw_text)

            images = page.get_images()
            has_images = len(images) > 0

            tables = page.find_tables()
            has_tables = len(tables.tables) > 0

            return PageContentDTO(
                page_num=page_num,
                raw_text=raw_text,
                char_count=char_count,
                has_images=has_images,
                has_tables_hint=has_tables,
            )
        except Exception as e:
            self._logger.error(
                "Failed extracting content from page",
                exc_info=e,
                file_path=file_path,
                page_num=page_num,
            )
            raise PageExtractionError(file_path, page_num, str(e)) from e
