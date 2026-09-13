from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from src.dependencies import get_audio_explanation_service
from src.schemas.tts import SynthesizeSpeechRequest
from src.services.audio_explanation_service import AudioExplanationService

router = APIRouter(prefix="/tts", tags=["TTS"])


@router.post(
    "/synthesize",
    status_code=status.HTTP_200_OK,
    summary="Synthesize Speech",
    description="""
    Synthesizes speech from input text and streams the resulting audio bytes directly to the frontend.
    """,
    responses={
        200: {
            "description": "Audio stream generated successfully.",
            "content": {"audio/mpeg": {}},
        },
        400: {"description": "Bad Request: Empty text or invalid parameters."},
        500: {"description": "Internal Server Error: TTS provider failure."},
    },
)
async def synthesize_speech(
    body: SynthesizeSpeechRequest,
    audio_service: AudioExplanationService = Depends(get_audio_explanation_service),
) -> StreamingResponse:
    return StreamingResponse(
        audio_service.synthesize_speech(text=body.text, voice=body.voice),
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": "inline",
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
