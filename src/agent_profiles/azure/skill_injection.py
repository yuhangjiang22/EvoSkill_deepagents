"""Inject .claude/skills/ content into a system prompt for non-Claude-Code agents."""

from pathlib import Path


def inject_skills(base_prompt: str, skills_dir: Path | None = None) -> str:
    """Read all SKILL.md files and append them to the system prompt.

    Args:
        base_prompt: The base system prompt text.
        skills_dir: Directory to scan. Defaults to .claude/skills/ relative to cwd.

    Returns:
        System prompt with skill content appended, or base_prompt unchanged if no skills.
    """
    if skills_dir is None:
        skills_dir = Path(".claude/skills")

    if not skills_dir.exists():
        return base_prompt

    skill_texts = []
    for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
        skill_name = skill_file.parent.name
        content = skill_file.read_text().strip()
        if content:
            skill_texts.append(f"## Skill: {skill_name}\n{content}")

    if not skill_texts:
        return base_prompt

    return base_prompt + "\n\n" + "\n\n".join(skill_texts)
