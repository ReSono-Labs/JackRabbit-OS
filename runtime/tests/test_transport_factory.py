"""Slice 1 — transport client factory dispatch (TDD)."""

from __future__ import annotations

import sys

import pytest

from resono_runtime.mcp.client import McpConnectionError, client_for
from resono_runtime.mcp.connections import McpConnectionConfiguration

from .conftest import STDIO_SCRIPT
from .fake_sse_server import FakeSseMcpServer


def test_client_for_dispatches_per_transport():
    # SSE construction connects immediately; a dead endpoint proves the SSE
    # client path was selected (connection error, not configuration error).
    with pytest.raises(McpConnectionError):
        client_for(McpConnectionConfiguration(transport="sse", endpoint="http://127.0.0.1:1/sse"))

    stdio = McpConnectionConfiguration(transport="stdio", command=sys.executable, args=(STDIO_SCRIPT,))
    assert type(client_for(stdio)).__name__ == "StdioMcpClient"

    http = McpConnectionConfiguration(transport="streamable-http", endpoint="http://127.0.0.1:1/mcp")
    assert type(client_for(http)).__name__ == "StreamableHttpMcpClient"

    with pytest.raises(McpConnectionError):
        client_for(McpConnectionConfiguration(transport="webtransport", endpoint="http://127.0.0.1:1/"))


def test_client_for_forwards_credential_headers():
    server = FakeSseMcpServer()
    server.start()
    try:
        client = client_for(
            McpConnectionConfiguration(transport="sse", endpoint=server.url),
            credential_headers={"Authorization": "Bearer x"},
        )
        try:
            init = client.initialize()
            assert init["serverInfo"]["name"] == "fake-sse"
        finally:
            client.close()
    finally:
        server.stop()
