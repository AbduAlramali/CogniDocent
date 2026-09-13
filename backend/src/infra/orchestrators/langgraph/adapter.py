from typing import AsyncIterator, Optional, Any
import uuid
from psycopg_pool import AsyncConnectionPool

from langgraph.graph import StateGraph, START, END  # type: ignore
from langchain_core.messages import HumanMessage, AIMessage  # type: ignore
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from src.core.dtos.universal_dtos import ThreadStateDTO
from src.core.enums import Role
from src.core.dtos.llm_provider_dtos import (
    LLMResponseDTO,
    DomainMessageDTO,
    StreamChunkDTO,
)
from src.core.interfaces.ichat_orchestrator import IChatOrchestrator
from src.infra.orchestrators.langgraph.state import AgentState
from src.infra.orchestrators.langgraph.nodes import (
    ToolNode,
    AgentNode,
    EvaluatorNode,
    CaptionDeciderNode,
    CaptionGeneratorNode,
    should_continue,
    should_revise,
    dispatch_caption_generators,
)


class LangGraphChatOrchestrator(IChatOrchestrator):
    def __init__(
        self,
        tool_factory: Any,
        llm_provider: Any,
        db_pool: Optional[AsyncConnectionPool] = None,
        max_revisions: int = 2,
    ):
        self.db_pool = db_pool
        self._tool_factory = tool_factory
        self._llm = llm_provider
        self._max_revisions = max_revisions
        self._graph = self._build_graph()
        self.checkpointer = AsyncPostgresSaver(self.db_pool) if self.db_pool else None
        self.app = self._graph.compile(checkpointer=self.checkpointer)

    def _build_graph(self):
        """Constructs the StateGraph with agent, tools, evaluator nodes, and edges."""
        builder = StateGraph(AgentState)

        tools = self._tool_factory.get_all_tools() if self._tool_factory else []

        # Nodes
        builder.add_node(
            "agent", AgentNode(llm=self._llm, tools=tools, max_tokens=4000)
        )
        builder.add_node("tools", ToolNode(tools=tools))
        builder.add_node(
            "evaluator",
            EvaluatorNode(llm=self._llm, max_revisions=self._max_revisions),
        )
        builder.add_node("decide_image_captions", CaptionDeciderNode())
        builder.add_node("caption_generator", CaptionGeneratorNode(llm=self._llm))

        # Normal edges
        builder.add_edge(START, "agent")
        builder.add_edge("tools", "agent")
        builder.add_edge("caption_generator", END)

        # Conditional edges
        builder.add_conditional_edges(
            "agent",
            should_continue,
            {
                "tools": "tools",
                "evaluator": "evaluator",
            },
        )
        builder.add_conditional_edges(
            "evaluator",
            lambda state: should_revise(state, max_revisions=self._max_revisions),
            {
                "agent": "agent",
                "decide_image_captions": "decide_image_captions",
            },
        )
        builder.add_conditional_edges(
            "decide_image_captions",
            dispatch_caption_generators,
            ["caption_generator", END],
        )

        return builder

    async def initialize_database(self) -> None:
        """
        Creates LangGraph's internal `checkpoints` tables.
        Run this ONCE during your App startup.
        """
        if self.db_pool:
            async with AsyncPostgresSaver(self.db_pool) as checkpointer:
                await checkpointer.setup()

    async def process_turn(
        self,
        thread_id: uuid.UUID,
        user_message: DomainMessageDTO,
        config: ThreadStateDTO,
        history_messages: list | None = None,
        images_to_caption: list | None = None,
    ) -> LLMResponseDTO:
        # 1. Translate Domain DTO to Langchain Message
        if user_message.images:
            multimodal_content: list[dict[str, Any]] = [
                {"type": "text", "text": user_message.content}
            ]
            for img_url in user_message.images:
                multimodal_content.append(
                    {"type": "image_url", "image_url": {"url": img_url}}
                )
            lc_msg = HumanMessage(content=multimodal_content)
        else:
            lc_msg = HumanMessage(content=user_message.content)

        # 2. Combine history with the user's new message
        converted_history = [
            AIMessage(content=m.content) if m.role == Role.ASSISTANT else HumanMessage(content=m.content)
            for m in (history_messages or [])
        ]
        combined_messages = converted_history + [lc_msg]

        # 3. Setup internal execution state
        initial_state = {
            "messages": combined_messages,
            "config": config,
            "revision_count": 0,
            "generated_captions": (),
            "images_to_caption": (
                images_to_caption if images_to_caption is not None else []
            ),
        }
        config_dict = {"configurable": {"thread_id": str(thread_id)}}

        # 4. Execute the graph
        final_state = await self.app.ainvoke(initial_state, config=config_dict)

        # 5. Generate title if requested
        if config.generate_chat_title:
            try:
                title_prompt = f"Generate a concise 3-6 word title for a conversation starting with: {user_message.content}"
                title_msg = await self._llm.ainvoke(
                    [HumanMessage(content=title_prompt)]
                )
                final_state["generated_chat_title"] = str(title_msg.content).strip(
                    '" \n'
                )
            except Exception:
                final_state["generated_chat_title"] = "New Chat"

        # 6. Translate back to Domain DTO
        last_message = next(m for m in reversed(final_state["messages"]) if isinstance(m, AIMessage))
        domain_msg = DomainMessageDTO(role=Role.ASSISTANT, content=str(last_message.content))

        metadata = {
            "generated_captions": final_state.get("generated_captions", ()),
            "generated_chat_title": final_state.get("generated_chat_title"),
        }

        return LLMResponseDTO(
            message=domain_msg,
            finish_reason="stop",
            metadata=metadata,
        )

    async def stream_turn(
        self,
        thread_id: uuid.UUID,
        user_message: DomainMessageDTO,
        config: ThreadStateDTO,
    ) -> AsyncIterator[StreamChunkDTO]:
        response = await self.process_turn(thread_id, user_message, config)
        yield StreamChunkDTO(
            content_delta=response.message.content,
            finish_reason=response.finish_reason,
        )
