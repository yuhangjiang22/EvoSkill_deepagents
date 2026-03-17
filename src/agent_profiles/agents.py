"""Factory functions for all 5 EvoSkill deepagents-backed agent options."""

from src.agent_profiles.options import DeepAgentOptions
from src.agent_profiles.tools import list_files, read_file, write_file
from src.agent_profiles.base_agent.prompt import BASE_AGENT_SYSTEM_PROMPT
from src.agent_profiles.skill_proposer.prompt import SKILL_PROPOSER_SYSTEM_PROMPT
from src.agent_profiles.prompt_proposer.prompt import PROMPT_PROPOSER_SYSTEM_PROMPT
from src.agent_profiles.skill_generator.prompt import SKILL_GENERATOR_SYSTEM_PROMPT
from src.agent_profiles.prompt_generator.prompt import PROMPT_GENERATOR_SYSTEM_PROMPT

_READ_ONLY = (list_files, read_file)
_READ_WRITE = (list_files, read_file, write_file)


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
