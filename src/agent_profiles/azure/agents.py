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
    """Return Azure agent options for the base agent."""
    return _make_options(
        system_prompt=BASE_AGENT_SYSTEM_PROMPT,
        output_schema=AgentResponse.model_json_schema(),
        include_write=False,
    )


def make_azure_skill_proposer_options(model: str | None = None) -> dict:
    """Return Azure agent options for the skill proposer agent."""
    return _make_options(
        system_prompt=SKILL_PROPOSER_SYSTEM_PROMPT,
        output_schema=SkillProposerResponse.model_json_schema(),
        include_write=False,
    )


def make_azure_prompt_proposer_options(model: str | None = None) -> dict:
    """Return Azure agent options for the prompt proposer agent."""
    return _make_options(
        system_prompt=PROMPT_PROPOSER_SYSTEM_PROMPT,
        output_schema=PromptProposerResponse.model_json_schema(),
        include_write=False,
    )


def make_azure_skill_generator_options(model: str | None = None) -> dict:
    """Return Azure agent options for the skill generator agent."""
    return _make_options(
        system_prompt=SKILL_GENERATOR_SYSTEM_PROMPT,
        output_schema=ToolGeneratorResponse.model_json_schema(),
        include_write=True,
    )


def make_azure_prompt_generator_options(model: str | None = None) -> dict:
    """Return Azure agent options for the prompt generator agent."""
    return _make_options(
        system_prompt=PROMPT_GENERATOR_SYSTEM_PROMPT,
        output_schema=PromptGeneratorResponse.model_json_schema(),
        include_write=True,
    )
