from src.agent_profiles.options import DeepAgentOptions
from src.agent_profiles.tools import list_files, read_file, write_file
from src.schemas import AgentResponse


# Use full tool suite for LiveCodeBench (agent can use tools to test/debug)
LIVECODEBENCH_AGENT_TOOLS = (list_files, read_file, write_file)

# NOTE: Question formatting (in livecodebench_format.py) matches Artificial Analysis.
# However, we use default system prompts and tools for better performance.
# Reference: https://artificialanalysis.ai/benchmarks/livecodebench


def make_livecodebench_agent_options(model: str | None = None) -> DeepAgentOptions:
    """Create DeepAgentOptions for LiveCodeBench evaluation.

    Args:
        model: Model to use (e.g., "opus", "sonnet"). If None, uses default.

    Returns:
        DeepAgentOptions configured for LiveCodeBench.
    """
    return DeepAgentOptions(
        system_prompt="You are an expert competitive programmer. Solve the given coding problem by writing correct, efficient Python code.",
        tools=LIVECODEBENCH_AGENT_TOOLS,
        model=model,
    )


def get_livecodebench_agent_options(
    model: str | None = None,
) -> DeepAgentOptions:
    """Factory function that creates agent options for LiveCodeBench evaluation.

    Args:
        model: Model to use (e.g., "opus", "sonnet"). If None, uses default.
    """
    return make_livecodebench_agent_options(model=model)


# For backward compatibility, expose the factory as the options
livecodebench_agent_options = get_livecodebench_agent_options
