import uuid
from typing import AsyncGenerator
from src.core.interfaces.inotification_service import INotificationService
from src.core.interfaces.ilogger import ILogger


class NotificationService:
    def __init__(self, notification_service: INotificationService, logger: ILogger):
        self._notification_service = notification_service
        self._logger = logger

    async def execute(self, user_id: uuid.UUID) -> AsyncGenerator[str, None]:
        self._logger.info("Executing NotificationService", user_id=str(user_id))
        try:
            async for notification in self._notification_service.subscribe(user_id):
                yield notification
        except Exception as e:
            self._logger.error(
                "Error in NotificationService", user_id=str(user_id), exc=e
            )
            raise
