import operator
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages  # type: ignore
from src.core.dtos.universal_dtos import ThreadStateDTO
import uuid


class AgentState(TypedDict):
    """Internal graph state, hidden from the domain."""

    messages: Annotated[list, add_messages]
    generated_captions: Annotated[tuple[str, str], operator.add]
    generated_chat_title: str
    config: ThreadStateDTO
    revision_count: int
    images_to_caption: list
