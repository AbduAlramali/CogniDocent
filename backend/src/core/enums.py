from enum import Enum


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ThinkingLevel(str, Enum):
    """Defines the reasoning effort budget for supporting models."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ChatProvider(str, Enum):
    """Providers that support text generation and reasoning."""

    OLLAMA = "OLLAMA"
    GEMINI = "GEMINI"
    OPENAI = "OPENAI"
    ANTHROPIC = "ANTHROPIC"


class EmbeddingProvider(str, Enum):
    """Providers that support vector representation."""

    OLLAMA = "OLLAMA"
    GEMINI = "GEMINI"
    OPENAI = "OPENAI"
    VOYAGE = "VOYAGE"
    COHERE = "COHERE"
    FASTEMBED = "FASTEMBED"


class ScanStatus(str, Enum):
    CLEAN = "CLEAN"
    INFECTED = "INFECTED"
    FAILED = "FAILED"


class FileType(str, Enum):
    ATTACHMENT = "attachment"
    DOCUMENT = "document"


class UploadStatus(str, Enum):
    """
    Enum representing the status of a file upload.
    """

    PROCESSING = "processing"
    COMPLETED = "completed"
    INFECTED = "infected"
    FAILED = "failed"
