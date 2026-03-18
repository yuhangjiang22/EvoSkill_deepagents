#!/usr/bin/env python3
"""Run EvoSkill self-improving loop on a single patient (smoke test)."""

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
    patient_id: str = Field(default="1168000029027992")
    max_iterations: int = Field(default=3)
    model: Optional[str] = Field(default=None)
    dataset: Path = Field(default=Path(".dataset/concordance_data.csv"))
    continue_loop: bool = Field(default=False)
    mode: str = Field(default="skill_only")


async def main(settings: Settings):
    data = pd.read_csv(settings.dataset)
    patient_rows = data[data["patient_id"].astype(str) == str(settings.patient_id)]
    if patient_rows.empty:
        print(f"No rows found for patient {settings.patient_id}")
        return

    # Each C-question is its own category; use all questions for both train and val
    train_pools: dict[str, list[tuple[str, str]]] = {}
    val_data: list[tuple[str, str, str]] = []

    for _, row in patient_rows.iterrows():
        cat = str(row.get("category", "unknown"))
        q = str(row["question"])
        g = str(row["ground_truth"])
        train_pools[cat] = [(q, g)]
        val_data.append((q, g, cat))

    print(f"Patient: {settings.patient_id}  questions: {list(train_pools.keys())}")
    print(f"Val samples: {len(val_data)}")

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
        concurrency=2,
        evolution_mode=settings.mode,
        failure_sample_count=2,
        categories_per_batch=2,
        cache_enabled=True,
        reset_feedback=not settings.continue_loop,
        continue_mode=settings.continue_loop,
    )

    loop = SelfImprovingLoop(
        config, agents, manager, train_pools, val_data,
        scorer=score_concordance,
    )
    result = await loop.run()

    print(f"\n[DONE] {settings.max_iterations} iterations, best: {result.best_program} ({result.best_score:.4f})")
    print(f"Best program : {result.best_program}")
    print(f"Best score   : {result.best_score:.2%}")
    print(f"Frontier     : {result.frontier}")


if __name__ == "__main__":
    settings = Settings()
    asyncio.run(main(settings))
