"""OpenAI LLM provider with function calling support."""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

from openai import AsyncOpenAI
from app.core.llm.base import LLMProvider
from app.config import settings


class OpenAIProvider(LLMProvider):
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.llm_model

    async def generate(self, prompt: str, system: str = "", session_id: str | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = await self.client.chat.completions.create(
            model=self.model, messages=messages,
        )
        return response.choices[0].message.content or ""

    async def generate_with_tools(
        self, messages: list[dict], tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"model": self.model, "messages": messages}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await self.client.chat.completions.create(**kwargs)
        msg = response.choices[0].message

        result: dict[str, Any] = {"content": msg.content, "tool_calls": None}

        if msg.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]

        return result

    async def generate_with_tools_stream(
        self, messages: list[dict], tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Streaming generation with tool calling support."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        stream = await self.client.chat.completions.create(**kwargs)

        content_parts: list[str] = []
        tool_calls_acc: dict[int, dict] = {}  # index -> accumulated tool call

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue

            # Accumulate content
            if delta.content:
                content_parts.append(delta.content)
                yield {"type": "content_delta", "delta": delta.content}

            # Accumulate tool calls (streamed in fragments)
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_calls_acc:
                        tool_calls_acc[idx] = {
                            "id": tc_delta.id or "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        }
                    acc = tool_calls_acc[idx]
                    if tc_delta.id:
                        acc["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            acc["function"]["name"] += tc_delta.function.name
                        if tc_delta.function.arguments:
                            acc["function"]["arguments"] += tc_delta.function.arguments

        # Emit completed tool calls if any
        if tool_calls_acc:
            tool_calls = [tool_calls_acc[i] for i in sorted(tool_calls_acc.keys())]
            yield {"type": "tool_calls", "tool_calls": tool_calls}

        full_content = "".join(content_parts)
        yield {"type": "done", "content": full_content}
