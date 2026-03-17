"""Options dataclass for deepagents-backed agents."""

from collections.abc import Sequence
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
    tools: Sequence[BaseTool] = field(default_factory=tuple)
    model: str | None = None
