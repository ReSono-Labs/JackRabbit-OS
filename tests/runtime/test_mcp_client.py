from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from resono_runtime.mcp.client import StreamableHttpMcpClient
from resono_runtime.mcp.connections import validate_connection_configuration


class McpClientTest(unittest.TestCase):
    @patch("resono_runtime.mcp.client.resolve_public_host", return_value=("example.com", ("93.184.216.34",)))
    @patch("resono_runtime.mcp.client._PinnedHttpsConnection")
    def test_discovers_tools_after_full_initialize(self, connection_type, _host) -> None:
        connection = _Connection(
            [
                _Response({"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2025-11-25"}}, session_id="session"),
                _Response(None, status=202),
                _Response({"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "lookup", "description": "Lookup.", "inputSchema": {}}]}}),
            ]
        )
        connection_type.return_value = connection
        client = StreamableHttpMcpClient(
            validate_connection_configuration({"type": "streamable-http", "url": "https://example.com/mcp"})
        )

        self.assertEqual("lookup", client.discover_tools()[0]["name"])
        self.assertEqual(["initialize", "notifications/initialized", "tools/list"], connection.methods)


class _Connection:
    def __init__(self, responses: list["_Response"]) -> None:
        self._responses = iter(responses)
        self.methods: list[str] = []

    def request(self, _verb: str, _path: str, *, body: bytes | None = None, headers: dict[str, str] | None = None) -> None:
        del headers
        if body:
            self.methods.append(json.loads(body)["method"])

    def getresponse(self) -> "_Response":
        return next(self._responses)

    def close(self) -> None:
        pass


class _Response:
    def __init__(self, value: object, *, status: int = 200, session_id: str | None = None) -> None:
        self.status = status
        self._value = value
        self._session_id = session_id

    def read(self, _limit: int) -> bytes:
        return b"" if self._value is None else json.dumps(self._value).encode()

    def getheader(self, name: str) -> str | None:
        if name == "Mcp-Session-Id":
            return self._session_id
        if name == "Content-Type":
            return "application/json"
        return None


if __name__ == "__main__":
    unittest.main()
