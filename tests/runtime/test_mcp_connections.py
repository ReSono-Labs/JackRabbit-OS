from __future__ import annotations

import unittest

from resono_runtime.mcp.connections import McpConnectionConfigurationError, validate_connection_configuration


class McpConnectionConfigurationTest(unittest.TestCase):
    def test_accepts_https_streamable_http_without_connecting(self) -> None:
        configuration = validate_connection_configuration({"type": "streamable-http", "url": "https://example.com/mcp"})
        self.assertEqual("streamable-http", configuration.transport)

    def test_rejects_insecure_remote_and_shell_command(self) -> None:
        with self.assertRaises(McpConnectionConfigurationError):
            validate_connection_configuration({"type": "sse", "url": "http://example.com/mcp"})
        with self.assertRaises(McpConnectionConfigurationError):
            validate_connection_configuration({"type": "stdio", "command": "python server.py"})
