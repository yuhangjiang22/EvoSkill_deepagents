import pytest
from unittest.mock import AsyncMock, patch
from pydantic import BaseModel
from langchain_core.messages import AIMessage, HumanMessage

from src.agent_profiles.base import Agent, AgentTrace
from src.agent_profiles.options import DeepAgentOptions
from src.agent_profiles.tools import list_files, read_file


class MyResponse(BaseModel):
    answer: str


def make_opts():
    return DeepAgentOptions(
        system_prompt="You are a test agent.",
        tools=(list_files, read_file),
    )


@pytest.mark.asyncio
async def test_agent_run_returns_agent_trace():
    """Agent.run() returns AgentTrace with populated output."""
    opts = make_opts()
    agent = Agent(opts, MyResponse)

    mock_state = {
        "messages": [
            HumanMessage(content="test query"),
            AIMessage(content="The answer is 42"),
        ],
        "structured_output": MyResponse(answer="42"),
    }

    with patch("src.agent_profiles.base.create_deep_agent") as mock_create:
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = mock_state
        mock_create.return_value = mock_graph

        trace = await agent.run("test query")

    assert isinstance(trace, AgentTrace)
    assert trace.output == MyResponse(answer="42")
    assert trace.is_error is False
    assert trace.result == "The answer is 42"
    assert trace.num_turns == 1


@pytest.mark.asyncio
async def test_agent_run_handles_missing_structured_output():
    opts = make_opts()
    agent = Agent(opts, MyResponse)

    mock_state = {
        "messages": [AIMessage(content="some text")],
        "structured_output": None,
    }

    with patch("src.agent_profiles.base.create_deep_agent") as mock_create:
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = mock_state
        mock_create.return_value = mock_graph

        trace = await agent.run("query")

    assert trace.is_error is True
    assert trace.parse_error is not None
    assert trace.output is None
