from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from src.core.enums import ChatProvider


class UpdateApiKeyRequest(BaseModel):
    """
    Request schema for updating an AI provider's API key.
    """
    api_key: str = Field(..., min_length=1, description="Plaintext API key to encrypt and store")


class UpdateApiKeyResponse(BaseModel):
    """
    Response schema after updating an AI provider's API key.
    """
    message: str
    provider_name: str
    is_active: bool


class ModelCapabilitiesResponse(BaseModel):
    """
    Capabilities and token limits for a specific provider model.
    """
    supports_thinking: bool
    allowed_levels: List[str] = Field(default_factory=list)
    max_input_tokens: Optional[int] = None
    max_output_tokens: Optional[int] = None
