"""Anthropic LLM provider with tool_use support."""
from __future__ import annotations

import json
import uuid
from typing import Any

from anthropic import AsyncAnthropic
from app.core.llm.base import LLMProvider
from app.config import settings


class AnthropicProvider(LLMProvider):
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.llm_model

    async def generate(self, prompt: str, system: str = "", session_id: str | None = None) -> str:
        response = await self.client.messages.create(
            model=self.model, max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    async def generate_with_tools(
        self, messages: list[dict], tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        # Convert OpenAI tool format to Anthropic format
        anthropic_tools = []
        if tools:
            for t in tools:
                fn = t["function"]
                anthropic_tools.append({
                    "name": fn["name"],
                    "description": fn.get("description", ""),
                    "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
                })

        # Convert messages: extract system, handle tool_calls/tool results
        system = ""
        anthropic_msgs = []
        for msg in messages:
            role = msg["role"]
            if role == "system":
                system = msg["content"]
            elif role == "assistant":
                # May contain tool_calls
                content_blocks = []
                if msg.get("content"):
                    content_blocks.append({"type": "text", "text": msg["content"]})
                if msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        args = tc["function"]["arguments"]
                        if isinstance(args, str):
                            args = json.loads(args)
                        content_blocks.append({
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["function"]["name"],
                            "input": args,
                        })
                anthropic_msgs.append({"role": "assistant", "content": content_blocks or msg.get("content", "")})
            elif role == "tool":
                anthropic_msgs.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg["tool_call_id"],
                        "content": msg["content"],
                    }],
                })
            else:
                anthropic_msgs.append({"role": role, "content": msg["content"]})

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": anthropic_msgs,
        }
        if system:
            kwargs["system"] = system
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        response = await self.client.messages.create(**kwargs)

        # Parse response
        text_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input),
                    },
                })

        return {
            "content": "\n".join(text_parts) if text_parts else None,
            "tool_calls": tool_calls if tool_calls else None,
        }
