from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, timezone


class NotificationType(str, Enum):
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"

    DOC_UPLOADED = "DOCUMENT_UPLOADED"
    ATTACHMENT_UPLOADED = "ATTACHMENT_UPLOADED"

    DOC_FAILED = "DOCUMENT_FAILED"
    DOC_READY = "DOCUMENT_READY"
    DOC_MALICIOUS = "DOCUMENT_MALICIOUS"

    ATTACHMENT_READY = "ATTACHMENT_READY"
    ATTACHMENT_FAILED = "ATTACHMENT_FAILED"
    ATTACHMENT_MALICIOUS = "ATTACHMENT_MALICIOUS"


class NotificationDTO(BaseModel):
    """
    Note: Notifications don't always need the full BaseEventDTO
    metadata since they are often transient 'fire and forget'
    messages for the UI.
    """

    type: NotificationType
    message: str
    project_id: Optional[str] = None
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible container for event-specific data (e.g., {'doc_id': '...'} or {'attachment_id': '...'}).",
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
