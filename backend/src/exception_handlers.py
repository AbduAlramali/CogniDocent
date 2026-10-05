from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.exceptions.antivirus_exceptions import AntivirusError
from src.core.exceptions.cache_exceptions import CacheClientError
from src.core.exceptions.chat_exceptions import ChatServiceError
from src.core.exceptions.chat_orchestrator_exceptions import (
    ChatSessionStateError,
    OrchestrationError,
    OrchestrationTimeoutError,
)
from src.core.exceptions.database import (
    DuplicateEntityError,
    EntityNotFoundError,
    RepositoryError,
)
from src.core.exceptions.document_exceptions import DocumentError
from src.core.exceptions.embedding_exceptions import (
    EmbeddingContextLengthExceededError,
    EmbeddingDimensionMismatchError,
    EmbeddingProviderError,
    EmbeddingRateLimitError,
)
from src.core.exceptions.event_publisher_exceptions import EventPublisherError
from src.core.exceptions.fast_parser_exceptions import (
    DocumentNotFoundError as ParserDocumentNotFoundError,
    FastParserError,
    ParserResourceLimitError,
)
from src.core.exceptions.encryption_exceptions import EncryptionError
from src.core.exceptions.http_exceptions import HTTPClientError, HTTPTimeoutError
from src.core.exceptions.keystore_exceptions import KeyStoreError
from src.core.exceptions.llm_provider_exceptions import (
    LLMContextLimitExceededError,
    LLMProviderError,
    LLMRateLimitError,
    LocalModelNotFoundError,
)
from src.core.exceptions.logger_exceptions import LoggerError
from src.core.exceptions.notification_exceptions import NotificationError
from src.core.exceptions.object_storage_exceptions import (
    ObjectNotFoundError,
    ObjectRepositoryError,
)
from src.core.exceptions.tts_exceptions import (
    TTSProviderError,
    TTSRateLimitError,
    TTSVoiceNotFoundError,
)
from src.core.interfaces.ilogger import ILogger


def register_exception_handlers(app: FastAPI, logger: ILogger) -> None:
    """
    Registers comprehensive global exception handlers for the FastAPI application.
    """

    # 404 - Not Found
    @app.exception_handler(EntityNotFoundError)
    async def entity_not_found_handler(
        request: Request, exc: EntityNotFoundError
    ) -> JSONResponse:
        logger.warning(f"Entity not found on path {request.url.path}: {str(exc)}")
        return JSONResponse(status_code=404, content={"message": str(exc)})

    @app.exception_handler(ObjectNotFoundError)
    async def object_not_found_handler(
        request: Request, exc: ObjectNotFoundError
    ) -> JSONResponse:
        logger.warning(f"Object not found on path {request.url.path}: {str(exc)}")
        return JSONResponse(status_code=404, content={"message": str(exc)})

    @app.exception_handler(ParserDocumentNotFoundError)
    async def parser_document_not_found_handler(
        request: Request, exc: ParserDocumentNotFoundError
    ) -> JSONResponse:
        logger.warning(f"Document not found on path {request.url.path}: {str(exc)}")
        return JSONResponse(status_code=404, content={"message": str(exc)})

    @app.exception_handler(TTSVoiceNotFoundError)
    async def tts_voice_not_found_handler(
        request: Request, exc: TTSVoiceNotFoundError
    ) -> JSONResponse:
        logger.warning(f"TTS voice not found on path {request.url.path}: {str(exc)}")
        return JSONResponse(status_code=404, content={"message": str(exc)})

    @app.exception_handler(FileNotFoundError)
    async def file_not_found_handler(
        request: Request, exc: FileNotFoundError
    ) -> JSONResponse:
        logger.warning(f"File not found on path {request.url.path}: {str(exc)}")
        return JSONResponse(status_code=404, content={"message": str(exc)})

    @app.exception_handler(LocalModelNotFoundError)
    async def local_model_not_found_handler(
        request: Request, exc: LocalModelNotFoundError
    ) -> JSONResponse:
        logger.warning(
            f"Local model not found on path {request.url.path}: {str(exc)}"
        )
        return JSONResponse(status_code=404, content={"message": str(exc)})

    # 409 - Conflict
    @app.exception_handler(DuplicateEntityError)
    async def duplicate_entity_handler(
        request: Request, exc: DuplicateEntityError
    ) -> JSONResponse:
        logger.warning(f"Duplicate entity on path {request.url.path}: {str(exc)}")
        return JSONResponse(status_code=409, content={"message": str(exc)})

    # 400 - Bad Request
    @app.exception_handler(ValueError)
    async def value_error_handler(
        request: Request, exc: ValueError
    ) -> JSONResponse:
        logger.warning(f"Value error on path {request.url.path}: {str(exc)}")
        return JSONResponse(status_code=400, content={"message": str(exc)})

    @app.exception_handler(ChatServiceError)
    async def chat_service_error_handler(
        request: Request, exc: ChatServiceError
    ) -> JSONResponse:
        logger.warning(f"Chat service error on path {request.url.path}: {str(exc)}")
        return JSONResponse(status_code=400, content={"message": str(exc)})

    @app.exception_handler(DocumentError)
    async def document_error_handler(
        request: Request, exc: DocumentError
    ) -> JSONResponse:
        logger.warning(f"Document error on path {request.url.path}: {str(exc)}")
        return JSONResponse(status_code=400, content={"message": str(exc)})

    @app.exception_handler(ChatSessionStateError)
    async def chat_session_state_error_handler(
        request: Request, exc: ChatSessionStateError
    ) -> JSONResponse:
        logger.warning(f"Chat session state error on path {request.url.path}: {str(exc)}")
        return JSONResponse(status_code=400, content={"message": str(exc)})

    @app.exception_handler(LLMContextLimitExceededError)
    async def llm_context_limit_handler(
        request: Request, exc: LLMContextLimitExceededError
    ) -> JSONResponse:
        logger.warning(
            f"LLM context limit exceeded on path {request.url.path}: {str(exc)}"
        )
        return JSONResponse(status_code=400, content={"message": str(exc)})

    @app.exception_handler(EmbeddingContextLengthExceededError)
    async def embedding_context_length_handler(
        request: Request, exc: EmbeddingContextLengthExceededError
    ) -> JSONResponse:
        logger.warning(
            f"Embedding context length exceeded on path {request.url.path}: {str(exc)}"
        )
        return JSONResponse(status_code=400, content={"message": str(exc)})

    @app.exception_handler(EmbeddingDimensionMismatchError)
    async def embedding_dim_mismatch_handler(
        request: Request, exc: EmbeddingDimensionMismatchError
    ) -> JSONResponse:
        logger.warning(
            f"Embedding dimension mismatch on path {request.url.path}: {str(exc)}"
        )
        return JSONResponse(status_code=400, content={"message": str(exc)})

    # 413 - Payload Too Large
    @app.exception_handler(ParserResourceLimitError)
    async def parser_resource_limit_handler(
        request: Request, exc: ParserResourceLimitError
    ) -> JSONResponse:
        logger.warning(
            f"Parser resource limit exceeded on path {request.url.path}: {str(exc)}"
        )
        return JSONResponse(status_code=413, content={"message": str(exc)})

    # 422 - Unprocessable Entity / Validation
    @app.exception_handler(FastParserError)
    async def fast_parser_error_handler(
        request: Request, exc: FastParserError
    ) -> JSONResponse:
        logger.warning(f"Fast parser error on path {request.url.path}: {str(exc)}")
        return JSONResponse(status_code=422, content={"message": str(exc)})

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warning(f"Validation error on path {request.url.path}: {str(exc)}")
        return JSONResponse(
            status_code=422,
            content={"message": "Validation error", "details": exc.errors()},
        )

    # 429 - Rate Limit
    @app.exception_handler(LLMRateLimitError)
    async def llm_rate_limit_handler(
        request: Request, exc: LLMRateLimitError
    ) -> JSONResponse:
        logger.warning(f"LLM rate limit reached on path {request.url.path}: {str(exc)}")
        return JSONResponse(status_code=429, content={"message": str(exc)})

    @app.exception_handler(EmbeddingRateLimitError)
    async def embedding_rate_limit_handler(
        request: Request, exc: EmbeddingRateLimitError
    ) -> JSONResponse:
        logger.warning(
            f"Embedding rate limit reached on path {request.url.path}: {str(exc)}"
        )
        return JSONResponse(status_code=429, content={"message": str(exc)})

    @app.exception_handler(TTSRateLimitError)
    async def tts_rate_limit_handler(
        request: Request, exc: TTSRateLimitError
    ) -> JSONResponse:
        logger.warning(f"TTS rate limit reached on path {request.url.path}: {str(exc)}")
        return JSONResponse(status_code=429, content={"message": str(exc)})

    # 504 - Gateway Timeout
    @app.exception_handler(OrchestrationTimeoutError)
    async def orchestration_timeout_handler(
        request: Request, exc: OrchestrationTimeoutError
    ) -> JSONResponse:
        logger.error(
            f"Orchestration timeout on path {request.url.path}: {str(exc)}", exc=exc
        )
        return JSONResponse(status_code=504, content={"message": str(exc)})

    @app.exception_handler(HTTPTimeoutError)
    async def http_timeout_handler(
        request: Request, exc: HTTPTimeoutError
    ) -> JSONResponse:
        logger.error(
            f"HTTP timeout on path {request.url.path}: {str(exc)}", exc=exc
        )
        return JSONResponse(status_code=504, content={"message": str(exc)})

    # 502 - Bad Gateway
    @app.exception_handler(LLMProviderError)
    async def llm_provider_error_handler(
        request: Request, exc: LLMProviderError
    ) -> JSONResponse:
        logger.error(
            f"LLM provider error on path {request.url.path}: {str(exc)}", exc=exc
        )
        return JSONResponse(status_code=502, content={"message": str(exc)})

    @app.exception_handler(EmbeddingProviderError)
    async def embedding_provider_error_handler(
        request: Request, exc: EmbeddingProviderError
    ) -> JSONResponse:
        logger.error(
            f"Embedding provider error on path {request.url.path}: {str(exc)}", exc=exc
        )
        return JSONResponse(status_code=502, content={"message": str(exc)})

    @app.exception_handler(TTSProviderError)
    async def tts_provider_error_handler(
        request: Request, exc: TTSProviderError
    ) -> JSONResponse:
        logger.error(
            f"TTS provider error on path {request.url.path}: {str(exc)}", exc=exc
        )
        return JSONResponse(status_code=502, content={"message": str(exc)})

    @app.exception_handler(HTTPClientError)
    async def http_client_error_handler(
        request: Request, exc: HTTPClientError
    ) -> JSONResponse:
        logger.error(
            f"HTTP client error on path {request.url.path}: {str(exc)}", exc=exc
        )
        return JSONResponse(status_code=502, content={"message": str(exc)})

    # 500 - Domain Infrastructure Errors
    @app.exception_handler(RepositoryError)
    async def repository_error_handler(
        request: Request, exc: RepositoryError
    ) -> JSONResponse:
        logger.error(
            f"Database error on path {request.url.path}: {str(exc)}", exc=exc
        )
        return JSONResponse(
            status_code=500, content={"message": "A database error occurred."}
        )

    @app.exception_handler(KeyStoreError)
    async def keystore_error_handler(
        request: Request, exc: KeyStoreError
    ) -> JSONResponse:
        logger.error(
            f"Key store error on path {request.url.path}: {str(exc)}", exc=exc
        )
        return JSONResponse(
            status_code=500, content={"message": "A key store error occurred."}
        )

    @app.exception_handler(EncryptionError)
    async def encryption_error_handler(
        request: Request, exc: EncryptionError
    ) -> JSONResponse:
        logger.error(
            f"Encryption error on path {request.url.path}: {str(exc)}", exc=exc
        )
        return JSONResponse(
            status_code=500, content={"message": "An encryption error occurred."}
        )

    @app.exception_handler(ObjectRepositoryError)
    async def object_repo_error_handler(
        request: Request, exc: ObjectRepositoryError
    ) -> JSONResponse:
        logger.error(
            f"Storage error on path {request.url.path}: {str(exc)}", exc=exc
        )
        return JSONResponse(
            status_code=500, content={"message": "A storage error occurred."}
        )

    @app.exception_handler(NotificationError)
    async def notification_error_handler(
        request: Request, exc: NotificationError
    ) -> JSONResponse:
        logger.error(
            f"Notification error on path {request.url.path}: {str(exc)}", exc=exc
        )
        return JSONResponse(
            status_code=500, content={"message": "A notification error occurred."}
        )

    @app.exception_handler(OrchestrationError)
    async def orchestration_error_handler(
        request: Request, exc: OrchestrationError
    ) -> JSONResponse:
        logger.error(
            f"Orchestration error on path {request.url.path}: {str(exc)}", exc=exc
        )
        return JSONResponse(
            status_code=500, content={"message": "An orchestration error occurred."}
        )

    @app.exception_handler(AntivirusError)
    async def antivirus_error_handler(
        request: Request, exc: AntivirusError
    ) -> JSONResponse:
        logger.error(
            f"Antivirus error on path {request.url.path}: {str(exc)}", exc=exc
        )
        return JSONResponse(
            status_code=500,
            content={"message": "A security scanning error occurred."},
        )

    @app.exception_handler(EventPublisherError)
    async def event_publisher_error_handler(
        request: Request, exc: EventPublisherError
    ) -> JSONResponse:
        logger.error(
            f"Event publisher error on path {request.url.path}: {str(exc)}", exc=exc
        )
        return JSONResponse(
            status_code=500,
            content={"message": "An event publishing error occurred."},
        )

    @app.exception_handler(CacheClientError)
    async def cache_client_error_handler(
        request: Request, exc: CacheClientError
    ) -> JSONResponse:
        logger.error(
            f"Cache error on path {request.url.path}: {str(exc)}", exc=exc
        )
        return JSONResponse(
            status_code=500, content={"message": "A cache error occurred."}
        )

    @app.exception_handler(LoggerError)
    async def logger_exception_handler(
        request: Request, exc: LoggerError
    ) -> JSONResponse:
        logger.error(f"Logger error occurred: {str(exc)}", exc=exc)
        return JSONResponse(
            status_code=500, content={"message": "Internal logging error."}
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content={"message": exc.detail}
        )

    # General catch-all to prevent app crashing on unhandled exceptions
    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(
            f"Unhandled exception occurred on path {request.url.path}: {str(exc)}",
            exc=exc,
        )
        return JSONResponse(
            status_code=500,
            content={"message": "An unexpected internal server error occurred."},
        )
