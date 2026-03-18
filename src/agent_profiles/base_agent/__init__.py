"""Base agent — lightweight shim so runner.py can call get_base_agent_options()."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROMPT_FILE = Path(__file__).parent / "prompt.txt"


@dataclass
class _BaseAgentCompat:
    """Minimal compatibility shim with the fields ProgramConfig expects."""
    system_prompt: Any
    allowed_tools: list = field(default_factory=list)
    output_format: Any = None


def get_base_agent_options(model=None) -> _BaseAgentCompat:
    """Return base agent options compatible with ProgramConfig fields."""
    prompt_text = PROMPT_FILE.read_text().strip()
    return _BaseAgentCompat(system_prompt=prompt_text)


def make_base_agent_options(model=None):
    def factory():
        return get_base_agent_options(model=model)
    return factory


base_agent_options = get_base_agent_options

__all__ = ["PROMPT_FILE", "get_base_agent_options", "make_base_agent_options", "base_agent_options"]
