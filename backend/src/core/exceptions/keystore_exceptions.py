"""Domain exceptions for KeyStore interactions."""


class KeyStoreError(Exception):
    """Base exception for all key store and credential storage operations."""

    def __init__(self, message: str = "An error occurred with key store operation."):
        self.message = message
        super().__init__(self.message)
