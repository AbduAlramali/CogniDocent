from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict


class DocumentChunkBase(BaseModel):
    doc_id: uuid.UUID
    chunk_index: int
    page_num: int
    content: str
    content_vector: Optional[List[float]] = None
    deep_content: Optional[str] = None
    deep_content_vector: Optional[List[float]] = None
    bbox: Optional[List[float]] = None


class DocumentChunkCreate(DocumentChunkBase):
    pass


class DocumentChunkUpdate(BaseModel):
    content: Optional[str] = None
    content_vector: Optional[List[float]] = None
    deep_content: Optional[str] = None
    deep_content_vector: Optional[List[float]] = None
    bbox: Optional[List[float]] = None


class ChunkUpdateDTO(BaseModel):
    chunk_id: uuid.UUID
    deep_content: Optional[str] = None
    deep_content_vector: Optional[List[float]] = None
    content: Optional[str] = None
    content_vector: Optional[List[float]] = None
    bbox: Optional[List[float]] = None


class DocumentChunkResponse(DocumentChunkBase):
    model_config = ConfigDict(from_attributes=True)

    chunk_id: uuid.UUID


class EmbeddingIndexMetadataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: uuid.UUID
    active_model: str
    dimensions: int
    updated_at: datetime
