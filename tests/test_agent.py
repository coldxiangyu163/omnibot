"""Tests for the agent loop."""
import pytest
from unittest.mock import AsyncMock
from app.core.agent.loop import AgentLoop, AgentResult
from app.core.mcp.registry import ToolRegistry


class TestAgentLoop:
    @pytest.fixture
    def registry(self):
        return ToolRegistry()

    @pytest.fixture
    def mock_llm_no_tools(self):
        """LLM that always returns text, no tool calls."""
        llm = AsyncMock()
        llm.generate_with_tools = AsyncMock(return_value={
            "content": "The answer is 42.",
            "tool_calls": None,
        })
        return llm

    @pytest.fixture
    def mock_llm_with_tools(self):
        """LLM that calls a tool first, then returns text."""
        llm = AsyncMock()
        call_count = 0

        async def side_effect(messages, tools):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "content": "Let me search for that.",
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "search",
                            "arguments": '{"query": "test"}',
                        },
                    }],
                }
            return {
                "content": "Based on the search results: found it!",
                "tool_calls": None,
            }

        llm.generate_with_tools = AsyncMock(side_effect=side_effect)
        return llm

    @pytest.mark.asyncio
    async def test_simple_response(self, mock_llm_no_tools, registry):
        loop = AgentLoop(llm=mock_llm_no_tools, registry=registry)
        result = await loop.run("What is 2+2?")
        assert isinstance(result, AgentResult)
        assert result.response == "The answer is 42."
        assert result.total_tool_calls == 0
        assert len(result.steps) == 1

    @pytest.mark.asyncio
    async def test_tool_calling(self, mock_llm_with_tools, registry):
        async def search_handler(query: str) -> str:
            return f"Search result for: {query}"

        registry.register_builtin(
            name="search",
            description="Search",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
            handler=search_handler,
        )

        loop = AgentLoop(llm=mock_llm_with_tools, registry=registry)
        result = await loop.run("Search for test")
        assert result.total_tool_calls == 1
        assert len(result.steps) == 2
        assert result.steps[0].tool_calls[0].tool_name == "search"
        assert "found it" in result.response

    @pytest.mark.asyncio
    async def test_max_iterations(self, registry):
        """LLM that always returns tool calls should hit max iterations."""
        llm = AsyncMock()
        llm.generate_with_tools = AsyncMock(return_value={
            "content": "Calling tool...",
            "tool_calls": [{
                "id": "call_loop",
                "type": "function",
                "function": {"name": "noop", "arguments": "{}"},
            }],
        })

        async def noop_handler() -> str:
            return "ok"

        registry.register_builtin(
            name="noop", description="No-op",
            input_schema={"type": "object", "properties": {}},
            handler=noop_handler,
        )

        loop = AgentLoop(llm=llm, registry=registry, max_iterations=3)
        result = await loop.run("Loop forever")
        assert result.total_tool_calls == 3
        assert "maximum" in result.response.lower()
