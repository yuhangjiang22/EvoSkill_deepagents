"""Task configuration registry."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable

ScorerFn = Callable[[str, str, str], float]


@dataclass
class TaskConfig:
    name: str
    make_agent_options: Callable[..., Any]
    scorer: ScorerFn | None = None
    question_col: str = "question"
    answer_col: str = "ground_truth"
    category_col: str = "category"
    column_renames: dict[str, str] = field(default_factory=dict)
    default_dataset: str = ""


_REGISTRY: dict[str, TaskConfig] = {}


def register_task(config: TaskConfig) -> None:
    _REGISTRY[config.name] = config


def get_task(name: str) -> TaskConfig:
    if name not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY.keys()))
        raise KeyError(f"Unknown task {name!r}. Available tasks: {available}")
    return _REGISTRY[name]


def list_tasks() -> list[str]:
    return sorted(_REGISTRY.keys())


def _concordance_scorer(question: str, predicted: str, ground_truth: str) -> float:
    from src.evaluation.concordance_scorer import score_concordance
    return score_concordance(question, predicted, ground_truth)


def _register_builtins() -> None:
    from src.agent_profiles import make_base_agent_options, make_concordance_agent_options

    register_task(TaskConfig(
        name="base",
        make_agent_options=make_base_agent_options,
        scorer=None,
        default_dataset=".dataset/new_runs_base/solved_dataset.csv",
    ))

    register_task(TaskConfig(
        name="concordance",
        make_agent_options=make_concordance_agent_options,
        scorer=_concordance_scorer,
        default_dataset=".dataset/concordance_data.csv",
    ))


_register_builtins()
