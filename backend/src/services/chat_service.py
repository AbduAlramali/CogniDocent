import asyncio
import base64
import hashlib
from pathlib import Path
from typing import List, Sequence
import uuid

from src.core.config import MinioSettings, get_ai_settings
from src.core.dtos.event_dtos import ProcessEventDTO
from src.core.dtos.llm_provider_dtos import (
    DomainMessageDTO,
    EmbeddingConfigDTO,
    LLMRouteConfigDTO,
    SystemAIConfigDTO,
)
from src.core.dtos.notification_dto import NotificationDTO, NotificationType
from src.core.dtos.parser_dtos import PageContentDTO
from src.core.dtos.chunk_dto import ChunkDTO
from src.core.dtos.universal_dtos import ThreadStateDTO
from src.core.enums import ChatProvider, EmbeddingProvider, FileType, Role, ScanStatus, UploadStatus
from src.core.exceptions.chat_exceptions import (
    EmptyFileContentError,
    FileHashMismatchError,
    InvalidEventDataError,
)
from src.core.exceptions.database import ChatNotFoundError, ProjectNotFoundError
from src.core.interfaces.ichat_orchestrator import IChatOrchestrator
from src.core.interfaces.ichat_repository import IChatRepository
from src.core.interfaces.ievent_publisher import IEventPublisher
from src.core.interfaces.ilogger import ILogger
from src.core.interfaces.imedia_repository import IMediaRepository
from src.core.interfaces.imessage_repository import IMessageRepository
from src.core.interfaces.inotification_service import INotificationService
from src.core.interfaces.iobject_repository import IObjectRepository
from src.core.interfaces.ichunker import IChunker
from src.core.interfaces.ifast_parser import IFastParser
from src.core.interfaces.iproject_repository import IProjectRepository
from src.models.chat import Chat
from src.models.media import Media
from src.models.media_chunk import MediaChunk
from src.models.message import Message
from src.schemas.message import MessageWithAttachments
from src.services.embedding_service import EmbeddingService
from src.services.scan_service import ScanService
from src.services.citation_service import CitationService


class ChatService:
    """
    Service handling chat attachments uploads, media lifecycle,
    and user interactions.
    """

    def __init__(
        self,
        storage: IObjectRepository,
        media_repo: IMediaRepository,
        notification_service: INotificationService,
        minio_settings: MinioSettings,
        logger: ILogger,
        publisher: IEventPublisher,
        scan_service: ScanService,
        chunker: IChunker,
        embedding_service: EmbeddingService,
        parser: IFastParser,
        chat_repo: IChatRepository,
        message_repo: IMessageRepository,
        project_repo: IProjectRepository,
        orchestrator: IChatOrchestrator,
        citation_service: CitationService,
    ) -> None:
        self.storage = storage
        self.media_repo = media_repo
        self.notification_service = notification_service
        self.minio_settings = minio_settings
        self.logger = logger
        self.publisher = publisher
        self.scan_service = scan_service
        self.chunker = chunker
        self.embedding_service = embedding_service
        self.parser = parser
        self.chat_repo = chat_repo
        self.message_repo = message_repo
        self.project_repo = project_repo
        self.orchestrator = orchestrator
        self.citation_service = citation_service

    async def upload_attachment(
        self,
        file_stream: bytes,
        filename: str,
        content_type: str,
        project_id: str,
        file_hash: str,
    ) -> Media:
        """
        Receives stream of bytes, saves to incoming uploads bucket,
        verifies computed hash matches client file_hash,
        creates media record in database, moves object to quarantine bucket
        with name equal to its uuid in the db (uuid.file_extension),
        and fires a task to ScanService.
        """
        self.logger.info(
            "Receiving attachment upload",
            filename=filename,
            content_type=content_type,
            project_id=project_id,
        )

        # 1. Validate not empty
        if not file_stream:
            raise EmptyFileContentError(filename)

        file_bytes = file_stream
        file_size = len(file_bytes)

        # 2. Upload to incoming uploads bucket
        temp_id = uuid.uuid4()
        incoming_key = f"incoming_{temp_id}_{filename}"
        await self.storage.upload_object(
            object_name=incoming_key,
            data=file_bytes,
            content_type=content_type,
            bucket=self.minio_settings.INCOMING_UPLOADS_BUCKET,
        )

        # 3. Compute hash and verify match with client provided hash
        computed_hash = hashlib.sha256(file_bytes).hexdigest()
        if computed_hash.lower() != file_hash.lower():
            self.logger.error(
                "File hash mismatch on attachment upload",
                filename=filename,
                provided_hash=file_hash,
                computed_hash=computed_hash,
            )
            # Remove uploaded object from incoming bucket on validation failure
            await self.storage.delete_object(
                object_name=incoming_key,
                bucket=self.minio_settings.INCOMING_UPLOADS_BUCKET,
            )
            raise FileHashMismatchError(
                filename=filename,
                expected_hash=file_hash,
                computed_hash=computed_hash,
            )

        # 4. Create Media record in DB (status=PROCESSING, message_id=None)
        media_id = uuid.uuid4()
        file_ext = Path(filename).suffix
        quarantine_key = f"{media_id}{file_ext}"

        media = Media(
            media_id=media_id,
            message_id=None,
            filename=filename,
            file_path=quarantine_key,
            file_size_bytes=file_size,
            file_hash=computed_hash,
            content_type=content_type,
            status=UploadStatus.PROCESSING,
        )
        saved_media = await self.media_repo.create(media)

        # 5. Move object from incoming bucket to quarantine bucket (uuid.file_extension)
        await self.storage.copy_object(
            source_key=incoming_key,
            destination_key=quarantine_key,
            source_bucket=self.minio_settings.INCOMING_UPLOADS_BUCKET,
            target_bucket=self.minio_settings.QUARANTINE_BUCKET,
        )
        await self.storage.delete_object(
            object_name=incoming_key,
            bucket=self.minio_settings.INCOMING_UPLOADS_BUCKET,
        )

        self.logger.info(
            "Attachment moved to quarantine and registered in database",
            media_id=str(media_id),
            quarantine_key=quarantine_key,
        )

        # 6. Fire task to ScanService
        event = ProcessEventDTO(
            project_id=str(project_id),
            file_type=FileType.ATTACHMENT,
            bucket_name=self.minio_settings.QUARANTINE_BUCKET,
            object_name=quarantine_key,
            scan_status=None,
            is_safe=None,
            content_type=content_type,
            media_id=media_id,
        )

        await self.publisher.publish_event("scan_service.scan_file", event)

        return saved_media

    async def upload_confirm(self, event: ProcessEventDTO) -> Media:
        """
        Handles post-processing confirmation from ScanService / ThumbnailService.
        Updates Media record status and notifies the user via NotificationService.
        """
        self.logger.info(
            "Received upload confirmation",
            object_name=event.object_name,
            scan_status=event.scan_status,
            is_safe=event.is_safe,
            project_id=event.project_id,
            media_id=str(event.media_id) if event.media_id else None,
        )

        # 1. Require media_id in DTO (do not fallback)
        if not event.media_id:
            self.logger.error(
                "Missing media_id in ProcessEventDTO",
                object_name=event.object_name,
            )
            raise InvalidEventDataError(
                f"ProcessEventDTO for object '{event.object_name}' is missing required media_id."
            )

        media_id = event.media_id

        # 2. Determine upload status and payload
        is_safe = event.is_safe is True and event.scan_status == ScanStatus.CLEAN

        update_kwargs = {
            "status": UploadStatus.COMPLETED if is_safe else UploadStatus.INFECTED,
            "file_path": event.object_name,
        }

        # Populate thumbnails map if file is image or PDF
        content_type = event.content_type
        if is_safe and (
            content_type.startswith("image/") or content_type == "application/pdf"
        ):
            folder = event.object_name.strip("/")
            update_kwargs["thumbnails"] = {
                "small": f"{folder}/small.jpg",
                "medium": f"{folder}/medium.jpg",
                "large": f"{folder}/large.jpg",
            }

        updated_media = await self.media_repo.update(media_id, **update_kwargs)

        # 3. Notify user via INotificationService (keyed by project_id)
        target_id = uuid.UUID(str(event.project_id))

        if is_safe:
            notification = NotificationDTO(
                type=NotificationType.ATTACHMENT_READY,
                message=f"Attachment {media_id} is safe and ready to use.",
                project_id=str(event.project_id),
                data={"media_id": str(media_id), "status": "clean"},
            )
        else:
            notification = NotificationDTO(
                type=NotificationType.ATTACHMENT_MALICIOUS,
                message=f"Attachment {media_id} failed security scan and was flagged as infected.",
                project_id=str(event.project_id),
                data={"media_id": str(media_id), "status": "infected"},
            )

        await self.notification_service.notify_user(
            user_id=target_id,
            payload=notification,
        )

        self.logger.info(
            "User notified of attachment status",
            media_id=str(media_id),
            is_safe=is_safe,
            project_id=event.project_id,
        )

        # 4. Chunk and embed attachment if safe, not an image, and can be chunked
        if is_safe and self._can_chunk_attachment(event.content_type, event.object_name):
            await self.chunk_and_embed_attachment(event)
            updated_media.has_chunks = True

        return updated_media

    def _is_image(self, content_type: str, filename: str) -> bool:
        mime = (content_type or "").lower()
        fn = (filename or "").lower()
        image_extensions = {
            ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".tiff", ".ico"
        }
        return mime.startswith("image/") or any(fn.endswith(ext) for ext in image_extensions)

    def _can_chunk_attachment(self, content_type: str, filename: str) -> bool:
        if self._is_image(content_type, filename):
            return False
        mime = (content_type or "").lower()
        fn = (filename or "").lower()
        if mime == "application/pdf" or fn.endswith(".pdf"):
            return True
        if mime.startswith("text/"):
            return True
        chunkable_extensions = {
            ".pdf", ".txt", ".md", ".markdown", ".json", ".csv", ".py", ".js",
            ".ts", ".html", ".htm", ".xml", ".yaml", ".yml", ".log", ".rst",
            ".sql", ".env", ".sh", ".ini", ".conf",
        }
        chunkable_mimes = {
            "application/json", "application/xml", "application/javascript",
            "application/x-yaml", "application/csv",
        }
        return mime in chunkable_mimes or any(fn.endswith(ext) for ext in chunkable_extensions)

    async def chunk_and_embed_attachment(
        self, event: ProcessEventDTO
    ) -> Sequence[MediaChunk]:
        """
        Processes safe, non-image chunkable attachments:
        - If PDF: parses document pages using IFastParser.
        - If other text-based file: reads raw text directly skipping PDF parsing.
        - Passes pages/text to IChunker to split into chunks.
        - Calls EmbeddingService to generate vector embeddings.
        - Uploads resulting MediaChunk records to media_chunks database table.
        - Updates Media.has_chunks = True.
        """
        media_id = event.media_id
        if not media_id:
            raise InvalidEventDataError("Missing media_id for chunking attachment.")

        bucket = event.bucket_name or self.minio_settings.TRUSTED_BUCKET
        file_bytes = await self.storage.download_object(
            object_name=event.object_name,
            bucket=bucket,
        )
        if not file_bytes:
            self.logger.warning(
                "Empty file downloaded for attachment chunking",
                object_name=event.object_name,
                media_id=str(media_id),
            )
            return []

        mime = (event.content_type or "").lower()
        fn = (event.object_name or "").lower()
        is_pdf = mime == "application/pdf" or fn.endswith(".pdf")

        pages: List[PageContentDTO] = []
        if is_pdf:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                tmp_file.write(file_bytes)
                tmp_path = tmp_file.name
            try:
                parsed_doc = await asyncio.to_thread(self.parser.extract_document, tmp_path)
                pages = parsed_doc.pages
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        else:
            text = file_bytes.decode("utf-8", errors="replace")
            pages = [
                PageContentDTO(
                    page_num=1,
                    raw_text=text,
                    char_count=len(text),
                    has_images=False,
                    has_tables_hint=False,
                )
            ]

        chunk_dtos = self.chunker.chunk_pages(pages)
        if not chunk_dtos:
            self.logger.info(
                "No chunks generated for attachment",
                media_id=str(media_id),
            )
            return []

        texts = [c.content for c in chunk_dtos]
        embeddings = await self.embedding_service.embed_batch(texts)

        media_chunks = [
            MediaChunk(
                chunk_id=uuid.uuid4(),
                media_id=media_id,
                chunk_index=c.chunk_index,
                content=c.content,
                content_vector=emb,
                chunk_metadata={"page_num": c.page_num},
            )
            for c, emb in zip(chunk_dtos, embeddings)
        ]

        saved_chunks = await self.media_repo.bulk_create_chunks(media_chunks)
        await self.media_repo.update(media_id, has_chunks=True)

        self.logger.info(
            "Uploaded media chunks for attachment",
            media_id=str(media_id),
            chunk_count=len(saved_chunks),
        )
        return saved_chunks

    async def search_media_chunks(
        self,
        query: str,
        media_id: uuid.UUID | Sequence[uuid.UUID] | None = None,
        limit: int = 3,
    ) -> Sequence[MediaChunk]:
        """
        Semantic vector search across media chunks.
        Computes query embedding via EmbeddingService and retrieves nearest chunks from media repository.
        Optionally filters by a single media_id or sequence of media_ids.
        """
        if not query or not query.strip():
            return []

        query_vector = await self.embedding_service.embed_text(query)
        chunks = await self.media_repo.search_media_chunks_vector(
            query_vector=query_vector,
            media_id=media_id,
            limit=limit,
        )
        return chunks

    async def expand_media_chunk_context(
        self,
        media_id: uuid.UUID,
        chunk_index: int,
        radius: int = 2,
    ) -> Sequence[MediaChunk]:
        """
        Retrieves sequential media chunks surrounding target chunk_index within radius.
        Used for semantic navigation when a vector search hits the middle of a concept.
        """
        chunks = await self.media_repo.get_media_chunks_in_context_window(
            media_id=media_id,
            target_chunk_index=chunk_index,
            radius=radius,
        )
        return chunks

    async def chat_completion(
        self,
        project_id: uuid.UUID,
        message: str,
        chat_id: uuid.UUID | None = None,
        attachment_ids: Sequence[uuid.UUID] | None = None,
        config: SystemAIConfigDTO | None = None,
    ) -> MessageWithAttachments:
        """
        Executes a turn in the chat session:
        1. Validates project, creates or loads chat.
        2. Saves user's message and links any attachment_ids.
        3. Retrieves chat history and appends captions to prior user messages.
        4. Encodes current turn images as Base64 data URLs for the LLM.
        5. Collects active non-image attachments across the chat for RAG tools.
        6. Runs orchestrator turn.
        7. Persists generated captions to media repository.
        8. Saves assistant message to DB, updates chat title if generated, and returns response.
        """
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise ProjectNotFoundError(project_id)

        generate_chat_title = chat_id is None
        if not chat_id:
            chat = await self.chat_repo.create(
                Chat(
                    chat_id=uuid.uuid4(),
                    project_id=project_id,
                    title="New Title",
                    ai_provider=ChatProvider.OPENAI,
                    ai_model="gpt-4o-mini",
                )
            )
            chat_id = chat.chat_id
        else:
            chat = await self.chat_repo.get_by_id(chat_id)
            if not chat:
                raise ChatNotFoundError(chat_id)

        user_msg = Message(
            message_id=uuid.uuid4(),
            chat_id=chat_id,
            role=Role.USER.value,
            content=message,
        )
        await self.message_repo.create(user_msg)

        new_attachments = [
            await self.media_repo.update(att_id, message_id=user_msg.message_id)
            for att_id in (attachment_ids or [])
        ]

        all_history = await self.message_repo.list_by_chat(chat_id)
        prior_history = [m for m in all_history if m.message_id != user_msg.message_id]

        history_messages = [
            DomainMessageDTO(role=Role.ASSISTANT, content=m.content)
            if m.role == Role.ASSISTANT.value
            else DomainMessageDTO(
                role=Role.USER,
                content=(
                    f"{m.content}\n"
                    + "\n".join(
                        f"[Image: {att.caption}]"
                        if att.caption
                        else "[Prior image attachment removed to save context]"
                        for att in m.image_attachments
                    )
                    if m.image_attachments
                    else m.content
                ),
            )
            for m in prior_history
        ]

        new_images = [
            att for att in new_attachments if self._is_image(att.content_type, att.filename)
        ]
        image_urls = []
        for img in new_images:
            img_bytes = await self.storage.download_object(
                object_name=img.file_path,
                bucket=self.minio_settings.TRUSTED_BUCKET,
            )
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            image_urls.append(f"data:{img.content_type};base64,{b64}")

        domain_user_msg = DomainMessageDTO(
            role=Role.USER,
            content=message,
            images=image_urls,
        )

        active_attachments = list(
            dict.fromkeys(
                att.media_id
                for m in all_history
                for att in m.doc_attachments
            )
        )
        images_to_caption = [img.media_id for img in new_images if not img.caption]

        ai_settings = get_ai_settings()
        system_config = config or SystemAIConfigDTO(
            active_chat_model=LLMRouteConfigDTO(
                provider=chat.ai_provider,
                model_name=chat.ai_model,
            ),
            embedding_config=EmbeddingConfigDTO(
                provider=EmbeddingProvider.OPENAI,
                model_name=ai_settings.DEFAULT_EMBEDDING_MODEL,
                dimensions=ai_settings.DEFAULT_EMBEDDING_DIMENSIONS,
            ),
            vision_model=LLMRouteConfigDTO(
                provider=ChatProvider.OPENAI,
                model_name=ai_settings.DEFAULT_VISION_MODEL,
            ),
        )

        thread_state = ThreadStateDTO(
            project_id=project_id,
            document_id=project.doc_id,
            config=system_config,
            active_attachments=active_attachments,
            generate_chat_title=generate_chat_title,
        )

        response = await self.orchestrator.process_turn(
            thread_id=chat_id,
            user_message=domain_user_msg,
            config=thread_state,
            history_messages=history_messages,
            images_to_caption=images_to_caption,
        )

        captions_tuple = response.metadata.get("generated_captions", ())
        for i in range(0, len(captions_tuple), 2):
            media_id_str, caption_text = captions_tuple[i], captions_tuple[i + 1]
            await self.media_repo.save_caption(uuid.UUID(str(media_id_str)), caption_text)

        raw_text, citations = await self.citation_service.build_citations(
            text=response.message.content,
            doc_id=project.doc_id,
        )

        citations_payload = [
            {
                "ref_id": c.ref_id,
                "page": c.page,
                "bbox": c.bbox,
                "source_name": c.source_name,
            }
            for c in citations
        ]

        assistant_msg = Message(
            message_id=uuid.uuid4(),
            chat_id=chat_id,
            role=Role.ASSISTANT.value,
            content=raw_text,
            citations=citations_payload if citations_payload else None,
            ai_provider=chat.ai_provider,
            ai_model=chat.ai_model,
            token_count=response.input_tokens + response.output_tokens,
        )
        saved_response = await self.message_repo.create(assistant_msg)

        if generate_chat_title and response.metadata.get("generated_chat_title"):
            await self.chat_repo.update(
                chat_id, title=response.metadata["generated_chat_title"]
            )

        return saved_response

    async def list_chats(
        self, project_id: uuid.UUID, include_archived: bool = False
    ) -> Sequence[Chat]:
        """
        Retrieves all chat sessions for the specified project.
        """
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise ProjectNotFoundError(project_id)
        return await self.chat_repo.list_by_project(
            project_id=project_id, include_archived=include_archived
        )

    async def delete_chat(self, chat_id: uuid.UUID) -> bool:
        """
        Deletes a chat session by ID.
        """
        chat = await self.chat_repo.get_by_id(chat_id)
        if not chat:
            raise ChatNotFoundError(chat_id)
        return await self.chat_repo.delete(chat_id)

    async def list_messages(
        self, chat_id: uuid.UUID
    ) -> Sequence[MessageWithAttachments]:
        """
        Retrieves all messages with attachments for a specific chat.
        """
        chat = await self.chat_repo.get_by_id(chat_id)
        if not chat:
            raise ChatNotFoundError(chat_id)
        return await self.message_repo.list_by_chat(chat_id)


