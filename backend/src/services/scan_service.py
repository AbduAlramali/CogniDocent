import asyncio
import io
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from src.core.config import MinioSettings
from src.core.dtos import ProcessEventDTO
from src.core.enums import ScanStatus
from src.core.interfaces.iantivirus_service import IAntivirusService
from src.core.interfaces.ievent_publisher import IEventPublisher
from src.core.interfaces.ilogger import ILogger
from src.core.interfaces.iobject_repository import IObjectRepository


class ScanService:
    """
    Service responsible for scanning uploaded files in quarantine storage,
    moving them to the trusted bucket if clean, or the infected bucket if malicious.
    Takes ProcessEventDTO as input and returns the updated ProcessEventDTO.
    """

    def __init__(
        self,
        antivirus: IAntivirusService,
        storage: IObjectRepository,
        minio_settings: MinioSettings,
        logger: ILogger,
        publisher: IEventPublisher,
        max_workers: int = 10,
    ) -> None:
        self.antivirus = antivirus
        self.storage = storage
        self.minio_settings = minio_settings
        self.logger = logger
        self.publisher = publisher
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    async def scan_file(self, event: ProcessEventDTO) -> ProcessEventDTO:
        """
        Scans a file from quarantine, moves it to either trusted or infected bucket,
        and returns the updated ProcessEventDTO.
        """
        src_bucket = event.bucket_name or self.minio_settings.QUARANTINE_BUCKET

        self.logger.info(
            "Starting antivirus scan for file",
            object_name=event.object_name,
            source_bucket=src_bucket,
        )

        # 1. Download file bytes from quarantine storage
        file_bytes = await self.storage.download_object(
            object_name=event.object_name,
            bucket=src_bucket,
        )

        # 2. Run antivirus scan in thread pool to avoid blocking async event loop
        loop = asyncio.get_running_loop()
        file_stream = io.BytesIO(file_bytes)
        is_clean = await loop.run_in_executor(
            self._executor,
            self.antivirus.scan_file,
            file_stream,
        )

        # 3. Determine destination bucket and status
        if is_clean:
            target_bucket = self.minio_settings.TRUSTED_BUCKET
            status = ScanStatus.CLEAN
        else:
            target_bucket = self.minio_settings.INFECTED_BUCKET
            status = ScanStatus.INFECTED

        self.logger.info(
            "Antivirus scan finished",
            object_name=event.object_name,
            is_clean=is_clean,
            status=status.value,
            target_bucket=target_bucket,
        )

        # 4. Move file from quarantine to target bucket (copy + delete)
        await self.storage.copy_object(
            source_key=event.object_name,
            destination_key=event.object_name,
            source_bucket=src_bucket,
            target_bucket=target_bucket,
        )
        await self.storage.delete_object(
            object_name=event.object_name,
            bucket=src_bucket,
        )

        # 5. Update ProcessEventDTO
        event.bucket_name = target_bucket
        event.scan_status = status
        event.is_safe = is_clean

        # 6. Fire next task
        if is_clean:
            await self.publisher.publish_event(
                "thumbnail_service.generate_thumbnails", event
            )
        else:
            await self.publisher.publish_event("chat_service.upload_confirm", event)

        return event

    def shutdown(self, wait: bool = False) -> None:
        """Shuts down the internal thread pool executor."""
        self._executor.shutdown(wait=wait)

    def __del__(self) -> None:
        self.shutdown(wait=False)

