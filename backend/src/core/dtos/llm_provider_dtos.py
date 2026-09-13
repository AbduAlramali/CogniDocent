"""Data Transfer Objects for the LLM Provider domain boundary."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from src.core.config import get_ai_settings
from src.core.enums import Role, ThinkingLevel, ChatProvider, EmbeddingProvider
from pydantic import Field


@dataclass(frozen=True)
class ToolCallDTO:
    """Represents a structured request from the LLM to execute a tool."""

    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass(frozen=True)
class ToolDefinitionDTO:
    """A pure domain representation of a tool's JSON schema signature."""

    name: str
    description: str
    parameters_schema: Dict[str, Any]


@dataclass(frozen=True)
class DomainMessageDTO:
    """A provider-agnostic representation of a conversation message."""

    role: Role
    content: str
    images: List[str] = field(default_factory=list)
    tool_calls: List[ToolCallDTO] = field(default_factory=list)
    tool_call_id: Optional[str] = None  # Used when role == TOOL


@dataclass(frozen=True)
class CitationMetadata:
    ref_id: str  # e.g., "chunk_982"
    page: int  # e.g., 4
    bbox: List[float]  # e.g., [100.0, 250.0, 400.0, 300.0] for PDF highlighting
    source_name: str  # e.g., "NVIDIA RTX Architecture.pdf"


@dataclass(frozen=True)
class LLMResponseDTO:
    """The final payload returned by the LLM Provider."""

    message: DomainMessageDTO
    finish_reason: str
    input_tokens: int = 0
    output_tokens: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    citations: List[CitationMetadata] = field(default_factory=list)


@dataclass(frozen=True)
class StreamChunkDTO:
    """A generic streaming chunk to pass back to the API."""

    content_delta: str = ""
    tool_name: Optional[str] = None
    finish_reason: Optional[str] = None


@dataclass(frozen=True)
class BaseLLMConfigDTO:
    """The active routing configuration retrieved from the user's database settings."""

    model_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None


@dataclass(frozen=True)
class LLMRouteConfigDTO(BaseLLMConfigDTO):
    """The active routing configuration retrieved from the user's database settings."""

    provider: ChatProvider = ChatProvider.OPENAI
    model_name: str
    temperature: float = 0.0
    thinking_level: ThinkingLevel = ThinkingLevel.NONE


@dataclass(frozen=True)
class EmbeddingConfigDTO(BaseLLMConfigDTO):
    """Configuration for the active embedding engine."""

    model_name: str = field(
        default_factory=lambda: get_ai_settings().DEFAULT_EMBEDDING_MODEL
    )
    provider: EmbeddingProvider = EmbeddingProvider.OPENAI
    dimensions: int = field(
        default_factory=lambda: get_ai_settings().DEFAULT_EMBEDDING_DIMENSIONS
    )
    timeout_seconds: int = 60


@dataclass(frozen=True)
class SystemAIConfigDTO:
    active_chat_model: LLMRouteConfigDTO
    embedding_config: EmbeddingConfigDTO
    vision_model: LLMRouteConfigDTO
