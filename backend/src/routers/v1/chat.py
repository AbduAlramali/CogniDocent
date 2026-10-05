from typing import Any, Dict, List, Optional
import uuid
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Path,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import RedirectResponse

from src.dependencies import (
    get_chat_service,
    get_thumbnail_service,
)
from src.schemas.chat import ChatCompletionRequest, ChatResponse
from src.schemas.media import MediaResponse
from src.schemas.message import MessageWithAttachments
from src.services.chat_service import ChatService
from src.services.thumbnail_service import ThumbnailService

router = APIRouter(prefix="/chats", tags=["Chats"])


@router.get(
    "",
    response_model=List[ChatResponse],
    status_code=status.HTTP_200_OK,
    summary="List Chats",
    description="""
    Retrieves all chat sessions associated with a specific project, ordered by creation time.
    """,
    responses={
        200: {
            "description": "Successfully retrieved list of chats for the project.",
            "model": List[ChatResponse],
        },
        404: {"description": "Not Found: Project ID does not exist."},
    },
)
async def list_chats(
    project_id: uuid.UUID = Query(..., description="UUID of the project to retrieve chats for"),
    include_archived: bool = Query(default=False, description="Include archived chats"),
    chat_service: ChatService = Depends(get_chat_service),
) -> List[ChatResponse]:
    chats = await chat_service.list_chats(project_id=project_id, include_archived=include_archived)
    return [ChatResponse.model_validate(c) for c in chats]


@router.delete(
    "/{chat_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Chat",
    description="""
    Permanently deletes a chat session and all its associated messages and attachment references.
    """,
    responses={
        204: {"description": "Chat successfully deleted."},
        404: {"description": "Not Found: Chat ID does not exist."},
    },
)
async def delete_chat(
    chat_id: uuid.UUID = Path(..., description="UUID of the chat session to delete"),
    chat_service: ChatService = Depends(get_chat_service),
) -> None:
    await chat_service.delete_chat(chat_id)


@router.post(
    "/completion",
    response_model=MessageWithAttachments,
    status_code=status.HTTP_200_OK,
    summary="Chat Completion",
    description="""
    Creates or sends a new message to a chat and returns the assistant response with inline citations
    and citation metadata. If chat_id is omitted from the request, a new chat session is created automatically.
    """,
    responses={
        200: {
            "description": "Assistant response successfully generated with inline citations and metadata.",
            "model": MessageWithAttachments,
        },
        404: {"description": "Not Found: Chat or Project does not exist."},
        500: {"description": "Internal Server Error: LLM or retrieval orchestration failure."},
    },
)
async def chat_completion(
    body: ChatCompletionRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> MessageWithAttachments:
    return await chat_service.chat_completion(
        project_id=body.project_id,
        chat_id=body.chat_id,
        message=body.message,
        attachment_ids=body.attachment_ids,
    )


@router.post(
    "/attachments",
    response_model=MediaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Chat Attachment",
    description="""
    Uploads an image or document attachment to the chat. Validates the SHA-256 hash against
    the uploaded bytes, registers a media record in PROCESSING status, transfers the file
    to quarantine storage, and fires an asynchronous event to scan and chunk the attachment.
    Once processed, the attachment_id can be passed to chat completion.
    """,
    responses={
        201: {
            "description": "Attachment uploaded successfully and queued for processing.",
            "model": MediaResponse,
        },
        400: {"description": "Bad Request: Empty file content or hash mismatch."},
    },
)
async def upload_attachment(
    file: UploadFile = File(..., description="Attachment file stream"),
    project_id: uuid.UUID = Form(..., description="UUID of the project"),
    file_hash: str = Form(..., description="Client-computed SHA-256 hex digest of the file"),
    chat_service: ChatService = Depends(get_chat_service),
) -> MediaResponse:
    content = await file.read()
    media = await chat_service.upload_attachment(
        file_stream=content,
        filename=file.filename or "attachment",
        content_type=file.content_type or "application/octet-stream",
        project_id=str(project_id),
        file_hash=file_hash,
    )
    return MediaResponse.model_validate(media)


@router.get(
    "/attachments/{media_id}/thumbnails",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Get Attachment Thumbnails",
    description="Returns presigned download URLs for all available thumbnail tiers of an attachment.",
    responses={
        200: {
            "description": "Presigned download URLs for each thumbnail tier.",
            "model": Dict[str, str],
        },
        404: {"description": "Attachment not found."},
    },
)
async def get_attachment_thumbnails(
    media_id: uuid.UUID = Path(..., description="UUID of the media attachment"),
    thumbnail_service: ThumbnailService = Depends(get_thumbnail_service),
) -> Dict[str, str]:
    return await thumbnail_service.get_attachment_thumbnail_urls(media_id)


@router.get(
    "/attachments/{media_id}/thumbnail",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    summary="Download Attachment Thumbnail",
    description="Redirects to the presigned download URL for the requested thumbnail tier.",
    responses={
        307: {"description": "Redirects to the presigned download URL in object storage."},
        404: {"description": "Attachment or requested thumbnail tier not found."},
    },
)
async def download_attachment_thumbnail(
    media_id: uuid.UUID = Path(..., description="UUID of the media attachment"),
    tier: str = Query(default="small", description="Thumbnail tier: small, medium, large"),
    thumbnail_service: ThumbnailService = Depends(get_thumbnail_service),
) -> RedirectResponse:
    url = await thumbnail_service.get_attachment_thumbnail_url(media_id, tier=tier)
    response = RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response
