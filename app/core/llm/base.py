"""LLM Provider base class with tool-calling support."""
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator


class LLMProvider(ABC):
    """Base class for LLM providers. Must support both plain generation and tool calling."""

    @abstractmethod
    async def generate(self, prompt: str, system: str = "", session_id: str | None = None) -> str:
        """Simple text generation (backward compatible)."""
        ...

    @abstractmethod
    async def generate_with_tools(
        self, messages: list[dict], tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Generate with optional tool calling.

        Returns:
            {
                "content": str | None,        # text response
                "tool_calls": list | None,     # tool calls if any
            }
        """
        ...

    async def generate_with_tools_stream(
        self, messages: list[dict], tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Streaming generation with tool calling support.

        Yields chunks:
            {"type": "content_delta", "delta": "partial text"}
            {"type": "tool_calls", "tool_calls": [...]}  # complete tool calls
            {"type": "done", "content": "full text"}

        Default implementation falls back to non-streaming.
        """
        result = await self.generate_with_tools(messages, tools)
        if result.get("tool_calls"):
            yield {"type": "tool_calls", "tool_calls": result["tool_calls"]}
        if result.get("content"):
            yield {"type": "content_delta", "delta": result["content"]}
            yield {"type": "done", "content": result["content"]}
        else:
            yield {"type": "done", "content": ""}
