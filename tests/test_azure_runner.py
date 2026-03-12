import json
import pytest
from unittest.mock import MagicMock
from src.agent_profiles.azure.runner import AzureReActRunner


def _make_mock_response(content: str, finish_reason: str = "stop", tool_calls=None):
    choice = MagicMock()
    choice.finish_reason = finish_reason
    choice.message.content = content
    choice.message.tool_calls = tool_calls
    choice.message.model_dump.return_value = {
        "role": "assistant",
        "content": content,
        "tool_calls": tool_calls,
    }
    response = MagicMock()
    response.choices = [choice]
    response.usage.prompt_tokens = 10
    response.usage.completion_tokens = 5
    return response


def test_simple_run_no_tools():
    """Agent answers directly without calling any tools."""
    final_answer = json.dumps({"final_answer": "42", "reasoning": "because"})
    mock_client = MagicMock()
    # Phase 1: model stops immediately (no tools), Phase 2: structured output
    mock_client.chat.completions.create.side_effect = [
        _make_mock_response("thinking...", finish_reason="stop"),
        _make_mock_response(final_answer),
    ]

    runner = AzureReActRunner(
        client=mock_client,
        deployment="gpt-4o",
        system_prompt="You are helpful.",
        tool_schemas=[],
        tool_fns={},
        output_schema={"type": "object", "properties": {"final_answer": {"type": "string"}, "reasoning": {"type": "string"}}},
    )
    result = runner.run("What is 6x7?")
    assert result["structured_output"] == {"final_answer": "42", "reasoning": "because"}
    assert result["is_error"] is False
    assert result["num_turns"] >= 1


def test_run_with_tool_call():
    """Agent calls a tool then gives final answer."""
    tool_call = MagicMock()
    tool_call.id = "call_1"
    tool_call.function.name = "read_file"
    tool_call.function.arguments = json.dumps({"path": "/tmp/test.txt"})

    tool_response = _make_mock_response("", finish_reason="tool_calls", tool_calls=[tool_call])
    stop_response = _make_mock_response("I read the file")
    final_response = _make_mock_response(
        json.dumps({"final_answer": "file contents", "reasoning": "read it"})
    )

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [tool_response, stop_response, final_response]

    tool_fns = {"read_file": lambda path: "file contents"}
    runner = AzureReActRunner(
        client=mock_client,
        deployment="gpt-4o",
        system_prompt="You are helpful.",
        tool_schemas=[],
        tool_fns=tool_fns,
        output_schema={},
    )
    result = runner.run("Read the file")
    assert result["structured_output"]["final_answer"] == "file contents"
    assert result["is_error"] is False


def test_result_keys():
    """Result dict has all required keys."""
    final_answer = json.dumps({"final_answer": "x", "reasoning": "y"})
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        _make_mock_response("done"),
        _make_mock_response(final_answer),
    ]
    runner = AzureReActRunner(
        client=mock_client, deployment="gpt-4o",
        system_prompt="", tool_schemas=[], tool_fns={}, output_schema={},
    )
    result = runner.run("q")
    for key in ["structured_output", "result", "duration_ms", "num_turns", "usage",
                "total_cost_usd", "is_error", "session_id", "uuid", "model", "tools", "messages"]:
        assert key in result, f"Missing key: {key}"


def test_agent_run_azure_path():
    """Agent.run() uses azure path when sdk is set to azure."""
    import asyncio
    import json
    from unittest.mock import patch, MagicMock
    from src.agent_profiles.base import Agent
    from src.agent_profiles.sdk_config import set_sdk
    from src.schemas import AgentResponse

    set_sdk("azure")

    azure_options = {
        "system": "You are helpful.",
        "output_schema": AgentResponse.model_json_schema(),
        "tool_schemas": [],
        "tool_fns": {},
    }

    mock_result = {
        "structured_output": {"final_answer": "42", "reasoning": "math"},
        "result": json.dumps({"final_answer": "42", "reasoning": "math"}),
        "duration_ms": 100,
        "num_turns": 1,
        "usage": {"input_tokens": 10, "output_tokens": 5},
        "total_cost_usd": 0.0,
        "is_error": False,
        "session_id": "sess-1",
        "uuid": "uuid-1",
        "model": "gpt-4o",
        "tools": [],
        "messages": [],
    }

    with patch("src.agent_profiles.base.AzureReActRunner") as MockRunner:
        MockRunner.return_value.run.return_value = mock_result
        # Also patch AzureOpenAI and inject_skills so no real credentials needed
        with patch("src.agent_profiles.base.AzureOpenAI"), \
             patch("src.agent_profiles.base.inject_skills", return_value="You are helpful."):
            agent = Agent(azure_options, AgentResponse)
            trace = asyncio.run(agent.run("What is 6x7?"))

    assert trace.output is not None
    assert trace.output.final_answer == "42"
    assert trace.is_error is False
    set_sdk("claude")  # reset
