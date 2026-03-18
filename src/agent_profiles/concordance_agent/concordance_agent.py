from pathlib import Path
from src.agent_profiles.options import DeepAgentOptions
from src.agent_profiles.tools import list_files, read_file

PROMPT_FILE = Path(__file__).parent / "prompt.txt"


def get_concordance_agent_options(model=None) -> DeepAgentOptions:
    return DeepAgentOptions(
        system_prompt=PROMPT_FILE.read_text().strip(),
        tools=(list_files, read_file),
        model=model,
    )


def make_concordance_agent_options(model=None):
    def factory():
        return get_concordance_agent_options(model=model)
    return factory


concordance_agent_options = make_concordance_agent_options()
