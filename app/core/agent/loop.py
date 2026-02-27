"""
Agent Loop — ReAct (Reason + Act) execution engine.

The agent iteratively:
1. Sends messages + available tools to LLM
2. If LLM returns tool calls → execute them → feed results back
3. If LLM returns text → done

Supports configurable max iterations, streaming, and conversation memory.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from app.core.mcp.registry import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class ToolCallResult:
    """Result of a single tool call within an agent step."""
    tool_name: str
    arguments: dict[str, Any]
    result: str
    duration_ms: int = 0


@dataclass
class AgentStep:
    """One iteration of the agent loop."""
    step_number: int
    reasoning: str | None = None
    tool_calls: list[ToolCallResult] = field(default_factory=list)
    response: str | None = None


@dataclass
class AgentResult:
    """Final result of an agent run."""
    response: str
    steps: list[AgentStep] = field(default_factory=list)
    total_tool_calls: int = 0
    total_duration_ms: int = 0


class AgentLoop:
    """
    ReAct agent loop. Coordinates LLM reasoning with tool execution.

    Usage:
        loop = AgentLoop(llm=provider, registry=registry)
        result = await loop.run("What's the weather in Tokyo?")
    """

    def __init__(
        self,
        llm,  # LLMProvider instance
        registry: ToolRegistry,
        system_prompt: str = "",
        max_iterations: int = 10,
    ):
        self.llm = llm
        self.registry = registry
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations

    async def run(
        self,
        user_message: str,
        conversation: list[dict] | None = None,
    ) -> AgentResult:
        """
        Run the agent loop until LLM produces a final text response
        or max_iterations is reached.
        """
        start = time.monotonic()
        steps: list[AgentStep] = []
        total_tool_calls = 0

        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        if conversation:
            messages.extend(conversation)
        messages.append({"role": "user", "content": user_message})

        tools = self.registry.all_tools

        for i in range(self.max_iterations):
            step = AgentStep(step_number=i + 1)

            # Ask LLM (with tools if available)
            if tools:
                response = await self.llm.generate_with_tools(
                    messages=messages, tools=tools,
                )
            else:
                response = await self.llm.generate_with_tools(
                    messages=messages, tools=[],
                )

            # Case 1: LLM returns tool calls
            if response.get("tool_calls"):
                # Add assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": response.get("content", ""),
                    "tool_calls": response["tool_calls"],
                })

                step.reasoning = response.get("content")

                for tc in response["tool_calls"]:
                    tool_name = tc["function"]["name"]
                    try:
                        arguments = tc["function"]["arguments"]
                        if isinstance(arguments, str):
                            import json
                            arguments = json.loads(arguments)
                    except Exception:
                        arguments = {}

                    t0 = time.monotonic()
                    result_text = await self.registry.call(tool_name, arguments)
                    duration = int((time.monotonic() - t0) * 1000)

                    tcr = ToolCallResult(
                        tool_name=tool_name,
                        arguments=arguments,
                        result=result_text,
                        duration_ms=duration,
                    )
                    step.tool_calls.append(tcr)
                    total_tool_calls += 1

                    logger.info(
                        f"Step {i+1}: {tool_name}({arguments}) "
                        f"→ {len(result_text)} chars in {duration}ms"
                    )

                    # Feed tool result back
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result_text,
                    })

                steps.append(step)
                continue

            # Case 2: LLM returns final text
            final_text = response.get("content", "")
            step.response = final_text
            steps.append(step)

            elapsed = int((time.monotonic() - start) * 1000)
            return AgentResult(
                response=final_text,
                steps=steps,
                total_tool_calls=total_tool_calls,
                total_duration_ms=elapsed,
            )

        # Max iterations reached
        elapsed = int((time.monotonic() - start) * 1000)
        return AgentResult(
            response="I've reached the maximum number of steps. Here's what I found so far based on the tools I used.",
            steps=steps,
            total_tool_calls=total_tool_calls,
            total_duration_ms=elapsed,
        )

    async def run_stream(
        self,
        user_message: str,
        conversation: list[dict] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Streaming version of run(). Yields events as they happen:

            {"event": "step_start", "step": 1}
            {"event": "content_delta", "delta": "partial text..."}
            {"event": "tool_start", "tool": "name", "arguments": {...}}
            {"event": "tool_result", "tool": "name", "result": "...", "duration_ms": 42}
            {"event": "done", "response": "full text", "total_tool_calls": 3, "duration_ms": 1234}
        """
        start = time.monotonic()
        total_tool_calls = 0

        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        if conversation:
            messages.extend(conversation)
        messages.append({"role": "user", "content": user_message})

        tools = self.registry.all_tools

        for i in range(self.max_iterations):
            yield {"event": "step_start", "step": i + 1}

            full_content = ""
            pending_tool_calls = None

            async for chunk in self.llm.generate_with_tools_stream(
                messages=messages, tools=tools if tools else [],
            ):
                if chunk["type"] == "content_delta":
                    yield {"event": "content_delta", "delta": chunk["delta"]}

                elif chunk["type"] == "tool_calls":
                    pending_tool_calls = chunk["tool_calls"]

                elif chunk["type"] == "done":
                    full_content = chunk.get("content", "")

            # If tool calls, execute them
            if pending_tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": full_content or "",
                    "tool_calls": pending_tool_calls,
                })

                for tc in pending_tool_calls:
                    tool_name = tc["function"]["name"]
                    try:
                        arguments = tc["function"]["arguments"]
                        if isinstance(arguments, str):
                            import json
                            arguments = json.loads(arguments)
                    except Exception:
                        arguments = {}

                    yield {"event": "tool_start", "tool": tool_name, "arguments": arguments}

                    t0 = time.monotonic()
                    result_text = await self.registry.call(tool_name, arguments)
                    duration = int((time.monotonic() - t0) * 1000)
                    total_tool_calls += 1

                    yield {
                        "event": "tool_result",
                        "tool": tool_name,
                        "result": result_text[:500],
                        "duration_ms": duration,
                    }

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result_text,
                    })

                continue

            # No tool calls — final response
            elapsed = int((time.monotonic() - start) * 1000)
            yield {
                "event": "done",
                "response": full_content,
                "total_tool_calls": total_tool_calls,
                "duration_ms": elapsed,
            }
            return

        # Max iterations
        elapsed = int((time.monotonic() - start) * 1000)
        yield {
            "event": "done",
            "response": "I've reached the maximum number of steps.",
            "total_tool_calls": total_tool_calls,
            "duration_ms": elapsed,
        }
