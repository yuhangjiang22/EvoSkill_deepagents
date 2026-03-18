"""Skill generator agent — lazy import to avoid circular imports."""

from pathlib import Path


def get_project_root() -> str:
    """Get the project root directory by looking for pyproject.toml."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return str(parent)
    return str(here.parent.parent.parent)


class _LazyOptions:
    """Lazy proxy for skill_generator_options that defers import until first use."""

    def __init__(self):
        self._opts = None

    def _load(self):
        if self._opts is None:
            from src.agent_profiles.agents import make_skill_generator_options
            self._opts = make_skill_generator_options()

    def __call__(self, *args, **kwargs):
        self._load()
        return self._opts(*args, **kwargs) if callable(self._opts) else self._opts

    def __getattr__(self, name):
        self._load()
        return getattr(self._opts, name)


skill_generator_options = _LazyOptions()

__all__ = ["skill_generator_options", "get_project_root"]
