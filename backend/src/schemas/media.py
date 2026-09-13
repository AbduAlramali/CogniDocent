from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from src.core.enums import UploadStatus
import uuid


class MediaBase(BaseModel):
    filename: str
    content_type: str
    status: UploadStatus = UploadStatus.PROCESSING


class MediaCreate(MediaBase):
    file_name: str
    file_path: str
    file_size_bytes: int
    file_hash: str


class MediaUpdate(BaseModel):
    filename: Optional[str] = None
    status: Optional[UploadStatus] = None
    file_path: Optional[str] = None
    message_id: Optional[uuid.UUID] = None


class MediaDelete(BaseModel):
    media_id: uuid.UUID


class MediaResponse(MediaBase):
    model_config = ConfigDict(from_attributes=True)

    media_id: uuid.UUID
    message_id: Optional[uuid.UUID] = None
    file_path: str

    file_size_bytes: int
    file_hash: str
    uploaded_at: datetime
    caption: Optional[str] = None
    has_chunks: bool = False
    thumbnails: Optional[Dict[str, Any]] = None

