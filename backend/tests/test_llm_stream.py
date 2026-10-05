import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import AIMessageChunk
from langchain_core.language_models.chat_models import BaseChatModel

from src.core.dtos.llm_provider_dtos import DomainMessageDTO, StreamChunkDTO
from src.core.enums import Role
from src.core.exceptions.llm_provider_exceptions import (
    LLMAuthenticationError,
    LLMContextLimitExceededError,
    LLMRateLimitError,
    LocalModelNotFoundError,
)
from src.core.interfaces.ilogger import ILogger
from src.infra.llms.base_langchain_adapter import BaseLangChainLLMAdapter


class DummyAdapter(BaseLangChainLLMAdapter):
    pass


@pytest.mark.asyncio
async def test_stream_response_yields_stream_chunk_dto():
    mock_model = MagicMock(spec=BaseChatModel)
    mock_logger = MagicMock(spec=ILogger)

    # Mock astream generator
    async def fake_astream(*args, **kwargs):
        chunk1 = AIMessageChunk(content="Hello ")
        chunk2 = AIMessageChunk(
            content="world!",
            response_metadata={"finish_reason": "stop"}
        )
        yield chunk1
        yield chunk2

    mock_model.astream = fake_astream

    adapter = DummyAdapter(model=mock_model, provider_name="dummy", logger=mock_logger)

    messages = [DomainMessageDTO(role=Role.USER, content="Hi")]
    chunks = []
    async for chunk in adapter.stream_response(messages):
        chunks.append(chunk)

    assert len(chunks) == 2
    assert isinstance(chunks[0], StreamChunkDTO)
    assert chunks[0].content_delta == "Hello "
    assert chunks[0].finish_reason is None

    assert isinstance(chunks[1], StreamChunkDTO)
    assert chunks[1].content_delta == "world!"
    assert chunks[1].finish_reason == "stop"


@pytest.mark.asyncio
async def test_ollama_model_not_found_translates_to_local_model_not_found_error():
    mock_model = MagicMock(spec=BaseChatModel)
    mock_model.model = "llama3:8b"
    mock_logger = MagicMock(spec=ILogger)

    mock_model.ainvoke = AsyncMock(
        side_effect=Exception("model 'llama3:8b' not found, try pulling it first")
    )

    adapter = DummyAdapter(model=mock_model, provider_name="Ollama", logger=mock_logger)
    messages = [DomainMessageDTO(role=Role.USER, content="Hello")]

    with pytest.raises(LocalModelNotFoundError) as exc_info:
        await adapter.generate_response(messages)

    assert "llama3:8b" in str(exc_info.value)
    assert "not downloaded" in str(exc_info.value)


@pytest.mark.asyncio
async def test_external_model_auth_failure_translates_to_llm_authentication_error():
    mock_model = MagicMock(spec=BaseChatModel)
    mock_model.model = "gpt-4o"
    mock_logger = MagicMock(spec=ILogger)

    mock_model.ainvoke = AsyncMock(
        side_effect=Exception("Incorrect API_KEY provided or unauthorized access")
    )

    adapter = DummyAdapter(model=mock_model, provider_name="OpenAI", logger=mock_logger)
    messages = [DomainMessageDTO(role=Role.USER, content="Hello")]

    with pytest.raises(LLMAuthenticationError) as exc_info:
        await adapter.generate_response(messages)

    assert "Authentication failed for provider: OpenAI" in str(exc_info.value)


@pytest.mark.asyncio
async def test_rate_limit_and_context_limit_static_exceptions():
    mock_model = MagicMock(spec=BaseChatModel)
    mock_model.model = "claude-3-5-sonnet"
    mock_logger = MagicMock(spec=ILogger)

    adapter = DummyAdapter(model=mock_model, provider_name="Anthropic", logger=mock_logger)
    messages = [DomainMessageDTO(role=Role.USER, content="Hello")]

    # Rate limit error
    mock_model.ainvoke = AsyncMock(side_effect=Exception("Rate limit 429 quota exceeded"))
    with pytest.raises(LLMRateLimitError) as exc_info:
        await adapter.generate_response(messages)
    assert "Rate limit exceeded" in str(exc_info.value)

    # Context limit error
    mock_model.ainvoke = AsyncMock(side_effect=Exception("Context length exceeded token limit"))
    with pytest.raises(LLMContextLimitExceededError) as exc_info:
        await adapter.generate_response(messages)
    assert "Context limit exceeded" in str(exc_info.value)
