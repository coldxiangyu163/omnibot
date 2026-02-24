"""
MCP Client — connects to MCP servers via stdio or SSE transport.

Handles lifecycle: start server process → initialize → list tools → call tools → shutdown.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """A tool discovered from an MCP server."""
    name: str
    description: str
    input_schema: dict[str, Any]
    server_name: str


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server."""
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    transport: str = "stdio"  # "stdio" or "sse"
    url: str | None = None    # for SSE transport


class MCPClient:
    """
    Lightweight MCP client using JSON-RPC over stdio.
    Zero external dependencies — just subprocess + JSON.
    """

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.process: asyncio.subprocess.Process | None = None
        self.tools: list[MCPTool] = []
        self._request_id = 0
        self._pending: dict[int, asyncio.Future] = {}
        self._reader_task: asyncio.Task | None = None
        self._ready = False

    @property
    def name(self) -> str:
        return self.config.name

    async def start(self) -> list[MCPTool]:
        """Start the MCP server process and discover tools."""
        if self.config.transport == "sse":
            logger.warning(f"[{self.name}] SSE transport not yet implemented, skipping")
            return []

        import os
        env = {**os.environ, **self.config.env}

        try:
            self.process = await asyncio.create_subprocess_exec(
                self.config.command, *self.config.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
        except FileNotFoundError:
            logger.error(f"[{self.name}] Command not found: {self.config.command}")
            return []

        self._reader_task = asyncio.create_task(self._read_loop())

        # Initialize handshake
        init_resp = await self._request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "omnibot", "version": "0.2.0"},
        })
        if init_resp is None:
            logger.error(f"[{self.name}] Initialize failed")
            await self.stop()
            return []

        await self._notify("notifications/initialized", {})
        self._ready = True

        # Discover tools
        tools_resp = await self._request("tools/list", {})
        if tools_resp and "tools" in tools_resp:
            for t in tools_resp["tools"]:
                self.tools.append(MCPTool(
                    name=t["name"],
                    description=t.get("description", ""),
                    input_schema=t.get("inputSchema", {}),
                    server_name=self.name,
                ))
        logger.info(f"[{self.name}] Discovered {len(self.tools)} tools")
        return self.tools

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool on this MCP server."""
        if not self._ready:
            raise RuntimeError(f"[{self.name}] Server not ready")
        result = await self._request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })
        if result and "content" in result:
            parts = []
            for block in result["content"]:
                if block.get("type") == "text":
                    parts.append(block["text"])
                else:
                    parts.append(json.dumps(block))
            return "\n".join(parts)
        return json.dumps(result) if result else ""

    async def stop(self):
        """Shutdown the MCP server."""
        self._ready = False
        if self._reader_task:
            self._reader_task.cancel()
        if self.process and self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self.process.kill()
        logger.info(f"[{self.name}] Stopped")

    # --- JSON-RPC internals ---

    async def _request(self, method: str, params: dict) -> dict | None:
        self._request_id += 1
        rid = self._request_id
        msg = {"jsonrpc": "2.0", "id": rid, "method": method, "params": params}
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[rid] = future
        await self._send(msg)
        try:
            return await asyncio.wait_for(future, timeout=30)
        except asyncio.TimeoutError:
            self._pending.pop(rid, None)
            logger.error(f"[{self.name}] Request timeout: {method}")
            return None

    async def _notify(self, method: str, params: dict):
        msg = {"jsonrpc": "2.0", "method": method, "params": params}
        await self._send(msg)

    async def _send(self, msg: dict):
        if not self.process or not self.process.stdin:
            return
        data = json.dumps(msg)
        line = f"Content-Length: {len(data)}\r\n\r\n{data}"
        self.process.stdin.write(line.encode())
        await self.process.stdin.drain()

    async def _read_loop(self):
        """Read JSON-RPC responses from stdout."""
        if not self.process or not self.process.stdout:
            return
        reader = self.process.stdout
        try:
            while True:
                # Read headers
                content_length = 0
                while True:
                    header = await reader.readline()
                    if not header or header == b"\r\n" or header == b"\n":
                        break
                    line = header.decode().strip()
                    if line.startswith("Content-Length:"):
                        content_length = int(line.split(":")[1].strip())

                if content_length == 0:
                    # Try reading a raw JSON line (some servers skip headers)
                    raw = await reader.readline()
                    if not raw:
                        break
                    try:
                        msg = json.loads(raw.decode())
                    except json.JSONDecodeError:
                        continue
                else:
                    body = await reader.readexactly(content_length)
                    msg = json.loads(body.decode())

                # Route response
                if "id" in msg and msg["id"] in self._pending:
                    future = self._pending.pop(msg["id"])
                    if "error" in msg:
                        future.set_exception(
                            RuntimeError(f"MCP error: {msg['error']}")
                        )
                    else:
                        future.set_result(msg.get("result"))
        except (asyncio.CancelledError, asyncio.IncompleteReadError):
            pass
        except Exception as e:
            logger.error(f"[{self.name}] Read loop error: {e}")
