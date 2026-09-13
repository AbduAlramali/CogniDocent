from abc import ABC, abstractmethod
from typing import AsyncIterator
from uuid import UUID
from src.core.dtos.llm_provider_dtos import (
    DomainMessageDTO,
    LLMResponseDTO,
    StreamChunkDTO,
)
from src.core.dtos.universal_dtos import ThreadStateDTO


class IChatOrchestrator(ABC):
    @abstractmethod
    async def process_turn(
        self,
        thread_id: UUID,
        user_message: DomainMessageDTO,
        config: ThreadStateDTO,
        history_messages: list | None = None,
        images_to_caption: list | None = None,
    ) -> LLMResponseDTO:
        """Executes the complete conversational graph synchronously.

        Raises:
            OrchestratorError: Base class for all orchestration failures.
            GraphRecursionLimitError: If the agent enters an infinite loop or exceeds max steps.
            ContextWindowExceededError: If the conversation history + context exceeds the LLM token budget.
            ProviderUnavailableError: If the underlying LLM provider times out or is unreachable.
            CorruptedThreadStateError: If the checkpointer fails to deserialize or load thread history.
        """
        pass

    @abstractmethod
    async def stream_turn(
        self, thread_id: UUID, user_message: DomainMessageDTO, config: ThreadStateDTO
    ) -> AsyncIterator[StreamChunkDTO]:
        """Streams the execution of the conversational graph.

        Raises:
            OrchestratorError: Base class for all orchestration failures.
            GraphRecursionLimitError: If the agent enters an infinite loop or exceeds max steps.
            ContextWindowExceededError: If the conversation history + context exceeds the LLM token budget.
            ProviderUnavailableError: If the underlying LLM provider times out or is unreachable.
            CorruptedThreadStateError: If the checkpointer fails to deserialize or load thread history.
        """
        pass
