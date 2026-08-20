from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from resono_runtime.agents import AgentAudience, AgentAudienceRouter
from resono_runtime.connections.records import ConnectionRepository
from resono_runtime.mcp.lifecycle import McpLifecycle
from resono_runtime.mcp.imports import McpDocumentImport
from resono_runtime.security.credentials import ConnectionCredentialEnvelopes
from resono_runtime.storage.agent_audiences import AgentAudienceRepository
from resono_runtime.storage.connection_credentials import ConnectionCredentialRepository
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.storage.mcp_connections import McpConnectionRepository
from resono_runtime.tools import ToolCatalog


class McpLifecycleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.database = RuntimeDatabase(Path(self.temporary.name) / "runtime.sqlite3")
        self.database.migrate()
        self.router = AgentAudienceRouter(AgentAudienceRepository(self.database))
        self.catalog = ToolCatalog(audience_router=self.router)
        self.credentials = ConnectionCredentialRepository(self.database)
        self.lifecycle = McpLifecycle(
            McpConnectionRepository(self.database),
            ConnectionRepository(self.database),
            self.router,
            self.catalog,
            self.credentials,
            ConnectionCredentialEnvelopes(_CredentialBridge()),
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @patch("resono_runtime.mcp.lifecycle.StreamableHttpMcpClient")
    def test_discovery_requires_grant_and_projects_live_without_restart(self, client_type) -> None:
        client = client_type.return_value
        client.initialize.return_value = {
            "protocolVersion": "2025-11-25",
            "serverInfo": {"name": "Example", "version": "1"},
        }
        client.discover_tools.return_value = [
            {
                "name": "lookup",
                "description": "Look up a record.",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
            }
        ]
        client.call_tool.return_value = {"content": [{"type": "text", "text": "found"}]}
        connection_id = str(uuid4())
        self.lifecycle.install(
            connection_id=connection_id,
            display_name="Example",
            configuration={"type": "streamable-http", "url": "https://example.com/mcp"},
            audience=AgentAudience.BOTH,
            credential_headers={"Authorization": "Bearer secret"},
            changed_by="test",
            reason="test import",
        )
        self.lifecycle.discover(connection_id, changed_by="test", reason="test discovery")
        self.assertEqual((), self.catalog.realtime_definitions())

        self.lifecycle.grant_tool(connection_id, "lookup", enabled=True, effect_class="read")
        self.lifecycle.set_enabled(connection_id, True, changed_by="test", reason="test enable")
        exposed_name = self.lifecycle.tools(connection_id)[0].exposed_name
        self.assertEqual(exposed_name, self.catalog.realtime_definitions()[0]["name"])
        self.assertEqual("found", self.catalog.invoke(exposed_name, {}).text)

        restored_catalog = ToolCatalog(audience_router=self.router)
        restored = McpLifecycle(
            McpConnectionRepository(self.database), ConnectionRepository(self.database), self.router,
            restored_catalog, self.credentials, ConnectionCredentialEnvelopes(_CredentialBridge()),
        )
        restored.restore()
        self.assertEqual(exposed_name, restored_catalog.realtime_definitions()[0]["name"])

        self.assertTrue(self.lifecycle.remove(connection_id, changed_by="test", reason="test delete"))
        self.assertEqual((), self.catalog.realtime_definitions())
        self.assertIsNone(self.credentials.get_envelope(connection_id))

    def test_standard_mcp_document_uses_exact_same_name_overwrite_preflight(self) -> None:
        imports = McpDocumentImport(self.lifecycle)
        first = _mcp_document("https://example.com/one")
        preflight = imports.preflight(first, audience=AgentAudience.BOTH)
        self.assertEqual("new", preflight.state)
        imports.confirm(preflight.token, replace=False, changed_by="test", reason="import")

        identical = imports.preflight(first, audience=AgentAudience.VOICE)
        self.assertEqual("identical", identical.state)
        changed = imports.preflight(_mcp_document("https://example.com/two"), audience=AgentAudience.VOICE)
        self.assertEqual("conflict", changed.state)
        imports.confirm(changed.token, replace=True, changed_by="test", reason="replace")
        self.assertEqual(1, len(self.lifecycle.list()))


class _CredentialBridge:
    def sealConnectionCredential(self, record_name: str, plaintext: str) -> str:
        return f"{record_name}|{plaintext}"

    def openConnectionCredential(self, record_name: str, envelope: str) -> str:
        prefix = f"{record_name}|"
        if not envelope.startswith(prefix):
            raise ValueError("wrong record")
        return envelope[len(prefix):]


def _mcp_document(url: str) -> bytes:
    return (
        '{"$schema":"https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",'
        '"mcpServers":{"example":{"type":"streamable-http","url":"' + url + '"}}}'
    ).encode()


if __name__ == "__main__":
    unittest.main()
