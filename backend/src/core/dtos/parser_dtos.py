"""Data Transfer Objects (DTOs) for parsed document payloads."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class TOCItemDTO:
    """Represents an entry in the document's Table of Contents (bookmarks)."""

    title: str
    page_num: int
    level: int = 1


@dataclass(frozen=True)
class PageContentDTO:
    """Extracted CPU-level text and basic metadata for a single document page."""

    page_num: int
    raw_text: str
    char_count: int
    has_images: bool = False
    has_tables_hint: bool = False


@dataclass(frozen=True)
class DocumentMetadataDTO:
    """High-level metadata extracted from document headers."""

    total_pages: int
    file_size_bytes: int
    title: Optional[str] = None
    author: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    custom_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ParsedDocumentDTO:
    """Complete document representation returned after Tier-1 bulk processing."""

    metadata: DocumentMetadataDTO
    table_of_contents: List[TOCItemDTO]
    pages: List[PageContentDTO]
