import uuid
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.core.interfaces.ilogger import ILogger
from src.core.interfaces.imessage_repository import IMessageRepository
from src.core.exceptions.database import (
    RepositoryError,
    MessageNotFoundError,
    DuplicateMessageError,
)
from src.models.message import Message
from src.models.media import Media
from src.schemas.message import MessageWithAttachments


class MessageRepository(IMessageRepository):
    """
    SQLAlchemy implementation of the IMessageRepository for PostgreSQL.
    """

    def __init__(self, session: AsyncSession, logger: ILogger) -> None:
        self.session = session
        self.logger = logger

    async def get_by_id(self, message_id: uuid.UUID) -> MessageWithAttachments | None:
        try:
            stmt = (
                select(Message)
                .options(selectinload(Message.media))
                .where(Message.message_id == message_id)
            )
            result = await self.session.execute(stmt)
            message = result.scalar_one_or_none()
            if not message:
                return None
            return MessageWithAttachments.model_validate(message)
        except SQLAlchemyError as e:
            self.logger.error(
                "Database error retrieving message by ID",
                message_id=message_id,
                exc_info=e,
            )
            raise RepositoryError(f"Failed to retrieve message: {str(e)}") from e

    async def list_by_chat(self, chat_id: uuid.UUID) -> Sequence[MessageWithAttachments]:
        try:
            stmt = (
                select(Message)
                .options(selectinload(Message.media))
                .where(Message.chat_id == chat_id)
                .order_by(Message.created_at.asc())
            )
            result = await self.session.execute(stmt)
            messages = result.scalars().all()
            return [MessageWithAttachments.model_validate(msg) for msg in messages]
        except SQLAlchemyError as e:
            self.logger.error(
                "Database error listing messages for chat",
                chat_id=chat_id,
                exc_info=e,
            )
            raise RepositoryError(f"Failed to list messages: {str(e)}") from e

    async def create(self, message: Message) -> MessageWithAttachments:
        try:
            self.session.add(message)
            await self.session.commit()
            created = await self.get_by_id(message.message_id)
            if not created:
                raise RepositoryError(f"Failed to retrieve created message: {message.message_id}")
            return created
        except IntegrityError as e:
            await self.session.rollback()
            self.logger.warning(
                "Message integrity violation on create",
                chat_id=message.chat_id,
                exc_info=e,
            )
            raise DuplicateMessageError("message_id", message.message_id) from e
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error(
                "Database error creating message",
                chat_id=message.chat_id,
                exc_info=e,
            )
            raise RepositoryError(f"Failed to create message: {str(e)}") from e

    async def delete(self, message_id: uuid.UUID) -> bool:
        try:
            stmt = select(Message).where(Message.message_id == message_id)
            result = await self.session.execute(stmt)
            message = result.scalar_one_or_none()
            if not message:
                return False

            await self.session.delete(message)
            await self.session.commit()
            return True
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error(
                "Database error deleting message",
                message_id=message_id,
                exc_info=e,
            )
            raise RepositoryError(f"Failed to delete message: {str(e)}") from e

    async def get_recent_history(self, chat_id: uuid.UUID, limit: int = 50) -> Sequence[MessageWithAttachments]:
        try:
            # Query recent messages descending to get the last N, then reverse to output chronologically
            stmt = (
                select(Message)
                .options(selectinload(Message.media))
                .where(Message.chat_id == chat_id)
                .order_by(Message.created_at.desc())
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            messages = list(result.scalars().all())
            messages.reverse()
            return [MessageWithAttachments.model_validate(msg) for msg in messages]
        except SQLAlchemyError as e:
            self.logger.error(
                "Database error fetching recent message history",
                chat_id=chat_id,
                limit=limit,
                exc_info=e,
            )
            raise RepositoryError(f"Failed to fetch recent history: {str(e)}") from e

    async def get_image_captions(self, message_id: uuid.UUID) -> Sequence[str]:
        try:
            message = await self.get_by_id(message_id)
            if not message:
                return []
            return [att.caption for att in message.image_attachments if att.caption]
        except SQLAlchemyError as e:
            self.logger.error(
                "Database error retrieving image captions",
                message_id=message_id,
                exc_info=e,
            )
            raise RepositoryError(f"Failed to retrieve image captions: {str(e)}") from e

