from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
import uuid


class ProjectBase(BaseModel):
    title: str
    description: Optional[str] = None
    is_archived: bool = False


class ProjectCreate(ProjectBase):
    doc_id: uuid.UUID


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_archived: Optional[bool] = None


class ProjectDelete(BaseModel):
    project_id: uuid.UUID


class ProjectQueryParams(BaseModel):
    search: Optional[str] = None
    is_archived: Optional[bool] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    sort_by: str = "created_at"
    sort_order: str = "desc"


class ProjectResponse(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    project_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    doc_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    thumbnails: Optional[dict] = None


class ProjectCreatedResponse(BaseModel):
    project_id: uuid.UUID
    doc_id: uuid.UUID
