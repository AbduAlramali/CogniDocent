from typing import Any
import uuid

from src.core.enums import ChatProvider
from src.core.interfaces.ilogger import ILogger
from src.core.interfaces.iprovider_settings_repository import (
    IProviderSettingsRepository,
)
from src.models.provider_settings import ProviderSettings
from src.services.encryption_service import EncryptionService
from src.services.provider_rules import build_models_registry


class ProviderService:
    """
    Business service managing available AI providers and their model registries,
    as well as secure encryption and storage of provider API keys.
    """

    def __init__(
        self,
        provider_settings_repo: IProviderSettingsRepository,
        encryption_service: EncryptionService,
        logger: ILogger,
    ) -> None:
        self.provider_settings_repo = provider_settings_repo
        self.encryption_service = encryption_service
        self.logger = logger

    def list_providers_models(self) -> dict[str, Any]:
        """
        Returns all supported AI providers and their available models with token limits
        and reasoning capabilities.
        """
        return build_models_registry()

    async def update_api_key(
        self,
        provider_name: ChatProvider,
        api_key: str,
    ) -> dict[str, Any]:
        """
        Encrypts and stores or updates the API key for a specified AI provider.
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty.")

        encrypted_key = self.encryption_service.encrypt_api_key(api_key.strip())
        existing = await self.provider_settings_repo.get_by_provider(provider_name)

        if existing:
            await self.provider_settings_repo.update(
                provider_name,
                encrypted_api_key=encrypted_key,
                is_active=True,
            )
        else:
            new_settings = ProviderSettings(
                provider_id=uuid.uuid4(),
                provider_name=provider_name,
                encrypted_api_key=encrypted_key,
                is_active=True,
            )
            await self.provider_settings_repo.create(new_settings)

        self.logger.info("Updated provider API key", provider=provider_name.value)
        return {
            "message": "API key updated successfully",
            "provider_name": provider_name.value,
            "is_active": True,
        }
