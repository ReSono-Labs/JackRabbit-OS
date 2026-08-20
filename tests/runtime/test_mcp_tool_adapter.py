from __future__ import annotations
import unittest
from resono_runtime.mcp.tool_adapter import normalize_tools

class McpToolAdapterTest(unittest.TestCase):
    def test_normalizes_tools_without_exposing_them(self) -> None:
        tools=normalize_tools("crm",[{"name":"lookup","description":"Lookup.","inputSchema":{"type":"object","properties":{}}}])
        self.assertEqual("crm",tools[0].connection_id)
        self.assertEqual("lookup",tools[0].name)
