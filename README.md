# Modifications from Original EvoSkill

This document describes what was changed in `EvoSkill_deepagents` relative to the original
[sentient-agi/EvoSkill](https://github.com/sentient-agi/EvoSkill), and explains why each
change was necessary.

## Background

The original EvoSkill was designed to run inside **Claude Code** — Anthropic's CLI tool.
`claude_agent_sdk` works by spawning Claude Code as a subprocess, sending it a query, and
streaming back typed messages. It assumes you are running Claude (Anthropic's model) locally
via the CLI, with Claude Code's own tool infrastructure.

The goal of this fork is to run the same self-improving loop against **Azure OpenAI**
(deployment: `gpt-5.2`). Azure OpenAI is not Claude, has no Claude Code CLI, and cannot use
`claude_agent_sdk`. A different execution path is required. The replacement backend is
[deepagents](https://github.com/sentient-agi/deep-agents) — a LangChain-based agent framework
that supports Azure OpenAI natively.

All changes are confined to the agent execution layer. The loop logic, registry, evaluation,
schemas, and proposer prompts are **unchanged** from the original.

---

## Changed Files

### 1. `src/agent_profiles/sdk_config.py` — deleted

**What it did:** Runtime switcher between two backends — `claude_agent_sdk` (Claude Code
subprocess) and `opencode_ai` (an OpenCode HTTP server). Exposed `set_sdk()`, `get_sdk()`,
`is_claude_sdk()`, `is_opencode_sdk()`. The rest of `base.py` called `is_claude_sdk()` to
branch between paths.

**Why deleted:** deepagents is a third, entirely different backend — not a variant of either
existing one. Rather than add a third branch to the switcher and a third `elif` everywhere,
the whole abstraction was dropped. With only one backend there is nothing to switch between.

---

### 2. `src/agent_profiles/base.py` — core of the swap

This is the only file that materially changes how agents execute. Four areas were rewritten.

#### 2a. Imports

```python
# Original
from .sdk_config import is_claude_sdk
if TYPE_CHECKING:
    from claude_agent_sdk import ClaudeAgentOptions as ClaudeAgentOptionsType
OptionsProvider = Union[ClaudeAgentOptionsType, dict, Callable[...]]

# Deepagents
from langchain_core.messages import AIMessage
from deepagents import create_deep_agent  # with ImportError guard
```

`OptionsProvider` (a union type covering ClaudeAgentOptions, dicts, and callables) is replaced
by a simple `Any` annotation since `DeepAgentOptions` is the only options type used.

#### 2b. `_execute_query()` — the agent invocation

**Original (~65 lines):** Branched on `is_claude_sdk()`.
- *Claude path*: `ClaudeSDKClient` spawns Claude Code as a subprocess, streams back typed
  message objects (`SystemMessage`, `AssistantMessage`, `ResultMessage`). Tool execution
  happens inside the subprocess — the SDK only sees the final result.
- *OpenCode path*: Launches an OpenCode HTTP server via `subprocess.Popen`, creates a session,
  calls `client.session.chat()`, returns a single message.

**Why neither works for Azure OpenAI:** Both SDKs require a local agent runtime (subprocess or
HTTP server). Azure OpenAI is a remote API — you call it directly with standard chat completion
requests. There is no subprocess to spawn.

**Deepagents replacement (~30 lines):**

```python
model = AzureChatOpenAI(deployment, endpoint, api_key, api_version)
backend = FilesystemBackend(root_dir=str(project_root), virtual_mode=True)
agent = create_deep_agent(
    model=model,
    tools=list(options.tools),
    system_prompt=options.system_prompt,
    response_format=self.response_model,
    backend=backend,
    skills=[".claude/skills/"],
)
return await agent.ainvoke({"messages": [{"role": "user", "content": query}]})
```

- `AzureChatOpenAI` — LangChain's wrapper for Azure OpenAI API calls, replacing the subprocess.
- `FilesystemBackend` — gives the agent controlled filesystem access (`list_files`, `read_file`,
  etc.). The original Claude Code subprocess had this natively via Claude Code's tool system;
  here it must be provided explicitly.
- `create_deep_agent` — builds a LangChain ReAct agent that handles the tool-calling loop
  internally.
- `skills=[".claude/skills/"]` — native skill loading, replacing the manual `inject_skills()`
  text injection used in the Azure-backend variant.

Note: `AzureChatOpenAI` and `FilesystemBackend` are imported lazily inside `_execute_query`
(guarded by `if "deepagents" in sys.modules`) so that the module can be imported and tested
without these packages installed.

#### 2c. `run()` — parsing the response

**Original:** Claude SDK returns a list of typed message objects with fixed fields:
- `messages[0]` (SystemMessage) → `uuid`, `model`, `tools`
- `messages[-1]` (ResultMessage) → `structured_output`, `session_id`, `duration_ms`,
  `total_cost_usd`, `num_turns`, `usage`

**Deepagents returns** a LangChain state dict:
```python
{
    "messages": [HumanMessage, AIMessage, ToolMessage, AIMessage, ...],
    "structured_response": <Pydantic object or dict>,
}
```

The parsing logic changes accordingly:
- Walk `messages` in reverse to find the last `AIMessage` for `result_text`.
- Count all `AIMessage` objects in the list for `num_turns`.
- Read `state["structured_response"]` (falling back to `state["structured_output"]`) for
  structured output.
- Check `isinstance(raw, self.response_model)` first — deepagents may already return a
  validated Pydantic instance, unlike the Claude SDK which always returns a raw dict.

#### 2d. `AgentTrace` metadata — synthesized locally

**Original:** `ResultMessage` from the Claude SDK carries `duration_ms`, `total_cost_usd`,
`num_turns`, and `usage` (token counts) produced by the subprocess.

**Deepagents:** These fields are not surfaced in the returned state dict, so they are
synthesized locally:
- `duration_ms` — measured with `time.time()` around `_run_with_retry`.
- `uuid` / `session_id` — generated with `uuid.uuid4()` (no session concept in deepagents).
- `total_cost_usd = 0.0` — Azure billing is not tracked by LangChain by default.
- `usage = {}` — token counts are not exposed by deepagents.

This is an accepted trade-off. Cost and token tracking are lost; everything else in the loop
(frontier management, feedback, evaluation) does not depend on these fields.

#### 2e. `AgentTrace.summarize()` — docstring stripped, logic unchanged

The method body is identical to the original. Only the extended docstring was removed,
consistent with the leaner commenting style throughout this fork.

---

### 3. `src/agent_profiles/base_agent/__init__.py` — compatibility shim added

**Original:** Simple re-export of `base_agent_options`, `get_base_agent_options`,
`make_base_agent_options`, `PROMPT_FILE` from `base_agent.py`.

**Why changed:** `runner.py` calls `get_base_agent_options()` and passes its result to
`ProgramConfig`:

```python
base_config = ProgramConfig(
    system_prompt=current_options.system_prompt,
    allowed_tools=current_options.allowed_tools,
    output_format=current_options.output_format,
    ...
)
```

The original `ClaudeAgentOptions` has `allowed_tools` and `output_format` fields.
`DeepAgentOptions` has neither — only `system_prompt`, `tools`, `model`. Accessing
`options.allowed_tools` on a `DeepAgentOptions` would raise `AttributeError`.

A `_BaseAgentCompat` shim dataclass is added:
```python
@dataclass
class _BaseAgentCompat:
    system_prompt: Any
    allowed_tools: list = field(default_factory=list)
    output_format: Any = None
```

`get_base_agent_options()` returns this shim, providing empty defaults for the two fields
`ProgramConfig` expects. `runner.py` was not changed — the shim absorbs the incompatibility.

---

### 4. `src/agent_profiles/options.py` — new file

Defines `DeepAgentOptions`, the replacement for `ClaudeAgentOptions`:

```python
@dataclass
class DeepAgentOptions:
    system_prompt: str
    tools: Sequence[BaseTool] = field(default_factory=tuple)
    model: str | None = None
```

Where the original used either a `ClaudeAgentOptions` object or a plain `dict`, all agents
now use this single dataclass. `tools` holds LangChain `BaseTool` objects (not OpenAI JSON
schema dicts).

---

### 5. `src/agent_profiles/tools.py` — new file (replaces `azure/tools.py` interface)

**Original `azure/tools.py`:** Tools defined as hand-written OpenAI JSON schema dicts
(`_LIST_FILES_SCHEMA`, `_READ_FILE_SCHEMA`, etc.) dispatched via a name→function map.
Also included `grep_files`, `edit_file`, `run_python`, and `load_skill_tools` (dynamic
Python script loader for skill tools).

**Why replaced:** `create_deep_agent` uses LangChain's tool interface — it expects
`BaseTool` objects, not raw JSON schema dicts. The `@tool` decorator converts a Python
function into a LangChain tool automatically (schema generated from docstring and type hints).

The extra tools (`grep_files`, `edit_file`, `run_python`) were dropped because the skill
generator's responsibility was simplified (see §7 below) and no longer needs them.
`load_skill_tools` was dropped because deepagents loads skills natively from SKILL.md files —
there is no Python script loading mechanism.

---

### 6. `src/agent_profiles/agents.py` — new file (replaces `azure/agents.py`)

Provides factory functions for all five agent roles using `DeepAgentOptions` instead of
the Azure dict format. The five roles (base agent, skill proposer, prompt proposer, skill
generator, prompt generator) and their tool sets are the same as in the original.

---

### 7. `src/agent_profiles/skill_generator/prompt.py` — rewritten

**Original prompt:** "Read `.claude/skills/skill-creator/SKILL.md` before doing anything.
Implement a complete, production-ready skill with scripts, tests, and validation following
skill-creator conventions."

This assumed a Claude Code agent that can execute Python, write scripts, and follow a
meta-skill stored in the project. Skills in the original can contain executable Python in
`skills/*/scripts/*.py`, loaded as additional tools via `load_skill_tools()`.

**Why rewritten:**
1. **No executable scripts** — deepagents loads skills as SKILL.md markdown injected into
   the system prompt. There is no `load_skill_tools()` equivalent. Skills must be
   guidance-only files.
2. **Frontmatter is mandatory** — deepagents' native skill loader uses YAML frontmatter
   (`name:`, `description:`) to identify skills. Without it, the skill is silently ignored.
   The original did not enforce this because `inject_skills()` read files directly.
3. **No meta-skill dependency** — the `skill-creator` meta-skill contains Claude Code-specific
   patterns that do not apply to deepagents.

New constraints enforced by the prompt:
- YAML frontmatter block required as the very first thing in the file.
- 300-word cap — concise guidance beats comprehensive documentation.
- No code, scripts, or executables — markdown guidance only.
- Kebab-case skill name, saved to `.claude/skills/<name>/SKILL.md`.

---

### 8. `src/loop/runner.py` — `_write_skill_to_disk()` added

**Original:** After `skill_generator.run(skill_query)` → `pass`. The generator, running as a
Claude Code agent with `write_file` in its tools, is expected to call that tool and write the
file itself. Claude Code agents reliably call tools when instructed.

**Why added:** The skill generator is now a deepagents agent with `response_format` set to a
Pydantic schema. This causes the agent to focus on returning a structured JSON output, which
can cause it to skip the `write_file` tool call before returning. The comment in the code
states: *"LLM returns generated_skill content but doesn't reliably call write_file itself."*

`_write_skill_to_disk()` reads `generated_skill` from the structured output and writes it
deterministically, parsing the skill name from YAML frontmatter (with fallback to first
heading or `generated-skill`). This makes skill creation reliable regardless of whether the
LLM chose to call the tool.

---

### 9. `src/registry/models.py` — `system_prompt` type widened

```python
# Original
system_prompt: dict[str, Any] = Field(...)

# Deepagents
system_prompt: dict[str, Any] | str = Field(...)
```

`ClaudeAgentOptions` uses a structured dict for its system prompt. `DeepAgentOptions` uses a
plain `str`. When `ProgramConfig` stores the current program's system prompt for git-based
versioning, it must accept either. Widening to `dict | str` prevents a Pydantic validation
error when a string prompt is stored.

---

## Unchanged

Everything not listed above is byte-for-byte identical to the original:

- `src/loop/config.py`, `src/loop/helpers.py` — loop configuration, query builders,
  feedback helpers, round-robin sampling logic
- `src/loop/runner.py` — main `SelfImprovingLoop.run()`, `_mutate()`,
  `_mutate_with_fallback()`, `_evaluate()`, frontier management, checkpointing
- `src/registry/manager.py`, `src/registry/sdk_utils.py` — git-based program versioning
- `src/evaluation/` — all scorers and evaluation utilities
- `src/cache/` — run cache
- `src/api/` — EvoSkill public API, task registry, eval runner
- `src/schemas/` — all Pydantic output schemas
- `src/agent_profiles/proposer/`, `skill_proposer/`, `prompt_proposer/`,
  `skill_generator/skill_generator.py`, `prompt_generator/` — agent implementations
  and all proposer/generator prompts except `skill_generator/prompt.py`
- `src/agent_profiles/base_agent/prompt.py` — base agent system prompt
- `src/feedback_descent.py`
