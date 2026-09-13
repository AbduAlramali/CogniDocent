from datetime import datetime, timezone
import hashlib
import io
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.core.config import MinioSettings
from src.core.dtos.chunk_dto import ChunkDTO
from src.core.dtos.event_dtos import ProcessEventDTO
from src.core.dtos.notification_dto import NotificationDTO, NotificationType
from src.core.dtos.parser_dtos import (
    DocumentMetadataDTO,
    PageContentDTO,
    ParsedDocumentDTO,
)
from src.core.dtos.llm_provider_dtos import DomainMessageDTO, LLMResponseDTO
from src.core.enums import ChatProvider, FileType, Role, ScanStatus, UploadStatus
from src.core.exceptions.chat_exceptions import (
    EmptyFileContentError,
    FileHashMismatchError,
    InvalidEventDataError,
)
from src.core.exceptions.database import ChatNotFoundError, ProjectNotFoundError
from src.core.interfaces.iantivirus_service import IAntivirusService
from src.core.interfaces.ichat_orchestrator import IChatOrchestrator
from src.core.interfaces.ichat_repository import IChatRepository
from src.core.interfaces.ichunker import IChunker
from src.core.interfaces.ievent_publisher import IEventPublisher
from src.core.interfaces.ifast_parser import IFastParser
from src.core.interfaces.ilogger import ILogger
from src.core.interfaces.imedia_repository import IMediaRepository
from src.core.interfaces.imessage_repository import IMessageRepository
from src.core.interfaces.inotification_service import INotificationService
from src.core.interfaces.iobject_repository import IObjectRepository
from src.core.interfaces.iproject_repository import IProjectRepository
from src.models.chat import Chat
from src.models.media import Media
from src.models.media_chunk import MediaChunk
from src.models.message import Message
from src.models.project import Project
from src.schemas.media import MediaResponse
from src.schemas.message import MessageWithAttachments
from src.services.chat_service import ChatService
from src.services.embedding_service import EmbeddingService
from src.services.scan_service import ScanService
from src.services.thumbnail_service import ThumbnailService


@pytest.fixture
def minio_settings():
    return MinioSettings(
        MINIO_ENDPOINT="http://localhost:9000",
        MINIO_ACCESS_KEY="minioadmin",
        MINIO_SECRET_KEY="minioadmin",
        MINIO_INCOMING_UPLOADS_BUCKET="uploads",
        MINIO_QUARANTINE_BUCKET="quarantine",
        MINIO_TRUSTED_BUCKET="trusted",
        MINIO_INFECTED_BUCKET="infected",
        MINIO_THUMBNAILS_BUCKET="thumbnails",
    )


@pytest.fixture
def mock_logger():
    logger = MagicMock(spec=ILogger)
    logger.info = MagicMock()
    logger.error = MagicMock()
    logger.warning = MagicMock()
    return logger


@pytest.fixture
def mock_storage():
    storage = MagicMock(spec=IObjectRepository)
    storage.upload_object = AsyncMock()
    storage.download_object = AsyncMock(return_value=b"File content for tests")
    storage.copy_object = AsyncMock()
    storage.delete_object = AsyncMock()
    return storage


@pytest.fixture
def mock_media_repo():
    repo = MagicMock(spec=IMediaRepository)
    repo.create = AsyncMock(side_effect=lambda media: media)
    repo.update = AsyncMock(side_effect=lambda media_id, **kwargs: MagicMock(media_id=media_id, **kwargs))
    repo.bulk_create_chunks = AsyncMock(side_effect=lambda chunks: chunks)
    repo.search_media_chunks_vector = AsyncMock(return_value=[])
    repo.get_media_chunks_in_context_window = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_notification_service():
    notif = MagicMock(spec=INotificationService)
    notif.notify_user = AsyncMock()
    return notif


@pytest.fixture
def mock_publisher():
    pub = MagicMock(spec=IEventPublisher)
    pub.publish_event = AsyncMock(return_value="task-123")
    return pub


@pytest.fixture
def mock_scan_service():
    scan = MagicMock(spec=ScanService)
    scan.scan_file = AsyncMock()
    return scan


@pytest.fixture
def mock_chunker():
    chunker = MagicMock(spec=IChunker)
    chunker.chunk_pages = MagicMock(
        side_effect=lambda pages: [
            ChunkDTO(page_num=p.page_num, content=p.raw_text, chunk_index=idx)
            for idx, p in enumerate(pages)
            if p.raw_text and p.raw_text.strip()
        ]
    )
    return chunker


@pytest.fixture
def mock_embedding_service():
    service = AsyncMock(spec=EmbeddingService)
    service.embed_batch = AsyncMock(
        side_effect=lambda texts: [[0.1, 0.2] for _ in texts]
    )
    service.embed_text = AsyncMock(return_value=[0.1, 0.2])
    return service


@pytest.fixture
def mock_parser():
    parser = MagicMock(spec=IFastParser)
    parser.extract_document = MagicMock(
        return_value=ParsedDocumentDTO(
            metadata=DocumentMetadataDTO(total_pages=1, file_size_bytes=100),
            table_of_contents=[],
            pages=[
                PageContentDTO(
                    page_num=1,
                    raw_text="Extracted PDF page text",
                    char_count=23,
                    has_images=False,
                    has_tables_hint=False,
                )
            ],
        )
    )
    return parser


@pytest.fixture
def mock_chat_repo():
    repo = MagicMock(spec=IChatRepository)
    repo.get_by_id = AsyncMock()
    repo.create = AsyncMock(side_effect=lambda chat: chat)
    repo.update = AsyncMock(side_effect=lambda chat_id, **kwargs: MagicMock(chat_id=chat_id, **kwargs))
    return repo


@pytest.fixture
def mock_message_repo():
    repo = MagicMock(spec=IMessageRepository)
    repo.create = AsyncMock(
        side_effect=lambda msg: MessageWithAttachments(
            message_id=msg.message_id,
            chat_id=msg.chat_id,
            role=Role(msg.role),
            content=msg.content,
            citations=msg.citations,
            created_at=msg.created_at or datetime.now(timezone.utc),
            ai_provider=msg.ai_provider.value if msg.ai_provider else None,
            ai_model=msg.ai_model,
            image_attachments=[],
            doc_attachments=[],
        )
    )
    repo.list_by_chat = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_project_repo():
    repo = MagicMock(spec=IProjectRepository)
    repo.get_by_id = AsyncMock()
    return repo


@pytest.fixture
def mock_orchestrator():
    orchestrator = MagicMock(spec=IChatOrchestrator)
    orchestrator.process_turn = AsyncMock(
        return_value=LLMResponseDTO(
            message=DomainMessageDTO(role=Role.ASSISTANT, content="AI answer"),
            finish_reason="stop",
            input_tokens=10,
            output_tokens=20,
            metadata={"generated_captions": (), "generated_chat_title": "Generated Chat Title"},
        )
    )
    return orchestrator


from src.services.citation_service import CitationService


@pytest.fixture
def mock_citation_service():
    service = MagicMock(spec=CitationService)
    service.build_citations = AsyncMock(side_effect=lambda text, doc_id: (text, []))
    return service


@pytest.fixture
def chat_service(
    mock_storage,
    mock_media_repo,
    mock_notification_service,
    minio_settings,
    mock_logger,
    mock_publisher,
    mock_scan_service,
    mock_chunker,
    mock_embedding_service,
    mock_parser,
    mock_chat_repo,
    mock_message_repo,
    mock_project_repo,
    mock_orchestrator,
    mock_citation_service,
):
    return ChatService(
        storage=mock_storage,
        media_repo=mock_media_repo,
        notification_service=mock_notification_service,
        minio_settings=minio_settings,
        logger=mock_logger,
        publisher=mock_publisher,
        scan_service=mock_scan_service,
        chunker=mock_chunker,
        embedding_service=mock_embedding_service,
        parser=mock_parser,
        chat_repo=mock_chat_repo,
        message_repo=mock_message_repo,
        project_repo=mock_project_repo,
        orchestrator=mock_orchestrator,
        citation_service=mock_citation_service,
    )


@pytest.mark.asyncio
async def test_upload_attachment_success(
    chat_service,
    mock_storage,
    mock_media_repo,
    mock_publisher,
    minio_settings,
):
    project_id = str(uuid.uuid4())
    content = b"Sample attachment file content"
    file_hash = hashlib.sha256(content).hexdigest()
    filename = "test_image.png"

    media = await chat_service.upload_attachment(
        file_stream=content,
        filename=filename,
        content_type="image/png",
        project_id=project_id,
        file_hash=file_hash,
    )

    assert media.filename == filename
    assert media.file_hash == file_hash
    assert media.status == UploadStatus.PROCESSING
    assert media.message_id is None

    # Storage uploads to incoming bucket
    mock_storage.upload_object.assert_awaited_once()
    # Storage copies from incoming to quarantine
    mock_storage.copy_object.assert_awaited_once()
    # Storage deletes from incoming
    assert mock_storage.delete_object.await_count == 1

    # Task fired to scan service
    mock_publisher.publish_event.assert_awaited_once()
    topic, event = mock_publisher.publish_event.call_args[0]
    assert topic == "scan_service.scan_file"
    assert event.project_id == project_id
    assert event.file_type == FileType.ATTACHMENT
    assert event.media_id == media.media_id
    assert event.bucket_name == minio_settings.QUARANTINE_BUCKET


@pytest.mark.asyncio
async def test_upload_attachment_hash_mismatch(chat_service, mock_storage):
    project_id = str(uuid.uuid4())
    content = b"Some data"
    wrong_hash = "wrong_hash_value"

    with pytest.raises(FileHashMismatchError):
        await chat_service.upload_attachment(
            file_stream=content,
            filename="file.txt",
            content_type="text/plain",
            project_id=project_id,
            file_hash=wrong_hash,
        )

    # Incoming upload cleaned up on mismatch
    mock_storage.delete_object.assert_awaited_once()


@pytest.mark.asyncio
async def test_upload_attachment_empty_file(chat_service):
    project_id = str(uuid.uuid4())
    with pytest.raises(EmptyFileContentError):
        await chat_service.upload_attachment(
            file_stream=b"",
            filename="empty.txt",
            content_type="text/plain",
            project_id=project_id,
            file_hash="dummy",
        )


@pytest.mark.asyncio
async def test_upload_confirm_clean_file(
    chat_service,
    mock_media_repo,
    mock_notification_service,
    minio_settings,
):
    project_id = str(uuid.uuid4())
    media_id = uuid.uuid4()
    event = ProcessEventDTO(
        project_id=project_id,
        file_type=FileType.ATTACHMENT,
        bucket_name=minio_settings.TRUSTED_BUCKET,
        object_name=f"{media_id}.png",
        scan_status=ScanStatus.CLEAN,
        is_safe=True,
        content_type="image/png",
        media_id=media_id,
    )

    await chat_service.upload_confirm(event)

    # Media updated with COMPLETED and thumbnails
    mock_media_repo.update.assert_awaited_once()
    call_media_id, kwargs = mock_media_repo.update.call_args[0][0], mock_media_repo.update.call_args[1]
    assert call_media_id == media_id
    assert kwargs["status"] == UploadStatus.COMPLETED
    assert "thumbnails" in kwargs

    # User notified with ATTACHMENT_READY
    mock_notification_service.notify_user.assert_awaited_once()
    target_user_id, notif_payload = mock_notification_service.notify_user.call_args[1].values()
    assert target_user_id == uuid.UUID(project_id)
    assert notif_payload.type == NotificationType.ATTACHMENT_READY
    assert notif_payload.data["media_id"] == str(media_id)
    assert notif_payload.data["status"] == "clean"

    # Image attachment skips chunking
    mock_media_repo.bulk_create_chunks.assert_not_called()


@pytest.mark.asyncio
async def test_upload_confirm_clean_text_file_chunks_and_embeds(
    chat_service,
    mock_storage,
    mock_media_repo,
    mock_notification_service,
    mock_chunker,
    mock_embedding_service,
    mock_parser,
    minio_settings,
):
    project_id = str(uuid.uuid4())
    media_id = uuid.uuid4()
    mock_storage.download_object.return_value = b"Hello world text content for chunking."

    event = ProcessEventDTO(
        project_id=project_id,
        file_type=FileType.ATTACHMENT,
        bucket_name=minio_settings.TRUSTED_BUCKET,
        object_name=f"{media_id}.txt",
        scan_status=ScanStatus.CLEAN,
        is_safe=True,
        content_type="text/plain",
        media_id=media_id,
    )

    result_media = await chat_service.upload_confirm(event)

    # 1. Downloaded from storage
    mock_storage.download_object.assert_awaited_with(
        object_name=f"{media_id}.txt",
        bucket=minio_settings.TRUSTED_BUCKET,
    )

    # 2. PDF parser was skipped for text file
    mock_parser.extract_document.assert_not_called()

    # 3. Chunker and embedding were called
    mock_chunker.chunk_pages.assert_called_once()
    mock_embedding_service.embed_batch.assert_awaited_once()

    # 4. Media chunks were persisted in DB
    mock_media_repo.bulk_create_chunks.assert_awaited_once()
    created_chunks = mock_media_repo.bulk_create_chunks.call_args[0][0]
    assert len(created_chunks) > 0
    assert all(isinstance(c, MediaChunk) for c in created_chunks)
    assert created_chunks[0].media_id == media_id
    assert created_chunks[0].content == "Hello world text content for chunking."
    assert created_chunks[0].content_vector == [0.1, 0.2]

    # 5. Media has_chunks updated to True
    assert result_media.has_chunks is True


@pytest.mark.asyncio
async def test_upload_confirm_clean_pdf_file_chunks_and_embeds(
    chat_service,
    mock_storage,
    mock_media_repo,
    mock_notification_service,
    mock_chunker,
    mock_embedding_service,
    mock_parser,
    minio_settings,
):
    project_id = str(uuid.uuid4())
    media_id = uuid.uuid4()
    mock_storage.download_object.return_value = b"%PDF-1.4 mock content"

    event = ProcessEventDTO(
        project_id=project_id,
        file_type=FileType.ATTACHMENT,
        bucket_name=minio_settings.TRUSTED_BUCKET,
        object_name=f"{media_id}.pdf",
        scan_status=ScanStatus.CLEAN,
        is_safe=True,
        content_type="application/pdf",
        media_id=media_id,
    )

    result_media = await chat_service.upload_confirm(event)

    # 1. Downloaded from storage
    mock_storage.download_object.assert_awaited_with(
        object_name=f"{media_id}.pdf",
        bucket=minio_settings.TRUSTED_BUCKET,
    )

    # 2. PDF parser was called
    mock_parser.extract_document.assert_called_once()

    # 3. Chunker and embedding were called
    mock_chunker.chunk_pages.assert_called_once()
    mock_embedding_service.embed_batch.assert_awaited_once()

    # 4. Media chunks persisted
    mock_media_repo.bulk_create_chunks.assert_awaited_once()
    created_chunks = mock_media_repo.bulk_create_chunks.call_args[0][0]
    assert len(created_chunks) > 0
    assert all(isinstance(c, MediaChunk) for c in created_chunks)
    assert created_chunks[0].media_id == media_id
    assert created_chunks[0].content == "Extracted PDF page text"
    assert created_chunks[0].content_vector == [0.1, 0.2]

    # 5. Media has_chunks updated to True
    assert result_media.has_chunks is True


@pytest.mark.asyncio
async def test_upload_confirm_infected_file(
    chat_service,
    mock_media_repo,
    mock_notification_service,
    minio_settings,
):
    project_id = str(uuid.uuid4())
    media_id = uuid.uuid4()
    event = ProcessEventDTO(
        project_id=project_id,
        file_type=FileType.ATTACHMENT,
        bucket_name=minio_settings.INFECTED_BUCKET,
        object_name=f"{media_id}.exe",
        scan_status=ScanStatus.INFECTED,
        is_safe=False,
        content_type="application/x-msdownload",
        media_id=media_id,
    )

    await chat_service.upload_confirm(event)

    # Media updated with INFECTED
    mock_media_repo.update.assert_awaited_once()
    call_media_id, kwargs = mock_media_repo.update.call_args[0][0], mock_media_repo.update.call_args[1]
    assert call_media_id == media_id
    assert kwargs["status"] == UploadStatus.INFECTED

    # User notified with ATTACHMENT_MALICIOUS
    mock_notification_service.notify_user.assert_awaited_once()
    target_user_id, notif_payload = mock_notification_service.notify_user.call_args[1].values()
    assert target_user_id == uuid.UUID(project_id)
    assert notif_payload.type == NotificationType.ATTACHMENT_MALICIOUS
    assert notif_payload.data["media_id"] == str(media_id)
    assert notif_payload.data["status"] == "infected"


@pytest.mark.asyncio
async def test_upload_confirm_missing_media_id_raises(chat_service, minio_settings):
    project_id = str(uuid.uuid4())
    event = ProcessEventDTO(
        project_id=project_id,
        file_type=FileType.ATTACHMENT,
        bucket_name=minio_settings.TRUSTED_BUCKET,
        object_name="some_file.png",
        scan_status=ScanStatus.CLEAN,
        is_safe=True,
        content_type="image/png",
        media_id=None,
    )

    with pytest.raises(InvalidEventDataError):
        await chat_service.upload_confirm(event)


@pytest.mark.asyncio
async def test_scan_service_fires_thumbnail_generator_when_clean(
    mock_storage,
    minio_settings,
    mock_logger,
    mock_publisher,
):
    antivirus = MagicMock(spec=IAntivirusService)
    antivirus.scan_file = MagicMock(return_value=True)  # Clean
    mock_storage.download_object = AsyncMock(return_value=b"clean content")

    scan_svc = ScanService(
        antivirus=antivirus,
        storage=mock_storage,
        minio_settings=minio_settings,
        logger=mock_logger,
        publisher=mock_publisher,
    )

    media_id = uuid.uuid4()
    event = ProcessEventDTO(
        project_id=str(uuid.uuid4()),
        file_type=FileType.ATTACHMENT,
        bucket_name=minio_settings.QUARANTINE_BUCKET,
        object_name=f"{media_id}.pdf",
        content_type="application/pdf",
        media_id=media_id,
    )

    result_event = await scan_svc.scan_file(event)
    assert result_event.is_safe is True
    assert result_event.scan_status == ScanStatus.CLEAN
    assert result_event.bucket_name == minio_settings.TRUSTED_BUCKET

    # Fires task to thumbnail generator
    mock_publisher.publish_event.assert_awaited_once_with(
        "thumbnail_service.generate_thumbnails", result_event
    )


@pytest.mark.asyncio
async def test_scan_service_fires_upload_confirm_when_infected(
    mock_storage,
    minio_settings,
    mock_logger,
    mock_publisher,
):
    antivirus = MagicMock(spec=IAntivirusService)
    antivirus.scan_file = MagicMock(return_value=False)  # Infected
    mock_storage.download_object = AsyncMock(return_value=b"infected content")

    scan_svc = ScanService(
        antivirus=antivirus,
        storage=mock_storage,
        minio_settings=minio_settings,
        logger=mock_logger,
        publisher=mock_publisher,
    )

    media_id = uuid.uuid4()
    event = ProcessEventDTO(
        project_id=str(uuid.uuid4()),
        file_type=FileType.ATTACHMENT,
        bucket_name=minio_settings.QUARANTINE_BUCKET,
        object_name=f"{media_id}.pdf",
        content_type="application/pdf",
        media_id=media_id,
    )

    result_event = await scan_svc.scan_file(event)
    assert result_event.is_safe is False
    assert result_event.scan_status == ScanStatus.INFECTED
    assert result_event.bucket_name == minio_settings.INFECTED_BUCKET

    # Fires task to upload confirm
    mock_publisher.publish_event.assert_awaited_once_with(
        "chat_service.upload_confirm", result_event
    )


@pytest.mark.asyncio
async def test_thumbnail_service_fires_upload_confirm(
    mock_storage,
    minio_settings,
    mock_logger,
    mock_publisher,
):
    mock_storage.download_object = AsyncMock(return_value=b"text data")

    thumb_svc = ThumbnailService(
        storage=mock_storage,
        minio_settings=minio_settings,
        logger=mock_logger,
        publisher=mock_publisher,
    )

    media_id = uuid.uuid4()
    event = ProcessEventDTO(
        project_id=str(uuid.uuid4()),
        file_type=FileType.ATTACHMENT,
        bucket_name=minio_settings.TRUSTED_BUCKET,
        object_name=f"{media_id}.txt",
        content_type="text/plain",
        media_id=media_id,
        is_safe=True,
        scan_status=ScanStatus.CLEAN,
    )

    result_event = await thumb_svc.generate_thumbnails(event)

    # Skipped text/plain but fires task back to upload confirm
    mock_publisher.publish_event.assert_awaited_once_with(
        "chat_service.upload_confirm", result_event
    )


@pytest.mark.asyncio
async def test_search_media_chunks_success(
    chat_service,
    mock_media_repo,
    mock_embedding_service,
):
    media_id = uuid.uuid4()
    query = "database architecture"
    mock_embedding_service.embed_text.return_value = [0.5, -0.2]
    expected_chunk = MediaChunk(
        chunk_id=uuid.uuid4(),
        media_id=media_id,
        chunk_index=0,
        content="database architecture details",
        content_vector=[0.5, -0.2],
    )
    mock_media_repo.search_media_chunks_vector.return_value = [expected_chunk]

    results = await chat_service.search_media_chunks(
        query=query,
        media_id=media_id,
        limit=5,
    )

    mock_embedding_service.embed_text.assert_awaited_once_with(query)
    mock_media_repo.search_media_chunks_vector.assert_awaited_once_with(
        query_vector=[0.5, -0.2],
        media_id=media_id,
        limit=5,
    )
    assert len(results) == 1
    assert results[0] == expected_chunk


@pytest.mark.asyncio
async def test_search_media_chunks_empty_query(
    chat_service,
    mock_media_repo,
    mock_embedding_service,
):
    results = await chat_service.search_media_chunks(query="   ")
    assert results == []
    mock_embedding_service.embed_text.assert_not_called()
    mock_media_repo.search_media_chunks_vector.assert_not_called()


@pytest.mark.asyncio
async def test_expand_media_chunk_context_success(
    chat_service,
    mock_media_repo,
):
    media_id = uuid.uuid4()
    chunk_1 = MediaChunk(
        chunk_id=uuid.uuid4(),
        media_id=media_id,
        chunk_index=1,
        content="chunk 1",
    )
    chunk_2 = MediaChunk(
        chunk_id=uuid.uuid4(),
        media_id=media_id,
        chunk_index=2,
        content="chunk 2",
    )
    mock_media_repo.get_media_chunks_in_context_window.return_value = [chunk_1, chunk_2]

    results = await chat_service.expand_media_chunk_context(
        media_id=media_id,
        chunk_index=2,
        radius=1,
    )

    mock_media_repo.get_media_chunks_in_context_window.assert_awaited_once_with(
        media_id=media_id,
        target_chunk_index=2,
        radius=1,
    )
    assert results == [chunk_1, chunk_2]


@pytest.mark.asyncio
async def test_chat_completion_project_not_found_raises(
    chat_service,
    mock_project_repo,
):
    project_id = uuid.uuid4()
    mock_project_repo.get_by_id.return_value = None

    with pytest.raises(ProjectNotFoundError):
        await chat_service.chat_completion(
            project_id=project_id,
            message="Hello",
        )


@pytest.mark.asyncio
async def test_chat_completion_chat_not_found_raises(
    chat_service,
    mock_project_repo,
    mock_chat_repo,
):
    project_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    mock_project_repo.get_by_id.return_value = MagicMock(project_id=project_id, doc_id=uuid.uuid4())
    mock_chat_repo.get_by_id.return_value = None

    with pytest.raises(ChatNotFoundError):
        await chat_service.chat_completion(
            project_id=project_id,
            chat_id=chat_id,
            message="Hello",
        )


@pytest.mark.asyncio
async def test_chat_completion_new_chat_success(
    chat_service,
    mock_project_repo,
    mock_chat_repo,
    mock_message_repo,
    mock_orchestrator,
):
    project_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    mock_project_repo.get_by_id.return_value = MagicMock(project_id=project_id, doc_id=doc_id)

    mock_orchestrator.process_turn.return_value = LLMResponseDTO(
        message=DomainMessageDTO(role=Role.ASSISTANT, content="Hello, I am CogniDocent."),
        finish_reason="stop",
        input_tokens=15,
        output_tokens=25,
        metadata={"generated_captions": (), "generated_chat_title": "Project Welcome"},
    )

    result = await chat_service.chat_completion(
        project_id=project_id,
        message="Hello assistant",
    )

    # 1. New chat created with "New Title"
    mock_chat_repo.create.assert_awaited_once()
    created_chat = mock_chat_repo.create.call_args[0][0]
    assert created_chat.title == "New Title"
    assert created_chat.project_id == project_id

    # 2. User message created
    assert mock_message_repo.create.await_count == 2
    first_created_msg = mock_message_repo.create.call_args_list[0][0][0]
    assert first_created_msg.role == Role.USER.value
    assert first_created_msg.content == "Hello assistant"

    # 3. Orchestrator turn executed
    mock_orchestrator.process_turn.assert_awaited_once()
    orch_kwargs = mock_orchestrator.process_turn.call_args[1]
    assert orch_kwargs["thread_id"] == created_chat.chat_id
    assert orch_kwargs["user_message"].content == "Hello assistant"
    assert orch_kwargs["config"].generate_chat_title is True
    assert orch_kwargs["config"].document_id == doc_id

    # 4. Chat renamed with generated title
    mock_chat_repo.update.assert_awaited_once_with(
        created_chat.chat_id, title="Project Welcome"
    )

    # 5. Assistant response returned
    assert result.content == "Hello, I am CogniDocent."
    assert result.role == Role.ASSISTANT


@pytest.mark.asyncio
async def test_chat_completion_existing_chat_with_history(
    chat_service,
    mock_project_repo,
    mock_chat_repo,
    mock_message_repo,
    mock_orchestrator,
):
    project_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    existing_chat = MagicMock(
        chat_id=chat_id,
        project_id=project_id,
        title="Existing Chat",
        ai_provider=ChatProvider.OPENAI,
        ai_model="gpt-4o-mini",
    )
    mock_project_repo.get_by_id.return_value = MagicMock(project_id=project_id, doc_id=doc_id)
    mock_chat_repo.get_by_id.return_value = existing_chat

    # Setup history: 1 prior user message with image caption, 1 prior assistant message
    prior_user_msg = MagicMock(
        message_id=uuid.uuid4(),
        chat_id=chat_id,
        role="user",
        content="Prior question",
        image_attachments=[MagicMock(caption="Diagram of architecture")],
        doc_attachments=[],
    )
    prior_ai_msg = MagicMock(
        message_id=uuid.uuid4(),
        chat_id=chat_id,
        role="assistant",
        content="Prior answer",
        image_attachments=[],
        doc_attachments=[],
    )

    def fake_list_by_chat(cid):
        return [prior_user_msg, prior_ai_msg]

    mock_message_repo.list_by_chat.side_effect = fake_list_by_chat

    await chat_service.chat_completion(
        project_id=project_id,
        chat_id=chat_id,
        message="Follow up question",
    )

    # Chat was not renamed for existing chat
    mock_chat_repo.update.assert_not_called()

    # Orchestrator received converted history messages
    mock_orchestrator.process_turn.assert_awaited_once()
    orch_kwargs = mock_orchestrator.process_turn.call_args[1]
    history = orch_kwargs["history_messages"]
    assert len(history) == 2
    assert history[0].role == Role.USER
    assert "[Image: Diagram of architecture]" in history[0].content
    assert history[1].role == Role.ASSISTANT
    assert history[1].content == "Prior answer"


@pytest.mark.asyncio
async def test_chat_completion_with_images_and_captions(
    chat_service,
    mock_storage,
    mock_media_repo,
    mock_project_repo,
    mock_chat_repo,
    mock_message_repo,
    mock_orchestrator,
    minio_settings,
):
    project_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    existing_chat = MagicMock(
        chat_id=chat_id,
        project_id=project_id,
        title="Chat With Images",
        ai_provider=ChatProvider.OPENAI,
        ai_model="gpt-4o-mini",
    )
    mock_project_repo.get_by_id.return_value = MagicMock(project_id=project_id, doc_id=doc_id)
    mock_chat_repo.get_by_id.return_value = existing_chat

    img_id = uuid.uuid4()
    img_media = MagicMock(
        media_id=img_id,
        file_path="img.png",
        content_type="image/png",
        filename="img.png",
        caption=None,
    )
    mock_media_repo.update = AsyncMock(return_value=img_media)
    mock_media_repo.save_caption = AsyncMock()
    mock_storage.download_object = AsyncMock(return_value=b"fake-image-bytes")

    mock_orchestrator.process_turn.return_value = LLMResponseDTO(
        message=DomainMessageDTO(role=Role.ASSISTANT, content="I analyzed the image."),
        finish_reason="stop",
        metadata={"generated_captions": (str(img_id), "A generated chart caption")},
    )

    await chat_service.chat_completion(
        project_id=project_id,
        chat_id=chat_id,
        message="What is this chart showing?",
        attachment_ids=[img_id],
    )

    # 1. Attachment linked to message
    mock_media_repo.update.assert_awaited_once()

    # 2. Storage downloaded object and user_message received Base64 image
    mock_storage.download_object.assert_awaited_once_with(
        object_name="img.png",
        bucket=minio_settings.TRUSTED_BUCKET,
    )
    orch_kwargs = mock_orchestrator.process_turn.call_args[1]
    assert len(orch_kwargs["user_message"].images) == 1
    assert orch_kwargs["user_message"].images[0].startswith("data:image/png;base64,")
    assert orch_kwargs["images_to_caption"] == [img_id]

    # 3. Generated caption saved to media repository
    mock_media_repo.save_caption.assert_awaited_once_with(
        img_id, "A generated chart caption"
    )


@pytest.mark.asyncio
async def test_chat_completion_with_doc_attachments_as_active(
    chat_service,
    mock_project_repo,
    mock_chat_repo,
    mock_message_repo,
    mock_orchestrator,
):
    project_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    doc_attachment_id = uuid.uuid4()

    mock_project_repo.get_by_id.return_value = MagicMock(project_id=project_id, doc_id=doc_id)
    mock_chat_repo.get_by_id.return_value = MagicMock(
        chat_id=chat_id,
        project_id=project_id,
        title="Chat With Docs",
        ai_provider=ChatProvider.OPENAI,
        ai_model="gpt-4o-mini",
    )

    msg_with_doc = MagicMock(
        message_id=uuid.uuid4(),
        chat_id=chat_id,
        role="user",
        content="Read this document",
        image_attachments=[],
        doc_attachments=[MagicMock(media_id=doc_attachment_id)],
    )
    mock_message_repo.list_by_chat.return_value = [msg_with_doc]

    await chat_service.chat_completion(
        project_id=project_id,
        chat_id=chat_id,
        message="Search the document",
    )

    orch_kwargs = mock_orchestrator.process_turn.call_args[1]
    assert doc_attachment_id in orch_kwargs["config"].active_attachments


@pytest.mark.asyncio
async def test_chat_completion_with_citations(
    chat_service,
    mock_project_repo,
    mock_chat_repo,
    mock_message_repo,
    mock_orchestrator,
    mock_citation_service,
):
    from src.core.dtos.llm_provider_dtos import CitationMetadata

    project_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    chat_id = uuid.uuid4()

    mock_project_repo.get_by_id.return_value = MagicMock(project_id=project_id, doc_id=doc_id)
    mock_chat_repo.get_by_id.return_value = MagicMock(
        chat_id=chat_id,
        project_id=project_id,
        title="Chat With Citations",
        ai_provider=ChatProvider.OPENAI,
        ai_model="gpt-4o-mini",
    )

    chunk_uuid = uuid.uuid4()
    mock_orchestrator.process_turn.return_value = LLMResponseDTO(
        message=DomainMessageDTO(role=Role.ASSISTANT, content="Here is a claim [ref: chunk_xyz]."),
        finish_reason="stop",
        input_tokens=10,
        output_tokens=15,
    )

    citation_metadata = CitationMetadata(
        ref_id=f"chunk_{chunk_uuid}",
        page=2,
        bbox=[100.0, 200.0, 300.0, 250.0],
        source_name="Architecture.pdf",
    )
    mock_citation_service.build_citations.side_effect = None
    mock_citation_service.build_citations.return_value = (
        f"Here is a claim [ref: chunk_{chunk_uuid}].",
        [citation_metadata],
    )

    result = await chat_service.chat_completion(
        project_id=project_id,
        chat_id=chat_id,
        message="Explain the architecture",
    )

    mock_citation_service.build_citations.assert_awaited_once_with(
        text="Here is a claim [ref: chunk_xyz].",
        doc_id=doc_id,
    )
    assert result.content == f"Here is a claim [ref: chunk_{chunk_uuid}]."
    assert len(result.citations) == 1
    assert result.citations[0].ref_id == f"chunk_{chunk_uuid}"
    assert result.citations[0].page == 2
    assert result.citations[0].bbox == [100.0, 200.0, 300.0, 250.0]
    assert result.citations[0].source_name == "Architecture.pdf"
