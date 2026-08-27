"""Slice 1 — SSE transport client tests (TDD)."""

from __future__ import annotations

import pytest

from resono_runtime.mcp.client import McpConnectionError, SseMcpClient
from resono_runtime.mcp.connections import McpConnectionConfiguration

from .fake_sse_server import FakeSseMcpServer, PROTOCOL_VERSION


def _config(server: FakeSseMcpServer, **headers) -> McpConnectionConfiguration:
    return McpConnectionConfiguration(transport="sse", endpoint=server.url, headers=tuple(sorted(headers.items())))


def test_sse_client_handshake_lists_and_calls_tool():
    server = FakeSseMcpServer()
    server.start()
    try:
        client = SseMcpClient(_config(server))
        try:
            init = client.initialize()
            assert isinstance(init, dict)
            assert init["protocolVersion"] == PROTOCOL_VERSION
            assert init["serverInfo"]["name"] == "fake-sse"

            tools = client.discover_tools()
            assert isinstance(tools, list) and len(tools) == 2
            names = {tool["name"] for tool in tools}
            assert names == {"echo", "add"}

            result = client.call_tool("echo", {"text": "hello"})
            assert result["isError"] is False
            assert '"text": "hello"' in result["content"][0]["text"]
        finally:
            client.close()
    finally:
        server.stop()


def test_sse_client_requires_endpoint_event():
    server = FakeSseMcpServer(send_endpoint_event=False)
    server.start()
    try:
        client = SseMcpClient(_config(server))
        try:
            with pytest.raises(McpConnectionError):
                client.initialize()
        finally:
            client.close()
    finally:
        server.stop()


def test_sse_client_classic_stream_mode_delivers_responses_over_sse():
    server = FakeSseMcpServer(respond_via_stream=True)
    server.start()
    try:
        client = SseMcpClient(_config(server))
        try:
            init = client.initialize()
            assert init["serverInfo"]["name"] == "fake-sse"
            assert server.session_id is not None  # client sent session id after first exchange
            tools = client.discover_tools()
            assert len(tools) == 2
        finally:
            client.close()
    finally:
        server.stop()


def test_sse_client_close_stops_further_requests():
    server = FakeSseMcpServer()
    server.start()
    try:
        client = SseMcpClient(_config(server))
        client.initialize()
        client.close()
        with pytest.raises(McpConnectionError):
            client.discover_tools()
    finally:
        server.stop()


def test_sse_client_rejects_non_sse_configuration():
    with pytest.raises(ValueError):
        SseMcpClient(McpConnectionConfiguration(transport="stdio", command="python"))
