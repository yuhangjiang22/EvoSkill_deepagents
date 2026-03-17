"""LangChain tool definitions for deepagents."""

from pathlib import Path
from langchain_core.tools import tool


@tool
def list_files(directory: str) -> str:
    """List files and directories at the given path."""
    path = Path(directory)
    if not path.exists():
        return f"Error: directory '{directory}' does not exist."
    entries = sorted(path.iterdir())
    if not entries:
        return "(empty directory)"
    return "\n".join(e.name + ("/" if e.is_dir() else "") for e in entries)


@tool
def read_file(path: str) -> str:
    """Read the full text content of a file."""
    try:
        return Path(path).read_text()
    except FileNotFoundError:
        return f"Error: file '{path}' not found."
    except Exception as e:
        return f"Error reading '{path}': {e}"


@tool
def write_file(path: str, content: str) -> str:
    """Write text content to a file, creating parent directories as needed."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"Successfully written to '{path}'."
    except Exception as e:
        return f"Error writing '{path}': {e}"
