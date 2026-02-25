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
    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    transport: str = "stdio"  # "stdio" or "sse"
    url: str | None = None    # for SSE transport


class MCPClient:
    """
    Lightweight MCP client supporting both stdio and SSE transports.
    Zero external dependencies for stdio — just subprocess + JSON.
    SSE transport requires httpx + httpx-sse.
    """

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.process: asyncio.subprocess.Process | None = None
        self.tools: list[MCPTool] = []
        self._request_id = 0
        self._pending: dict[int, asyncio.Future] = {}
        self._reader_task: asyncio.Task | None = None
        self._ready = False
        # SSE-specific
        self._http_client = None
        self._sse_task: asyncio.Task | None = None
        self._message_endpoint: str | None = None

    @property
    def name(self) -> str:
        return self.config.name

    async def start(self) -> list[MCPTool]:
        """Start the MCP server and discover tools."""
        if self.config.transport == "sse":
            return await self._start_sse()
        return await self._start_stdio()

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
        if self._sse_task:
            self._sse_task.cancel()
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        if self.process and self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self.process.kill()
        logger.info(f"[{self.name}] Stopped")

    # ==================== stdio transport ====================

    async def _start_stdio(self) -> list[MCPTool]:
        """Start MCP server via stdio subprocess."""
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

        self._reader_task = asyncio.create_task(self._stdio_read_loop())
        return await self._handshake_and_discover()

    async def _stdio_read_loop(self):
        """Read JSON-RPC responses from stdout."""
        if not self.process or not self.process.stdout:
            return
        reader = self.process.stdout
        try:
            while True:
                content_length = 0
                while True:
                    header = await reader.readline()
                    if not header or header == b"\r\n" or header == b"\n":
                        break
                    line = header.decode().strip()
                    if line.startswith("Content-Length:"):
                        content_length = int(line.split(":")[1].strip())

                if content_length == 0:
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

                self._route_message(msg)
        except (asyncio.CancelledError, asyncio.IncompleteReadError):
            pass
        except Exception as e:
            logger.error(f"[{self.name}] Stdio read loop error: {e}")

    async def _stdio_send(self, msg: dict):
        if not self.process or not self.process.stdin:
            return
        data = json.dumps(msg)
        line = f"Content-Length: {len(data)}\r\n\r\n{data}"
        self.process.stdin.write(line.encode())
        await self.process.stdin.drain()

    # ==================== SSE transport ====================

    async def _start_sse(self) -> list[MCPTool]:
        """Connect to MCP server via SSE transport."""
        if not self.config.url:
            logger.error(f"[{self.name}] SSE transport requires 'url' in config")
            return []

        try:
            import httpx
        except ImportError:
            logger.error(f"[{self.name}] SSE transport requires 'httpx'. Install: pip install httpx httpx-sse")
            return []

        self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0))

        # Connect to SSE endpoint to receive messages
        self._sse_task = asyncio.create_task(self._sse_read_loop())

        # Wait briefly for SSE connection to establish and get message endpoint
        for _ in range(50):  # 5 seconds max
            await asyncio.sleep(0.1)
            if self._message_endpoint:
                break

        if not self._message_endpoint:
            logger.error(f"[{self.name}] Failed to get message endpoint from SSE")
            await self.stop()
            return []

        return await self._handshake_and_discover()

    async def _sse_read_loop(self):
        """Read SSE events from the MCP server."""
        try:
            import httpx
            from httpx_sse import aconnect_sse
        except ImportError:
            logger.error(f"[{self.name}] Missing httpx-sse. Install: pip install httpx-sse")
            return

        sse_url = self.config.url
        try:
            async with aconnect_sse(self._http_client, "GET", sse_url) as event_source:
                async for event in event_source.aiter_sse():
                    if event.event == "endpoint":
                        # Server tells us where to POST messages
                        endpoint = event.data
                        # Handle relative URLs
                        if endpoint.startswith("/"):
                            from urllib.parse import urljoin
                            self._message_endpoint = urljoin(sse_url, endpoint)
                        else:
                            self._message_endpoint = endpoint
                        logger.debug(f"[{self.name}] Message endpoint: {self._message_endpoint}")

                    elif event.event == "message":
                        try:
                            msg = json.loads(event.data)
                            self._route_message(msg)
                        except json.JSONDecodeError:
                            logger.warning(f"[{self.name}] Invalid JSON in SSE message: {event.data[:100]}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[{self.name}] SSE read loop error: {e}")

    async def _sse_send(self, msg: dict):
        """Send JSON-RPC message via HTTP POST to the message endpoint."""
        if not self._http_client or not self._message_endpoint:
            logger.error(f"[{self.name}] SSE not connected")
            return
        try:
            response = await self._http_client.post(
                self._message_endpoint,
                json=msg,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"[{self.name}] SSE send error: {e}")

    # ==================== shared internals ====================

    def _route_message(self, msg: dict):
        """Route an incoming JSON-RPC message to the pending future."""
        if "id" in msg and msg["id"] in self._pending:
            future = self._pending.pop(msg["id"])
            if "error" in msg:
                future.set_exception(RuntimeError(f"MCP error: {msg['error']}"))
            else:
                future.set_result(msg.get("result"))

    async def _send(self, msg: dict):
        """Send via the active transport."""
        if self.config.transport == "sse":
            await self._sse_send(msg)
        else:
            await self._stdio_send(msg)

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

    async def _handshake_and_discover(self) -> list[MCPTool]:
        """Perform MCP initialize handshake and discover tools."""
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

        tools_resp = await self._request("tools/list", {})
        if tools_resp and "tools" in tools_resp:
            for t in tools_resp["tools"]:
                self.tools.append(MCPTool(
                    name=t["name"],
                    description=t.get("description", ""),
                    input_schema=t.get("inputSchema", {}),
                    server_name=self.name,
                ))
        logger.info(f"[{self.name}] Discovered {len(self.tools)} tools via {self.config.transport}")
        return self.tools
