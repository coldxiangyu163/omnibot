"""Tests for MCP client and tool registry."""
import pytest
import asyncio
from app.core.mcp.client import MCPClient, MCPServerConfig, MCPTool
from app.core.mcp.registry import ToolRegistry


class TestMCPTool:
    def test_tool_creation(self):
        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {}},
            server_name="test_server",
        )
        assert tool.name == "test_tool"
        assert tool.server_name == "test_server"


class TestMCPServerConfig:
    def test_default_transport(self):
        config = MCPServerConfig(name="test", command="echo")
        assert config.transport == "stdio"
        assert config.args == []
        assert config.env == {}


class TestToolRegistry:
    @pytest.fixture
    def registry(self):
        return ToolRegistry()

    def test_empty_registry(self, registry):
        assert registry.all_tools == []
        assert registry.tool_names == []

    @pytest.mark.asyncio
    async def test_register_builtin(self, registry):
        async def handler(query: str) -> str:
            return f"result for {query}"

        registry.register_builtin(
            name="test_search",
            description="Test search tool",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            handler=handler,
        )

        assert "test_search" in registry.tool_names
        assert len(registry.all_tools) == 1
        assert registry.all_tools[0]["function"]["name"] == "test_search"

    @pytest.mark.asyncio
    async def test_call_builtin(self, registry):
        async def handler(query: str) -> str:
            return f"found: {query}"

        registry.register_builtin(
            name="search",
            description="Search",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
            handler=handler,
        )

        result = await registry.call("search", {"query": "hello"})
        assert result == "found: hello"

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self, registry):
        result = await registry.call("nonexistent", {})
        assert "Unknown tool" in result

    @pytest.mark.asyncio
    async def test_load_missing_config(self, registry):
        await registry.load_from_config("/nonexistent/path.json")
        assert registry.tool_names == []
