# EvoSkill deepagents Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the three-SDK abstraction (claude/opencode/azure) with LangChain deepagents backed by Azure OpenAI, gaining native SKILL.md progressive disclosure.

**Architecture:** Keep `Agent[T]` / `AgentTrace[T]` as the public interface. New `options.py` + `tools.py` + `agents.py` replace the old per-agent modules and `azure/` directory. `base.py` `_execute_query` becomes a single deepagents `ainvoke` call. Old SDK files deleted.

**Tech Stack:** `deepagents>=0.3.12`, `langchain-openai>=0.3`, `langchain>=0.3`, `langchain-core`, Azure OpenAI via `AzureChatOpenAI`

---

### Task 1: LangChain tools

Convert the three plain functions into LangChain `@tool` decorated functions. These replace `src/agent_profiles/azure/tools.py`.

**Files:**
- Create: `src/agent_profiles/tools.py`
- Create: `tests/test_deepagent_tools.py`

**Step 1: Write the failing test**

```python
# tests/test_deepagent_tools.py
import pytest
from pathlib import Path
from langchain_core.tools import BaseTool
from src.agent_profiles.tools import list_files, read_file, write_file


def test_tools_are_langchain_tools():
    assert isinstance(list_files, BaseTool)
    assert isinstance(read_file, BaseTool)
    assert isinstance(write_file, BaseTool)


def test_list_files(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "b.txt").write_text("world")
    result = list_files.invoke({"directory": str(tmp_path)})
    assert "a.txt" in result
    assert "b.txt" in result


def test_read_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("file content here")
    result = read_file.invoke({"path": str(f)})
    assert result == "file content here"


def test_read_file_not_found():
    result = read_file.invoke({"path": "/nonexistent/path/file.txt"})
    assert "Error" in result


def test_write_file(tmp_path):
    path = str(tmp_path / "subdir" / "skill.md")
    result = write_file.invoke({"path": path, "content": "# My Skill"})
    assert "written" in result.lower()
    assert Path(path).read_text() == "# My Skill"
```

**Step 2: Run test to verify it fails**

```bash
.venv/bin/python -m pytest tests/test_deepagent_tools.py -v
```
Expected: FAIL with `ModuleNotFoundError` or `ImportError`

**Step 3: Write implementation**

```python
# src/agent_profiles/tools.py
"""LangChain tool definitions for deepagents."""

from pathlib import Path
from langchain_core.tools import tool


@tool
def list_files(directory: str) -> str:
    """List files and directories at the given path."""
    path = Path(directory)
    if not path.exists():
        return f"Error: directory '{directory}' does not exist."
    entries = sorted(path.iterdir())
    if not entries:
        return "(empty directory)"
    return "\n".join(e.name + ("/" if e.is_dir() else "") for e in entries)


@tool
def read_file(path: str) -> str:
    """Read the full text content of a file."""
    try:
        return Path(path).read_text()
    except FileNotFoundError:
        return f"Error: file '{path}' not found."
    except Exception as e:
        return f"Error reading '{path}': {e}"


@tool
def write_file(path: str, content: str) -> str:
    """Write text content to a file, creating parent directories as needed."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"Successfully written to '{path}'."
    except Exception as e:
        return f"Error writing '{path}': {e}"
```

**Step 4: Run test to verify it passes**

```bash
.venv/bin/python -m pytest tests/test_deepagent_tools.py -v
```
Expected: 5 PASSED

**Step 5: Commit**

```bash
git add src/agent_profiles/tools.py tests/test_deepagent_tools.py
git commit -m "feat: add LangChain @tool definitions for deepagents"
```

---

### Task 2: DeepAgentOptions dataclass

**Files:**
- Create: `src/agent_profiles/options.py`

No separate test needed — it's a plain dataclass tested implicitly in Task 3.

**Step 1: Write implementation**

```python
# src/agent_profiles/options.py
"""Options dataclass for deepagents-backed agents."""

from dataclasses import dataclass, field
from langchain_core.tools import BaseTool


@dataclass
class DeepAgentOptions:
    """Configuration for a deepagents-backed agent.

    Attributes:
        system_prompt: System prompt for the agent.
        tools: LangChain @tool functions available to the agent.
        model: Optional Azure deployment name override. If None, uses
               AZURE_OPENAI_DEPLOYMENT env var.
    """
    system_prompt: str
    tools: list = field(default_factory=list)
    model: str | None = None
```

**Step 2: Commit**

```bash
git add src/agent_profiles/options.py
git commit -m "feat: add DeepAgentOptions dataclass"
```

---

### Task 3: Agent factory functions

Creates `agents.py` with 5 factory functions that return `DeepAgentOptions`. These replace the old per-agent option modules and `azure/agents.py`.

**Files:**
- Create: `src/agent_profiles/agents.py`

**Step 1: Write the failing test**

Add to `tests/test_deepagent_tools.py`:

```python
# Append to tests/test_deepagent_tools.py
from src.agent_profiles.options import DeepAgentOptions
from src.agent_profiles.agents import (
    make_base_agent_options,
    make_skill_proposer_options,
    make_prompt_proposer_options,
    make_skill_generator_options,
    make_prompt_generator_options,
)
from src.agent_profiles.tools import list_files, read_file, write_file


def test_base_agent_options_has_read_only_tools():
    opts = make_base_agent_options()
    assert isinstance(opts, DeepAgentOptions)
    tool_names = [t.name for t in opts.tools]
    assert "list_files" in tool_names
    assert "read_file" in tool_names
    assert "write_file" not in tool_names


def test_skill_generator_options_has_write_tool():
    opts = make_skill_generator_options()
    tool_names = [t.name for t in opts.tools]
    assert "write_file" in tool_names


def test_prompt_generator_options_has_write_tool():
    opts = make_prompt_generator_options()
    tool_names = [t.name for t in opts.tools]
    assert "write_file" in tool_names


def test_make_base_agent_options_accepts_model():
    opts = make_base_agent_options(model="gpt-4o")
    assert opts.model == "gpt-4o"
```

**Step 2: Run test to verify it fails**

```bash
.venv/bin/python -m pytest tests/test_deepagent_tools.py -v -k "agent_options"
```
Expected: FAIL with `ImportError`

**Step 3: Write implementation**

```python
# src/agent_profiles/agents.py
"""Factory functions for all 5 EvoSkill deepagents-backed agent options."""

from src.agent_profiles.options import DeepAgentOptions
from src.agent_profiles.tools import list_files, read_file, write_file
from src.agent_profiles.base_agent.prompt import BASE_AGENT_SYSTEM_PROMPT
from src.agent_profiles.skill_proposer.prompt import SKILL_PROPOSER_SYSTEM_PROMPT
from src.agent_profiles.prompt_proposer.prompt import PROMPT_PROPOSER_SYSTEM_PROMPT
from src.agent_profiles.skill_generator.prompt import SKILL_GENERATOR_SYSTEM_PROMPT
from src.agent_profiles.prompt_generator.prompt import PROMPT_GENERATOR_SYSTEM_PROMPT

_READ_ONLY = [list_files, read_file]
_READ_WRITE = [list_files, read_file, write_file]


def make_base_agent_options(model: str | None = None) -> DeepAgentOptions:
    return DeepAgentOptions(
        system_prompt=BASE_AGENT_SYSTEM_PROMPT.strip(),
        tools=_READ_ONLY,
        model=model,
    )


def make_skill_proposer_options(model: str | None = None) -> DeepAgentOptions:
    return DeepAgentOptions(
        system_prompt=SKILL_PROPOSER_SYSTEM_PROMPT.strip(),
        tools=_READ_ONLY,
        model=model,
    )


def make_prompt_proposer_options(model: str | None = None) -> DeepAgentOptions:
    return DeepAgentOptions(
        system_prompt=PROMPT_PROPOSER_SYSTEM_PROMPT.strip(),
        tools=_READ_ONLY,
        model=model,
    )


def make_skill_generator_options(model: str | None = None) -> DeepAgentOptions:
    return DeepAgentOptions(
        system_prompt=SKILL_GENERATOR_SYSTEM_PROMPT.strip(),
        tools=_READ_WRITE,
        model=model,
    )


def make_prompt_generator_options(model: str | None = None) -> DeepAgentOptions:
    return DeepAgentOptions(
        system_prompt=PROMPT_GENERATOR_SYSTEM_PROMPT.strip(),
        tools=_READ_WRITE,
        model=model,
    )


# Pre-built default instances (used when no model override needed)
base_agent_options = make_base_agent_options()
skill_proposer_options = make_skill_proposer_options()
prompt_proposer_options = make_prompt_proposer_options()
skill_generator_options = make_skill_generator_options()
prompt_generator_options = make_prompt_generator_options()
```

**Step 4: Run test to verify it passes**

```bash
.venv/bin/python -m pytest tests/test_deepagent_tools.py -v
```
Expected: all PASSED

**Step 5: Commit**

```bash
git add src/agent_profiles/agents.py tests/test_deepagent_tools.py
git commit -m "feat: add deepagents agent factory functions"
```

---

### Task 4: Rewrite Agent[T] in base.py

Replace the three SDK branches in `_execute_query` and `run` with a single deepagents branch.

**Files:**
- Modify: `src/agent_profiles/base.py`
- Create: `tests/test_deepagent_runner.py`

**Step 1: Write the failing test**

```python
# tests/test_deepagent_runner.py
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
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
        tools=[list_files, read_file],
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
```

**Step 2: Run test to verify it fails**

```bash
.venv/bin/python -m pytest tests/test_deepagent_runner.py -v
```
Expected: FAIL — `create_deep_agent` not imported yet

**Step 3: Rewrite base.py**

Replace the entire content of `src/agent_profiles/base.py` with:

```python
import asyncio
import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Generic, Optional, Type, TypeVar

from langchain_core.messages import AIMessage
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class AgentTrace(BaseModel, Generic[T]):
    """Metadata and output from an agent run."""

    uuid: str
    session_id: str
    model: str
    tools: list[str]

    duration_ms: int
    total_cost_usd: float
    num_turns: int
    usage: dict[str, Any]
    result: str
    is_error: bool

    output: Optional[T] = None
    parse_error: Optional[str] = None
    raw_structured_output: Optional[Any] = None
    messages: list[Any]

    class Config:
        arbitrary_types_allowed = True

    def summarize(
        self,
        head_chars: int = 60_000,
        tail_chars: int = 60_000,
    ) -> str:
        lines = [
            f"Model: {self.model}",
            f"Turns: {self.num_turns}",
            f"Duration: {self.duration_ms}ms",
            f"Is Error: {self.is_error}",
        ]

        if self.parse_error:
            lines.append(f"Parse Error: {self.parse_error}")

        if self.output:
            lines.append(f"Output: {self.output}")

        result_str = str(self.result) if self.result else ""

        if self.parse_error and len(result_str) > (head_chars + tail_chars):
            truncated_middle = len(result_str) - head_chars - tail_chars
            lines.append(f"\n## Result (truncated, {truncated_middle:,} chars omitted)")
            lines.append(f"### Start:\n{result_str[:head_chars]}")
            lines.append(f"\n[... {truncated_middle:,} characters truncated ...]\n")
            lines.append(f"### End:\n{result_str[-tail_chars:]}")
        else:
            lines.append(f"\n## Full Result\n{result_str}")

        return "\n".join(lines)


def _get_project_root() -> Path:
    """Return project root (directory containing pyproject.toml)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


class Agent(Generic[T]):
    """Wrapper for running deepagents-backed agents.

    Args:
        options: DeepAgentOptions instance.
        response_model: Pydantic model for structured output validation.
    """

    TIMEOUT_SECONDS = 1200  # 20 minutes
    MAX_RETRIES = 3
    INITIAL_BACKOFF = 30  # seconds

    def __init__(self, options: Any, response_model: Type[T]):
        self._options = options
        self.response_model = response_model

    def _get_options(self) -> Any:
        if callable(self._options):
            return self._options()
        return self._options

    async def _execute_query(self, query: str) -> dict:
        from deepagents import create_deep_agent
        from deepagents.backends import FilesystemBackend
        from langchain_openai import AzureChatOpenAI

        options = self._get_options()
        project_root = _get_project_root()

        deployment = options.model or os.environ.get("AZURE_OPENAI_DEPLOYMENT", "")
        model = AzureChatOpenAI(
            azure_deployment=deployment,
            azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
            api_key=os.environ.get("AZURE_OPENAI_API_KEY", ""),
            api_version="2024-08-01-preview",
        )

        agent = create_deep_agent(
            model=model,
            tools=options.tools,
            system_prompt=options.system_prompt,
            response_format=self.response_model,
            backend=FilesystemBackend(root_dir=str(project_root), virtual_mode=True),
            skills=[".claude/skills/"],
        )

        return await agent.ainvoke({"messages": [{"role": "user", "content": query}]})

    async def _run_with_retry(self, query: str) -> dict:
        last_error: Exception | None = None
        backoff = self.INITIAL_BACKOFF

        for attempt in range(self.MAX_RETRIES):
            try:
                async with asyncio.timeout(self.TIMEOUT_SECONDS):
                    return await self._execute_query(query)
            except asyncio.TimeoutError:
                last_error = TimeoutError(
                    f"Query timed out after {self.TIMEOUT_SECONDS}s"
                )
                logger.warning(
                    f"Attempt {attempt + 1}/{self.MAX_RETRIES} timed out. Retrying in {backoff}s..."
                )
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}. Retrying in {backoff}s..."
                )

            if attempt < self.MAX_RETRIES - 1:
                await asyncio.sleep(backoff)
                backoff *= 2

        raise last_error if last_error else RuntimeError("All retries exhausted")

    async def run(self, query: str) -> AgentTrace[T]:
        start_ms = int(time.time() * 1000)
        options = self._get_options()

        state = await self._run_with_retry(query)

        messages = state.get("messages", [])
        raw_structured_output = state.get("structured_output")

        # Extract text from last AI message
        result_text = ""
        num_turns = 0
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                if not result_text:
                    result_text = msg.content or ""
                num_turns += 1

        # Validate structured output
        output = None
        parse_error = None
        if raw_structured_output is not None:
            if isinstance(raw_structured_output, self.response_model):
                output = raw_structured_output
            else:
                try:
                    output = self.response_model.model_validate(raw_structured_output)
                except (ValidationError, TypeError) as e:
                    parse_error = f"{type(e).__name__}: {e}"
        else:
            parse_error = "No structured output returned (context limit likely exceeded)"

        deployment = options.model or os.environ.get("AZURE_OPENAI_DEPLOYMENT", "unknown")

        return AgentTrace(
            uuid=str(uuid.uuid4()),
            session_id=str(uuid.uuid4()),
            model=deployment,
            tools=[t.name for t in options.tools],
            duration_ms=int(time.time() * 1000) - start_ms,
            total_cost_usd=0.0,
            num_turns=num_turns,
            usage={},
            result=result_text,
            is_error=parse_error is not None,
            output=output,
            parse_error=parse_error,
            raw_structured_output=raw_structured_output,
            messages=messages,
        )
```

**Step 4: Run test to verify it passes**

```bash
.venv/bin/python -m pytest tests/test_deepagent_runner.py -v
```
Expected: 2 PASSED

**Step 5: Commit**

```bash
git add src/agent_profiles/base.py tests/test_deepagent_runner.py
git commit -m "feat: rewrite Agent[T] to use deepagents runner"
```

---

### Task 5: Update __init__.py

Remove SDK exports, add new agent factory exports.

**Files:**
- Modify: `src/agent_profiles/__init__.py`

**Step 1: Replace content**

```python
# src/agent_profiles/__init__.py
from .base import Agent, AgentTrace
from .options import DeepAgentOptions
from .agents import (
    make_base_agent_options,
    make_skill_proposer_options,
    make_prompt_proposer_options,
    make_skill_generator_options,
    make_prompt_generator_options,
    base_agent_options,
    skill_proposer_options,
    prompt_proposer_options,
    skill_generator_options,
    prompt_generator_options,
)
from .sealqa_agent import sealqa_agent_options, make_sealqa_agent_options
from .dabstep_agent import dabstep_agent_options, make_dabstep_agent_options
from .livecodebench_agent import (
    livecodebench_agent_options,
    make_livecodebench_agent_options,
)

__all__ = [
    "Agent",
    "AgentTrace",
    "DeepAgentOptions",
    "make_base_agent_options",
    "make_skill_proposer_options",
    "make_prompt_proposer_options",
    "make_skill_generator_options",
    "make_prompt_generator_options",
    "base_agent_options",
    "skill_proposer_options",
    "prompt_proposer_options",
    "skill_generator_options",
    "prompt_generator_options",
    "sealqa_agent_options",
    "make_sealqa_agent_options",
    "dabstep_agent_options",
    "make_dabstep_agent_options",
    "livecodebench_agent_options",
    "make_livecodebench_agent_options",
]
```

**Step 2: Verify imports work**

```bash
.venv/bin/python -c "from src.agent_profiles import Agent, AgentTrace, make_base_agent_options, base_agent_options; print('OK')"
```
Expected: `OK`

**Step 3: Commit**

```bash
git add src/agent_profiles/__init__.py
git commit -m "feat: update agent_profiles __init__ for deepagents"
```

---

### Task 6: Update scripts

Remove `--sdk` flag and `set_sdk()` calls from all four scripts.

**Files:**
- Modify: `scripts/run_loop.py`
- Modify: `scripts/run_eval.py`
- Modify: `scripts/run_loop_sealqa.py`
- Modify: `scripts/run_eval_sealqa.py`

**Step 1: Update `scripts/run_loop.py`**

Remove these lines:
```python
# Remove from imports:
set_sdk,

# Remove field:
sdk: Literal["claude", "opencode", "azure"] = Field(...)

# Remove in main():
set_sdk(settings.sdk)
from src.agent_profiles.sdk_config import is_azure_sdk
if is_azure_sdk():
    from src.agent_profiles.azure.agents import (...)
    _base_opts = make_azure_base_agent_options(settings.model)
    ...
else:
    _base_opts = (make_base_agent_options(...) if settings.model else base_agent_options)
    ...
```

Replace the agent options block with:
```python
_base_opts = make_base_agent_options(model=settings.model) if settings.model else base_agent_options
_skill_proposer_opts = skill_proposer_options
_prompt_proposer_opts = prompt_proposer_options
_skill_gen_opts = skill_generator_options
_prompt_gen_opts = prompt_generator_options
```

Also update imports at top to replace the old SDK-specific ones:
```python
from src.agent_profiles import (
    Agent,
    base_agent_options,
    make_base_agent_options,
    skill_proposer_options,
    prompt_proposer_options,
    skill_generator_options,
    prompt_generator_options,
)
```

**Step 2: Update `scripts/run_eval.py`**

Remove:
```python
set_sdk,          # from imports
sdk: Literal[...] = Field(...)   # field
set_sdk(settings.sdk)            # in main()
from src.agent_profiles.sdk_config import is_azure_sdk
if is_azure_sdk(): ...
```

Replace agent options with:
```python
agent_options = (
    make_base_agent_options(model=settings.model)
    if settings.model
    else base_agent_options
)
```

Remove `sdk` from imports:
```python
from src.agent_profiles import (
    Agent,
    base_agent_options,
    make_base_agent_options,
)
```

**Step 3: Update `scripts/run_loop_sealqa.py` and `scripts/run_eval_sealqa.py`**

Apply the same pattern: remove `set_sdk`, `--sdk` field, and any `is_azure_sdk()` block. Replace with direct factory calls.

**Step 4: Verify scripts parse correctly**

```bash
.venv/bin/python scripts/run_loop.py --help
.venv/bin/python scripts/run_eval.py --help
```
Expected: help text shown, no `--sdk` flag listed, no import errors

**Step 5: Commit**

```bash
git add scripts/run_loop.py scripts/run_eval.py scripts/run_loop_sealqa.py scripts/run_eval_sealqa.py
git commit -m "feat: remove SDK abstraction layer from scripts"
```

---

### Task 7: Update pyproject.toml and install deps

**Files:**
- Modify: `pyproject.toml`

**Step 1: Update dependencies**

In `pyproject.toml`, change the dependencies list:

Remove:
```toml
"opencode-ai>=0.0.26",
"claude-agent-sdk>=0.1.16",
"openai>=1.0.0",
```

Add:
```toml
"deepagents>=0.3.12",
"langchain-openai>=0.3",
"langchain>=0.3",
```

**Step 2: Install updated deps**

```bash
.venv/bin/pip install deepagents langchain-openai langchain
```
Expected: packages install successfully

**Step 3: Verify imports**

```bash
.venv/bin/python -c "from deepagents import create_deep_agent; from deepagents.backends import FilesystemBackend; from langchain_openai import AzureChatOpenAI; print('OK')"
```
Expected: `OK`

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "feat: replace SDK deps with deepagents + langchain-openai"
```

---

### Task 8: Delete old files and run all tests

**Files to delete:**
- `src/agent_profiles/sdk_config.py`
- `src/agent_profiles/azure/__init__.py`
- `src/agent_profiles/azure/agents.py`
- `src/agent_profiles/azure/runner.py`
- `src/agent_profiles/azure/skill_injection.py`
- `src/agent_profiles/azure/tools.py`
- `tests/test_sdk_config.py`
- `tests/test_skill_injection.py`
- `tests/test_azure_tools.py`
- `tests/test_azure_runner.py`

**Step 1: Delete old files**

```bash
rm -rf src/agent_profiles/azure/
rm src/agent_profiles/sdk_config.py
rm tests/test_sdk_config.py tests/test_skill_injection.py tests/test_azure_tools.py tests/test_azure_runner.py
```

**Step 2: Run all tests**

```bash
.venv/bin/python -m pytest tests/test_deepagent_tools.py tests/test_deepagent_runner.py -v
```
Expected: all PASSED, no import errors from deleted modules

**Step 3: Verify no remaining references to old SDK**

```bash
grep -r "sdk_config\|is_azure_sdk\|is_claude_sdk\|is_opencode_sdk\|AzureReActRunner\|inject_skills\|from src.agent_profiles.azure" src/ scripts/ tests/
```
Expected: no output (zero matches)

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: delete old SDK abstraction (azure/, sdk_config.py, old tests)"
```
