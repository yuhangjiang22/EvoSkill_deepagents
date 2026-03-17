# EvoSkill deepagents Migration Design

**Goal:** Replace the three-SDK abstraction (claude/opencode/azure) with LangChain deepagents backed by Azure OpenAI, gaining native SKILL.md progressive disclosure.

**Architecture:** Keep `Agent[T]` / `AgentTrace[T]` as the public interface. Replace internals with a single deepagents runner. Delete `sdk_config.py`, `azure/` directory, and all three-branch logic.

**Tech Stack:** `deepagents>=0.3.12`, `langchain-openai>=0.3`, `langchain>=0.3`, Azure OpenAI via `AzureChatOpenAI`

---

## What Changes

### Deleted
- `src/agent_profiles/sdk_config.py`
- `src/agent_profiles/azure/` (agents.py, runner.py, skill_injection.py, tools.py, __init__.py)
- `tests/test_sdk_config.py`, `tests/test_skill_injection.py`, `tests/test_azure_tools.py`, `tests/test_azure_runner.py`

### New files
- `src/agent_profiles/options.py` — `DeepAgentOptions(system_prompt, tools)` dataclass
- `src/agent_profiles/tools.py` — `list_files`, `read_file`, `write_file` as LangChain `@tool`
- `src/agent_profiles/agents.py` — 5 factory functions
- `tests/test_deepagent_tools.py`, `tests/test_deepagent_runner.py`

### Rewritten
- `src/agent_profiles/base.py` — single deepagents branch replaces three SDK branches
- `src/agent_profiles/__init__.py` — remove SDK exports
- `scripts/run_loop.py`, `run_eval.py`, `run_loop_sealqa.py`, `run_eval_sealqa.py` — remove `--sdk`, `set_sdk()`

---

## Agent Options

```python
@dataclass
class DeepAgentOptions:
    system_prompt: str
    tools: list  # LangChain @tool functions
```

- Base agent, proposers: `tools=[list_files, read_file]`
- Generators: `tools=[list_files, read_file, write_file]`

---

## Runner (inside `Agent[T]._execute_query`)

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_openai import AzureChatOpenAI

model = AzureChatOpenAI(
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version="2024-08-01-preview",
)
agent = create_deep_agent(
    model=model,
    tools=options.tools,
    system_prompt=options.system_prompt,
    response_format=self.response_model,   # Pydantic model → structured output
    backend=FilesystemBackend(root_dir=project_root, virtual_mode=True),
    skills=[".claude/skills/"],            # native progressive disclosure
)
result = await agent.ainvoke({"messages": [{"role": "user", "content": query}]})
```

---

## AgentTrace Population

| Field | Source |
|---|---|
| `output` | `result["structured_output"]` — already validated Pydantic instance |
| `result` | last `AIMessage.content` in `result["messages"]` |
| `messages` | `result["messages"]` |
| `num_turns` | count of `AIMessage` in messages |
| `duration_ms` | timed around `ainvoke` |
| `model` | `AZURE_OPENAI_DEPLOYMENT` env var |
| `tools` | `[t.name for t in options.tools]` |
| `uuid`, `session_id` | `uuid4()` generated locally |
| `total_cost_usd` | `0.0` |
| `usage` | `{}` |

---

## Dependencies

```toml
# Remove
"claude-agent-sdk>=...",
"opencode-ai>=...",
"openai>=1.0.0",

# Add
"deepagents>=0.3.12",
"langchain-openai>=0.3",
"langchain>=0.3",
```

---

## run_loop.py Change

```python
# Before
set_sdk(settings.sdk)
sdk: Literal["claude", "opencode", "azure"] = ...
_base_opts = make_azure_base_agent_options(settings.model)

# After
_base_opts = make_base_agent_options(settings.model)
# --sdk flag removed entirely
```
