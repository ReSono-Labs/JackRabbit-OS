from __future__ import annotations

from io import BytesIO
from pathlib import Path
import tempfile
import unittest
import zipfile

from resono_runtime.plugins.archives import PluginArchiveInspector, PluginArchiveRejected


class PluginArchiveInspectorTest(unittest.TestCase):
    def test_discovers_standard_components_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = PluginArchiveInspector(Path(directory)).inspect(_zip({
                "demo/plugin.json": b'{"$schema":"https://agent-plugins.org/schemas/1.0.0/plugin.schema.json","name":"demo"}',
                "demo/skills/plan/SKILL.md": b"---\nname: plan\ndescription: Plan.\n---\nPlan.",
                "demo/mcp.json": b'{"$schema":"https://agent-plugins.org/schemas/1.0.0/mcp.schema.json","mcpServers":{}}',
            }), "demo.zip")
        self.assertEqual("demo", result.manifest.name)
        self.assertEqual(("plan",), result.skills)
        self.assertTrue(result.mcp_valid)

    def test_rejects_missing_root_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(PluginArchiveRejected, "plugin.json"):
            PluginArchiveInspector(Path(directory)).inspect(_zip({"demo/file.txt": b"x"}), "demo.zip")


def _zip(files: dict[str, bytes]) -> bytes:
    payload = BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return payload.getvalue()
