import operator
from typing import Annotated
from dataclasses import dataclass, field
from typing import Optional
import uuid
from src.core.dtos.llm_provider_dtos import SystemAIConfigDTO


@dataclass
class ThreadStateDTO:
    """Internal graph state, hidden from the domain."""

    project_id: uuid.UUID
    document_id: uuid.UUID
    config: SystemAIConfigDTO
    active_attachments: Annotated[list[uuid.UUID], operator.add] = field(
        default_factory=list
    )
    generate_chat_title: bool = False
