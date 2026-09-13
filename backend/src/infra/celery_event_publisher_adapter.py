import asyncio
import time
from typing import Optional
from celery import Celery
from src.core.interfaces.ievent_publisher import IEventPublisher
from src.core.interfaces.ilogger import ILogger
from src.core.dtos import BaseEventDTO
from src.core.exceptions.event_publisher_exceptions import EventPublisherError
from kombu import Exchange


class CeleryEventPublisherAdapter(IEventPublisher):
    """
    Concrete implementation of IEventPublisher using Celery.
    """

    def __init__(self, celery_app: Celery, broker_url: str, logger: ILogger):
        self._celery_app = celery_app
        self._exchange = Exchange("main_exchange", type="topic")
        self._broker_url = broker_url
        self._logger = logger

    async def publish_event(self, topic: str, payload: BaseEventDTO) -> Optional[str]:
        """
        Publishes an event as a Celery task using send_task, ensuring compatibility
        with the target microservice's task names.
        Returns the unique task ID.
        """
        self._logger.info("Attempting to publish event task", topic=topic)
        data = payload.model_dump(mode="json")
        try:
            # We use send_task to trigger a Celery task in the target worker.
            # We pass the specific exchange and routing key requested.
            result = self._celery_app.send_task(
                name=topic,
                args=[data],
                exchange=self._exchange.name,
                routing_key=topic,
                retry=True,
            )
            self._logger.info(
                "Event task published successfully", topic=topic, task_id=result.id
            )
            return result.id
        except Exception as exc:
            self._logger.error(
                "Failed to publish event task to broker", topic=topic, exc=exc
            )
            raise EventPublisherError("Failed to publish event task.") from exc

    async def wait_for_tasks(
        self, task_ids: list[str], timeout: float = 10.0
    ) -> dict[str, bool]:
        """
        Polls Celery for the status of multiple task IDs until they are all
        finished or the timeout is reached.
        """
        if not task_ids:
            return {}

        self._logger.info(
            "Waiting for background tasks to complete", count=len(task_ids)
        )
        results = {}
        pending_ids = set(task_ids)
        start_time = time.time()

        while pending_ids and (time.time() - start_time) < timeout:
            for tid in list(pending_ids):
                res = self._celery_app.AsyncResult(tid)
                state = res.state
                if res.ready():
                    results[tid] = res.successful()
                    pending_ids.remove(tid)
                    self._logger.info(
                        "Background task completed",
                        task_id=tid,
                        state=state,
                        success=results[tid],
                    )
                else:
                    # Optional: Log periodically or just stay silent
                    pass

            if pending_ids:
                await asyncio.sleep(0.5)

        # For anything still pending after timeout, mark as False (incomplete)
        for tid in pending_ids:
            res = self._celery_app.AsyncResult(tid)
            results[tid] = False
            self._logger.warning(
                "Task wait timed out", task_id=tid, last_state=res.state
            )

        return results
