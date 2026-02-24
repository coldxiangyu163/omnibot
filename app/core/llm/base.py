"""LLM Provider base class with tool-calling support."""
from abc import ABC, abstractmethod
from typing import Any


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
