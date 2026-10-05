"""Port/Interface defining the contract for encryption and decryption capabilities."""

from abc import ABC, abstractmethod

from src.core.exceptions.encryption_exceptions import EncryptionError


class IEncryptor(ABC):
    """Interface for symmetric encryption and decryption operations."""

    @abstractmethod
    def generate_key(self) -> str:
        """Generate a secure encryption key string.

        Returns:
            A new key string.

        Raises:
            EncryptionError: If key generation fails.
        """
        pass

    @abstractmethod
    def encrypt(self, plain_text: str, key: str) -> str:
        """Encrypt plaintext using the specified key into a ciphertext token.

        Args:
            plain_text: The plaintext string to encrypt.
            key: The encryption key string.

        Returns:
            The encrypted ciphertext string.

        Raises:
            EncryptionError: If encryption fails.
        """
        pass

    @abstractmethod
    def decrypt(self, cipher_text: str, key: str) -> str:
        """Decrypt ciphertext token back into plaintext using the specified key.

        Args:
            cipher_text: The encrypted token string to decrypt.
            key: The encryption key string.

        Returns:
            The decrypted plaintext string.

        Raises:
            EncryptionError: If decryption fails.
        """
        pass
