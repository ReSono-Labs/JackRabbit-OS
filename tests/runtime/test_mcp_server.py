from __future__ import annotations

import unittest

from resono_runtime.mcp.server import LocalMcpServer, PROTOCOL_VERSION


class McpServerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.server = LocalMcpServer(
            lambda: {"status": "ready", "service": "resono-runtime", "contractVersion": 1}
        )
        initialized = self.server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            },
            session_id=None,
            protocol_version=None,
        )
        self.session_id = initialized.session_id

    def call(self, message: dict[str, object]):
        return self.server.handle(
            message,
            session_id=self.session_id,
            protocol_version=PROTOCOL_VERSION,
        )

    def test_lists_and_calls_real_status_tool(self) -> None:
        listed = self.call({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        self.assertEqual("get_device_status", listed.payload["result"]["tools"][0]["name"])

        called = self.call(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "get_device_status", "arguments": {}},
            }
        )
        self.assertFalse(called.payload["result"]["isError"])
        self.assertEqual("ready", called.payload["result"]["structuredContent"]["status"])

    def test_denies_ungranted_tool(self) -> None:
        denied = self.call(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "shell", "arguments": {}},
            }
        )
        self.assertTrue(denied.payload["result"]["isError"])

    def test_requires_initialized_session_and_version(self) -> None:
        denied = self.server.handle(
            {"jsonrpc": "2.0", "id": 5, "method": "tools/list", "params": {}},
            session_id=None,
            protocol_version=None,
        )
        self.assertEqual(400, denied.status)


if __name__ == "__main__":
    unittest.main()
