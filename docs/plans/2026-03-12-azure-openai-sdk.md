# Azure OpenAI SDK Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Azure OpenAI as a third SDK option (`--sdk azure`) in EvoSkill, supporting both `skill_only` and `prompt_only` evolution modes, with skills injected from `.claude/skills/` into the system prompt at runtime.

**Architecture:** Add `"azure"` to `sdk_config.py`, implement a `AzureReActRunner` that runs a ReAct loop using the `openai` Python SDK against Azure, inject skills by reading `.claude/skills/*/SKILL.md` at the start of each run, and add a third branch in `Agent._execute_query()` / `Agent.run()`. Create Azure-compatible options for all 5 agents using their existing system prompt strings.

**Tech Stack:** `openai>=1.0.0` (Azure OpenAI client), `pydantic` (already present), Python `asyncio`

---

### Task 1: Add `openai` dependency

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add dependency**

In `pyproject.toml`, add `"openai>=1.0.0"` to the `dependencies` list.

**Step 2: Sync**

```bash
uv sync
```
Expected: resolves and installs `openai` package.

**Step 3: Verify import works**

```bash
uv run python -c "from openai import AzureOpenAI; print('ok')"
```
Expected: prints `ok`.

**Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "feat: add openai dependency for Azure SDK"
```

---

### Task 2: Extend `sdk_config.py` with `"azure"`

**Files:**
- Modify: `src/agent_profiles/sdk_config.py`
- Modify: `src/agent_profiles/__init__.py`

**Step 1: Write the failing test**

Create `tests/test_sdk_config.py`:

```python
from src.agent_profiles.sdk_config import set_sdk, get_sdk, is_azure_sdk, is_claude_sdk

def test_azure_sdk_type():
    set_sdk("azure")
    assert get_sdk() == "azure"
    assert is_azure_sdk() is True
    assert is_claude_sdk() is False
    set_sdk("claude")  # reset

def test_invalid_sdk_raises():
    import pytest
    with pytest.raises(ValueError):
        set_sdk("invalid")
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_sdk_config.py -v
```
Expected: FAIL with `ImportError: cannot import name 'is_azure_sdk'`

**Step 3: Implement**

In `src/agent_profiles/sdk_config.py`, change:

```python
SDKType = Literal["claude", "opencode"]
```
to:
```python
SDKType = Literal["claude", "opencode", "azure"]
```

Add after `is_opencode_sdk()`:

```python
def is_azure_sdk() -> bool:
    """Check if azure is the current SDK."""
    return _current_sdk == "azure"
```

In `src/agent_profiles/__init__.py`, add `is_azure_sdk` to the import line and `__all__`:

```python
from .sdk_config import set_sdk, get_sdk, is_claude_sdk, is_opencode_sdk, is_azure_sdk
```

And add `"is_azure_sdk"` to `__all__`.

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_sdk_config.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add src/agent_profiles/sdk_config.py src/agent_profiles/__init__.py tests/test_sdk_config.py
git commit -m "feat: add azure SDK type to sdk_config"
```

---

### Task 3: Implement skill injection utility

**Files:**
- Create: `src/agent_profiles/azure/skill_injection.py`

**Step 1: Write the failing test**

Create `tests/test_skill_injection.py`:

```python
import pytest
from pathlib import Path
from src.agent_profiles.azure.skill_injection import inject_skills

def test_no_skills_dir(tmp_path):
    result = inject_skills("base prompt", skills_dir=tmp_path / "nonexistent")
    assert result == "base prompt"

def test_empty_skills_dir(tmp_path):
    result = inject_skills("base prompt", skills_dir=tmp_path)
    assert result == "base prompt"

def test_single_skill_injected(tmp_path):
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("Do X when Y.")
    result = inject_skills("base prompt", skills_dir=tmp_path)
    assert "base prompt" in result
    assert "my-skill" in result
    assert "Do X when Y." in result

def test_multiple_skills_sorted(tmp_path):
    for name in ["z-skill", "a-skill"]:
        d = tmp_path / name
        d.mkdir()
        (d / "SKILL.md").write_text(f"Content of {name}")
    result = inject_skills("base", skills_dir=tmp_path)
    assert result.index("a-skill") < result.index("z-skill")
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_skill_injection.py -v
```
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Create directory and implement**

Create `src/agent_profiles/azure/__init__.py` (empty).

Create `src/agent_profiles/azure/skill_injection.py`:

```python
"""Inject .claude/skills/ content into a system prompt for non-Claude-Code agents."""

from pathlib import Path


def inject_skills(base_prompt: str, skills_dir: Path | None = None) -> str:
    """Read all SKILL.md files and append them to the system prompt.

    Args:
        base_prompt: The base system prompt text.
        skills_dir: Directory to scan. Defaults to .claude/skills/ relative to cwd.

    Returns:
        System prompt with skill content appended, or base_prompt unchanged if no skills.
    """
    if skills_dir is None:
        skills_dir = Path(".claude/skills")

    if not skills_dir.exists():
        return base_prompt

    skill_texts = []
    for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
        skill_name = skill_file.parent.name
        content = skill_file.read_text().strip()
        if content:
            skill_texts.append(f"## Skill: {skill_name}\n{content}")

    if not skill_texts:
        return base_prompt

    return base_prompt + "\n\n" + "\n\n".join(skill_texts)
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_skill_injection.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add src/agent_profiles/azure/ tests/test_skill_injection.py
git commit -m "feat: add skill injection utility for azure SDK"
```

---

### Task 4: Implement Azure tools

**Files:**
- Create: `src/agent_profiles/azure/tools.py`

These are the Python functions that implement `list_files` and `read_file` (called by the ReAct loop when the model requests them), plus the OpenAI tool schema definitions.

**Step 1: Write the failing test**

Create `tests/test_azure_tools.py`:

```python
import pytest
from pathlib import Path
from src.agent_profiles.azure.tools import make_tools, list_files, read_file

def test_list_files(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "b.txt").write_text("world")
    result = list_files(str(tmp_path))
    assert "a.txt" in result
    assert "b.txt" in result

def test_read_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("file content here")
    result = read_file(str(f))
    assert result == "file content here"

def test_read_file_not_found():
    result = read_file("/nonexistent/path/file.txt")
    assert "Error" in result

def test_make_tools_returns_schemas_and_fns():
    schemas, fns = make_tools(include_write=False)
    assert len(schemas) == 2
    assert "list_files" in fns
    assert "read_file" in fns
    assert "write_file" not in fns

def test_make_tools_with_write():
    schemas, fns = make_tools(include_write=True)
    assert len(schemas) == 3
    assert "write_file" in fns

def test_write_file(tmp_path):
    from src.agent_profiles.azure.tools import write_file
    path = str(tmp_path / "subdir" / "skill.md")
    result = write_file(path, "# My Skill")
    assert "written" in result.lower()
    assert Path(path).read_text() == "# My Skill"
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_azure_tools.py -v
```
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement**

Create `src/agent_profiles/azure/tools.py`:

```python
"""Tool definitions and implementations for Azure ReAct agents."""

import os
from pathlib import Path


def list_files(directory: str) -> str:
    """List files in a directory."""
    path = Path(directory)
    if not path.exists():
        return f"Error: directory '{directory}' does not exist."
    entries = sorted(path.iterdir())
    if not entries:
        return "(empty directory)"
    return "\n".join(e.name + ("/" if e.is_dir() else "") for e in entries)


def read_file(path: str) -> str:
    """Read the full text of a file."""
    try:
        return Path(path).read_text()
    except FileNotFoundError:
        return f"Error: file '{path}' not found."
    except Exception as e:
        return f"Error reading '{path}': {e}"


def write_file(path: str, content: str) -> str:
    """Write content to a file, creating parent directories as needed."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"Successfully written to '{path}'."
    except Exception as e:
        return f"Error writing '{path}': {e}"


# OpenAI tool schema definitions
_LIST_FILES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "list_files",
        "description": "List files and directories at the given path.",
        "parameters": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Absolute or relative path to list."}
            },
            "required": ["directory"],
        },
    },
}

_READ_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read the full text content of a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or relative path to the file."}
            },
            "required": ["path"],
        },
    },
}

_WRITE_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Write text content to a file. Creates parent directories if needed.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to write the file to."},
                "content": {"type": "string", "description": "Text content to write."},
            },
            "required": ["path", "content"],
        },
    },
}


def make_tools(include_write: bool = False) -> tuple[list[dict], dict[str, callable]]:
    """Return (tool_schemas, tool_fn_map) for use with AzureReActRunner.

    Args:
        include_write: Whether to include write_file tool (needed by generator agents).

    Returns:
        Tuple of (list of OpenAI tool schemas, dict mapping tool name -> callable).
    """
    schemas = [_LIST_FILES_SCHEMA, _READ_FILE_SCHEMA]
    fns = {"list_files": list_files, "read_file": read_file}

    if include_write:
        schemas.append(_WRITE_FILE_SCHEMA)
        fns["write_file"] = write_file

    return schemas, fns
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_azure_tools.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add src/agent_profiles/azure/tools.py tests/test_azure_tools.py
git commit -m "feat: add Azure tool definitions (list_files, read_file, write_file)"
```

---

### Task 5: Implement `AzureReActRunner`

**Files:**
- Create: `src/agent_profiles/azure/runner.py`

This class runs the two-phase ReAct loop:
- Phase 1: tool loop (no structured output format, tools active)
- Phase 2: one final call with `response_format: json_schema` to extract structured output

**Step 1: Write the failing test**

Create `tests/test_azure_runner.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from src.agent_profiles.azure.runner import AzureReActRunner


def _make_mock_response(content: str, finish_reason: str = "stop", tool_calls=None):
    """Helper to create a mock Azure OpenAI response."""
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
    import json

    final_answer = json.dumps({"final_answer": "42", "reasoning": "because"})
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response(final_answer)

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
    import json

    tool_call = MagicMock()
    tool_call.id = "call_1"
    tool_call.function.name = "read_file"
    tool_call.function.arguments = json.dumps({"path": "/tmp/test.txt"})

    tool_response = _make_mock_response("", finish_reason="tool_calls", tool_calls=[tool_call])
    final_response = _make_mock_response(
        json.dumps({"final_answer": "file contents", "reasoning": "read it"})
    )

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [tool_response, final_response]

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
    assert result["num_turns"] == 2
    assert result["structured_output"]["final_answer"] == "file contents"
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_azure_runner.py -v
```
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement**

Create `src/agent_profiles/azure/runner.py`:

```python
"""Azure OpenAI ReAct loop runner."""

import json
import time
import uuid
from typing import Any


class AzureReActRunner:
    """Two-phase ReAct loop using Azure OpenAI.

    Phase 1: Tool loop — model calls tools until it stops.
    Phase 2: Structured output — one final call with json_schema response_format.

    Args:
        client: An AzureOpenAI client instance.
        deployment: Azure deployment name (e.g. "gpt-4o").
        system_prompt: System prompt (with skills already injected).
        tool_schemas: List of OpenAI tool schema dicts.
        tool_fns: Dict mapping tool name -> callable.
        output_schema: JSON schema dict for structured output.
        max_turns: Maximum ReAct loop iterations before forcing final answer.
    """

    def __init__(
        self,
        client: Any,
        deployment: str,
        system_prompt: str,
        tool_schemas: list[dict],
        tool_fns: dict[str, Any],
        output_schema: dict,
        max_turns: int = 30,
    ):
        self.client = client
        self.deployment = deployment
        self.system_prompt = system_prompt
        self.tool_schemas = tool_schemas
        self.tool_fns = tool_fns
        self.output_schema = output_schema
        self.max_turns = max_turns

    def run(self, query: str) -> dict:
        """Run the ReAct loop for a single query.

        Returns:
            Dict with keys: structured_output, result, duration_ms, num_turns,
            usage, total_cost_usd, is_error, session_id, uuid, model, tools, messages.
        """
        start_ms = int(time.time() * 1000)
        messages: list[dict] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": query},
        ]
        total_input = 0
        total_output = 0
        turns = 0

        # Phase 1: ReAct tool loop
        while turns < self.max_turns:
            turns += 1
            kwargs: dict = {
                "model": self.deployment,
                "messages": messages,
            }
            if self.tool_schemas:
                kwargs["tools"] = self.tool_schemas
                kwargs["tool_choice"] = "auto"

            response = self.client.chat.completions.create(**kwargs)

            if response.usage:
                total_input += response.usage.prompt_tokens
                total_output += response.usage.completion_tokens

            choice = response.choices[0]
            messages.append(choice.message.model_dump())

            if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
                for tool_call in choice.message.tool_calls:
                    name = tool_call.function.name
                    try:
                        args = json.loads(tool_call.function.arguments)
                        result_text = str(self.tool_fns[name](**args)) if name in self.tool_fns else f"Unknown tool: {name}"
                    except Exception as e:
                        result_text = f"Error: {e}"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_text,
                    })
            else:
                break  # Model finished reasoning

        # Phase 2: Extract structured output
        final_response = self.client.chat.completions.create(
            model=self.deployment,
            messages=messages + [{"role": "user", "content": "Provide your final answer in the required JSON format."}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "output",
                    "schema": self.output_schema,
                    "strict": False,
                },
            },
        )
        if final_response.usage:
            total_input += final_response.usage.prompt_tokens
            total_output += final_response.usage.completion_tokens
        turns += 1

        raw_text = final_response.choices[0].message.content or ""
        try:
            structured = json.loads(raw_text)
            is_error = False
        except (json.JSONDecodeError, TypeError):
            structured = None
            is_error = True

        return {
            "structured_output": structured,
            "result": raw_text,
            "duration_ms": int(time.time() * 1000) - start_ms,
            "num_turns": turns,
            "usage": {"input_tokens": total_input, "output_tokens": total_output},
            "total_cost_usd": 0.0,
            "is_error": is_error,
            "session_id": str(uuid.uuid4()),
            "uuid": str(uuid.uuid4()),
            "model": self.deployment,
            "tools": list(self.tool_fns.keys()),
            "messages": messages,
        }
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_azure_runner.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add src/agent_profiles/azure/runner.py tests/test_azure_runner.py
git commit -m "feat: implement AzureReActRunner two-phase loop"
```

---

### Task 6: Add azure path in `Agent._execute_query()` and `Agent.run()`

**Files:**
- Modify: `src/agent_profiles/base.py`

**Step 1: Write the failing test**

Add to `tests/test_azure_runner.py`:

```python
def test_agent_run_azure_path():
    """Agent.run() uses azure path when sdk is set to azure."""
    import json
    from src.agent_profiles.base import Agent
    from src.agent_profiles.sdk_config import set_sdk
    from src.agent_profiles.azure.runner import AzureReActRunner
    from src.schemas import AgentResponse
    from unittest.mock import patch

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
        agent = Agent(azure_options, AgentResponse)
        import asyncio
        trace = asyncio.run(agent.run("What is 6x7?"))

    assert trace.output is not None
    assert trace.output.final_answer == "42"
    assert trace.is_error is False
    set_sdk("claude")  # reset
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_azure_runner.py::test_agent_run_azure_path -v
```
Expected: FAIL

**Step 3: Implement**

In `src/agent_profiles/base.py`:

1. Add import at top of file:
```python
from src.agent_profiles.sdk_config import is_claude_sdk, is_opencode_sdk, is_azure_sdk
```

2. Add the azure import inside `_execute_query()` alongside the existing SDK imports, after the opencode block:

```python
        elif is_azure_sdk():
            from openai import AzureOpenAI
            from src.agent_profiles.azure.runner import AzureReActRunner
            from src.agent_profiles.azure.skill_injection import inject_skills
            from src.agent_profiles.skill_generator import get_project_root
            from pathlib import Path

            system_prompt = inject_skills(
                options.get("system", ""),
                skills_dir=Path(get_project_root()) / ".claude" / "skills",
            )
            client = AzureOpenAI(
                api_key=os.environ["AZURE_OPENAI_API_KEY"],
                azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                api_version="2024-08-01-preview",
            )
            deployment = os.environ["AZURE_OPENAI_DEPLOYMENT"]
            runner = AzureReActRunner(
                client=client,
                deployment=deployment,
                system_prompt=system_prompt,
                tool_schemas=options.get("tool_schemas", []),
                tool_fns=options.get("tool_fns", {}),
                output_schema=options.get("output_schema", {}),
            )
            return [runner.run(query)]
```

3. Add a third branch in `Agent.run()` after the opencode `else` block:

```python
        elif is_azure_sdk():
            result = messages[0]  # Single dict from AzureReActRunner.run()
            raw_structured_output = result.get("structured_output")
            output = None
            parse_error = None

            if raw_structured_output is not None:
                try:
                    output = self.response_model.model_validate(raw_structured_output)
                except (ValidationError, json.JSONDecodeError, TypeError) as e:
                    parse_error = f"{type(e).__name__}: {str(e)}"
            else:
                parse_error = "No structured output returned"

            return AgentTrace(
                uuid=result.get("uuid", "unknown"),
                session_id=result.get("session_id", "unknown"),
                model=result.get("model", "unknown"),
                tools=result.get("tools", []),
                duration_ms=result.get("duration_ms", 0),
                total_cost_usd=result.get("total_cost_usd", 0.0),
                num_turns=result.get("num_turns", 1),
                usage=result.get("usage", {}),
                result=result.get("result", ""),
                is_error=result.get("is_error", False) or parse_error is not None,
                output=output,
                parse_error=parse_error,
                raw_structured_output=raw_structured_output,
                messages=messages,
            )
```

Note: also add `import os` at the top of `base.py` if not already present.

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_azure_runner.py -v
```
Expected: all PASS

**Step 5: Commit**

```bash
git add src/agent_profiles/base.py
git commit -m "feat: add azure execution path to Agent._execute_query and Agent.run"
```

---

### Task 7: Create Azure agent options for all 5 agents

**Files:**
- Create: `src/agent_profiles/azure/agents.py`
- Modify: `src/agent_profiles/azure/__init__.py`

All 5 agents reuse the existing system prompt strings from their respective `prompt.py` files. They just need Azure-compatible options dicts.

**Step 1: Implement**

Create `src/agent_profiles/azure/agents.py`:

```python
"""Azure OpenAI agent options for all 5 EvoSkill agents."""

from src.agent_profiles.azure.tools import make_tools
from src.agent_profiles.base_agent.prompt import BASE_AGENT_SYSTEM_PROMPT
from src.agent_profiles.skill_proposer.prompt import SKILL_PROPOSER_SYSTEM_PROMPT
from src.agent_profiles.prompt_proposer.prompt import PROMPT_PROPOSER_SYSTEM_PROMPT
from src.agent_profiles.skill_generator.prompt import SKILL_GENERATOR_SYSTEM_PROMPT
from src.agent_profiles.prompt_generator.prompt import PROMPT_GENERATOR_SYSTEM_PROMPT
from src.schemas import (
    AgentResponse,
    SkillProposerResponse,
    PromptProposerResponse,
    ToolGeneratorResponse,
    PromptGeneratorResponse,
)


def _make_options(system_prompt: str, output_schema: dict, include_write: bool = False) -> dict:
    tool_schemas, tool_fns = make_tools(include_write=include_write)
    return {
        "system": system_prompt.strip(),
        "output_schema": output_schema,
        "tool_schemas": tool_schemas,
        "tool_fns": tool_fns,
    }


def make_azure_base_agent_options(model: str | None = None) -> dict:
    """Options for base agent (read-only tools)."""
    return _make_options(BASE_AGENT_SYSTEM_PROMPT, AgentResponse.model_json_schema())


def make_azure_skill_proposer_options(model: str | None = None) -> dict:
    """Options for skill proposer (read-only tools)."""
    return _make_options(SKILL_PROPOSER_SYSTEM_PROMPT, SkillProposerResponse.model_json_schema())


def make_azure_prompt_proposer_options(model: str | None = None) -> dict:
    """Options for prompt proposer (read-only tools)."""
    return _make_options(PROMPT_PROPOSER_SYSTEM_PROMPT, PromptProposerResponse.model_json_schema())


def make_azure_skill_generator_options(model: str | None = None) -> dict:
    """Options for skill generator (includes write_file tool)."""
    return _make_options(SKILL_GENERATOR_SYSTEM_PROMPT, ToolGeneratorResponse.model_json_schema(), include_write=True)


def make_azure_prompt_generator_options(model: str | None = None) -> dict:
    """Options for prompt generator (includes write_file tool)."""
    return _make_options(PROMPT_GENERATOR_SYSTEM_PROMPT, PromptGeneratorResponse.model_json_schema(), include_write=True)
```

Update `src/agent_profiles/azure/__init__.py`:

```python
from .agents import (
    make_azure_base_agent_options,
    make_azure_skill_proposer_options,
    make_azure_prompt_proposer_options,
    make_azure_skill_generator_options,
    make_azure_prompt_generator_options,
)

__all__ = [
    "make_azure_base_agent_options",
    "make_azure_skill_proposer_options",
    "make_azure_prompt_proposer_options",
    "make_azure_skill_generator_options",
    "make_azure_prompt_generator_options",
]
```

**Step 2: Verify import works**

```bash
uv run python -c "from src.agent_profiles.azure import make_azure_base_agent_options; print(make_azure_base_agent_options()['tool_schemas'])"
```
Expected: prints list of 2 tool schemas.

**Step 3: Commit**

```bash
git add src/agent_profiles/azure/
git commit -m "feat: add Azure agent options for all 5 EvoSkill agents"
```

Note: `BASE_AGENT_SYSTEM_PROMPT` is currently in `src/agent_profiles/base_agent/prompt.py` as a Python variable. If it's stored as `prompt.txt` on disk instead, read it with `Path(__file__).parent.parent / "base_agent" / "prompt.txt").read_text()` in `agents.py`.

---

### Task 8: Update CLI scripts to accept `--sdk azure`

**Files:**
- Modify: `scripts/run_loop.py`
- Modify: `scripts/run_eval.py`
- Modify: `scripts/run_loop_sealqa.py`
- Modify: `scripts/run_eval_sealqa.py`

**Step 1: Update `run_loop.py`**

Change the `sdk` field type annotation from:
```python
sdk: Literal["claude", "opencode"] = Field(...)
```
to:
```python
sdk: Literal["claude", "opencode", "azure"] = Field(
    default="claude",
    description="SDK to use: 'claude', 'opencode', or 'azure'",
)
```

Find where `set_sdk(settings.sdk)` is called in `main()` — it already exists. No other changes needed there since `set_sdk` now accepts `"azure"`.

Also update agent options selection in `main()`. Currently it uses `base_agent_options` / `skill_proposer_options` etc. directly. Wrap in a conditional:

```python
from src.agent_profiles.sdk_config import is_azure_sdk

# After set_sdk(settings.sdk):
if is_azure_sdk():
    from src.agent_profiles.azure import (
        make_azure_base_agent_options,
        make_azure_skill_proposer_options,
        make_azure_prompt_proposer_options,
        make_azure_skill_generator_options,
        make_azure_prompt_generator_options,
    )
    _base_opts = make_azure_base_agent_options(settings.model)
    _skill_proposer_opts = make_azure_skill_proposer_options()
    _prompt_proposer_opts = make_azure_prompt_proposer_options()
    _skill_gen_opts = make_azure_skill_generator_options()
    _prompt_gen_opts = make_azure_prompt_generator_options()
else:
    _base_opts = make_base_agent_options(settings.model)
    _skill_proposer_opts = skill_proposer_options
    _prompt_proposer_opts = prompt_proposer_options
    _skill_gen_opts = skill_generator_options
    _prompt_gen_opts = prompt_generator_options

agents = LoopAgents(
    base=Agent(_base_opts, AgentResponse),
    skill_proposer=Agent(_skill_proposer_opts, SkillProposerResponse),
    prompt_proposer=Agent(_prompt_proposer_opts, PromptProposerResponse),
    skill_generator=Agent(_skill_gen_opts, ToolGeneratorResponse),
    prompt_generator=Agent(_prompt_gen_opts, PromptGeneratorResponse),
)
```

Apply the same pattern to `run_loop_sealqa.py`, `run_eval.py`, `run_eval_sealqa.py`.

**Step 2: Verify the CLI accepts --sdk azure**

```bash
uv run python scripts/run_loop.py --help | grep azure
```
Expected: shows `azure` as valid option for `--sdk`.

**Step 3: Commit**

```bash
git add scripts/
git commit -m "feat: add --sdk azure option to all CLI scripts"
```

---

### Task 9: End-to-end smoke test

**Step 1: Set environment variables**

```bash
export AZURE_OPENAI_API_KEY=your-key
export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
export AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

**Step 2: Run a single eval with azure SDK**

```bash
uv run python scripts/run_eval.py --sdk azure --num-samples 2 --max-concurrent 1
```
Expected: runs 2 samples, prints accuracy score, no errors.

**Step 3: Run a short loop with azure SDK (skill_only mode)**

```bash
uv run python scripts/run_loop.py --sdk azure --mode skill_only --max-iterations 2
```
Expected: runs 2 iterations, creates skill files in `.claude/skills/`, prints frontier scores.

**Step 4: Verify skill injection on second iteration**

After iteration 1 creates a skill, iteration 2's agent should have the skill content in its system prompt. Check the `messages` field in any returned `AgentTrace` to confirm.

---

## Running All Tests

```bash
uv run pytest tests/test_sdk_config.py tests/test_skill_injection.py tests/test_azure_tools.py tests/test_azure_runner.py -v
```
