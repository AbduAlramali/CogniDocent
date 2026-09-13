import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END
from langgraph.types import Send

from src.core.dtos.universal_dtos import ThreadStateDTO
from src.core.dtos.llm_provider_dtos import (
    DomainMessageDTO,
    SystemAIConfigDTO,
    LLMRouteConfigDTO,
    EmbeddingConfigDTO,
)
from src.core.enums import Role, ChatProvider, EmbeddingProvider
from src.infra.orchestrators.langgraph.nodes import (
    ToolNode,
    AgentNode,
    EvaluatorNode,
    EvaluationResult,
    FeedbackMessage,
    CaptionDeciderNode,
    CaptionGeneratorNode,
    should_continue,
    should_revise,
    dispatch_caption_generators,
)
from src.infra.orchestrators.langgraph.adapter import LangGraphChatOrchestrator


@pytest.fixture
def system_ai_config():
    chat_route = LLMRouteConfigDTO(provider=ChatProvider.OPENAI, model_name="gpt-4o-mini")
    emb_config = EmbeddingConfigDTO(provider=EmbeddingProvider.OPENAI)
    vision_route = LLMRouteConfigDTO(provider=ChatProvider.OPENAI, model_name="gpt-4o")
    return SystemAIConfigDTO(
        active_chat_model=chat_route,
        embedding_config=emb_config,
        vision_model=vision_route,
    )


@tool("sample_search")
def sample_search(query: str) -> str:
    """Sample search tool for testing."""
    return f"Search result for {query}"


@pytest.mark.asyncio
async def test_agent_node_injects_system_prompt_and_tools():
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Agent response"))
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.get_num_tokens_from_messages.return_value = 10

    node = AgentNode(llm=mock_llm, tools=[sample_search])
    state = {
        "messages": [HumanMessage(content="Hello")],
        "config": None,
        "revision_count": 0,
    }

    result = await node(state)
    assert len(result["messages"]) == 1
    assert result["messages"][0].content == "Agent response"

    # Verify system instructions were prepended
    mock_llm.ainvoke.assert_called_once()
    called_messages = mock_llm.ainvoke.call_args[0][0]
    assert any(isinstance(m, SystemMessage) for m in called_messages)


@pytest.mark.asyncio
async def test_evaluator_node_pass():
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(
        return_value=EvaluationResult(is_approved=True, feedback="Good answer.")
    )
    mock_llm.with_structured_output.return_value = mock_structured

    evaluator = EvaluatorNode(llm=mock_llm, max_revisions=2)
    state = {
        "messages": [
            HumanMessage(content="What is Python?"),
            AIMessage(content="Python is a programming language."),
        ],
        "config": None,
        "revision_count": 0,
    }

    result = await evaluator(state)
    assert result["is_approved"] is True
    assert result["revision_count"] == 0
    assert result["feedback"] == "Good answer."


@pytest.mark.asyncio
async def test_evaluator_node_revise_uses_feedback_message_and_context():
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(
        return_value=EvaluationResult(
            is_approved=False, feedback="Please provide more details on syntax."
        )
    )
    mock_llm.with_structured_output.return_value = mock_structured

    evaluator = EvaluatorNode(llm=mock_llm, max_revisions=2)
    state = {
        "messages": [
            HumanMessage(content="What is Python?"),
            ToolMessage(content="Python 3.13 was released recently.", name="sample_search", tool_call_id="c1"),
            AIMessage(content="It is code."),
        ],
        "config": None,
        "revision_count": 0,
    }

    result = await evaluator(state)
    assert result["is_approved"] is False
    assert result["revision_count"] == 1
    assert len(result["messages"]) == 1

    feedback_msg = result["messages"][0]
    assert isinstance(feedback_msg, FeedbackMessage)
    assert "[Evaluator Feedback]" in feedback_msg.content
    assert "Please provide more details on syntax." in feedback_msg.content

    # Check that tool output was injected under Retrieved Context:
    mock_structured.ainvoke.assert_called_once()
    judge_call_messages = mock_structured.ainvoke.call_args[0][0]
    judge_prompt = judge_call_messages[0].content
    assert "Retrieved Context:" in judge_prompt
    assert "Python 3.13 was released recently." in judge_prompt


@pytest.mark.asyncio
async def test_evaluator_node_max_revisions():
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured

    evaluator = EvaluatorNode(llm=mock_llm, max_revisions=2)
    state = {
        "messages": [
            HumanMessage(content="What is Python?"),
            AIMessage(content="Still incomplete."),
        ],
        "config": None,
        "revision_count": 2,
    }

    result = await evaluator(state)
    assert result["is_approved"] is True
    assert result["revision_count"] == 2
    mock_structured.ainvoke.assert_not_called()


def test_routing_functions():
    msg_with_tools = AIMessage(
        content="",
        tool_calls=[{"name": "sample_search", "args": {"query": "test"}, "id": "call_1", "type": "tool_call"}],
    )
    assert should_continue({"messages": [msg_with_tools]}) == "tools"

    msg_without_tools = AIMessage(content="Final answer")
    assert should_continue({"messages": [msg_without_tools]}) == "evaluator"

    assert should_revise({"is_approved": True, "revision_count": 0}) == "decide_image_captions"
    assert should_revise({"is_approved": False, "revision_count": 1}, max_revisions=2) == "agent"
    assert should_revise({"is_approved": False, "revision_count": 2}, max_revisions=2) == "decide_image_captions"

    assert dispatch_caption_generators({"images_to_caption": []}) == END
    img_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    dispatched = dispatch_caption_generators({"images_to_caption": img_ids})
    assert len(dispatched) == 2
    assert all(isinstance(s, Send) for s in dispatched)
    assert dispatched[0].node == "caption_generator"
    assert dispatched[0].arg == {"media_id": img_ids[0]}


@pytest.mark.asyncio
async def test_caption_decider_node():
    node = CaptionDeciderNode()
    img_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    res = await node({"images_to_caption": img_ids})
    assert res == {"images_to_caption": img_ids}

    res_empty = await node({})
    assert res_empty == {"images_to_caption": []}


@pytest.mark.asyncio
async def test_caption_generator_node():
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Generated caption text."))
    node = CaptionGeneratorNode(llm=mock_llm)

    img_id = str(uuid.uuid4())
    res = await node({"media_id": img_id})
    assert res == {"generated_captions": (img_id, "Generated caption text.")}
    mock_llm.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_orchestrator_dynamic_caption_generation_with_images():
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=[
        AIMessage(content="Final assistant response."),
        AIMessage(content="Caption for image 1."),
        AIMessage(content="Caption for image 2."),
    ])
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.get_num_tokens_from_messages.return_value = 10

    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=EvaluationResult(is_approved=True, feedback="Pass"))
    mock_llm.with_structured_output.return_value = mock_structured

    mock_tool_factory = MagicMock()
    mock_tool_factory.get_all_tools.return_value = []

    orchestrator = LangGraphChatOrchestrator(
        tool_factory=mock_tool_factory,
        llm_provider=mock_llm,
    )

    img1 = str(uuid.uuid4())
    img2 = str(uuid.uuid4())
    state_input = {
        "messages": [HumanMessage(content="Describe the images")],
        "images_to_caption": [img1, img2],
        "config": ThreadStateDTO(project_id=uuid.uuid4(), document_id=uuid.uuid4(), config=system_ai_config),
        "revision_count": 0,
        "generated_captions": (),
    }

    final_state = await orchestrator.app.ainvoke(state_input)
    assert final_state["generated_captions"] == (img1, "Caption for image 1.", img2, "Caption for image 2.")


@pytest.mark.asyncio
async def test_orchestrator_process_turn_direct_answer(system_ai_config):
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Here is the accurate answer."))
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.get_num_tokens_from_messages.return_value = 10

    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=EvaluationResult(is_approved=True, feedback="Pass"))
    mock_llm.with_structured_output.return_value = mock_structured

    mock_tool_factory = MagicMock()
    mock_tool_factory.get_all_tools.return_value = [sample_search]

    orchestrator = LangGraphChatOrchestrator(
        tool_factory=mock_tool_factory,
        llm_provider=mock_llm,
    )

    thread_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    config = ThreadStateDTO(project_id=proj_id, document_id=doc_id, config=system_ai_config)
    user_msg = DomainMessageDTO(role=Role.USER, content="Hello")

    response = await orchestrator.process_turn(thread_id, user_msg, config)

    assert response.message.content == "Here is the accurate answer."
    assert response.message.role == Role.ASSISTANT
    assert response.finish_reason == "stop"


@pytest.mark.asyncio
async def test_orchestrator_process_turn_with_tools_and_revision(system_ai_config):
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=[
        AIMessage(
            content="",
            tool_calls=[{"name": "sample_search", "args": {"query": "python"}, "id": "call_1", "type": "tool_call"}],
        ),
        AIMessage(content="Initial answer."),
        AIMessage(content="Revised and improved answer."),
    ])
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.get_num_tokens_from_messages.return_value = 10

    # Evaluator: Step 1 rejects, Step 2 approves
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(side_effect=[
        EvaluationResult(is_approved=False, feedback="Needs more citations."),
        EvaluationResult(is_approved=True, feedback="Approved."),
    ])
    mock_llm.with_structured_output.return_value = mock_structured

    mock_tool_factory = MagicMock()
    mock_tool_factory.get_all_tools.return_value = [sample_search]

    orchestrator = LangGraphChatOrchestrator(
        tool_factory=mock_tool_factory,
        llm_provider=mock_llm,
        max_revisions=2,
    )

    thread_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    config = ThreadStateDTO(project_id=proj_id, document_id=doc_id, config=system_ai_config)
    user_msg = DomainMessageDTO(role=Role.USER, content="Tell me about python")

    response = await orchestrator.process_turn(thread_id, user_msg, config)

    assert response.message.content == "Revised and improved answer."
    assert response.message.role == Role.ASSISTANT


@pytest.mark.asyncio
async def test_orchestrator_stream_turn(system_ai_config):
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Streamed answer."))
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.get_num_tokens_from_messages.return_value = 10

    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=EvaluationResult(is_approved=True, feedback="Approved."))
    mock_llm.with_structured_output.return_value = mock_structured

    mock_tool_factory = MagicMock()
    mock_tool_factory.get_all_tools.return_value = []

    orchestrator = LangGraphChatOrchestrator(
        tool_factory=mock_tool_factory,
        llm_provider=mock_llm,
    )

    thread_id = uuid.uuid4()
    config = ThreadStateDTO(project_id=uuid.uuid4(), document_id=uuid.uuid4(), config=system_ai_config)
    user_msg = DomainMessageDTO(role=Role.USER, content="Hi")

    chunks = []
    async for chunk in orchestrator.stream_turn(thread_id, user_msg, config):
        chunks.append(chunk)

    assert len(chunks) == 1
    assert chunks[0].content_delta == "Streamed answer."
