"""Fernet adapter implementing IEncryptor using cryptography.fernet."""

from cryptography.fernet import Fernet, InvalidToken

from src.core.exceptions.encryption_exceptions import (
    EncryptionError,
    InvalidKeyTokenError,
)
from src.core.interfaces.iencryptor import IEncryptor


class FernetAdapter(IEncryptor):
    """Infrastructure adapter implementing IEncryptor using the Fernet symmetric cipher."""

    def generate_key(self) -> str:
        """Generate a URL-safe base64-encoded 32-byte key."""
        try:
            return Fernet.generate_key().decode()
        except Exception as e:
            raise EncryptionError(f"Failed to generate encryption key: {e}") from e

    def encrypt(self, plain_text: str, key: str) -> str:
        """Encrypt plaintext using Fernet symmetric encryption."""
        try:
            cipher = Fernet(key.encode())
            return cipher.encrypt(plain_text.encode()).decode()
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {e}") from e

    def decrypt(self, cipher_text: str, key: str) -> str:
        """Decrypt ciphertext token using Fernet symmetric encryption."""
        try:
            cipher = Fernet(key.encode())
            return cipher.decrypt(cipher_text.encode()).decode()
        except InvalidToken as e:
            raise InvalidKeyTokenError("Invalid encryption key token.") from e
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {e}") from e
