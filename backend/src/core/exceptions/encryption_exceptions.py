"""Domain exceptions for Encryption and Cipher operations."""


class EncryptionError(Exception):
    """Base exception for all encryption and decryption failures."""

    def __init__(self, message: str = "An encryption error occurred."):
        self.message = message
        super().__init__(self.message)


class InvalidKeyTokenError(EncryptionError):
    """Raised when decrypting with an invalid token or corrupt key."""

    def __init__(self, message: str = "Invalid or corrupted encryption token."):
        super().__init__(message)
