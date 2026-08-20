"""Bounded MCP 2025-11-25 Streamable HTTP client for outbound connections."""

from __future__ import annotations

import http.client
import json
import socket
import ssl
from urllib.parse import urlsplit

from resono_runtime.security.outbound import resolve_public_host

from .connections import McpConnectionConfiguration


PROTOCOL_VERSION = "2025-11-25"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class McpConnectionError(RuntimeError):
    pass


class StreamableHttpMcpClient:
    def __init__(self, configuration: McpConnectionConfiguration, *, credential_headers: dict[str, str] | None = None) -> None:
        if configuration.transport != "streamable-http" or configuration.endpoint is None:
            raise ValueError("Streamable HTTP configuration is required.")
        parsed = urlsplit(configuration.endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("MCP endpoint is invalid.")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if parsed.scheme == "http":
            if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError("Non-loopback MCP endpoints require HTTPS.")
            addresses = (parsed.hostname,)
        else:
            _, addresses = resolve_public_host(parsed.hostname, port)
        self._parsed = parsed
        self._addresses = addresses
        self._headers = {**dict(configuration.headers), **(credential_headers or {})}
        self._session_id: str | None = None
        self._next_id = 1
        self._initialized = False

    def initialize(self) -> dict[str, object]:
        result = self._request(
            "initialize",
            {"protocolVersion": PROTOCOL_VERSION, "capabilities": {}, "clientInfo": {"name": "resono-r1", "version": "0.1.0"}},
        )
        if not isinstance(result, dict) or result.get("protocolVersion") != PROTOCOL_VERSION:
            raise McpConnectionError("MCP server negotiated an unsupported protocol version.")
        self._notify("notifications/initialized", {})
        self._initialized = True
        return result

    def discover_tools(self) -> object:
        if not self._initialized:
            self.initialize()
        result = self._request("tools/list", {})
        if not isinstance(result, dict) or not isinstance(result.get("tools"), list):
            raise McpConnectionError("MCP tools/list response is invalid.")
        return result["tools"]

    def call_tool(self, name: str, arguments: dict[str, object]) -> object:
        if not self._initialized:
            self.initialize()
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        if not isinstance(result, dict):
            raise McpConnectionError("MCP tools/call response is invalid.")
        return result

    def close(self) -> None:
        if self._session_id is None:
            return
        connection = self._connection()
        try:
            connection.request("DELETE", self._path(), headers={"Mcp-Session-Id": self._session_id, "MCP-Protocol-Version": PROTOCOL_VERSION})
            response = connection.getresponse()
            response.read(MAX_RESPONSE_BYTES + 1)
        finally:
            connection.close()
            self._session_id = None
            self._initialized = False

    def _request(self, method: str, params: dict[str, object]) -> object:
        request_id = self._next_id
        self._next_id += 1
        payload = self._post({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0" or payload.get("id") != request_id or "error" in payload:
            raise McpConnectionError("MCP server returned an invalid response.")
        return payload.get("result")

    def _notify(self, method: str, params: dict[str, object]) -> None:
        self._post({"jsonrpc": "2.0", "method": method, "params": params}, response_optional=True)

    def _post(self, value: dict[str, object], *, response_optional: bool = False) -> object:
        connection = self._connection()
        headers = {**self._headers, "Content-Type": "application/json", "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": PROTOCOL_VERSION}
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        try:
            connection.request("POST", self._path(), body=json.dumps(value, separators=(",", ":")).encode(), headers=headers)
            response = connection.getresponse()
            if 300 <= response.status < 400:
                raise McpConnectionError("MCP redirects are not followed.")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise McpConnectionError("MCP response exceeded the size limit.")
            if response.status >= 400:
                raise McpConnectionError("MCP server rejected the request.")
            self._session_id = response.getheader("Mcp-Session-Id") or self._session_id
            if not raw and response_optional:
                return None
            content_type = (response.getheader("Content-Type") or "").split(";", 1)[0].strip().casefold()
            if content_type == "application/json":
                return json.loads(raw)
            if content_type == "text/event-stream":
                return _sse_json(raw)
            raise McpConnectionError("MCP response content type is unsupported.")
        except (OSError, json.JSONDecodeError) as error:
            raise McpConnectionError("MCP connection failed.") from error
        finally:
            connection.close()

    def _connection(self) -> http.client.HTTPConnection:
        port = self._parsed.port or (443 if self._parsed.scheme == "https" else 80)
        if self._parsed.scheme == "https":
            return _PinnedHttpsConnection(self._parsed.hostname, port, self._addresses[0], timeout=10)
        return http.client.HTTPConnection(self._parsed.hostname, port, timeout=10)

    def _path(self) -> str:
        path = self._parsed.path or "/"
        return path + (f"?{self._parsed.query}" if self._parsed.query else "")


def _sse_json(raw: bytes) -> object:
    data_lines: list[str] = []
    for line in raw.decode("utf-8").splitlines():
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
        elif not line and data_lines:
            break
    if not data_lines:
        raise McpConnectionError("MCP event stream contained no response event.")
    return json.loads("\n".join(data_lines))


class _PinnedHttpsConnection(http.client.HTTPSConnection):
    """Connect to the validated address while retaining hostname TLS checks."""

    def __init__(self, host: str, port: int, address: str, *, timeout: float) -> None:
        super().__init__(host, port, timeout=timeout, context=ssl.create_default_context())
        self._validated_address = address

    def connect(self) -> None:
        self.sock = socket.create_connection(
            (self._validated_address, self.port),
            self.timeout,
            self.source_address,
        )
        if self._tunnel_host:
            self._tunnel()
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)
