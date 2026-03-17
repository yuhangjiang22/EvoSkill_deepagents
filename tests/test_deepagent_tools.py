import pytest
from pathlib import Path
from langchain_core.tools import BaseTool
from src.agent_profiles.tools import list_files, read_file, write_file


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
