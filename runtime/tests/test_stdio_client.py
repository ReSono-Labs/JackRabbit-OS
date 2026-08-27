"""Slice 1 — stdio transport client tests (TDD)."""

from __future__ import annotations

import os
import sys

import pytest

from resono_runtime.mcp.client import McpConnectionError, StdioMcpClient
from resono_runtime.mcp.connections import McpConnectionConfiguration

from .fake_stdio_mcp_server import PROTOCOL_VERSION  # noqa: F401  (pin the version both sides use)

_SCRIPT = os.path.join(os.path.dirname(__file__), "fake_stdio_mcp_server.py")


def _config(*extra_args: str, timeout: float | None = None) -> McpConnectionConfiguration:
    return McpConnectionConfiguration(transport="stdio", command=sys.executable, args=(_SCRIPT, *extra_args))


def test_stdio_client_handshake_lists_and_calls_tool():
    client = StdioMcpClient(_config(), timeout=3.0)
    try:
        init = client.initialize()
        assert init["protocolVersion"] == PROTOCOL_VERSION
        assert init["serverInfo"]["name"] == "fake-stdio"

        tools = client.discover_tools()
        assert isinstance(tools, list) and len(tools) == 1
        assert tools[0]["name"] == "say"

        result = client.call_tool("say", {"message": "hello"})
        assert result["isError"] is False
        assert '"message": "hello"' in result["content"][0]["text"]
    finally:
        client.close()


def test_stdio_client_rejects_failed_initialize():
    client = StdioMcpClient(_config("--fail"), timeout=3.0)
    try:
        with pytest.raises(McpConnectionError):
            client.initialize()
    finally:
        client.close()


def test_stdio_client_timeout_kills_process():
    client = StdioMcpClient(_config("--slow"), timeout=1.0)
    try:
        client.initialize()
        with pytest.raises(McpConnectionError):
            client.discover_tools()
        process = client._process
        assert process.poll() is not None  # killed, not left running
    finally:
        client.close()


def test_stdio_client_captures_stderr_diagnostics():
    client = StdioMcpClient(_config("--stderr", "boom diagnostics"), timeout=3.0)
    try:
        client.initialize()
        assert "boom diagnostics" in client.diagnostics()
    finally:
        client.close()


def test_stdio_client_rejects_non_stdio_configuration():
    with pytest.raises(ValueError):
        StdioMcpClient(McpConnectionConfiguration(transport="sse", endpoint="http://127.0.0.1:1/sse"))
