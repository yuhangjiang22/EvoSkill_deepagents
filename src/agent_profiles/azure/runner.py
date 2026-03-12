"""Azure OpenAI ReAct loop runner."""

import json
import time
import uuid
from typing import Any


class AzureReActRunner:
    """Two-phase ReAct loop using Azure OpenAI.

    Phase 1: Tool loop — model calls tools until finish_reason != tool_calls.
    Phase 2: Structured output — one final call with json_schema response_format.
    """

    def __init__(
        self,
        client: Any,
        deployment: str,
        system_prompt: str,
        tool_schemas: list[dict],
        tool_fns: dict[str, Any],
        output_schema: dict,
        max_turns: int = 30,
    ):
        self.client = client
        self.deployment = deployment
        self.system_prompt = system_prompt
        self.tool_schemas = tool_schemas
        self.tool_fns = tool_fns
        self.output_schema = output_schema
        self.max_turns = max_turns

    def run(self, query: str) -> dict:
        """Run the ReAct loop for a single query."""
        start_ms = int(time.time() * 1000)
        messages: list[dict] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": query},
        ]
        total_input = 0
        total_output = 0
        turns = 0

        # Phase 1: ReAct tool loop
        while turns < self.max_turns:
            turns += 1
            kwargs: dict = {"model": self.deployment, "messages": messages}
            if self.tool_schemas:
                kwargs["tools"] = self.tool_schemas
                kwargs["tool_choice"] = "auto"

            response = self.client.chat.completions.create(**kwargs)

            if response.usage:
                total_input += response.usage.prompt_tokens
                total_output += response.usage.completion_tokens

            choice = response.choices[0]
            messages.append(choice.message.model_dump())

            if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
                for tool_call in choice.message.tool_calls:
                    name = tool_call.function.name
                    try:
                        args = json.loads(tool_call.function.arguments)
                        result_text = (
                            str(self.tool_fns[name](**args))
                            if name in self.tool_fns
                            else f"Unknown tool: {name}"
                        )
                    except Exception as e:
                        result_text = f"Error: {e}"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_text,
                    })
            else:
                break  # Model finished reasoning

        # Phase 2: Extract structured output
        final_response = self.client.chat.completions.create(
            model=self.deployment,
            messages=messages + [
                {"role": "user", "content": "Provide your final answer in the required JSON format."}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "output", "schema": self.output_schema, "strict": False},
            },
        )
        if final_response.usage:
            total_input += final_response.usage.prompt_tokens
            total_output += final_response.usage.completion_tokens
        turns += 1

        raw_text = final_response.choices[0].message.content or ""
        try:
            structured = json.loads(raw_text)
            is_error = False
        except (json.JSONDecodeError, TypeError):
            structured = None
            is_error = True

        return {
            "structured_output": structured,
            "result": raw_text,
            "duration_ms": int(time.time() * 1000) - start_ms,
            "num_turns": turns,
            "usage": {"input_tokens": total_input, "output_tokens": total_output},
            "total_cost_usd": 0.0,
            "is_error": is_error,
            "session_id": str(uuid.uuid4()),
            "uuid": str(uuid.uuid4()),
            "model": self.deployment,
            "tools": list(self.tool_fns.keys()),
            "messages": messages,
        }
