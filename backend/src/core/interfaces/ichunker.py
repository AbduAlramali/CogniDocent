from abc import ABC, abstractmethod
from typing import List
from src.core.dtos.chunk_dto import ChunkDTO
from src.core.dtos.parser_dtos import PageContentDTO


class IChunker(ABC):
    @abstractmethod
    def chunk_pages(self, pages: List[PageContentDTO]) -> List[ChunkDTO]:
        """Splits physical pages into semantic chunks while preserving metadata."""
        pass
