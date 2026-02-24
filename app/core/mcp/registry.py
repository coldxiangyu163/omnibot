"""
Tool Registry — unified tool management for MCP tools + built-in tools.

Loads MCP server configs from omnibot.json, starts clients, collects tools.
Provides a single interface for the Agent loop to discover and call tools.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Awaitable

from app.core.mcp.client import MCPClient, MCPServerConfig, MCPTool

logger = logging.getLogger(__name__)


@dataclass
class BuiltinTool:
    """A tool implemented directly in Python."""
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., Awaitable[str]]


class ToolRegistry:
    """
    Central registry for all tools available to the agent.
    Sources: MCP servers (external) + built-in tools (Python functions).
    """

    def __init__(self):
        self._mcp_clients: dict[str, MCPClient] = {}
        self._mcp_tools: dict[str, MCPTool] = {}
        self._builtin_tools: dict[str, BuiltinTool] = {}

    @property
    def all_tools(self) -> list[dict[str, Any]]:
        """Return all tools in OpenAI function-calling format."""
        tools = []
        for t in self._mcp_tools.values():
            tools.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": f"[{t.server_name}] {t.description}",
                    "parameters": t.input_schema,
                },
            })
        for t in self._builtin_tools.values():
            tools.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                },
            })
        return tools

    @property
    def tool_names(self) -> list[str]:
        return list(self._mcp_tools.keys()) + list(self._builtin_tools.keys())

    async def load_from_config(self, config_path: str = "omnibot.json"):
        """Load MCP server configs and start all clients."""
        path = Path(config_path)
        if not path.exists():
            logger.info(f"No config file at {config_path}, running without MCP tools")
            return

        with open(path) as f:
            config = json.load(f)

        servers = config.get("mcpServers", {})
        for name, srv in servers.items():
            sc = MCPServerConfig(
                name=name,
                command=srv["command"],
                args=srv.get("args", []),
                env=srv.get("env", {}),
                transport=srv.get("transport", "stdio"),
                url=srv.get("url"),
            )
            client = MCPClient(sc)
            try:
                tools = await client.start()
                self._mcp_clients[name] = client
                for tool in tools:
                    qualified = f"{name}__{tool.name}" if tool.name in self._mcp_tools else tool.name
                    self._mcp_tools[qualified] = tool
                logger.info(f"Loaded {len(tools)} tools from MCP server '{name}'")
            except Exception as e:
                logger.error(f"Failed to start MCP server '{name}': {e}")

    def register_builtin(self, name: str, description: str,
                         input_schema: dict, handler: Callable[..., Awaitable[str]]):
        """Register a built-in Python tool."""
        self._builtin_tools[name] = BuiltinTool(
            name=name, description=description,
            input_schema=input_schema, handler=handler,
        )

    async def call(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Call a tool by name. Routes to MCP or built-in."""
        if tool_name in self._mcp_tools:
            tool = self._mcp_tools[tool_name]
            client = self._mcp_clients.get(tool.server_name)
            if not client:
                return f"Error: MCP server '{tool.server_name}' not connected"
            actual_name = tool.name  # use original name for MCP call
            return await client.call_tool(actual_name, arguments)

        if tool_name in self._builtin_tools:
            tool = self._builtin_tools[tool_name]
            try:
                return await tool.handler(**arguments)
            except Exception as e:
                return f"Error calling {tool_name}: {e}"

        return f"Error: Unknown tool '{tool_name}'"

    async def shutdown(self):
        """Stop all MCP server processes."""
        for client in self._mcp_clients.values():
            await client.stop()
        self._mcp_clients.clear()
        self._mcp_tools.clear()
        logger.info("All MCP servers stopped")
