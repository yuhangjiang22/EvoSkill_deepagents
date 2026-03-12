# Azure OpenAI SDK Integration Design

**Date:** 2026-03-12
**Status:** Approved

## Goal

Add Azure OpenAI as a third SDK option in EvoSkill, supporting both `skill_only` and `prompt_only` evolution modes, replacing all 5 agents (base, skill_proposer, prompt_proposer, skill_generator, prompt_generator).

## Architecture

The change is localized to 3 areas. Everything else (loop, frontier, git versioning, evaluation, caching) is untouched.

```
sdk_config.py              → add "azure" as a valid SDK type
src/agent_profiles/base.py → add azure path in _execute_query()
src/agent_profiles/azure/  → azure options for all 5 agents
scripts/run_*.py           → accept --sdk azure flag
```

## The Azure ReAct Loop

Azure OpenAI does not run tools itself. Python drives the loop:

1. Build system prompt = base prompt + all skill files injected from `.claude/skills/*/SKILL.md`
2. Send message to Azure OpenAI
3. If response requests a tool call → run the tool in Python → send result back
4. Repeat until response has no tool calls
5. Extract final answer as structured JSON via `response_format={"type": "json_schema", ...}`

### Tools

All agents get minimal tools:
- `list_files(directory)` — lists files in a directory
- `read_file(path)` — reads a file's content

Skill/prompt generator agents additionally get:
- `write_file(path, content)` — writes skill files or prompt to disk

## Skill Injection

At the start of each Azure agent run, skill files are read and appended to the system prompt:

```python
skills_dir = Path(".claude/skills")
skill_texts = []
for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
    skill_name = skill_file.parent.name
    skill_texts.append(f"## Skill: {skill_name}\n{skill_file.read_text()}")

system_prompt = base_prompt + "\n\n" + "\n\n".join(skill_texts)
```

- `skill_only` mode: skill generator writes a file → next run it is injected automatically
- `prompt_only` mode: base prompt is rewritten → skills (if any) still appended
- No skills yet: system prompt is just the base prompt, no error

## Configuration

### Environment variables

```bash
export AZURE_OPENAI_API_KEY=your-key
export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
export AZURE_OPENAI_DEPLOYMENT=your-deployment-name  # e.g. "gpt-4o"
```

### CLI

```bash
uv run python scripts/run_loop.py --sdk azure --mode skill_only --max-iterations 20
uv run python scripts/run_eval.py --sdk azure --max-concurrent 8
```

### sdk_config.py change

```python
SDKType = Literal["claude", "opencode", "azure"]
```

## Files to Create / Modify

| File | Change |
|------|--------|
| `src/agent_profiles/sdk_config.py` | Add `"azure"` to `SDKType` literal and helper `is_azure_sdk()` |
| `src/agent_profiles/base.py` | Add azure path in `_execute_query()` |
| `src/agent_profiles/azure/__init__.py` | Export azure options for all 5 agents |
| `src/agent_profiles/azure/azure_agent.py` | Base agent options + ReAct loop implementation |
| `src/agent_profiles/azure/azure_proposer.py` | Skill proposer options |
| `src/agent_profiles/azure/azure_prompt_proposer.py` | Prompt proposer options |
| `src/agent_profiles/azure/azure_skill_generator.py` | Skill generator options (includes write_file tool) |
| `src/agent_profiles/azure/azure_prompt_generator.py` | Prompt generator options (includes write_file tool) |
| `scripts/run_loop.py` | Accept `--sdk azure` |
| `scripts/run_eval.py` | Accept `--sdk azure` |
| `pyproject.toml` | Add `openai>=1.0.0` dependency |

## Structured Output

Uses the same Pydantic schemas already in `src/schemas/`:
- `AgentResponse` — base agent
- `SkillProposerResponse` — skill proposer
- `PromptProposerResponse` — prompt proposer
- `ToolGeneratorResponse` — skill generator
- `PromptGeneratorResponse` — prompt generator

Azure OpenAI's `response_format` accepts JSON schema directly, which Pydantic can generate via `.model_json_schema()`.

## Return Format

The azure path in `_execute_query()` returns a list with a single synthetic message dict that mimics the Claude SDK's `ResultMessage` shape, so the existing `AgentTrace` construction in `Agent.run()` works without changes.
