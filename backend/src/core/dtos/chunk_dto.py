from dataclasses import dataclass


@dataclass
class ChunkDTO:
    page_num: int
    content: str
    chunk_index: int
    bbox: list[float] | None = None
