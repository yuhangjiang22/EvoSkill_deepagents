#!/usr/bin/env python3
"""Run concordance evaluation on a single patient (smoke test)."""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

import pandas as pd
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.agent_profiles import Agent, make_concordance_agent_options
from src.evaluation.concordance_scorer import score_concordance
from src.schemas import AgentResponse


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", cli_parse_args=True
    )
    patient_id: str = Field(default="1168000029027992")
    model: Optional[str] = Field(default=None)
    dataset: Path = Field(default=Path(".dataset/concordance_data.csv"))


async def main(settings: Settings):
    data = pd.read_csv(settings.dataset)
    patient_rows = data[data["patient_id"].astype(str) == str(settings.patient_id)]
    if patient_rows.empty:
        print(f"No rows found for patient {settings.patient_id}")
        return

    agent_opts = make_concordance_agent_options(model=settings.model)()
    agent = Agent(agent_opts, AgentResponse)

    print(f"Patient: {settings.patient_id}  ({len(patient_rows)} questions)\n")
    total_score = 0.0
    for _, row in patient_rows.iterrows():
        question = str(row["question"])
        gold = str(row["ground_truth"])
        category = str(row.get("category", ""))
        trace = await agent.run(question)
        predicted = trace.output.final_answer if trace.output else "(no output)"
        score = score_concordance(question, predicted, gold)
        total_score += score
        status = "[OK]" if score >= 0.8 else "[FAIL]"
        print(f"{status} {category:5s}  predicted={predicted:<17s} gold={gold:<17s} score={score:.1f}")
        if trace.output and trace.output.reasoning:
            print(f"       Reasoning: {trace.output.reasoning[:120]}")
        print()

    n = len(patient_rows)
    print(f"Total: {total_score:.1f}/{n}  avg={total_score/n:.2f}")


if __name__ == "__main__":
    settings = Settings()
    asyncio.run(main(settings))
