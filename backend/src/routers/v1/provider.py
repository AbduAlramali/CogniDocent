from typing import Any, Dict
from fastapi import APIRouter, Depends, Path, status

from src.core.enums import ChatProvider
from src.dependencies import get_provider_service
from src.schemas.provider import UpdateApiKeyRequest, UpdateApiKeyResponse
from src.services.provider_service import ProviderService

router = APIRouter(prefix="/providers", tags=["Providers"])


@router.get(
    "/models",
    status_code=status.HTTP_200_OK,
    summary="List Providers and Models",
    description="""
    Lists all supported AI LLM providers and their available models that users can connect to,
    including reasoning capabilities, supported levels, and token limits.
    """,
    responses={
        200: {
            "description": "Successfully retrieved dictionary of available providers and their models.",
        }
    },
)
async def list_providers_models(
    provider_service: ProviderService = Depends(get_provider_service),
) -> Dict[str, Any]:
    return provider_service.list_providers_models()


@router.put(
    "/{provider_name}/api-key",
    response_model=UpdateApiKeyResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Provider API Key",
    description="""
    Encrypts and securely stores the API key for a specified AI provider (e.g., openai, gemini, ollama).
    Activates the provider configuration.
    """,
    responses={
        200: {
            "description": "API key successfully encrypted and updated.",
            "model": UpdateApiKeyResponse,
        },
        400: {"description": "Bad Request: Empty or invalid API key."},
    },
)
async def update_api_key(
    provider_name: ChatProvider = Path(..., description="Provider name enum (e.g. openai, gemini, anthropic, ollama)"),
    body: UpdateApiKeyRequest = ...,
    provider_service: ProviderService = Depends(get_provider_service),
) -> UpdateApiKeyResponse:
    result = await provider_service.update_api_key(
        provider_name=provider_name,
        api_key=body.api_key,
    )
    return UpdateApiKeyResponse(**result)
