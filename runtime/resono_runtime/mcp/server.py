from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
import secrets
import threading
from typing import TYPE_CHECKING

from ..agents import AgentKind
from ..tools import ToolCatalog, ToolInvocationContext, ToolInvocationResult, register_device_status, register_memory_lookup

if TYPE_CHECKING:
    from ..memory.tools import MemoryLookupTool


PROTOCOL_VERSION = "2025-11-25"
DEVICE_STATUS_TOOL = {
    "name": "get_device_status",
    "description": "Read the current health of this ReSono R1 on-device runtime.",
    "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
}


@dataclass(frozen=True, slots=True)
class McpHttpResult:
    status: int
    payload: dict[str, object] | None
    session_id: str | None = None


class LocalMcpServer:
    """Minimal MCP Streamable HTTP server for trusted on-device clients.

    Two tools may be granted: ``get_device_status`` (always) and
    ``memory_lookup`` (when a ``MemoryLookupTool`` is wired in). The voice
    Realtime model calls these via the Android peer's MCP ``tools/call``;
    the text agent's MCP client filters to ``get_device_status`` only, so
    ``memory_lookup`` is effectively voice-only.
    """

    def __init__(
        self,
        health: Callable[[], dict[str, object]],
        *,
        memory_lookup: "MemoryLookupTool | None" = None,
        catalog: ToolCatalog | None = None,
        agent: AgentKind = AgentKind.VOICE,
    ) -> None:
        self._health = health
        self._catalog = catalog or ToolCatalog()
        self._agent = agent
        if catalog is None:
            register_device_status(self._catalog, health)
            if memory_lookup is not None:
                register_memory_lookup(self._catalog, memory_lookup)
        self._sessions: set[str] = set()
        self._lock = threading.Lock()

    def handle(
        self,
        message: dict[str, object],
        *,
        session_id: str | None,
        protocol_version: str | None,
        voice_session_id: str | None = None,
        tool_call_id: str | None = None,
        user_utterance: str | None = None,
        user_utterance_id: int | None = None,
    ) -> McpHttpResult:
        request_id = message.get("id")
        if message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
            return self._error(request_id, -32600, "Invalid Request")
        method = str(message["method"])
        if method == "initialize":
            return self._initialize(request_id, message.get("params"))
        if not self._authorized_session(session_id, protocol_version):
            return self._error(request_id, -32001, "MCP session is not initialized", status=400)
        if method == "notifications/initialized":
            return McpHttpResult(202, None)
        if method == "tools/list":
            return self._result(request_id, {"tools": self._listed_tools()})
        if method == "tools/call":
            return self._call_tool(
                request_id,
                message.get("params"),
                voice_session_id=voice_session_id,
                tool_call_id=tool_call_id,
                user_utterance=user_utterance,
                user_utterance_id=user_utterance_id,
            )
        return self._error(request_id, -32601, "Method not found")

    def _initialize(self, request_id: object, params: object) -> McpHttpResult:
        values = params if isinstance(params, dict) else {}
        if values.get("protocolVersion") != PROTOCOL_VERSION:
            return self._error(request_id, -32602, "Unsupported protocol version", status=400)
        session_id = secrets.token_urlsafe(24)
        with self._lock:
            self._sessions.add(session_id)
        return McpHttpResult(
            200,
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "resono-r1", "version": "0.1.0"},
                    "instructions": "Tools expose only explicitly granted on-device capabilities.",
                },
            },
            session_id,
        )

    def _listed_tools(self) -> list[dict[str, object]]:
        return self._catalog.mcp_definitions(self._agent)

    def _call_tool(self, request_id: object, params: object, *, voice_session_id: str | None, tool_call_id: str | None, user_utterance: str | None, user_utterance_id: int | None) -> McpHttpResult:
        values = params if isinstance(params, dict) else {}
        name = values.get("name")
        arguments = values.get("arguments", {})
        result: ToolInvocationResult = self._catalog.invoke(
            name,
            arguments,
            agent=self._agent,
            context=ToolInvocationContext(self._agent, voice_session_id, tool_call_id, user_utterance, user_utterance_id),
        )
        return self._result(request_id, result.mcp_result())

    def _authorized_session(self, session_id: str | None, version: str | None) -> bool:
        if version != PROTOCOL_VERSION or not session_id:
            return False
        with self._lock:
            return session_id in self._sessions

    @staticmethod
    def _result(request_id: object, result: dict[str, object]) -> McpHttpResult:
        return McpHttpResult(200, {"jsonrpc": "2.0", "id": request_id, "result": result})

    @staticmethod
    def _error(request_id: object, code: int, message: str, *, status: int = 200) -> McpHttpResult:
        return McpHttpResult(
            status,
            {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}},
        )
