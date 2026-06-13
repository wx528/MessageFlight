"""MCP (Model Context Protocol) client for connecting to external tool servers.

Manages connections to MCP servers (e.g. Obsidian, filesystem, databases)
via stdio transport, discovers their tools, and provides a unified interface
for the LLM agent to call them.

MCP server configuration is stored as JSON in the app config:
    {
        "obsidian": {
            "command": "npx",
            "args": ["-y", "@huangyihe/obsidian-mcp"],
            "env": {"OBSIDIAN_VAULT_PATH": "/path/to/vault"}
        },
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        }
    }

Uses the ``mcp`` Python SDK for protocol handling. Falls back gracefully
if the SDK is not installed.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal, pyqtSlot

logger = logging.getLogger(__name__)

# Try importing the MCP SDK — it's an optional dependency
_MCP_AVAILABLE = False
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    _MCP_AVAILABLE = True
except ImportError:
    pass


class MCPServerConfig:
    """Configuration for a single MCP server."""

    def __init__(self, name: str, command: str, args: list[str] | None = None,
                 env: dict[str, str] | None = None) -> None:
        self.name = name
        self.command = command
        self.args = args or []
        self.env = env or {}

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"command": self.command}
        if self.args:
            d["args"] = self.args
        if self.env:
            d["env"] = self.env
        return d

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> MCPServerConfig:
        return cls(
            name=name,
            command=data.get("command", ""),
            args=data.get("args", []),
            env=data.get("env", {}),
        )


class MCPToolInfo:
    """Discovered tool from an MCP server."""

    def __init__(self, server_name: str, tool_name: str,
                 description: str, input_schema: dict[str, Any]) -> None:
        self.server_name = server_name
        self.tool_name = tool_name
        self.description = description
        self.input_schema = input_schema

    def to_function_definition(self) -> dict[str, Any]:
        """Convert to OpenAI function-calling tool definition format."""
        return {
            "type": "function",
            "function": {
                "name": f"mcp__{self.server_name}__{self.tool_name}",
                "description": f"[{self.server_name}] {self.description}",
                "parameters": self.input_schema,
            },
        }


class _MCPWorker(QThread):
    """Background thread that runs the async MCP client loop."""

    tools_discovered = pyqtSignal(list)  # list of MCPToolInfo
    tool_result = pyqtSignal(str, str, str)  # server_name, tool_name, result_json
    tool_error = pyqtSignal(str, str, str)  # server_name, tool_name, error_msg
    connection_error = pyqtSignal(str, str)  # server_name, error_msg
    finished_connecting = pyqtSignal(str, bool)  # server_name, success

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._servers: dict[str, MCPServerConfig] = {}
        self._sessions: dict[str, ClientSession] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._pending_calls: list[tuple[str, str, dict]] = []
        self._running = False

    def add_server(self, config: MCPServerConfig) -> None:
        self._servers[config.name] = config

    def remove_server(self, name: str) -> None:
        self._servers.pop(name, None)

    def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> None:
        """Queue a tool call to be executed on the worker thread's event loop."""
        self._pending_calls.append((server_name, tool_name, arguments))

    def run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._running = True
        try:
            self._loop.run_until_complete(self._main_loop())
        except Exception as exc:
            logger.error("MCPWorker: fatal error: %s", exc)
        finally:
            self._loop.close()

    async def _main_loop(self) -> None:
        """Connect to all servers, then process tool calls."""
        # Connect to all configured servers
        for name, config in self._servers.items():
            try:
                await self._connect_server(name, config)
            except Exception as exc:
                logger.warning("MCPWorker: failed to connect to %s: %s", name, exc)
                self.connection_error.emit(name, str(exc))
                self.finished_connecting.emit(name, False)

        # Process pending tool calls
        while self._running:
            if self._pending_calls:
                server_name, tool_name, arguments = self._pending_calls.pop(0)
                try:
                    result = await self._execute_tool(server_name, tool_name, arguments)
                    self.tool_result.emit(server_name, tool_name, result)
                except Exception as exc:
                    logger.warning("MCPWorker: tool call %s/%s failed: %s", server_name, tool_name, exc)
                    self.tool_error.emit(server_name, tool_name, str(exc))
            else:
                await asyncio.sleep(0.05)

    async def _connect_server(self, name: str, config: MCPServerConfig) -> None:
        """Connect to a single MCP server and discover its tools."""
        if not _MCP_AVAILABLE:
            raise RuntimeError("mcp SDK not installed")

        server_params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env or None,
        )

        read_stream, write_stream = await stdio_client(server_params).__aenter__()
        session = await ClientSession(read_stream, write_stream).__aenter__()
        await session.initialize()

        self._sessions[name] = session

        # Discover tools
        response = await session.list_tools()
        tools = []
        for tool in response.tools:
            tool_info = MCPToolInfo(
                server_name=name,
                tool_name=tool.name,
                description=tool.description or "",
                input_schema=tool.inputSchema if hasattr(tool, 'inputSchema') else {"type": "object", "properties": {}},
            )
            tools.append(tool_info)
            logger.info("MCPWorker: discovered tool %s/%s", name, tool.name)

        self.tools_discovered.emit(tools)
        self.finished_connecting.emit(name, True)

    async def _execute_tool(self, server_name: str, tool_name: str, arguments: dict) -> str:
        """Execute a tool call on the specified MCP server."""
        session = self._sessions.get(server_name)
        if session is None:
            raise RuntimeError(f"not connected to server {server_name!r}")

        try:
            result = await session.call_tool(tool_name, arguments)
        except Exception as exc:
            # Session likely broken — remove it so we can reconnect
            logger.warning("MCPWorker: session for %s appears broken: %s", server_name, exc)
            self._sessions.pop(server_name, None)
            # Try to reconnect once
            config = self._servers.get(server_name)
            if config:
                try:
                    await self._connect_server(server_name, config)
                    logger.info("MCPWorker: reconnected to %s, retrying tool call", server_name)
                    session = self._sessions[server_name]
                    result = await session.call_tool(tool_name, arguments)
                except Exception as reconnect_exc:
                    raise RuntimeError(
                        f"tool call failed and reconnect to {server_name} also failed: {reconnect_exc}"
                    ) from exc
            else:
                raise

        # Extract text content from the result
        parts = []
        for content in result.content:
            if hasattr(content, 'text'):
                parts.append(content.text)
            else:
                parts.append(str(content))

        return json.dumps(parts if len(parts) > 1 else (parts[0] if parts else ""), ensure_ascii=False)

    def stop(self) -> None:
        self._running = False


class MCPClientManager(QObject):
    """Manages MCP server connections and provides tool discovery for the agent.

    Signals:
        tools_updated(): Emitted when the available tool list changes.
        tool_result(server_name, tool_name, result_json): Result from an MCP tool call.
        tool_error(server_name, tool_name, error_msg): Error from an MCP tool call.
    """

    tools_updated = pyqtSignal()
    tool_result = pyqtSignal(str, str, str)
    tool_error = pyqtSignal(str, str, str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._worker: Optional[_MCPWorker] = None
        self._tools: dict[str, MCPToolInfo] = {}  # qualified_name -> MCPToolInfo
        self._connected_servers: set[str] = set()
        self._servers_config_json: str = ""
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setInterval(60_000)  # Check every 60 seconds
        self._reconnect_timer.timeout.connect(self._on_reconnect_check)

    @property
    def available(self) -> bool:
        return _MCP_AVAILABLE

    @property
    def connected_servers(self) -> set[str]:
        return self._connected_servers.copy()

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Return all discovered MCP tools in OpenAI function-calling format."""
        return [t.to_function_definition() for t in self._tools.values()]

    def parse_tool_call(self, qualified_name: str) -> tuple[str, str] | None:
        """Parse a qualified MCP tool name (mcp__server__tool) into (server, tool)."""
        if not qualified_name.startswith("mcp__"):
            return None
        parts = qualified_name.split("__", 2)
        if len(parts) != 3:
            return None
        return parts[1], parts[2]

    def start(self, servers_config_json: str) -> None:
        """Start the MCP client worker and connect to configured servers."""
        if not _MCP_AVAILABLE:
            logger.warning("MCPClientManager: mcp SDK not installed, skipping")
            return

        # Parse server configs
        configs = self._parse_servers_config(servers_config_json)
        if not configs:
            logger.info("MCPClientManager: no MCP servers configured")
            return

        # Stop existing worker if any
        self.stop()

        self._servers_config_json = servers_config_json
        self._worker = _MCPWorker(self)
        self._worker.tools_discovered.connect(self._on_tools_discovered)
        self._worker.tool_result.connect(self.tool_result)
        self._worker.tool_error.connect(self.tool_error)
        self._worker.connection_error.connect(self._on_connection_error)
        self._worker.finished_connecting.connect(self._on_finished_connecting)

        for config in configs.values():
            self._worker.add_server(config)

        self._worker.start()
        self._reconnect_timer.start()
        logger.info("MCPClientManager: starting worker with %d servers", len(configs))

    def stop(self) -> None:
        self._reconnect_timer.stop()
        if self._worker is not None:
            self._worker.stop()
            self._worker.wait(3000)
            self._worker = None
        self._tools.clear()
        self._connected_servers.clear()

    def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> None:
        """Request an MCP tool call (executed on the worker thread)."""
        if self._worker is None:
            self.tool_error.emit(server_name, tool_name, "MCP client not running")
            return
        self._worker.call_tool(server_name, tool_name, arguments)

    def _parse_servers_config(self, json_str: str) -> dict[str, MCPServerConfig]:
        """Parse the MCP servers JSON config string."""
        if not json_str.strip():
            return {}
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            logger.warning("MCPClientManager: invalid JSON config: %s", exc)
            return {}
        if not isinstance(data, dict):
            return {}
        configs = {}
        for name, server_data in data.items():
            if isinstance(server_data, dict) and "command" in server_data:
                configs[name] = MCPServerConfig.from_dict(name, server_data)
        return configs

    @pyqtSlot(list)
    def _on_tools_discovered(self, tools: list) -> None:
        for tool in tools:
            qualified = f"mcp__{tool.server_name}__{tool.tool_name}"
            self._tools[qualified] = tool
            logger.info("MCPClientManager: registered tool %s", qualified)
        self.tools_updated.emit()

    @pyqtSlot(str, str)
    def _on_connection_error(self, server_name: str, error_msg: str) -> None:
        logger.warning("MCPClientManager: connection error for %s: %s", server_name, error_msg)

    @pyqtSlot(str, bool)
    def _on_finished_connecting(self, server_name: str, success: bool) -> None:
        if success:
            self._connected_servers.add(server_name)
            logger.info("MCPClientManager: connected to %s", server_name)
        else:
            logger.warning("MCPClientManager: failed to connect to %s", server_name)

    def _on_reconnect_check(self) -> None:
        """Periodic check: if worker died or servers disconnected, restart."""
        if not self._servers_config_json:
            return
        if self._worker is None or not self._worker.isRunning():
            logger.info("MCPClientManager: worker not running, restarting...")
            self.start(self._servers_config_json)
