from typing import Optional
from abc import ABC, abstractmethod
from src.core.dtos import BaseEventDTO


class IEventPublisher(ABC):
    """
    Abstract contract for publishing events to a message broker.
    """

    @abstractmethod
    async def publish_event(self, topic: str, payload: BaseEventDTO) -> Optional[str]:
        pass

    @abstractmethod
    async def wait_for_tasks(
        self, task_ids: list[str], timeout: float = 10.0
    ) -> dict[str, bool]:
        """
        Waits for a list of Celery tasks to complete.
        Returns a mapping of task_id to success status.
        """
        pass
