import uuid
import asyncio
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from src.dependencies import get_stream_notifications_use_case, get_current_user
from src.services.notification_service import (
    NotificationService,
)
from src.core.dtos.notification_dto import NotificationDTO

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "/stream",
    summary="SSE Real-Time Notifications",
    description="""
    Establishes a persistent Server-Sent Events (SSE) connection to receive real-time notifications.
    The stream remains open until the client disconnects or the server shuts down.
    Notifications are pushed automatically as they occur in the background (e.g., document processing updates).
    """,
    responses={
        200: {
            "description": "Successfully established SSE connection. Each event data chunk is a NotificationDTO.",
            "model": NotificationDTO,
            "content": {"text/event-stream": {}},
        },
        401: {"description": "Unauthorized: Missing or invalid session token."},
        500: {
            "description": "Internal Server Error: Failed to establish subscription."
        },
    },
)
async def notification_stream(
    request: Request,
    current_user=Depends(get_current_user),
    stream_use_case: NotificationService = Depends(get_stream_notifications_use_case),
):
    """
    Establishes an SSE connection. Listens to the user's specific notifications.
    """

    async def event_generator():
        # current_user.provider_id is a string, we need UUID for the use case
        user_uuid = uuid.UUID(current_user.provider_id)

        # Get the async generator for notifications
        notification_gen = stream_use_case.execute(user_uuid)

        # We use a task for the next notification to avoid cancelling it on timeout
        next_notification_task = asyncio.create_task(notification_gen.__anext__())

        try:
            while True:
                # Check if client is still connected
                if await request.is_disconnected():
                    break

                # Wait for next notification or timeout to send heartbeat
                done, _ = await asyncio.wait(
                    [next_notification_task],
                    timeout=30.0,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if next_notification_task in done:
                    try:
                        notification = next_notification_task.result()
                        if isinstance(notification, bytes):
                            notification = notification.decode("utf-8")
                        yield f"data: {notification}\n\n"
                        # Start the next notification task
                        next_notification_task = asyncio.create_task(
                            notification_gen.__anext__()
                        )
                    except StopAsyncIteration:
                        break
                    except Exception:
                        # On error, we stop
                        break
                else:
                    # Send SSE comment as heartbeat
                    yield ": heartbeat\n\n"
        finally:
            # Ensure the task is cancelled if we exit the loop
            if not next_notification_task.done():
                next_notification_task.cancel()
                try:
                    await next_notification_task
                except (asyncio.CancelledError, StopAsyncIteration):
                    pass
                except Exception:
                    pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Recommended for Nginx proxying SSE
        },
    )
