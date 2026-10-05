"""Keyring adapter implementing IKeyStore using python-keyring."""

from typing import Optional
import keyring
from keyring.errors import KeyringError

from src.core.exceptions.keystore_exceptions import KeyStoreError
from src.core.interfaces.ikey_store import IKeyStore


class KeyringAdapter(IKeyStore):
    """Infrastructure adapter implementing IKeyStore using the OS keyring vault."""

    def get_key(self, service_name: str, key_name: str) -> Optional[str]:
        """Retrieve a stored secret from the OS keyring."""
        try:
            return keyring.get_password(service_name, key_name)
        except KeyringError as e:
            raise KeyStoreError(
                f"Failed to retrieve key '{key_name}' from keyring: {e}"
            ) from e
        except Exception as e:
            raise KeyStoreError(
                f"Unexpected error retrieving key '{key_name}' from keyring: {e}"
            ) from e

    def set_key(self, service_name: str, key_name: str, value: str) -> None:
        """Store a secret in the OS keyring."""
        try:
            keyring.set_password(service_name, key_name, value)
        except KeyringError as e:
            raise KeyStoreError(
                f"Failed to set key '{key_name}' in keyring: {e}"
            ) from e
        except Exception as e:
            raise KeyStoreError(
                f"Unexpected error setting key '{key_name}' in keyring: {e}"
            ) from e
