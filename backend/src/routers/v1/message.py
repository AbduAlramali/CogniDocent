from typing import List
import uuid
from fastapi import APIRouter, Depends, Path, status

from src.dependencies import get_chat_service
from src.schemas.message import MessageWithAttachments
from src.services.chat_service import ChatService

router = APIRouter(prefix="/chats", tags=["Messages"])


@router.get(
    "/{chat_id}/messages",
    response_model=List[MessageWithAttachments],
    status_code=status.HTTP_200_OK,
    summary="List Messages",
    description="""
    Retrieves all messages for a specific chat session in chronological order,
    including attachments and citations.
    """,
    responses={
        200: {
            "description": "Successfully retrieved list of messages.",
            "model": List[MessageWithAttachments],
        },
        404: {"description": "Not Found: Chat ID does not exist."},
    },
)
async def list_messages(
    chat_id: uuid.UUID = Path(..., description="UUID of the chat session"),
    chat_service: ChatService = Depends(get_chat_service),
) -> List[MessageWithAttachments]:
    return await chat_service.list_messages(chat_id)
