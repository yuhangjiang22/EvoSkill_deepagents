"""Tool definitions and implementations for Azure ReAct agents."""

from pathlib import Path


def list_files(directory: str) -> str:
    """List files in a directory."""
    path = Path(directory)
    if not path.exists():
        return f"Error: directory '{directory}' does not exist."
    entries = sorted(path.iterdir())
    if not entries:
        return "(empty directory)"
    return "\n".join(e.name + ("/" if e.is_dir() else "") for e in entries)


def read_file(path: str) -> str:
    """Read the full text of a file."""
    try:
        return Path(path).read_text()
    except FileNotFoundError:
        return f"Error: file '{path}' not found."
    except Exception as e:
        return f"Error reading '{path}': {e}"


def write_file(path: str, content: str) -> str:
    """Write content to a file, creating parent directories as needed."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"Successfully written to '{path}'."
    except Exception as e:
        return f"Error writing '{path}': {e}"


_LIST_FILES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "list_files",
        "description": "List files and directories at the given path.",
        "parameters": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Absolute or relative path to list."}
            },
            "required": ["directory"],
        },
    },
}

_READ_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read the full text content of a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or relative path to the file."}
            },
            "required": ["path"],
        },
    },
}

_WRITE_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Write text content to a file. Creates parent directories if needed.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to write the file to."},
                "content": {"type": "string", "description": "Text content to write."},
            },
            "required": ["path", "content"],
        },
    },
}


def make_tools(include_write: bool = False) -> tuple[list[dict], dict]:
    """Return (tool_schemas, tool_fn_map) for use with AzureReActRunner.

    Args:
        include_write: Whether to include write_file tool (needed by generator agents).

    Returns:
        Tuple of (list of OpenAI tool schemas, dict mapping tool name -> callable).
    """
    schemas = [_LIST_FILES_SCHEMA, _READ_FILE_SCHEMA]
    fns: dict = {"list_files": list_files, "read_file": read_file}

    if include_write:
        schemas.append(_WRITE_FILE_SCHEMA)
        fns["write_file"] = write_file

    return schemas, fns
