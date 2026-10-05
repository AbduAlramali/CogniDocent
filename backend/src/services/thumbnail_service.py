from typing import Dict, List, Optional
import uuid
import pymupdf as fitz

from src.core.config import MinioSettings
from src.core.dtos import ProcessEventDTO
from src.core.enums import UploadStatus
from src.core.exceptions.object_storage_exceptions import ObjectNotFoundError
from src.core.interfaces.ievent_publisher import IEventPublisher
from src.core.interfaces.ilogger import ILogger
from src.core.interfaces.imedia_repository import IMediaRepository
from src.core.interfaces.iobject_repository import IObjectRepository
from src.schemas.thumbnail import ThumbnailSpec


DEFAULT_SPECS = [
    ThumbnailSpec(name="small", width=128, height=128, shape="fit"),
    ThumbnailSpec(name="medium", width=256, height=256, shape="fit"),
    ThumbnailSpec(name="large", width=512, height=512, shape="fit"),
]


class ThumbnailService:
    """
    Downloads files from MinIO, generates thumbnails of different sizes,
    and uploads them to THUMBNAILS_BUCKET.
    Only processes PDFs and images. Skips TXT, DOCX, etc.
    Takes ProcessEventDTO as input and returns ProcessEventDTO.
    """

    def __init__(
        self,
        storage: IObjectRepository,
        minio_settings: MinioSettings,
        logger: ILogger,
        publisher: IEventPublisher,
        media_repo: IMediaRepository,
        specs: Optional[List[ThumbnailSpec]] = None,
    ) -> None:
        self.storage = storage
        self.minio_settings = minio_settings
        self.logger = logger
        self.publisher = publisher
        self.media_repo = media_repo
        self.specs = specs or list(DEFAULT_SPECS)

    async def generate_thumbnails(
        self,
        event: ProcessEventDTO,
        specs: Optional[List[ThumbnailSpec]] = None,
    ) -> ProcessEventDTO:
        """
        Downloads target file from MinIO, generates thumbnails,
        and uploads them to THUMBNAILS_BUCKET under folder `event.object_name/`.
        Returns the input ProcessEventDTO.
        """
        active_specs = specs or self.specs
        mime = (event.content_type or "").lower()

        # 1. Download file content from MinIO
        file_content = await self.storage.download_object(
            object_name=event.object_name,
            bucket=event.bucket_name,
        )
        if not file_content:
            raise ValueError(f"Empty file content for {event.object_name}")

        # 2. If it's a PDF, take the first page
        if mime == "application/pdf" or event.object_name.lower().endswith(".pdf"):
            thumbnails = self._generate_pdf_thumbnails(file_content, active_specs)

        # 3. If it's an image, resize it
        elif mime.startswith("image/"):
            thumbnails = self._generate_image_thumbnails(file_content, active_specs)

        # 4. Skip other formats (e.g. DOCX, XLSX, TXT, etc.)
        else:
            self.logger.info(
                "Skipping non-image/pdf format for thumbnails",
                object_name=event.object_name,
                content_type=mime,
            )
            await self.publisher.publish_event("chat_service.upload_confirm", event)
            return event

        if not thumbnails:
            await self.publisher.publish_event("chat_service.upload_confirm", event)
            return event

        # 5. Upload generated thumbnails to THUMBNAILS_BUCKET
        folder = event.object_name.strip("/")
        for tier, data in thumbnails.items():
            thumb_key = f"{folder}/{tier}.jpg"
            await self.storage.upload_object(
                object_name=thumb_key,
                data=data,
                content_type="image/jpeg",
                bucket=self.minio_settings.THUMBNAILS_BUCKET,
            )

        self.logger.info(
            "Uploaded thumbnails to MinIO",
            folder=folder,
            tiers=list(thumbnails.keys()),
        )

        # 6. Fire back to upload confirm
        await self.publisher.publish_event("chat_service.upload_confirm", event)

        return event

    def _render_page(self, page, spec: ThumbnailSpec, fmt: str = "jpg") -> bytes:
        rect = page.rect
        src_w, src_h = rect.width, rect.height
        if src_w <= 0 or src_h <= 0:
            return b""

        shape = (spec.shape or "fit").lower()
        if shape in ("crop", "square"):
            target_aspect = spec.width / spec.height
            src_aspect = src_w / src_h
            if src_aspect > target_aspect:
                new_w = src_h * target_aspect
                x0 = (src_w - new_w) / 2
                clip = fitz.Rect(x0, 0, x0 + new_w, src_h)
                scale = spec.height / src_h
            else:
                new_h = src_w / target_aspect
                y0 = (src_h - new_h) / 2
                clip = fitz.Rect(0, y0, src_w, y0 + new_h)
                scale = spec.width / src_w
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip)
        elif shape in ("fill", "exact"):
            scale_x = spec.width / src_w
            scale_y = spec.height / src_h
            pix = page.get_pixmap(matrix=fitz.Matrix(scale_x, scale_y))
        else:  # "fit" (preserving aspect ratio)
            scale = min(spec.width / src_w, spec.height / src_h)
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))

        return pix.tobytes(fmt)

    def _generate_pdf_thumbnails(
        self, file_content: bytes, specs: List[ThumbnailSpec]
    ) -> Dict[str, bytes]:
        thumbnails = {}
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            if len(doc) == 0:
                doc.close()
                return {}

            page = doc.load_page(0)
            for spec in specs:
                thumb = self._render_page(page, spec, fmt="jpg")
                if thumb:
                    thumbnails[spec.name] = thumb
            doc.close()
        except Exception as e:
            self.logger.error("Error generating PDF thumbnails", exc_info=e)

        return thumbnails

    def _generate_image_thumbnails(
        self, file_content: bytes, specs: List[ThumbnailSpec]
    ) -> Dict[str, bytes]:
        thumbnails = {}
        try:
            img = fitz.open(stream=file_content, filetype="image")
            if len(img) == 0:
                img.close()
                return {}

            page = img.load_page(0)
            for spec in specs:
                thumb = self._render_page(page, spec, fmt="jpg")
                if thumb:
                    thumbnails[spec.name] = thumb
            img.close()
        except Exception as e:
            self.logger.error("Error generating image thumbnails", exc_info=e)

        return thumbnails

    async def get_attachment_thumbnail_url(
        self,
        media_id: uuid.UUID,
        tier: str = "small",
        expires_in_minutes: int = 60,
    ) -> str:
        """
        Generates a presigned download URL for a specific thumbnail tier of an attachment.
        """
        media = await self.media_repo.get_by_id(media_id)
        if not media:
            raise ObjectNotFoundError(f"Attachment '{media_id}' was not found.")

        thumbnails = media.thumbnails or {}
        thumb_key = thumbnails.get(tier)
        if not thumb_key:
            raise ObjectNotFoundError(
                f"Thumbnail tier '{tier}' not found for attachment '{media_id}'."
            )

        return await self.storage.get_download_url(
            object_name=thumb_key,
            expires_in_minutes=expires_in_minutes,
            bucket=self.minio_settings.THUMBNAILS_BUCKET,
        )

    async def get_attachment_thumbnail_urls(
        self,
        media_id: uuid.UUID,
        expires_in_minutes: int = 60,
    ) -> Dict[str, str]:
        """
        Generates presigned download URLs for all thumbnail tiers of an attachment.
        """
        media = await self.media_repo.get_by_id(media_id)
        if not media:
            raise ObjectNotFoundError(f"Attachment '{media_id}' was not found.")

        thumbnails = media.thumbnails or {}
        if not thumbnails:
            return {}

        presigned_urls: Dict[str, str] = {}
        for tier_name, key in thumbnails.items():
            presigned_urls[tier_name] = await self.storage.get_download_url(
                object_name=key,
                expires_in_minutes=expires_in_minutes,
                bucket=self.minio_settings.THUMBNAILS_BUCKET,
            )
        return presigned_urls

