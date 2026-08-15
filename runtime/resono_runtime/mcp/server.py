from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
import secrets
import threading


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
    """Minimal MCP Streamable HTTP server for trusted on-device clients."""

    def __init__(self, health: Callable[[], dict[str, object]]) -> None:
        self._health = health
        self._sessions: set[str] = set()
        self._lock = threading.Lock()

    def handle(
        self,
        message: dict[str, object],
        *,
        session_id: str | None,
        protocol_version: str | None,
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
            return self._result(request_id, {"tools": [DEVICE_STATUS_TOOL]})
        if method == "tools/call":
            return self._call_tool(request_id, message.get("params"))
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

    def _call_tool(self, request_id: object, params: object) -> McpHttpResult:
        values = params if isinstance(params, dict) else {}
        name = values.get("name")
        arguments = values.get("arguments", {})
        if name != DEVICE_STATUS_TOOL["name"] or not isinstance(arguments, dict) or arguments:
            return self._result(
                request_id,
                {
                    "content": [{"type": "text", "text": "Tool is not granted."}],
                    "isError": True,
                },
            )
        status = self._health()
        safe = {
            "status": status.get("status", "not_ready"),
            "service": status.get("service", "resono-runtime"),
            "contractVersion": status.get("contractVersion"),
        }
        text = json.dumps(safe, separators=(",", ":"))
        return self._result(
            request_id,
            {
                "content": [{"type": "text", "text": text}],
                "structuredContent": safe,
                "isError": False,
            },
        )

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
