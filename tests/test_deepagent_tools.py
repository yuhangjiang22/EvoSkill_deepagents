import pytest
from pathlib import Path
from langchain_core.tools import BaseTool
from src.agent_profiles.tools import list_files, read_file, write_file
from src.agent_profiles.options import DeepAgentOptions
from src.agent_profiles.agents import (
    make_base_agent_options,
    make_skill_proposer_options,
    make_prompt_proposer_options,
    make_skill_generator_options,
    make_prompt_generator_options,
)


def test_tools_are_langchain_tools():
    assert isinstance(list_files, BaseTool)
    assert isinstance(read_file, BaseTool)
    assert isinstance(write_file, BaseTool)


def test_list_files(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "b.txt").write_text("world")
    result = list_files.invoke({"directory": str(tmp_path)})
    assert "a.txt" in result
    assert "b.txt" in result


def test_read_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("file content here")
    result = read_file.invoke({"path": str(f)})
    assert result == "file content here"


def test_read_file_not_found():
    result = read_file.invoke({"path": "/nonexistent/path/file.txt"})
    assert "Error" in result


def test_write_file(tmp_path):
    path = str(tmp_path / "subdir" / "skill.md")
    result = write_file.invoke({"path": path, "content": "# My Skill"})
    assert "written" in result.lower()
    assert Path(path).read_text() == "# My Skill"


def test_list_files_on_file_path(tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("content")
    result = list_files.invoke({"directory": str(f)})
    assert "Error" in result


def test_base_agent_options_has_read_only_tools():
    opts = make_base_agent_options()
    assert isinstance(opts, DeepAgentOptions)
    tool_names = [t.name for t in opts.tools]
    assert "list_files" in tool_names
    assert "read_file" in tool_names
    assert "write_file" not in tool_names


def test_skill_generator_options_has_write_tool():
    opts = make_skill_generator_options()
    tool_names = [t.name for t in opts.tools]
    assert "write_file" in tool_names


def test_prompt_generator_options_has_write_tool():
    opts = make_prompt_generator_options()
    tool_names = [t.name for t in opts.tools]
    assert "write_file" in tool_names


def test_make_base_agent_options_accepts_model():
    opts = make_base_agent_options(model="gpt-4o")
    assert opts.model == "gpt-4o"
