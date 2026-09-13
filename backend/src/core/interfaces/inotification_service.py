from abc import ABC, abstractmethod
import uuid
from typing import AsyncGenerator
from src.core.dtos.notification_dto import NotificationDTO


class INotificationService(ABC):
    """
    Abstract contract for sending notifications to users.
    """

    @abstractmethod
    async def notify_user(self, user_id: uuid.UUID, payload: NotificationDTO):
        """Sends a real-time notification to a specific user."""
        pass

    @abstractmethod
    async def subscribe(self, user_id: uuid.UUID) -> AsyncGenerator[str, None]:
        """Subscribes to notifications for a specific user and yields them."""
        pass
