from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
import uuid


class ChatBase(BaseModel):
    title: str = "New Chat"
    ai_provider: str
    ai_model: str
    thinking_mode: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    is_archived: bool = False


class ChatCreate(BaseModel):
    content: str
    ai_provider: str
    ai_model: str
    thinking_mode: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatUpdate(BaseModel):
    title: Optional[str] = None
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    thinking_mode: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    is_archived: Optional[bool] = None


class ChatDelete(BaseModel):
    chat_id: uuid.UUID


class ChatQueryParams(BaseModel):
    project_id: uuid.UUID
    is_archived: Optional[bool] = False
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    sort_order: str = "desc"


class ChatResponse(ChatBase):
    model_config = ConfigDict(from_attributes=True)

    chat_id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None


class ChatCompletionRequest(BaseModel):
    """
    Request schema for chat completion. If chat_id is omitted, a new chat is automatically created.
    """
    project_id: uuid.UUID = Field(..., description="UUID of the project")
    chat_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional UUID of an existing chat. If omitted, creates a new chat session.",
    )
    message: str = Field(..., min_length=1, description="Message to send to the assistant")
    attachment_ids: List[uuid.UUID] = Field(
        default_factory=list,
        description="Optional list of attachment media UUIDs to include with the message",
    )

