import pytest
from unittest.mock import patch, MagicMock
from cryptography.fernet import Fernet

from src.core.config import get_app_settings
from src.core.exceptions.encryption_exceptions import InvalidKeyTokenError, EncryptionError
from src.core.interfaces.ikey_store import IKeyStore
from src.core.interfaces.iencryptor import IEncryptor
from src.infra.fernet_adapter import FernetAdapter
from src.infra.keyring_adapter import KeyringAdapter
from src.services.encryption_service import EncryptionService


def test_encryption_service_first_run_generates_and_stores_key():
    mock_vault = {}

    def fake_get_password(service_name, username):
        return mock_vault.get((service_name, username))

    def fake_set_password(service_name, username, password):
        mock_vault[(service_name, username)] = password

    with patch("keyring.get_password", side_effect=fake_get_password) as mock_get, \
         patch("keyring.set_password", side_effect=fake_set_password) as mock_set:

        service = EncryptionService(
            keystore=KeyringAdapter(),
            encryptor=FernetAdapter(),
        )
        expected_app_name = get_app_settings().APP_NAME
        assert service.app_name == expected_app_name

        # Master key was fetched and created
        mock_get.assert_called_once_with(expected_app_name, "master_encryption_key")
        mock_set.assert_called_once()
        assert (expected_app_name, "master_encryption_key") in mock_vault

        # Encrypt and decrypt roundtrip
        plain_key = "sk-proj-test123456789"
        encrypted = service.encrypt_api_key(plain_key)
        assert encrypted != plain_key
        assert isinstance(encrypted, str)

        decrypted = service.decrypt_api_key(encrypted)
        assert decrypted == plain_key


def test_encryption_service_uses_existing_key():
    existing_key = Fernet.generate_key().decode()
    mock_vault = {("CustomApp", "master_encryption_key"): existing_key}

    with patch("keyring.get_password", return_value=existing_key) as mock_get, \
         patch("keyring.set_password") as mock_set:

        service = EncryptionService(
            keystore=KeyringAdapter(),
            encryptor=FernetAdapter(),
            app_name="CustomApp",
        )
        assert service.app_name == "CustomApp"

        mock_get.assert_called_once_with("CustomApp", "master_encryption_key")
        mock_set.assert_not_called()

        plain_key = "openai-secret-key"
        encrypted = service.encrypt_api_key(plain_key)
        decrypted = service.decrypt_api_key(encrypted)
        assert decrypted == plain_key


def test_encryption_service_with_mock_dependencies():
    mock_keystore = MagicMock(spec=IKeyStore)
    mock_encryptor = MagicMock(spec=IEncryptor)

    mock_keystore.get_key.return_value = None
    mock_encryptor.generate_key.return_value = "mocked-master-key"
    mock_encryptor.encrypt.return_value = "mocked-encrypted-token"
    mock_encryptor.decrypt.return_value = "my-secret-key"

    service = EncryptionService(
        keystore=mock_keystore,
        encryptor=mock_encryptor,
        app_name="TestApp",
    )

    mock_keystore.get_key.assert_called_once_with("TestApp", "master_encryption_key")
    mock_encryptor.generate_key.assert_called_once()
    mock_keystore.set_key.assert_called_once_with("TestApp", "master_encryption_key", "mocked-master-key")

    enc = service.encrypt_api_key("my-secret-key")
    assert enc == "mocked-encrypted-token"
    mock_encryptor.encrypt.assert_called_once_with("my-secret-key", "mocked-master-key")

    dec = service.decrypt_api_key("mocked-encrypted-token")
    assert dec == "my-secret-key"
    mock_encryptor.decrypt.assert_called_once_with("mocked-encrypted-token", "mocked-master-key")


def test_encryption_service_decrypt_invalid_token():
    existing_key = Fernet.generate_key().decode()
    with patch("keyring.get_password", return_value=existing_key):
        service = EncryptionService(
            keystore=KeyringAdapter(),
            encryptor=FernetAdapter(),
        )
        with pytest.raises(InvalidKeyTokenError):
            service.decrypt_api_key("invalid-token-string")
