from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
import uuid
from src.core.enums import UploadStatus


class DocumentBase(BaseModel):
    primary_name: str
    content_type: str = "application/pdf"
    status: UploadStatus = UploadStatus.PROCESSING
    thumbnails: Optional[Dict[str, Any]] = None


class DocumentCreate(DocumentBase):
    file_path: str
    file_size_bytes: int
    file_hash: str


class DocumentUpdate(BaseModel):
    primary_name: Optional[str] = None
    status: Optional[str] = None
    toc: Optional[List[Dict[str, Any]]] = None
    doc_metadata: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")
    thumbnails: Optional[Dict[str, Any]] = None


class DocumentDelete(BaseModel):
    doc_id: uuid.UUID


class DocumentQueryParams(BaseModel):
    status: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    sort_order: str = "desc"


class DocumentResponse(DocumentBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    doc_id: uuid.UUID
    file_path: str
    file_size_bytes: int
    file_hash: str
    uploaded_at: datetime
    toc: Optional[List[Dict[str, Any]]] = None
    doc_metadata: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")
    thumbnails: Optional[Dict[str, Any]] = None


class PageDescriptionResponse(BaseModel):
    """
    Response schema for requested page multimodal description.
    """
    document_id: uuid.UUID
    page_num: int
    description: str

