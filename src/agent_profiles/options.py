# src/agent_profiles/options.py
"""Options dataclass for deepagents-backed agents."""

from dataclasses import dataclass, field


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
