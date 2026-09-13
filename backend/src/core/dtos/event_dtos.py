from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime, timezone
from src.core.enums import ScanStatus, FileType


class BaseEventDTO(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "1.0"


class ProcessEventDTO(BaseEventDTO):
    project_id: str
    file_type: FileType
    bucket_name: str
    object_name: str
    scan_status: ScanStatus | None = None
    is_safe: bool | None = None
    content_type: str
    media_id: UUID | None = None
