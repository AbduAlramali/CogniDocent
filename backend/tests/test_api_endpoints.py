from datetime import datetime, UTC
import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
import pytest
from starlette.testclient import TestClient

from src.core.enums import ChatProvider, Role, UploadStatus
from src.dependencies import (
    get_audio_explanation_service,
    get_chat_service,
    get_pdf_service,
    get_project_service,
    get_provider_service,
)
from src.main import app
from src.schemas.message import CitationMetadataResponse, MessageWithAttachments
from src.schemas.project import ProjectCreatedResponse, ProjectResponse
from src.services.audio_explanation_service import AudioExplanationService
from src.services.chat_service import ChatService
from src.services.pdf_service import PDFService
from src.services.project_service import ProjectService
from src.services.provider_service import ProviderService


@pytest.fixture
def client():
    return TestClient(app)


def test_create_project(client):
    mock_service = MagicMock(spec=ProjectService)
    project_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    mock_service.create_project = AsyncMock(
        return_value=ProjectCreatedResponse(
            project_id=project_id,
            doc_id=doc_id,
        )
    )

    app.dependency_overrides[get_project_service] = lambda: mock_service
    try:
        response = client.post(
            "/v1/projects",
            files={"file": ("test.pdf", b"%PDF-1.4 dummy content", "application/pdf")},
            data={"title": "Custom Project"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["project_id"] == str(project_id)
        assert data["doc_id"] == str(doc_id)
    finally:
        app.dependency_overrides.pop(get_project_service, None)


def test_list_projects(client):
    mock_service = MagicMock(spec=ProjectService)
    proj_id = uuid.uuid4()
    mock_service.list_projects = AsyncMock(
        return_value=[
            ProjectResponse(
                project_id=proj_id,
                title="Alpha Project",
                description="Test description",
                doc_id=uuid.uuid4(),
                thumbnails={"small": "s3://small.png"},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        ]
    )

    app.dependency_overrides[get_project_service] = lambda: mock_service
    try:
        response = client.get("/v1/projects")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["project_id"] == str(proj_id)
        assert data[0]["thumbnails"]["small"] == "s3://small.png"
    finally:
        app.dependency_overrides.pop(get_project_service, None)


def test_delete_project(client):
    mock_service = MagicMock(spec=ProjectService)
    mock_service.delete_project = AsyncMock()
    proj_id = uuid.uuid4()

    app.dependency_overrides[get_project_service] = lambda: mock_service
    try:
        response = client.delete(f"/v1/projects/{proj_id}")
        assert response.status_code == 204
        mock_service.delete_project.assert_awaited_once_with(proj_id)
    finally:
        app.dependency_overrides.pop(get_project_service, None)


def test_list_chats(client):
    mock_service = MagicMock(spec=ChatService)
    chat_id = uuid.uuid4()
    proj_id = uuid.uuid4()

    chat_obj = MagicMock()
    chat_obj.chat_id = chat_id
    chat_obj.project_id = proj_id
    chat_obj.title = "Main Discussion"
    chat_obj.ai_provider = "OPENAI"
    chat_obj.ai_model = "gpt-4o"
    chat_obj.thinking_mode = None
    chat_obj.metadata = {}
    chat_obj.is_archived = False
    chat_obj.created_at = datetime.now(UTC)
    chat_obj.updated_at = None

    mock_service.list_chats = AsyncMock(return_value=[chat_obj])

    app.dependency_overrides[get_chat_service] = lambda: mock_service
    try:
        response = client.get(f"/v1/chats?project_id={proj_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["chat_id"] == str(chat_id)
        assert data[0]["title"] == "Main Discussion"
    finally:
        app.dependency_overrides.pop(get_chat_service, None)


def test_delete_chat(client):
    mock_service = MagicMock(spec=ChatService)
    mock_service.delete_chat = AsyncMock()
    chat_id = uuid.uuid4()

    app.dependency_overrides[get_chat_service] = lambda: mock_service
    try:
        response = client.delete(f"/v1/chats/{chat_id}")
        assert response.status_code == 204
        mock_service.delete_chat.assert_awaited_once_with(chat_id)
    finally:
        app.dependency_overrides.pop(get_chat_service, None)


def test_chat_completion(client):
    mock_service = MagicMock(spec=ChatService)
    msg_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    proj_id = uuid.uuid4()

    citation = CitationMetadataResponse(
        ref_id="ref_1",
        page=1,
        bbox=[0.1, 0.2, 0.3, 0.4],
        source_name="doc.pdf",
    )

    mock_service.chat_completion = AsyncMock(
        return_value=MessageWithAttachments(
            message_id=msg_id,
            chat_id=chat_id,
            role=Role.ASSISTANT,
            content="According to the document [ref_1], the results are valid.",
            citations=[citation],
            created_at=datetime.now(UTC),
        )
    )

    app.dependency_overrides[get_chat_service] = lambda: mock_service
    try:
        # 1. New chat without chat_id
        response = client.post(
            "/v1/chats/completion",
            json={
                "project_id": str(proj_id),
                "message": "What does the paper conclude?",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message_id"] == str(msg_id)
        assert data["chat_id"] == str(chat_id)
        assert data["role"] == "assistant"
        assert len(data["citations"]) == 1

        # 2. Existing chat with chat_id
        response2 = client.post(
            "/v1/chats/completion",
            json={
                "project_id": str(proj_id),
                "chat_id": str(chat_id),
                "message": "Tell me more.",
            },
        )
        assert response2.status_code == 200
    finally:
        app.dependency_overrides.pop(get_chat_service, None)


def test_upload_attachment(client):
    mock_service = MagicMock(spec=ChatService)
    media_id = uuid.uuid4()
    proj_id = uuid.uuid4()

    mock_media = MagicMock()
    mock_media.media_id = media_id
    mock_media.message_id = None
    mock_media.filename = "diagram.png"
    mock_media.file_path = f"{media_id}.png"
    mock_media.file_size_bytes = 1024
    mock_media.file_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    mock_media.content_type = "image/png"
    mock_media.status = UploadStatus.PROCESSING
    mock_media.uploaded_at = datetime.now(UTC)
    mock_media.caption = None
    mock_media.has_chunks = False
    mock_media.thumbnails = None

    mock_service.upload_attachment = AsyncMock(return_value=mock_media)

    app.dependency_overrides[get_chat_service] = lambda: mock_service
    try:
        response = client.post(
            "/v1/chats/attachments",
            files={"file": ("diagram.png", b"fake image bytes", "image/png")},
            data={
                "project_id": str(proj_id),
                "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["media_id"] == str(media_id)
        assert data["filename"] == "diagram.png"
        assert data["status"] == "processing"
    finally:
        app.dependency_overrides.pop(get_chat_service, None)


def test_list_messages(client):
    mock_service = MagicMock(spec=ChatService)
    chat_id = uuid.uuid4()
    msg_id = uuid.uuid4()

    mock_service.list_messages = AsyncMock(
        return_value=[
            MessageWithAttachments(
                message_id=msg_id,
                chat_id=chat_id,
                role=Role.USER,
                content="Hello there!",
                citations=[],
                created_at=datetime.now(UTC),
            )
        ]
    )

    app.dependency_overrides[get_chat_service] = lambda: mock_service
    try:
        response = client.get(f"/v1/chats/{chat_id}/messages")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["message_id"] == str(msg_id)
        assert data[0]["role"] == "user"
    finally:
        app.dependency_overrides.pop(get_chat_service, None)


def test_get_page_description(client):
    mock_pdf = MagicMock(spec=PDFService)
    doc_id = uuid.uuid4()
    mock_pdf.get_page_description = AsyncMock(
        return_value="This page shows a diagram of system architecture with 3 tiers."
    )

    app.dependency_overrides[get_pdf_service] = lambda: mock_pdf
    try:
        response = client.get(f"/v1/documents/{doc_id}/pages/1/description")
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == str(doc_id)
        assert data["page_num"] == 1
        assert "diagram of system architecture" in data["description"]
    finally:
        app.dependency_overrides.pop(get_pdf_service, None)


def test_list_providers_models(client):
    mock_provider = MagicMock(spec=ProviderService)
    mock_provider.list_providers_models = MagicMock(
        return_value={
            "openai": {
                "display_name": "OpenAI",
                "is_active": True,
                "models": [{"id": "gpt-4o", "name": "GPT-4o"}],
            }
        }
    )

    app.dependency_overrides[get_provider_service] = lambda: mock_provider
    try:
        response = client.get("/v1/providers/models")
        assert response.status_code == 200
        data = response.json()
        assert "openai" in data
        assert data["openai"]["display_name"] == "OpenAI"
    finally:
        app.dependency_overrides.pop(get_provider_service, None)


def test_update_api_key(client):
    mock_provider = MagicMock(spec=ProviderService)
    mock_provider.update_api_key = AsyncMock(
        return_value={
            "provider_name": "OPENAI",
            "is_active": True,
            "message": "API key successfully updated and validated.",
        }
    )

    app.dependency_overrides[get_provider_service] = lambda: mock_provider
    try:
        response = client.put(
            "/v1/providers/OPENAI/api-key",
            json={"api_key": "sk-proj-test12345"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["provider_name"] == "OPENAI"
        assert data["is_active"] is True
    finally:
        app.dependency_overrides.pop(get_provider_service, None)


def test_synthesize_speech_streaming(client):
    mock_audio = MagicMock(spec=AudioExplanationService)

    async def fake_stream(text: str, voice: str) -> AsyncGenerator[bytes, None]:
        yield b"ID3"
        yield b"\x01\x02\x03\x04"
        yield b"chunk_audio"

    mock_audio.synthesize_speech = fake_stream

    app.dependency_overrides[get_audio_explanation_service] = lambda: mock_audio
    try:
        response = client.post(
            "/v1/tts/synthesize",
            json={"text": "Test synthesis", "voice": "alloy"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/mpeg"
        assert response.headers.get("x-accel-buffering") == "no"
        assert response.content == b"ID3\x01\x02\x03\x04chunk_audio"
    finally:
        app.dependency_overrides.pop(get_audio_explanation_service, None)
