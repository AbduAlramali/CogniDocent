from src.core.config import get_app_settings
from src.core.interfaces.iencryptor import IEncryptor
from src.core.interfaces.ikey_store import IKeyStore


class EncryptionService:
    """Service for securing and managing API keys using symmetric encryption
    and a secure key store for master key management.
    """

    def __init__(
        self,
        keystore: IKeyStore,
        encryptor: IEncryptor,
        app_name: str = "",
    ) -> None:
        self.keystore = keystore
        self.encryptor = encryptor
        self.app_name = app_name or get_app_settings().APP_NAME

        master_key = self.keystore.get_key(self.app_name, "master_encryption_key")
        if not master_key:
            master_key = self.encryptor.generate_key()
            self.keystore.set_key(self.app_name, "master_encryption_key", master_key)

        self._master_key = master_key

    def encrypt_api_key(self, plain_key: str) -> str:
        """Encrypts a plaintext API key string into an encrypted token."""
        return self.encryptor.encrypt(plain_key, self._master_key)

    def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypts an encrypted token back into the original plaintext API key."""
        return self.encryptor.decrypt(encrypted_key, self._master_key)
