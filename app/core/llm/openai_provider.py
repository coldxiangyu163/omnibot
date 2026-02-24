"""OpenAI LLM provider with function calling support."""
from __future__ import annotations

import json
from typing import Any

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
