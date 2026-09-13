from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.core.dtos.chunk_dto import ChunkDTO
from src.core.dtos.parser_dtos import PageContentDTO
from src.core.interfaces.ichunker import IChunker
from src.core.interfaces.ilogger import ILogger


class RecursiveChunkerAdapter(IChunker):
    """
    Adapter implementation of IChunker using LangChain's RecursiveCharacterTextSplitter.
    Splits physical document pages into semantic chunks while preserving metadata and global chunk order.
    """

    def __init__(
        self,
        logger: ILogger,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> None:
        self.logger = logger
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def chunk_pages(self, pages: List[PageContentDTO]) -> List[ChunkDTO]:
        self.logger.info("Starting recursive chunking for pages", page_count=len(pages))
        chunks: List[ChunkDTO] = []
        global_index = 0

        for page in pages:
            if not page.raw_text or not page.raw_text.strip():
                continue

            page_chunks = self.splitter.split_text(page.raw_text)
            for text in page_chunks:
                chunks.append(
                    ChunkDTO(
                        page_num=page.page_num,
                        content=text,
                        chunk_index=global_index,
                    )
                )
                global_index += 1

        self.logger.info("Recursive chunking completed", total_chunks=len(chunks))
        return chunks
