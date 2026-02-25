"""Anthropic LLM provider with tool_use support."""
from __future__ import annotations

import json
import uuid
from typing import Any, AsyncIterator

from anthropic import AsyncAnthropic
from app.core.llm.base import LLMProvider
from app.config import settings


class AnthropicProvider(LLMProvider):
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.llm_model

    def _convert_messages(self, messages: list[dict]) -> tuple[str, list[dict]]:
        """Convert OpenAI-format messages to Anthropic format. Returns (system, messages)."""
        system = ""
        anthropic_msgs = []
        for msg in messages:
            role = msg["role"]
            if role == "system":
                system = msg["content"]
            elif role == "assistant":
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
                    "content": [{"type": "tool_result", "tool_use_id": msg["tool_call_id"], "content": msg["content"]}],
                })
            else:
                anthropic_msgs.append({"role": role, "content": msg["content"]})
        return system, anthropic_msgs

    def _convert_tools(self, tools: list[dict[str, Any]] | None) -> list[dict]:
        """Convert OpenAI tool format to Anthropic format."""
        if not tools:
            return []
        anthropic_tools = []
        for t in tools:
            fn = t["function"]
            anthropic_tools.append({
                "name": fn["name"],
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
            })
        return anthropic_tools

    @staticmethod
    def _parse_response(response) -> dict[str, Any]:
        """Parse Anthropic response into unified format."""
        text_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {"name": block.name, "arguments": json.dumps(block.input)},
                })
        return {
            "content": "\n".join(text_parts) if text_parts else None,
            "tool_calls": tool_calls if tool_calls else None,
        }

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
        system, anthropic_msgs = self._convert_messages(messages)
        anthropic_tools = self._convert_tools(tools)

        kwargs: dict[str, Any] = {
            "model": self.model, "max_tokens": 4096, "messages": anthropic_msgs,
        }
        if system:
            kwargs["system"] = system
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        response = await self.client.messages.create(**kwargs)
        return self._parse_response(response)

    async def generate_with_tools_stream(
        self, messages: list[dict], tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Streaming generation with tool calling support."""
        system, anthropic_msgs = self._convert_messages(messages)
        anthropic_tools = self._convert_tools(tools)

        kwargs: dict[str, Any] = {
            "model": self.model, "max_tokens": 4096, "messages": anthropic_msgs,
        }
        if system:
            kwargs["system"] = system
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        content_parts: list[str] = []
        tool_calls: list[dict] = []
        current_tool: dict | None = None
        current_tool_input = ""

        async with self.client.messages.stream(**kwargs) as stream:
            async for event in stream:
                if event.type == "content_block_start":
                    if event.content_block.type == "tool_use":
                        current_tool = {
                            "id": event.content_block.id,
                            "type": "function",
                            "function": {"name": event.content_block.name, "arguments": ""},
                        }
                        current_tool_input = ""
                elif event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        content_parts.append(event.delta.text)
                        yield {"type": "content_delta", "delta": event.delta.text}
                    elif event.delta.type == "input_json_delta":
                        if current_tool:
                            current_tool_input += event.delta.partial_json
                elif event.type == "content_block_stop":
                    if current_tool:
                        current_tool["function"]["arguments"] = current_tool_input
                        tool_calls.append(current_tool)
                        current_tool = None

        if tool_calls:
            yield {"type": "tool_calls", "tool_calls": tool_calls}

        full_content = "".join(content_parts)
        yield {"type": "done", "content": full_content}
