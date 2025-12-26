import asyncio
from dataclasses import dataclass
from typing import Generic, TypeVar

from tqdm.asyncio import tqdm_asyncio

from src.agent_profiles.base import Agent, AgentTrace

T = TypeVar("T")


@dataclass
class EvalResult(Generic[T]):
    """Result of evaluating a single question."""
    question: str
    ground_truth: str
    trace: AgentTrace[T] | None


async def evaluate(
    agent: Agent[T],
    items: list[tuple[str, str]],
    max_concurrent: int = 5,
) -> list[EvalResult[T]]:
    """
    Run agent on multiple questions in parallel.

    Args:
        agent: The agent to evaluate
        items: List of (question, ground_truth) tuples
        max_concurrent: Max concurrent agent runs (default 5)

    Returns:
        List of EvalResult containing question, ground_truth, and trace
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def run_one(question: str, ground_truth: str) -> EvalResult[T]:
        async with semaphore:
            try:
                trace = await agent.run(question)
            except Exception as e:
                print(f"Failed on question: {question[:50]}... Error: {e}")
                trace = None
            return EvalResult(question=question, ground_truth=ground_truth, trace=trace)

    tasks = [run_one(q, gt) for q, gt in items]
    results = await tqdm_asyncio.gather(*tasks, desc="Evaluating")
    return results
