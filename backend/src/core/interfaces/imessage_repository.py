from abc import ABC, abstractmethod
import uuid
from typing import Sequence
from src.models.message import Message
from src.schemas.message import MessageWithAttachments


class IMessageRepository(ABC):
    """
    Interface for Message repository operations (Port).
    """

    @abstractmethod
    async def get_by_id(self, message_id: uuid.UUID) -> MessageWithAttachments | None:
        """
        Retrieve a message by its ID with attachments.
        """
        pass

    @abstractmethod
    async def list_by_chat(self, chat_id: uuid.UUID) -> Sequence[MessageWithAttachments]:
        """
        Retrieve all messages for a specific chat, ordered by creation time, with attachments.
        """
        pass

    @abstractmethod
    async def create(self, message: Message) -> MessageWithAttachments:
        """
        Save a new message and return it with attachments.
        """
        pass

    @abstractmethod
    async def delete(self, message_id: uuid.UUID) -> bool:
        """
        Delete a message by its ID.
        """
        pass

    @abstractmethod
    async def get_recent_history(self, chat_id: uuid.UUID, limit: int = 50) -> Sequence[MessageWithAttachments]:
        """
        Retrieve recent message history for a chat session, ordered chronologically, with attachments.
        """
        pass

    @abstractmethod
    async def get_image_captions(self, message_id: uuid.UUID) -> Sequence[str]:
        """
        Retrieve captions of associated image media (excluding media with chunks) for a message.
        """
        pass

