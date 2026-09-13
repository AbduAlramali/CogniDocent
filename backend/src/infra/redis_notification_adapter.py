import uuid
import asyncio
from typing import AsyncGenerator
from redis.asyncio import Redis
from src.core.interfaces.inotification_service import INotificationService
from src.core.interfaces.ilogger import ILogger
from src.core.dtos.notification_dto import NotificationDTO


from src.core.exceptions.notification_exceptions import (
    NotificationSendError,
    NotificationSubscriptionError,
)


class RedisPubSubNotificationAdapter(INotificationService):
    """
    Adapter injected with the global Redis client.
    """

    def __init__(self, redis_client: Redis, logger: ILogger):
        self._redis = redis_client
        self._logger = logger

    async def notify_user(self, user_id: uuid.UUID, payload: NotificationDTO):
        self._logger.info("Publishing notification to user", user_id=str(user_id))
        channel_name = f"user_notifications:{user_id}"
        try:
            await self._redis.publish(channel_name, payload.model_dump_json())
            self._logger.info(
                "Notification published successfully", user_id=str(user_id)
            )
        except Exception as e:
            self._logger.error(
                "Failed to publish notification to Redis", user_id=str(user_id), exc=e
            )
            raise NotificationSendError("Failed to publish notification.") from e

    async def subscribe(self, user_id: uuid.UUID) -> AsyncGenerator[str, None]:
        pubsub = self._redis.pubsub()
        channel_name = f"user_notifications:{user_id}"

        try:
            await pubsub.subscribe(channel_name)
            self._logger.info(
                "Subscribed to notification channel", channel=channel_name
            )
        except Exception as e:
            self._logger.error(
                "Failed to subscribe to Redis channel", channel=channel_name, exc=e
            )
            raise NotificationSubscriptionError(
                f"Failed to subscribe to {channel_name}"
            ) from e

        try:
            while True:
                # Get message from Redis (with a small timeout)
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )

                if message is not None:
                    yield message["data"]

                await asyncio.sleep(0.1)  # Yield control to the event loop
        except asyncio.CancelledError:
            self._logger.info("Subscription cancelled", channel=channel_name)
            raise
        except Exception as e:
            self._logger.error(
                "Error during notification subscription", channel=channel_name, exc=e
            )
            raise NotificationSubscriptionError(
                "Error during notification streaming."
            ) from e
        finally:
            self._logger.info(
                "Unsubscribing from notification channel", channel=channel_name
            )
            try:
                await pubsub.unsubscribe(channel_name)
                await pubsub.close()
            except Exception as e:
                self._logger.warning("Failed to close pubsub cleanly", exc=e)
