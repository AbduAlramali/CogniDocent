from pydantic import BaseModel, Field


class SynthesizeSpeechRequest(BaseModel):
    """
    Request schema for synthesizing speech audio from plain text.
    """
    text: str = Field(..., min_length=1, description="Text to synthesize into speech")
    voice: str = Field(default="alloy", description="TTS voice name (e.g. alloy, echo, fable, onyx, nova, shimmer)")
