from abc import ABC, abstractmethod
from typing import List


class IObjectRepository(ABC):
    @abstractmethod
    async def get_upload_url(
        self, object_name: str, expires_in_minutes: int = 60, bucket: str | None = None
    ) -> str:
        """Generates a presigned URL for a client to PUT a file directly."""
        pass

    @abstractmethod
    async def get_download_url(
        self, object_name: str, expires_in_minutes: int = 60, bucket: str | None = None
    ) -> str:
        """Generates a presigned URL for external services to GET a file."""
        pass

    @abstractmethod
    async def upload_object(
        self,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        bucket: str | None = None,
    ) -> None:
        """Directly upload bytes (useful for server-generated files)."""
        pass

    @abstractmethod
    async def download_object(
        self, object_name: str, bucket: str | None = None
    ) -> bytes:
        """Directly download bytes into memory."""
        pass

    @abstractmethod
    async def check_exists(self, object_name: str, bucket: str | None = None) -> bool:
        """Checks if an object exists in storage."""
        pass

    @abstractmethod
    async def delete_object(self, object_name: str, bucket: str | None = None) -> None:
        """Removes an object from storage."""
        pass

    @abstractmethod
    async def copy_object(
        self,
        source_key: str,
        destination_key: str,
        source_bucket: str | None = None,
        target_bucket: str | None = None,
    ) -> None:
        """Copies an object to a new location."""
        pass

    @abstractmethod
    async def list_objects(self, prefix: str, bucket: str | None = None) -> List[str]:
        """Lists all object names matching a specific prefix."""
        pass

    @abstractmethod
    def get_public_url(self, bucket: str, key: str) -> str:
        """Constructs a public URL for an object."""
        pass

    @abstractmethod
    def format_thumbnails_urls(
        self, thumbnails: dict[str, str] | None, bucket: str
    ) -> dict[str, str] | None:
        """Converts thumbnail paths to public URLs."""
        pass
