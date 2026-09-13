from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from src.core.enums import Role, ThinkingLevel
import uuid
from src.schemas.media import MediaResponse


class CitationMetadataResponse(BaseModel):
    ref_id: str
    page: int
    bbox: list[float]
    source_name: str


class MessageBase(BaseModel):
    role: Role
    content: str
    citations: Optional[list[CitationMetadataResponse]] = None


class MessageCreate(MessageBase):
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    thinking_mode: Optional[ThinkingLevel] = None
    token_count: Optional[int] = None
    latency_ms: Optional[int] = None


class MessageQueryParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    sort_order: str = "asc"  # Messages are typically fetched chronologically


class MessageResponse(MessageBase):
    model_config = ConfigDict(from_attributes=True)

    message_id: uuid.UUID
    chat_id: uuid.UUID
    created_at: datetime
    token_count: Optional[int] = None
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    thinking_mode: Optional[ThinkingLevel] = None


class MessageWithAttachments(MessageResponse):
    image_attachments: List[MediaResponse] = Field(default_factory=list)
    doc_attachments: List[MediaResponse] = Field(default_factory=list)

