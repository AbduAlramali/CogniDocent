"""LangGraph nodes for chat orchestration: ToolNode, AgentNode, and EvaluatorNode."""

from typing import Any, Optional, Sequence
import uuid
from pydantic import BaseModel, Field
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    ToolMessage,
    trim_messages,
)
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.types import Send
from langgraph.prebuilt import ToolNode as PrebuiltToolNode

from src.core.prompts import (
    AGENT_SYSTEM_PROMPT,
    EVALUATOR_JUDGE_PROMPT_TEMPLATE,
    IMAGE_CAPTION_PROMPT_TEMPLATE,
)
from src.infra.llms.base_langchain_adapter import BaseLangChainLLMAdapter
from src.infra.orchestrators.langgraph.state import AgentState


class FeedbackMessage(SystemMessage):
    """Message representing feedback from the LLM evaluator to guide agent revisions."""

    def __init__(self, content: str, **kwargs: Any):
        super().__init__(content=content, **kwargs)


class EvaluationResult(BaseModel):
    """Structured evaluation judgment from the LLM-as-a-judge."""

    is_approved: bool = Field(
        description="True if the response accurately, groundedly, and sufficiently answers the user query; False if it needs revision."
    )
    feedback: Optional[str] = Field(
        default=None,
        description="Actionable critique and instructions for revision if not approved, or optional explanation if approved.",
    )


def _extract_model(llm: Any) -> Any:
    """Extracts underlying chat model if passed a BaseLangChainLLMAdapter."""
    if isinstance(llm, BaseLangChainLLMAdapter):
        return llm._model
    return llm


class ToolNode:
    """Tool execution node wrapping LangGraph's prebuilt ToolNode."""

    def __init__(self, tools: Sequence[Any]):
        self._prebuilt = PrebuiltToolNode(list(tools))

    async def __call__(
        self, state: AgentState, config: Optional[RunnableConfig] = None
    ) -> dict:
        return await self._prebuilt.ainvoke(state, config=config)


class AgentNode:
    """Agent node that generates responses or tool calls using the bound LLM."""

    def __init__(
        self,
        llm: Any,
        tools: Optional[Sequence[Any]] = None,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4000,
    ):
        self.llm = _extract_model(llm)
        self.tools = list(tools) if tools else []
        self.system_prompt = system_prompt or AGENT_SYSTEM_PROMPT
        self.max_tokens = max_tokens
        if self.tools:
            self.model_runnable = self.llm.bind_tools(self.tools)
        else:
            self.model_runnable = self.llm

        # Configure the LangChain message trimmer
        self.trimmer = trim_messages(
            max_tokens=max_tokens,
            strategy="last",
            token_counter=self.llm,  # Uses the model's native token counting
            include_system=True,  # NEVER trim the system prompt
            start_on="human",  # CRITICAL for preventing API errors
            allow_partial=False,  # Don't split individual message text in half
        )

    async def __call__(
        self, state: AgentState, config: Optional[RunnableConfig] = None
    ) -> dict:
        messages = list(state["messages"])

        # Inject system instructions if not already present
        if self.system_prompt and not any(
            isinstance(m, SystemMessage) and not isinstance(m, FeedbackMessage)
            for m in messages
        ):
            messages = [SystemMessage(content=self.system_prompt)] + messages

        trimmed_messages = self.trimmer.invoke(messages)

        response = await self.model_runnable.ainvoke(trimmed_messages, config=config)
        return {"messages": [response]}


class EvaluatorNode:
    """Evaluator node (LLM as a judge) assessing response quality with structured output."""

    def __init__(self, llm: Any, max_revisions: int = 2):
        raw_llm = _extract_model(llm)
        self.max_revisions = max_revisions
        self._judge_llm = raw_llm.with_structured_output(EvaluationResult)

    async def __call__(
        self, state: AgentState, config: Optional[RunnableConfig] = None
    ) -> dict:
        messages = state["messages"]
        revision_count = state.get("revision_count", 0)

        # If already reached max revisions, approve and exit
        if revision_count >= self.max_revisions:
            return {"revision_count": revision_count, "is_approved": True}

        # Extract user query
        user_prompt = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                user_prompt = str(m.content)
                break

        # Extract last assistant message
        last_msg = messages[-1]
        candidate_answer = str(last_msg.content)

        last_human_idx = -1
        for i in range(len(messages) - 1, -1, -1):
            if isinstance(messages[i], HumanMessage):
                last_human_idx = i
                user_prompt = str(messages[i].content)
                break

        current_turn_messages = (
            messages[last_human_idx + 1 :] if last_human_idx != -1 else messages
        )

        # Collect all recent tool outputs from messages
        tool_outputs = [
            f"- [{m.name or 'Tool'}]: {m.content}"
            for m in current_turn_messages
            if isinstance(m, ToolMessage)
        ]
        retrieved_context = (
            "\n".join(tool_outputs) if tool_outputs else "No tool outputs retrieved."
        )

        judge_prompt = EVALUATOR_JUDGE_PROMPT_TEMPLATE.format(
            user_prompt=user_prompt,
            retrieved_context=retrieved_context,
            candidate_answer=candidate_answer,
        )

        res: EvaluationResult = await self._judge_llm.ainvoke(
            [HumanMessage(content=judge_prompt)], config=config
        )

        if not res.is_approved:
            feedback_msg = FeedbackMessage(
                content=f"[Evaluator Feedback]: {res.feedback or 'Please revise and improve your response.'}"
            )
            return {
                "messages": [feedback_msg],
                "revision_count": revision_count + 1,
                "is_approved": False,
                "feedback": res.feedback,
            }

        return {
            "revision_count": revision_count,
            "is_approved": True,
            "feedback": res.feedback,
        }


def should_continue(state: AgentState) -> str:
    """
    Conditional edge from agent:
    - If the agent requested tool calls, route to 'tools'.
    - Otherwise, route to 'evaluator'.
    """
    messages = state["messages"]
    last_message = messages[-1]
    if getattr(last_message, "tool_calls", None) and len(last_message.tool_calls) > 0:
        return "tools"
    return "evaluator"


def should_revise(state: AgentState, max_revisions: int = 2) -> str:
    """
    Conditional edge from evaluator:
    - If approved or max revisions reached, route to 'decide_image_captions'.
    - If revisions are needed, route back to 'agent'.
    """
    if state.get("is_approved") or state.get("revision_count", 0) >= max_revisions:
        return "decide_image_captions"
    return "agent"


class CaptionDeciderNode:
    """Decides how many attachment images need captions from state."""

    async def __call__(self, state: AgentState) -> dict:
        return {"images_to_caption": state.get("images_to_caption", [])}


def dispatch_caption_generators(state: AgentState) -> list[Send] | str:
    """Routes to END if no captions, otherwise fans out to caption_generator for each image."""
    images = state.get("images_to_caption", [])
    if not images:
        return END
    return [Send("caption_generator", {"media_id": str(img)}) for img in images]


class CaptionGeneratorNode:
    """Generates a caption for an individual image attachment."""

    def __init__(self, llm: Any):
        self.llm = _extract_model(llm)

    async def __call__(self, state: dict) -> dict:
        media_id = state["media_id"]
        prompt = IMAGE_CAPTION_PROMPT_TEMPLATE.format(media_id=media_id)
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        caption = str(response.content)
        return {"generated_captions": (str(media_id), caption)}
