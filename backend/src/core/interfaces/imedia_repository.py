from abc import ABC, abstractmethod
import uuid
from typing import Sequence
from src.models.media import Media
from src.models.media_chunk import MediaChunk


class IMediaRepository(ABC):
    """
    Interface for Media repository operations (Port).
    """

    @abstractmethod
    async def get_by_id(self, media_id: uuid.UUID) -> Media | None:
        """
        Retrieve a media file by its ID.
        """
        pass

    @abstractmethod
    async def get_by_hash(self, file_hash: str) -> Media | None:
        """
        Retrieve a media record by its unique content hash (useful for duplicate detection).
        """
        pass

    @abstractmethod
    async def list_by_message(self, message_id: uuid.UUID) -> Sequence[Media]:
        """
        Retrieve all media attachments associated with a message.
        """
        pass

    @abstractmethod
    async def create(self, media: Media) -> Media:
        """
        Save a new media attachment record.
        """
        pass

    @abstractmethod
    async def update(self, media_id: uuid.UUID, **kwargs) -> Media:
        """
        Update an existing media record.
        """
        pass

    @abstractmethod
    async def delete(self, media_id: uuid.UUID) -> bool:
        """
        Delete a media attachment record.
        """
        pass

    @abstractmethod
    async def save_caption(self, media_id: uuid.UUID, text: str) -> Media:
        """
        Save or update the caption for a media item.
        """
        pass

    @abstractmethod
    async def get_media_ids_with_chunks(self) -> Sequence[uuid.UUID]:
        """
        Retrieve all media_ids of rows that have entries in media_chunks.
        """
        pass

    @abstractmethod
    async def bulk_create_chunks(
        self, chunks: Sequence[MediaChunk]
    ) -> Sequence[MediaChunk]:
        """
        Save a batch of media chunk records.
        """
        pass

    @abstractmethod
    async def search_media_chunks_vector(
        self,
        query_vector: list[float],
        media_id: uuid.UUID | Sequence[uuid.UUID] | None = None,
        limit: int = 3,
    ) -> Sequence[MediaChunk]:
        """
        Search media chunks ordered by cosine similarity to the query vector.
        Optionally filters by a single media_id or a sequence of media_ids.
        """
        pass

    @abstractmethod
    async def get_media_chunks_in_context_window(
        self,
        media_id: uuid.UUID,
        target_chunk_index: int,
        radius: int = 2,
    ) -> Sequence[MediaChunk]:
        """
        Retrieve chunks surrounding target_chunk_index within radius for a specific media_id.
        """
        pass



