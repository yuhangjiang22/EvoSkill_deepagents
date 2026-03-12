from pathlib import Path
from src.agent_profiles.azure.skill_injection import inject_skills

def test_no_skills_dir(tmp_path):
    result = inject_skills("base prompt", skills_dir=tmp_path / "nonexistent")
    assert result == "base prompt"

def test_empty_skills_dir(tmp_path):
    result = inject_skills("base prompt", skills_dir=tmp_path)
    assert result == "base prompt"

def test_single_skill_injected(tmp_path):
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("Do X when Y.")
    result = inject_skills("base prompt", skills_dir=tmp_path)
    assert "base prompt" in result
    assert "my-skill" in result
    assert "Do X when Y." in result

def test_multiple_skills_sorted(tmp_path):
    for name in ["z-skill", "a-skill"]:
        d = tmp_path / name
        d.mkdir()
        (d / "SKILL.md").write_text(f"Content of {name}")
    result = inject_skills("base", skills_dir=tmp_path)
    assert result.index("a-skill") < result.index("z-skill")
