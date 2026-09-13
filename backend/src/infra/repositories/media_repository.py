import uuid
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.core.interfaces.ilogger import ILogger
from src.core.interfaces.imedia_repository import IMediaRepository
from src.core.exceptions.database import (
    RepositoryError,
    MediaNotFoundError,
    DuplicateMediaError,
)
from src.models.media import Media
from src.models.media_chunk import MediaChunk


class MediaRepository(IMediaRepository):
    """
    SQLAlchemy implementation of the IMediaRepository for PostgreSQL.
    """

    def __init__(self, session: AsyncSession, logger: ILogger) -> None:
        self.session = session
        self.logger = logger

    async def get_by_id(self, media_id: uuid.UUID) -> Media | None:
        try:
            stmt = select(Media).where(Media.media_id == media_id)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            self.logger.error(
                "Database error retrieving media by ID",
                media_id=media_id,
                exc_info=e,
            )
            raise RepositoryError(f"Failed to retrieve media: {str(e)}") from e

    async def get_by_hash(self, file_hash: str) -> Media | None:
        try:
            stmt = select(Media).where(Media.file_hash == file_hash)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            self.logger.error(
                "Database error retrieving media by hash",
                file_hash=file_hash,
                exc_info=e,
            )
            raise RepositoryError(f"Failed to retrieve media by hash: {str(e)}") from e

    async def list_by_message(self, message_id: uuid.UUID) -> Sequence[Media]:
        try:
            stmt = (
                select(Media)
                .where(Media.message_id == message_id)
                .order_by(Media.uploaded_at.asc())
            )
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            self.logger.error(
                "Database error listing media for message",
                message_id=message_id,
                exc_info=e,
            )
            raise RepositoryError(f"Failed to list media: {str(e)}") from e

    async def create(self, media: Media) -> Media:
        try:
            self.session.add(media)
            await self.session.commit()
            await self.session.refresh(media)
            return media
        except IntegrityError as e:
            await self.session.rollback()
            self.logger.warning(
                "Media integrity violation on create",
                message_id=media.message_id,
                exc_info=e,
            )
            raise DuplicateMediaError("file_hash", media.file_hash) from e
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error(
                "Database error creating media",
                message_id=media.message_id,
                exc_info=e,
            )
            raise RepositoryError(f"Failed to create media: {str(e)}") from e

    async def update(self, media_id: uuid.UUID, **kwargs) -> Media:
        try:
            media = await self.get_by_id(media_id)
            if not media:
                raise MediaNotFoundError(media_id)

            for key, value in kwargs.items():
                if hasattr(media, key):
                    setattr(media, key, value)

            await self.session.commit()
            await self.session.refresh(media)
            return media
        except MediaNotFoundError:
            raise
        except IntegrityError as e:
            await self.session.rollback()
            self.logger.warning(
                "Media integrity violation on update",
                media_id=media_id,
                exc_info=e,
            )
            raise DuplicateMediaError("fields", str(kwargs)) from e
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error(
                "Database error updating media",
                media_id=media_id,
                exc_info=e,
            )
            raise RepositoryError(f"Failed to update media: {str(e)}") from e

    async def delete(self, media_id: uuid.UUID) -> bool:
        try:
            media = await self.get_by_id(media_id)
            if not media:
                return False

            await self.session.delete(media)
            await self.session.commit()
            return True
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error(
                "Database error deleting media",
                media_id=media_id,
                exc_info=e,
            )
            raise RepositoryError(f"Failed to delete media: {str(e)}") from e

    async def save_caption(self, media_id: uuid.UUID, text: str) -> Media:
        """
        Save or update the caption for a media item.
        """
        return await self.update(media_id, caption=text)

    async def get_media_ids_with_chunks(self) -> Sequence[uuid.UUID]:
        """
        Retrieve all media_ids of rows that have entries in media_chunks.
        """
        try:
            stmt = select(Media.media_id).where(
                (Media.has_chunks.is_(True))
                | (Media.media_id.in_(select(MediaChunk.media_id)))
            ).distinct()
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            self.logger.error(
                "Database error retrieving media IDs with chunks",
                exc_info=e,
            )
            raise RepositoryError(
                f"Failed to retrieve media IDs with chunks: {str(e)}"
            ) from e

    async def bulk_create_chunks(
        self, chunks: Sequence[MediaChunk]
    ) -> Sequence[MediaChunk]:
        """
        Save a batch of media chunk records.
        """
        try:
            self.session.add_all(chunks)
            await self.session.commit()
            return chunks
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error(
                "Database error bulk creating media chunks",
                exc_info=e,
            )
            raise RepositoryError(
                f"Failed to bulk create media chunks: {str(e)}"
            ) from e

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
        try:
            conditions = [MediaChunk.content_vector.isnot(None)]
            if isinstance(media_id, (list, tuple, set, Sequence)) and not isinstance(media_id, (str, bytes)):
                conditions.append(MediaChunk.media_id.in_(media_id))
            elif media_id is not None:
                conditions.append(MediaChunk.media_id == media_id)

            stmt = (
                select(MediaChunk)
                .where(*conditions)
                .order_by(MediaChunk.content_vector.cosine_distance(query_vector))
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            self.logger.error(
                "Database error during media chunks vector search",
                media_id=str(media_id) if media_id else None,
                exc_info=e,
            )
            raise RepositoryError(
                f"Media chunk vector search failed: {str(e)}"
            ) from e

    async def get_media_chunks_in_context_window(
        self,
        media_id: uuid.UUID,
        target_chunk_index: int,
        radius: int = 2,
    ) -> Sequence[MediaChunk]:
        """
        Retrieve chunks surrounding target_chunk_index within radius for a specific media_id.
        """
        try:
            min_index = max(0, target_chunk_index - radius)
            max_index = target_chunk_index + radius
            stmt = (
                select(MediaChunk)
                .where(
                    MediaChunk.media_id == media_id,
                    MediaChunk.chunk_index >= min_index,
                    MediaChunk.chunk_index <= max_index,
                )
                .order_by(MediaChunk.chunk_index.asc())
            )
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            self.logger.error(
                "Database error expanding media chunk context",
                media_id=media_id,
                target_chunk_index=target_chunk_index,
                radius=radius,
                exc_info=e,
            )
            raise RepositoryError(
                f"Failed to expand media chunk context: {str(e)}"
            ) from e



