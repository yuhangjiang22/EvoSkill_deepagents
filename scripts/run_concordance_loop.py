#!/usr/bin/env python3
"""Run EvoSkill self-improving loop on the concordance dataset.

Uses the pre-split train/val column in the CSV.
Train patients provide failure examples; val patients score each iteration.

Usage:
    uv run python scripts/run_concordance_loop.py --num_train_patients 2 --max_iterations 5
    uv run python scripts/run_concordance_loop.py  # full 15/15 split
"""

import asyncio
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

import pandas as pd
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.agent_profiles import (
    Agent,
    make_concordance_agent_options,
    skill_proposer_options,
    prompt_proposer_options,
    skill_generator_options,
    prompt_generator_options,
)
from src.agent_profiles.skill_generator import get_project_root
from src.evaluation.concordance_scorer import score_concordance
from src.loop import SelfImprovingLoop, LoopConfig, LoopAgents
from src.registry import ProgramManager
from src.schemas import (
    AgentResponse,
    SkillProposerResponse,
    PromptProposerResponse,
    ToolGeneratorResponse,
    PromptGeneratorResponse,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", cli_parse_args=True
    )
    num_train_patients: Optional[int] = Field(default=None, description="Limit train patients (None = all)")
    num_val_patients: Optional[int] = Field(default=None, description="Limit val patients (None = all)")
    max_iterations: int = Field(default=5)
    concurrency: int = Field(default=4)
    failure_samples: int = Field(default=3, description="Train samples per iteration")
    categories_per_batch: int = Field(default=3)
    model: Optional[str] = Field(default=None)
    dataset: Path = Field(default=Path(".dataset/concordance_data.csv"))
    continue_loop: bool = Field(default=False)
    mode: str = Field(default="skill_only")


async def main(settings: Settings):
    data = pd.read_csv(settings.dataset)

    train_df = data[data["split"] == "train"]
    val_df = data[data["split"] == "val"]

    # Optionally limit number of patients
    if settings.num_train_patients is not None:
        train_pids = train_df["patient_id"].unique()[:settings.num_train_patients]
        train_df = train_df[train_df["patient_id"].isin(train_pids)]
    if settings.num_val_patients is not None:
        val_pids = val_df["patient_id"].unique()[:settings.num_val_patients]
        val_df = val_df[val_df["patient_id"].isin(val_pids)]

    # Build train_pools: category -> list of (question, ground_truth)
    train_pools: dict[str, list[tuple[str, str]]] = {}
    for _, row in train_df.iterrows():
        cat = str(row["category"])
        train_pools.setdefault(cat, []).append((str(row["question"]), str(row["ground_truth"])))

    # Build val_data: list of (question, ground_truth, category)
    val_data = [
        (str(row["question"]), str(row["ground_truth"]), str(row["category"]))
        for _, row in val_df.iterrows()
    ]

    n_train_patients = train_df["patient_id"].nunique()
    n_val_patients = val_df["patient_id"].nunique()
    print(f"Train: {n_train_patients} patients, {len(train_df)} questions")
    print(f"Val:   {n_val_patients} patients, {len(val_df)} questions")
    print(f"Categories: {sorted(train_pools.keys())}")
    print(f"Train pool sizes: { {k: len(v) for k, v in train_pools.items()} }")

    base_opts = make_concordance_agent_options(model=settings.model)()
    agents = LoopAgents(
        base=Agent(base_opts, AgentResponse),
        skill_proposer=Agent(skill_proposer_options, SkillProposerResponse),
        prompt_proposer=Agent(prompt_proposer_options, PromptProposerResponse),
        skill_generator=Agent(skill_generator_options, ToolGeneratorResponse),
        prompt_generator=Agent(prompt_generator_options, PromptGeneratorResponse),
    )
    manager = ProgramManager(cwd=get_project_root())

    config = LoopConfig(
        max_iterations=settings.max_iterations,
        frontier_size=3,
        no_improvement_limit=settings.max_iterations,
        concurrency=settings.concurrency,
        evolution_mode=settings.mode,
        failure_sample_count=settings.failure_samples,
        categories_per_batch=settings.categories_per_batch,
        cache_enabled=True,
        reset_feedback=not settings.continue_loop,
        continue_mode=settings.continue_loop,
    )

    loop = SelfImprovingLoop(
        config, agents, manager, train_pools, val_data,
        scorer=score_concordance,
    )
    result = await loop.run()

    print(f"\nBest program : {result.best_program}")
    print(f"Best score   : {result.best_score:.2%}  ({result.best_score * len(val_data):.1f}/{len(val_data)} pts)")
    print(f"Frontier     : {result.frontier}")


if __name__ == "__main__":
    settings = Settings()
    asyncio.run(main(settings))
