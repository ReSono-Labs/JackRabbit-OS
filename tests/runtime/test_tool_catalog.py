from __future__ import annotations

import unittest

from resono_runtime.tools import ToolCatalog, register_device_status


class ToolCatalogTest(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = ToolCatalog()
        register_device_status(
            self.catalog,
            lambda: {"status": "ready", "service": "resono-runtime", "contractVersion": 1},
        )

    def test_one_definition_projects_to_mcp_and_realtime(self) -> None:
        self.assertEqual("get_device_status", self.catalog.mcp_definitions()[0]["name"])
        self.assertEqual("get_device_status", self.catalog.realtime_definitions()[0]["name"])

    def test_rejects_unknown_tool_and_invalid_arguments(self) -> None:
        self.assertTrue(self.catalog.invoke("unknown", {}).is_error)
        self.assertTrue(self.catalog.invoke("get_device_status", {"unexpected": True}).is_error)

    def test_invokes_valid_builtin(self) -> None:
        result = self.catalog.invoke("get_device_status", {})
        self.assertFalse(result.is_error)
        self.assertEqual("ready", result.structured_content["status"])


if __name__ == "__main__":
    unittest.main()
