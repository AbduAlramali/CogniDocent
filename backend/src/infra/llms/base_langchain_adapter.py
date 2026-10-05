"""Base adapter bridging LangChain ChatModels to the ILLMProvider domain port."""

import json
from typing import Any, AsyncIterator, Dict, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from src.core.enums import Role
from src.core.interfaces.illm_provider import ILLMProvider
from src.core.interfaces.ilogger import ILogger
from src.core.dtos.llm_provider_dtos import (
    DomainMessageDTO,
    LLMResponseDTO,
    StreamChunkDTO,
    ToolCallDTO,
    ToolDefinitionDTO,
)
from src.core.exceptions.llm_provider_exceptions import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMContextLimitExceededError,
    LLMProviderError,
    LLMRateLimitError,
    LocalModelNotFoundError,
)


class BaseLangChainLLMAdapter(ILLMProvider):
    """Abstract base adapter managing shared translation and error handling for LangChain models."""

    def __init__(
        self, model: BaseChatModel, provider_name: str, logger: ILogger
    ) -> None:
        self._model = model
        self._provider_name = provider_name
        self._logger = logger

    # --- Public Port Methods ---

    async def generate_response(
        self,
        messages: List[DomainMessageDTO],
        tools: Optional[List[ToolDefinitionDTO]] = None,
    ) -> LLMResponseDTO:
        lc_messages = self._to_langchain_messages(messages)
        model_runnable = self._bind_tools_if_needed(self._model, tools)

        try:
            ai_message: AIMessage = await model_runnable.ainvoke(lc_messages)
            return self._to_domain_response(ai_message)
        except Exception as e:
            self._handle_exception(e)

    async def stream_response(
        self,
        messages: List[DomainMessageDTO],
        tools: Optional[List[ToolDefinitionDTO]] = None,
    ) -> AsyncIterator[StreamChunkDTO]:
        lc_messages = self._to_langchain_messages(messages)
        model_runnable = self._bind_tools_if_needed(self._model, tools)

        try:
            async for chunk in model_runnable.astream(lc_messages):
                yield self._to_domain_chunk_response(chunk)
        except Exception as e:
            self._handle_exception(e)

    # --- Internal Translation Helpers ---

    def _bind_tools_if_needed(
        self, model: BaseChatModel, tools: Optional[List[ToolDefinitionDTO]]
    ) -> Any:
        """Converts ToolDefinitionDTOs to standard OpenAI-style tool schema dictionaries."""
        if not tools:
            return model

        formatted_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters_schema,
                },
            }
            for tool in tools
        ]
        return model.bind_tools(formatted_tools)

    def _to_langchain_messages(
        self, messages: List[DomainMessageDTO]
    ) -> List[BaseMessage]:
        """Translates domain DTO messages into native LangChain BaseMessage instances."""
        lc_messages: List[BaseMessage] = []

        for msg in messages:
            if msg.role == Role.USER:
                lc_messages.append(HumanMessage(content=msg.content))
            elif msg.role == Role.SYSTEM:
                lc_messages.append(SystemMessage(content=msg.content))
            elif msg.role == Role.TOOL:
                lc_messages.append(
                    ToolMessage(
                        content=msg.content,
                        tool_call_id=msg.tool_call_id or "",
                    )
                )
            elif msg.role == Role.ASSISTANT:
                tool_calls_payload = [
                    {
                        "id": tc.id,
                        "name": tc.name,
                        "args": tc.arguments,
                        "type": "tool_call",
                    }
                    for tc in msg.tool_calls
                ]
                lc_messages.append(
                    AIMessage(
                        content=msg.content,
                        tool_calls=tool_calls_payload,
                    )
                )
            else:
                lc_messages.append(HumanMessage(content=msg.content))

        return lc_messages

    def _to_domain_response(self, ai_message: AIMessage) -> LLMResponseDTO:
        """Translates a full LangChain AIMessage into an LLMResponseDTO."""
        domain_tool_calls: List[ToolCallDTO] = []

        if getattr(ai_message, "tool_calls", None):
            for tc in ai_message.tool_calls:
                args = tc.get("args", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {"raw_args": args}

                domain_tool_calls.append(
                    ToolCallDTO(
                        id=tc.get("id", ""),
                        name=tc.get("name", ""),
                        arguments=args,
                    )
                )

        usage = getattr(ai_message, "usage_metadata", {}) or {}
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        domain_msg = DomainMessageDTO(
            role=Role.ASSISTANT,
            content=str(ai_message.content or ""),
            tool_calls=domain_tool_calls,
        )

        finish_reason = ai_message.response_metadata.get("finish_reason") or (
            "tool_calls" if domain_tool_calls else "stop"
        )

        return LLMResponseDTO(
            message=domain_msg,
            finish_reason=str(finish_reason),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def _to_domain_chunk_response(self, chunk: AIMessageChunk) -> StreamChunkDTO:
        """Translates streaming chunks into StreamChunkDTOs."""
        tool_name: Optional[str] = None

        if getattr(chunk, "tool_call_chunks", None):
            for tc_chunk in chunk.tool_call_chunks:
                name = tc_chunk.get("name")
                if name:
                    tool_name = name
                    break

        content_delta = str(chunk.content or "")
        finish_reason = getattr(chunk, "response_metadata", {}).get("finish_reason")

        return StreamChunkDTO(
            content_delta=content_delta,
            tool_name=tool_name,
            finish_reason=str(finish_reason) if finish_reason else None,
        )

    def _handle_exception(self, exc: Exception) -> None:
        """Translates provider and library-level errors into domain exceptions."""
        exc_str = str(exc).lower()
        self._logger.error(
            f"{self._provider_name} request failed",
            exc_info=exc,
            provider=self._provider_name,
            error=str(exc),
        )

        if self._provider_name.lower() == "ollama" and (
            "not found" in exc_str
            or "does not exist" in exc_str
            or "pull" in exc_str
            or "404" in exc_str
        ):
            raise LocalModelNotFoundError(self._model.model) from exc

        if (
            "auth" in exc_str
            or "api_key" in exc_str
            or "unauthorized" in exc_str
            or "forbidden" in exc_str
            or "credential" in exc_str
        ):
            raise LLMAuthenticationError(self._provider_name) from exc

        if "rate limit" in exc_str or "429" in exc_str or "quota" in exc_str:
            raise LLMRateLimitError() from exc

        if (
            "context length" in exc_str
            or "maximum context" in exc_str
            or "token limit" in exc_str
        ):
            raise LLMContextLimitExceededError() from exc

        if "connection" in exc_str or "refused" in exc_str or "unreachable" in exc_str:
            raise LLMConnectionError(
                self._provider_name, endpoint="configured endpoint"
            ) from exc

        raise LLMProviderError(
            f"An error occurred while communicating with {self._provider_name}."
        ) from exc
