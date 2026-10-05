"""Port/Interface defining the contract for secure key and credential storage."""

from abc import ABC, abstractmethod
from typing import Optional

from src.core.exceptions.keystore_exceptions import KeyStoreError


class IKeyStore(ABC):
    """Interface for secure key and credential storage."""

    @abstractmethod
    def get_key(self, service_name: str, key_name: str) -> Optional[str]:
        """Retrieve a stored key or password.

        Args:
            service_name: Name of the service or application.
            key_name: Identifier for the key.

        Returns:
            The stored key string, or None if not found.

        Raises:
            KeyStoreError: If retrieval fails due to underlying storage errors.
        """
        pass

    @abstractmethod
    def set_key(self, service_name: str, key_name: str, value: str) -> None:
        """Store a key or password.

        Args:
            service_name: Name of the service or application.
            key_name: Identifier for the key.
            value: Secret value to store.

        Raises:
            KeyStoreError: If saving fails due to underlying storage errors.
        """
        pass
