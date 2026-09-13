from typing import AsyncGenerator
import uuid

from src.core.enums import Role
from src.core.dtos.llm_provider_dtos import DomainMessageDTO
from src.core.interfaces.illm_provider import ILLMProvider
from src.core.interfaces.itts_provider import ITextToSpeechProvider
from src.core.prompts import AUDIO_SCRIPT_PROMPT_TEMPLATE
from src.services.pdf_service import PDFService


class AudioExplanationService:
    """Service orchestrating conversational audio explanations for document pages."""

    def __init__(
        self,
        pdf_service: PDFService,
        llm_provider: ILLMProvider,
        tts_provider: ITextToSpeechProvider,
        script_prompt_template: str = AUDIO_SCRIPT_PROMPT_TEMPLATE,
    ):
        self.pdf_service = pdf_service
        self.llm = llm_provider
        self.tts = tts_provider
        self.script_prompt_template = script_prompt_template

    async def _generate_script(self, prompt: str) -> str:
        """Invokes the LLM to generate the conversational spoken script."""
        response = await self.llm.generate_response(
            messages=[DomainMessageDTO(role=Role.USER, content=prompt)]
        )
        return response.message.content

    async def explain_page_audio(
        self,
        doc_id: uuid.UUID,
        page_num: int,
        voice: str = "alloy",
    ) -> AsyncGenerator[bytes, None]:
        """
        Fetches the requested document page, transforms its content into a conversational
        spoken script, and streams generated audio chunks back to the client.
        """
        # 1. Fetch the required page using the PDF service
        pages = await self.pdf_service.get_pages_in_range(
            doc_id, start_page=page_num, end_page=page_num
        )
        if not pages:
            raise FileNotFoundError(f"Page {page_num} not found for document {doc_id}")
        page = pages[0]

        # 2. Convert Markdown/Tables into a conversational script
        page_content = (
            getattr(page, "deep_content", None) or getattr(page, "content", None) or ""
        ).strip()
        script_prompt = self.script_prompt_template.format(page_content=page_content)

        script_text = await self._generate_script(script_prompt)

        # 3. Stream the audio bytes back to the caller
        async for audio_chunk in self.tts.stream_audio(script_text, voice=voice):
            yield audio_chunk

    async def synthesize_speech(
        self,
        text: str,
        voice: str = "alloy",
    ) -> AsyncGenerator[bytes, None]:
        """
        Takes raw text and streams generated audio chunks back to the client.
        """
        async for audio_chunk in self.tts.stream_audio(text, voice=voice):
            yield audio_chunk

