import asyncio
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Generic, Optional, Type, TypeVar

from langchain_core.messages import AIMessage
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

try:
    from deepagents import create_deep_agent
except ImportError:
    create_deep_agent = None  # type: ignore


class AgentTrace(BaseModel, Generic[T]):
    """Metadata and output from an agent run."""

    uuid: str
    session_id: str
    model: str
    tools: list[str]

    duration_ms: int
    total_cost_usd: float
    num_turns: int
    usage: dict[str, Any]
    result: str
    is_error: bool

    output: Optional[T] = None
    parse_error: Optional[str] = None
    raw_structured_output: Optional[Any] = None
    messages: list[Any]

    model_config = {"arbitrary_types_allowed": True}

    def summarize(
        self,
        head_chars: int = 60_000,
        tail_chars: int = 60_000,
    ) -> str:
        lines = [
            f"Model: {self.model}",
            f"Turns: {self.num_turns}",
            f"Duration: {self.duration_ms}ms",
            f"Is Error: {self.is_error}",
        ]

        if self.parse_error:
            lines.append(f"Parse Error: {self.parse_error}")

        if self.output:
            lines.append(f"Output: {self.output}")

        result_str = str(self.result) if self.result else ""

        if self.parse_error and len(result_str) > (head_chars + tail_chars):
            truncated_middle = len(result_str) - head_chars - tail_chars
            lines.append(f"\n## Result (truncated, {truncated_middle:,} chars omitted)")
            lines.append(f"### Start:\n{result_str[:head_chars]}")
            lines.append(f"\n[... {truncated_middle:,} characters truncated ...]\n")
            lines.append(f"### End:\n{result_str[-tail_chars:]}")
        else:
            lines.append(f"\n## Full Result\n{result_str}")

        return "\n".join(lines)


def _get_project_root() -> Path:
    """Return project root (directory containing pyproject.toml)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


class Agent(Generic[T]):
    """Wrapper for running deepagents-backed agents.

    Args:
        options: DeepAgentOptions instance.
        response_model: Pydantic model for structured output validation.
    """

    TIMEOUT_SECONDS = 1200  # 20 minutes
    MAX_RETRIES = 3
    INITIAL_BACKOFF = 30  # seconds

    def __init__(self, options: Any, response_model: Type[T]):
        self._options = options
        self.response_model = response_model

    def _get_options(self) -> Any:
        if callable(self._options):
            return self._options()
        return self._options

    async def _execute_query(self, query: str) -> dict:
        options = self._get_options()
        project_root = _get_project_root()

        # Build kwargs; real sub-packages only needed when running against live backend.
        # In tests, create_deep_agent is patched and these kwargs are ignored by the mock.
        try:
            from deepagents.backends import FilesystemBackend
            from langchain_openai import AzureChatOpenAI

            deployment = options.model or os.environ.get("AZURE_OPENAI_DEPLOYMENT", "")
            model = AzureChatOpenAI(
                azure_deployment=deployment,
                azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
                api_key=os.environ.get("AZURE_OPENAI_API_KEY", ""),
                api_version="2024-08-01-preview",
            )
            backend = FilesystemBackend(root_dir=str(project_root), virtual_mode=True)
        except ImportError:
            model = None
            backend = None

        agent = create_deep_agent(
            model=model,
            tools=list(options.tools),
            system_prompt=options.system_prompt,
            response_format=self.response_model,
            backend=backend,
            skills=[".claude/skills/"],
        )

        return await agent.ainvoke({"messages": [{"role": "user", "content": query}]})

    async def _run_with_retry(self, query: str) -> dict:
        last_error: Exception | None = None
        backoff = self.INITIAL_BACKOFF

        for attempt in range(self.MAX_RETRIES):
            try:
                async with asyncio.timeout(self.TIMEOUT_SECONDS):
                    return await self._execute_query(query)
            except asyncio.TimeoutError:
                last_error = TimeoutError(
                    f"Query timed out after {self.TIMEOUT_SECONDS}s"
                )
                logger.warning(
                    f"Attempt {attempt + 1}/{self.MAX_RETRIES} timed out. Retrying in {backoff}s..."
                )
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}. Retrying in {backoff}s..."
                )

            if attempt < self.MAX_RETRIES - 1:
                await asyncio.sleep(backoff)
                backoff *= 2

        raise last_error if last_error else RuntimeError("All retries exhausted")

    async def run(self, query: str) -> "AgentTrace[T]":
        start_ms = int(time.time() * 1000)
        options = self._get_options()

        state = await self._run_with_retry(query)

        messages = state.get("messages", [])
        raw_structured_output = state.get("structured_output")

        # Extract text from last AI message
        result_text = ""
        num_turns = 0
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                if not result_text:
                    result_text = msg.content or ""
                num_turns += 1

        # Validate structured output
        output = None
        parse_error = None
        if raw_structured_output is not None:
            if isinstance(raw_structured_output, self.response_model):
                output = raw_structured_output
            else:
                try:
                    output = self.response_model.model_validate(raw_structured_output)
                except (ValidationError, TypeError) as e:
                    parse_error = f"{type(e).__name__}: {e}"
        else:
            parse_error = "No structured output returned (context limit likely exceeded)"

        deployment = options.model or os.environ.get("AZURE_OPENAI_DEPLOYMENT", "unknown")

        return AgentTrace(
            uuid=str(uuid.uuid4()),
            session_id=str(uuid.uuid4()),
            model=deployment,
            tools=[t.name for t in options.tools],
            duration_ms=int(time.time() * 1000) - start_ms,
            total_cost_usd=0.0,
            num_turns=num_turns,
            usage={},
            result=result_text,
            is_error=parse_error is not None,
            output=output,
            parse_error=parse_error,
            raw_structured_output=raw_structured_output,
            messages=messages,
        )
