import uuid
from unittest.mock import MagicMock
import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from src.core.exceptions.chat_exceptions import EmptyFileContentError
from src.core.exceptions.chat_orchestrator_exceptions import OrchestrationTimeoutError
from src.core.exceptions.database import DuplicateProjectError, ProjectNotFoundError, RepositoryError
from src.core.exceptions.fast_parser_exceptions import DocumentCorruptedError, ParserResourceLimitError
from src.core.exceptions.llm_provider_exceptions import LLMAuthenticationError, LLMRateLimitError
from src.core.exceptions.tts_exceptions import TTSVoiceNotFoundError
from src.core.interfaces.ilogger import ILogger
from src.exception_handlers import register_exception_handlers


@pytest.fixture
def app_with_handlers():
    app = FastAPI()
    mock_logger = MagicMock(spec=ILogger)
    register_exception_handlers(app, mock_logger)

    @app.get("/test-not-found")
    def route_not_found():
        raise ProjectNotFoundError(uuid.uuid4())

    @app.get("/test-duplicate")
    def route_duplicate():
        raise DuplicateProjectError("name", "Project Alpha")

    @app.get("/test-value-error")
    def route_value_error():
        raise ValueError("Invalid configuration parameter")

    @app.get("/test-chat-service-error")
    def route_chat_service_error():
        raise EmptyFileContentError("empty.txt")

    @app.get("/test-parser-limit")
    def route_parser_limit():
        raise ParserResourceLimitError(150, 100)

    @app.get("/test-parser-corrupted")
    def route_parser_corrupted():
        raise DocumentCorruptedError("/path/to/doc.pdf", "corrupted header")

    @app.get("/test-rate-limit")
    def route_rate_limit():
        raise LLMRateLimitError(60)

    @app.get("/test-llm-provider-error")
    def route_llm_provider_error():
        raise LLMAuthenticationError("OpenAI")

    @app.get("/test-timeout")
    def route_timeout():
        raise OrchestrationTimeoutError(15.0)

    @app.get("/test-tts-voice-not-found")
    def route_tts_voice_not_found():
        raise TTSVoiceNotFoundError("ElevenLabs", "voice-123")

    @app.get("/test-repository-error")
    def route_repository_error():
        raise RepositoryError("Connection pool exhausted")

    @app.get("/test-unexpected-crash")
    def route_unexpected_crash():
        raise RuntimeError("Unexpected failure in background thread")

    return app, mock_logger


def test_entity_not_found_handled(app_with_handlers):
    app, mock_logger = app_with_handlers
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-not-found")
    assert response.status_code == 404
    assert "Project" in response.json()["message"]
    mock_logger.warning.assert_called_once()


def test_duplicate_entity_handled(app_with_handlers):
    app, mock_logger = app_with_handlers
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-duplicate")
    assert response.status_code == 409
    mock_logger.warning.assert_called_once()


def test_value_error_handled(app_with_handlers):
    app, mock_logger = app_with_handlers
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-value-error")
    assert response.status_code == 400
    assert response.json()["message"] == "Invalid configuration parameter"
    mock_logger.warning.assert_called_once()


def test_chat_service_error_handled(app_with_handlers):
    app, mock_logger = app_with_handlers
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-chat-service-error")
    assert response.status_code == 400
    assert "empty.txt" in response.json()["message"]
    mock_logger.warning.assert_called_once()


def test_parser_resource_limit_handled(app_with_handlers):
    app, mock_logger = app_with_handlers
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-parser-limit")
    assert response.status_code == 413
    mock_logger.warning.assert_called_once()


def test_fast_parser_error_handled(app_with_handlers):
    app, mock_logger = app_with_handlers
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-parser-corrupted")
    assert response.status_code == 422
    mock_logger.warning.assert_called_once()


def test_llm_rate_limit_handled(app_with_handlers):
    app, mock_logger = app_with_handlers
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-rate-limit")
    assert response.status_code == 429
    mock_logger.warning.assert_called_once()


def test_llm_provider_error_handled(app_with_handlers):
    app, mock_logger = app_with_handlers
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-llm-provider-error")
    assert response.status_code == 502
    mock_logger.error.assert_called_once()


def test_orchestration_timeout_handled(app_with_handlers):
    app, mock_logger = app_with_handlers
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-timeout")
    assert response.status_code == 504
    mock_logger.error.assert_called_once()


def test_tts_voice_not_found_handled(app_with_handlers):
    app, mock_logger = app_with_handlers
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-tts-voice-not-found")
    assert response.status_code == 404
    mock_logger.warning.assert_called_once()


def test_repository_error_handled(app_with_handlers):
    app, mock_logger = app_with_handlers
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-repository-error")
    assert response.status_code == 500
    assert response.json()["message"] == "A database error occurred."
    mock_logger.error.assert_called_once()


def test_global_exception_handler_catches_all_and_prevents_crash(app_with_handlers):
    app, mock_logger = app_with_handlers
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-unexpected-crash")
    assert response.status_code == 500
    assert response.json()["message"] == "An unexpected internal server error occurred."
    mock_logger.error.assert_called_once()
