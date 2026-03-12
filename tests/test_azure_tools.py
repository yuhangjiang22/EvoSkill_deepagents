import pytest
from pathlib import Path
from src.agent_profiles.azure.tools import make_tools, list_files, read_file

def test_list_files(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "b.txt").write_text("world")
    result = list_files(str(tmp_path))
    assert "a.txt" in result
    assert "b.txt" in result

def test_read_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("file content here")
    result = read_file(str(f))
    assert result == "file content here"

def test_read_file_not_found():
    result = read_file("/nonexistent/path/file.txt")
    assert "Error" in result

def test_make_tools_returns_schemas_and_fns():
    schemas, fns = make_tools(include_write=False)
    assert len(schemas) == 2
    assert "list_files" in fns
    assert "read_file" in fns
    assert "write_file" not in fns

def test_make_tools_with_write():
    schemas, fns = make_tools(include_write=True)
    assert len(schemas) == 3
    assert "write_file" in fns

def test_write_file(tmp_path):
    from src.agent_profiles.azure.tools import write_file
    path = str(tmp_path / "subdir" / "skill.md")
    result = write_file(path, "# My Skill")
    assert "written" in result.lower()
    assert Path(path).read_text() == "# My Skill"
