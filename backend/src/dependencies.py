from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_app_settings
from src.core.dtos.llm_provider_dtos import LLMRouteConfigDTO, EmbeddingConfigDTO
from src.core.enums import EmbeddingProvider
from src.core.interfaces.ilogger import ILogger
from src.core.interfaces.iproject_repository import IProjectRepository
from src.core.interfaces.idocument_chunk_repository import IDocumentChunkRepository
from src.core.interfaces.ichat_repository import IChatRepository
from src.core.interfaces.imessage_repository import IMessageRepository
from src.core.interfaces.imedia_repository import IMediaRepository
from src.core.interfaces.iprovider_settings_repository import (
    IProviderSettingsRepository,
)
from src.core.interfaces.idocument_repository import IDocumentRepository
from src.core.interfaces.iembedding_provider import IEmbeddingProvider
from src.core.interfaces.ichunker import IChunker
from src.core.interfaces.icache_client import ICacheClient
from src.core.interfaces.ievent_publisher import IEventPublisher
from src.core.interfaces.iobject_repository import IObjectRepository
from src.core.interfaces.iantivirus_service import IAntivirusService
from src.core.interfaces.inotification_service import INotificationService
from src.core.interfaces.ichat_orchestrator import IChatOrchestrator
from src.core.interfaces.ifast_parser import IFastParser
from pydantic import BaseModel
from src.infra.llms.litellm_embedding_adapter import LiteLLMEmbeddingAdapter
from src.services.embedding_service import EmbeddingService

from src.infra.python_logger import PythonLogger
from src.infra.postgres_adapter import AsyncSessionLocal
from src.infra.repositories.project_repository import ProjectRepository
from src.infra.repositories.document_repository import DocumentRepository
from src.infra.repositories.document_chunk_repository import DocumentChunkRepository
from src.infra.repositories.chat_repository import ChatRepository
from src.infra.repositories.message_repository import MessageRepository
from src.infra.repositories.media_repository import MediaRepository
from src.infra.repositories.provider_settings_repository import (
    ProviderSettingsRepository,
)

# Initialize logger wrapper
app_settings = get_app_settings()
_logger_instance = PythonLogger(
    name=app_settings.APP_NAME,
    app_state=app_settings.APP_ENV,
    level=app_settings.APP_LOG_LEVEL,
)

active_embedding_config = EmbeddingConfigDTO(
    provider=EmbeddingProvider.OLLAMA,
    model_name="nomic-embed-text-v2-moe",
    dimensions=768,
    base_url="http://localhost:11434",
)


async def get_logger() -> ILogger:
    """
    Dependency that provides an instance of ILogger.
    """
    return _logger_instance


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides an AsyncSession per request, ensuring clean disposal/rollback.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_project_repository(
    session: AsyncSession = Depends(get_db_session),
    logger: ILogger = Depends(get_logger),
) -> IProjectRepository:
    """
    Dependency that injects the Project repository.
    """
    return ProjectRepository(session=session, logger=logger)


def get_document_repository(
    session: AsyncSession = Depends(get_db_session),
    logger: ILogger = Depends(get_logger),
) -> IDocumentRepository:
    """
    Dependency that injects the Document repository.
    """
    return DocumentRepository(session=session, logger=logger)


def get_document_chunk_repository(
    session: AsyncSession = Depends(get_db_session),
    logger: ILogger = Depends(get_logger),
) -> IDocumentChunkRepository:
    """
    Dependency that injects the DocumentChunk repository.
    """
    return DocumentChunkRepository(session=session, logger=logger)


def get_chat_repository(
    session: AsyncSession = Depends(get_db_session),
    logger: ILogger = Depends(get_logger),
) -> IChatRepository:
    """
    Dependency that injects the Chat repository.
    """
    return ChatRepository(session=session, logger=logger)


def get_message_repository(
    session: AsyncSession = Depends(get_db_session),
    logger: ILogger = Depends(get_logger),
) -> IMessageRepository:
    """
    Dependency that injects the Message repository.
    """
    return MessageRepository(session=session, logger=logger)


def get_media_repository(
    session: AsyncSession = Depends(get_db_session),
    logger: ILogger = Depends(get_logger),
) -> IMediaRepository:
    """
    Dependency that injects the Media repository.
    """
    return MediaRepository(session=session, logger=logger)


def get_provider_settings_repository(
    session: AsyncSession = Depends(get_db_session),
    logger: ILogger = Depends(get_logger),
) -> IProviderSettingsRepository:
    """
    Dependency that injects the ProviderSettings repository.
    """
    return ProviderSettingsRepository(session=session, logger=logger)


def get_embedding_provider(
    logger: ILogger = Depends(get_logger),
) -> IEmbeddingProvider:
    """
    Dependency that injects the LiteLLM embedding adapter initialized with active_embedding_config.
    """
    return LiteLLMEmbeddingAdapter(config=active_embedding_config, logger=logger)


def get_fast_parser(logger: ILogger = Depends(get_logger)):
    import pymupdf
    from src.infra.pymupdf_parser import PyMuPDFParser

    return PyMuPDFParser(mupdf_client=pymupdf, logger=logger)


def get_vision_provider():
    from src.infra.llms.litellm_vision_adapter import LiteLLMVisionProvider
    from src.core.enums import ChatProvider

    vision_config = LLMRouteConfigDTO(
        provider=ChatProvider.OPENAI,
        model_name="gpt-4o",
        temperature=0.0,
    )
    return LiteLLMVisionProvider(config=vision_config)


def get_chunker(logger: ILogger = Depends(get_logger)) -> IChunker:
    from src.infra.chunkers.recursive_chunker import RecursiveChunkerAdapter

    return RecursiveChunkerAdapter(logger=logger)


def get_embedding_service(
    document_chunk_repo: IDocumentChunkRepository = Depends(get_document_chunk_repository),
    embedding_provider: IEmbeddingProvider = Depends(get_embedding_provider),
    logger: ILogger = Depends(get_logger),
) -> EmbeddingService:
    """
    Dependency that injects the EmbeddingService use case layer.
    """
    return EmbeddingService(
        document_chunk_repo=document_chunk_repo,
        embedding_provider=embedding_provider,
        logger=logger,
    )


def get_pdf_service(
    parser=Depends(get_fast_parser),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    chunk_repo: IDocumentChunkRepository = Depends(get_document_chunk_repository),
    doc_repo: IDocumentRepository = Depends(get_document_repository),
    vision_llm=Depends(get_vision_provider),
    logger: ILogger = Depends(get_logger),
    chunker: IChunker = Depends(get_chunker),
):
    from src.services.pdf_service import PDFService

    return PDFService(
        parser=parser,
        embedding_service=embedding_service,
        chunk_repo=chunk_repo,
        doc_repo=doc_repo,
        vision_llm=vision_llm,
        logger=logger,
        chunker=chunker,
    )


def get_encryption_service():
    """
    Dependency that provides the EncryptionService for securing API keys.
    """
    from src.services.encryption_service import EncryptionService

    return EncryptionService()


def get_http_client(
    logger: ILogger = Depends(get_logger),
):
    """
    Dependency that provides an instance of IHTTPClient backed by HttpxClient.
    """
    from src.infra.clients import httpx_client
    from src.infra.httpx_adapter import HttpxClient

    return HttpxClient(client=httpx_client.client, logger=logger)



def get_tts_provider(
    logger: ILogger = Depends(get_logger),
    http_client=Depends(get_http_client),
):
    """
    Dependency that provides the configured text-to-speech provider.
    """
    import os
    from src.infra.tts import OpenAITTSProvider

    return OpenAITTSProvider(
        api_key=os.getenv("OPENAI_API_KEY", ""),
        logger=logger,
        http_client=http_client,
    )


def get_llm_provider(
    logger: ILogger = Depends(get_logger),
):
    """
    Dependency that provides the default LiteLLMAdapter provider.
    """
    import os
    from src.infra.llms.litellm_adapter import LiteLLMAdapter
    from src.core.dtos.llm_provider_dtos import LLMRouteConfigDTO
    from src.core.enums import ChatProvider

    config = LLMRouteConfigDTO(
        provider=ChatProvider.OPENAI,
        model_name="gpt-4o-mini",
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    return LiteLLMAdapter(config=config, logger=logger)


def get_audio_script_prompt() -> str:
    """
    Dependency that provides the prompt template for generating audio scripts.
    """
    from src.core.prompts import AUDIO_SCRIPT_PROMPT_TEMPLATE

    return AUDIO_SCRIPT_PROMPT_TEMPLATE


def get_audio_explanation_service(
    pdf_service=Depends(get_pdf_service),
    llm_provider=Depends(get_llm_provider),
    tts_provider=Depends(get_tts_provider),
    script_prompt_template: str = Depends(get_audio_script_prompt),
):
    """
    Dependency that injects AudioExplanationService.
    """
    from src.services.audio_explanation_service import AudioExplanationService

    return AudioExplanationService(
        pdf_service=pdf_service,
        llm_provider=llm_provider,
        tts_provider=tts_provider,
        script_prompt_template=script_prompt_template,
    )


def get_cache_client(
    logger: ILogger = Depends(get_logger),
) -> ICacheClient:
    """
    Dependency that provides an instance of ICacheClient backed by RedisClient.
    Retrieves the client instance initialized in src.infra.clients.
    """
    from src.infra.clients import redis_client
    from src.infra.redis_adapter import RedisClient

    return RedisClient(client=redis_client.client, logger=logger)


def get_event_publisher(
    logger: ILogger = Depends(get_logger),
) -> IEventPublisher:
    """
    Dependency that provides an instance of IEventPublisher backed by CeleryEventPublisherAdapter.
    Retrieves the Celery app initialized in src.infra.clients.
    """
    from src.core.config import get_celery_settings
    from src.infra.clients.celery_client import celery_app
    from src.infra.celery_event_publisher_adapter import CeleryEventPublisherAdapter

    celery_settings = get_celery_settings()
    return CeleryEventPublisherAdapter(
        celery_app=celery_app,
        broker_url=celery_settings.broker_url,
        logger=logger,
    )


def get_object_repository(
    logger: ILogger = Depends(get_logger),
) -> IObjectRepository:
    """
    Dependency that provides an instance of IObjectRepository backed by MinioObjectRepository.
    Retrieves the session and configs initialized in src.infra.clients.
    """
    from src.core.config import get_minio_settings
    from src.infra.clients import minio_client
    from src.infra.repositories.minio_repository import MinioObjectRepository

    minio_settings = get_minio_settings()
    return MinioObjectRepository(
        session=minio_client.session,
        internal_config=minio_client.internal_config,
        external_config=minio_client.external_config,
        bucket_name=minio_settings.INCOMING_UPLOADS_BUCKET,
        logger=logger,
    )


def get_citation_service(
    chunk_repo: IDocumentChunkRepository = Depends(get_document_chunk_repository),
    doc_repo: IDocumentRepository = Depends(get_document_repository),
    logger: ILogger = Depends(get_logger),
):
    from src.services.citation_service import CitationService

    return CitationService(
        chunk_repo=chunk_repo,
        doc_repo=doc_repo,
        logger=logger,
    )


def get_antivirus_service() -> IAntivirusService:
    """
    Dependency that provides an instance of IAntivirusService backed by ClamAVAdapter.
    """
    import os
    import clamd
    from src.infra.clamav_adapter import ClamAVAdapter

    clamav_host = os.getenv("CLAMAV_HOST", "localhost")
    clamav_port = int(os.getenv("CLAMAV_PORT", "3310"))
    try:
        client = clamd.ClamdNetworkSocket(host=clamav_host, port=clamav_port, timeout=5.0)
    except Exception:
        client = None
    return ClamAVAdapter(client=client)


def get_thumbnail_service(
    storage: IObjectRepository = Depends(get_object_repository),
    logger: ILogger = Depends(get_logger),
    publisher: IEventPublisher = Depends(get_event_publisher),
):
    """
    Dependency that provides an instance of ThumbnailService.
    """
    from src.core.config import get_minio_settings
    from src.services.thumbnail_service import ThumbnailService

    return ThumbnailService(
        storage=storage,
        minio_settings=get_minio_settings(),
        logger=logger,
        publisher=publisher,
    )


def get_scan_service(
    antivirus: IAntivirusService = Depends(get_antivirus_service),
    storage: IObjectRepository = Depends(get_object_repository),
    logger: ILogger = Depends(get_logger),
    publisher: IEventPublisher = Depends(get_event_publisher),
):
    """
    Dependency that provides an instance of ScanService.
    """
    from src.core.config import get_minio_settings
    from src.services.scan_service import ScanService

    return ScanService(
        antivirus=antivirus,
        storage=storage,
        minio_settings=get_minio_settings(),
        logger=logger,
        publisher=publisher,
    )


def get_project_service(
    project_repo: IProjectRepository = Depends(get_project_repository),
    doc_repo: IDocumentRepository = Depends(get_document_repository),
    pdf_service=Depends(get_pdf_service),
    thumbnail_service=Depends(get_thumbnail_service),
    antivirus: IAntivirusService = Depends(get_antivirus_service),
    storage: IObjectRepository = Depends(get_object_repository),
    logger: ILogger = Depends(get_logger),
):
    """
    Dependency that provides an instance of ProjectService.
    """
    from src.core.config import get_minio_settings
    from src.services.project_service import ProjectService

    return ProjectService(
        project_repo=project_repo,
        doc_repo=doc_repo,
        pdf_service=pdf_service,
        thumbnail_service=thumbnail_service,
        antivirus=antivirus,
        storage=storage,
        minio_settings=get_minio_settings(),
        logger=logger,
    )


def get_provider_service(
    provider_settings_repo: IProviderSettingsRepository = Depends(get_provider_settings_repository),
    encryption_service=Depends(get_encryption_service),
    logger: ILogger = Depends(get_logger),
):
    """
    Dependency that provides an instance of ProviderService.
    """
    from src.services.provider_service import ProviderService

    return ProviderService(
        provider_settings_repo=provider_settings_repo,
        encryption_service=encryption_service,
        logger=logger,
    )


class CurrentUserDTO(BaseModel):
    provider_id: str = "00000000-0000-0000-0000-000000000000"


def get_current_user() -> CurrentUserDTO:
    """
    Mock/Default current user dependency.
    """
    return CurrentUserDTO()


def get_stream_notifications_use_case(
    logger: ILogger = Depends(get_logger),
):
    """
    Dependency providing NotificationService for user notification streams.
    """
    from src.infra.clients import redis_client
    from src.infra.redis_notification_adapter import RedisPubSubNotificationAdapter
    from src.services.notification_service import NotificationService

    adapter = RedisPubSubNotificationAdapter(redis_client=redis_client.client, logger=logger)
    return NotificationService(notification_service=adapter, logger=logger)


def get_chat_orchestrator(
    pdf_service=Depends(get_pdf_service),
    citation_service=Depends(get_citation_service),
    llm_provider=Depends(get_llm_provider),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    media_repo: IMediaRepository = Depends(get_media_repository),
) -> IChatOrchestrator:
    """
    Dependency that provides LangGraphChatOrchestrator wired with LangGraphToolFactory.
    """
    from src.infra.orchestrators.langgraph.adapter import LangGraphChatOrchestrator
    from src.infra.orchestrators.langgraph.tools.tool_factory import LangGraphToolFactory

    class _MediaSearcher:
        def __init__(self, emb_svc, m_repo):
            self._emb = emb_svc
            self._repo = m_repo

        async def search_media_chunks(self, query: str, media_id=None, limit: int = 3):
            q_vec = await self._emb.embed_text(query)
            return await self._repo.search_media_chunks_vector(query_vector=q_vec, media_id=media_id, limit=limit)

        async def expand_media_chunk_context(self, media_id, chunk_index: int, radius: int = 2):
            return await self._repo.get_media_chunks_in_context_window(media_id=media_id, target_chunk_index=chunk_index, radius=radius)

    media_searcher = _MediaSearcher(embedding_service, media_repo)
    tool_factory = LangGraphToolFactory(
        pdf_service=pdf_service,
        chat_service=media_searcher,
        citation_service=citation_service,
    )
    return LangGraphChatOrchestrator(
        tool_factory=tool_factory,
        llm_provider=llm_provider,
    )


def get_chat_service(
    storage: IObjectRepository = Depends(get_object_repository),
    media_repo: IMediaRepository = Depends(get_media_repository),
    notification_service: INotificationService = Depends(get_stream_notifications_use_case),
    logger: ILogger = Depends(get_logger),
    publisher: IEventPublisher = Depends(get_event_publisher),
    scan_service=Depends(get_scan_service),
    chunker: IChunker = Depends(get_chunker),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    parser: IFastParser = Depends(get_fast_parser),
    chat_repo: IChatRepository = Depends(get_chat_repository),
    message_repo: IMessageRepository = Depends(get_message_repository),
    project_repo: IProjectRepository = Depends(get_project_repository),
    orchestrator: IChatOrchestrator = Depends(get_chat_orchestrator),
    citation_service=Depends(get_citation_service),
):
    """
    Dependency that provides an instance of ChatService.
    """
    from src.core.config import get_minio_settings
    from src.services.chat_service import ChatService

    return ChatService(
        storage=storage,
        media_repo=media_repo,
        notification_service=notification_service,
        minio_settings=get_minio_settings(),
        logger=logger,
        publisher=publisher,
        scan_service=scan_service,
        chunker=chunker,
        embedding_service=embedding_service,
        parser=parser,
        chat_repo=chat_repo,
        message_repo=message_repo,
        project_repo=project_repo,
        orchestrator=orchestrator,
        citation_service=citation_service,
    )



