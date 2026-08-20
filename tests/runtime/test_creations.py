from __future__ import annotations

from io import BytesIO
from pathlib import Path
import tempfile
import unittest
import zipfile

from resono_runtime.agents import AgentAudience, AgentAudienceRouter
from resono_runtime.creations import CreationArchiveInspector, CreationDescriptorInspector, CreationLifecycle
from resono_runtime.imports import ImportRecovery
from resono_runtime.storage.agent_audiences import AgentAudienceRepository
from resono_runtime.storage.creations import CreationCatalogRepository
from resono_runtime.storage.creations import StoredCreation
from resono_runtime.storage.database import RuntimeDatabase


class CreationLifecycleTest(unittest.TestCase):
    def test_import_overwrite_enable_dynamic_generation_and_delete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = RuntimeDatabase(root / "runtime.sqlite3")
            database.migrate()
            lifecycle = CreationLifecycle(
                CreationCatalogRepository(database),
                AgentAudienceRouter(AgentAudienceRepository(database)),
                root / "creations",
                root / "rollbacks",
                ImportRecovery(database),
            )
            inspector = CreationArchiveInspector(root / "quarantine")
            first = lifecycle.preflight(inspector.inspect(_zip("First"), "quick-capture.zip"), audience=AgentAudience.BOTH)
            installed = lifecycle.confirm(first.token, replace=False, changed_by="test", reason="import")
            generation = lifecycle.generation()
            enabled = lifecycle.set_enabled(installed.creation_id, True, changed_by="test", reason="enable")
            self.assertEqual("enabled", enabled.lifecycle_state)
            self.assertGreater(lifecycle.generation(), generation)

            replacement = lifecycle.preflight(inspector.inspect(_zip("Second"), "quick-capture.zip"), audience=AgentAudience.VOICE)
            self.assertEqual("conflict", replacement.state)
            lifecycle.confirm(replacement.token, replace=True, changed_by="test", reason="replace")
            self.assertIn("Second", (lifecycle.get("quick-capture").install_path / "index.html").read_text())
            lifecycle.delete("quick-capture", changed_by="test", reason="delete")
            self.assertIsNone(lifecycle.get("quick-capture"))

    def test_rabbit_qr_link_uses_shared_overwrite_catalog_and_delete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = RuntimeDatabase(root / "runtime.sqlite3")
            database.migrate()
            lifecycle = CreationLifecycle(CreationCatalogRepository(database), AgentAudienceRouter(AgentAudienceRepository(database)), root / "creations", root / "rollbacks", ImportRecovery(database))
            inspector = CreationDescriptorInspector(root / "quarantine", host_validator=lambda host, port: host.casefold())
            candidate = inspector.inspect({"title": "Advanced Notes App", "url": "https://notes.example/app", "description": "Persistent notes", "iconUrl": "https://notes.example/icon.png", "themeColor": "#FE5000"})
            preview = lifecycle.preflight(candidate, audience=AgentAudience.BOTH)
            installed = lifecycle.confirm(preview.token, replace=False, changed_by="test", reason="qr import")
            self.assertEqual("rabbit_qr_link", installed.source_type)
            self.assertEqual("https://notes.example/app", installed.entry_url)
            self.assertTrue((installed.install_path / "creation.json").is_file())
            replacement = lifecycle.preflight(inspector.inspect({"title": "Advanced Notes App", "url": "https://notes.example/v2", "description": "Updated", "themeColor": "#112233"}), audience=AgentAudience.BOTH)
            self.assertEqual("conflict", replacement.state)
            updated = lifecycle.confirm(replacement.token, replace=True, changed_by="test", reason="replace")
            self.assertEqual("https://notes.example/v2", updated.entry_url)
            lifecycle.delete(updated.creation_id, changed_by="test", reason="delete")
            self.assertIsNone(lifecycle.get(updated.creation_id))

    def test_rabbit_qr_link_rejects_non_https_and_unknown_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            inspector = CreationDescriptorInspector(Path(directory), host_validator=lambda host, port: host)
            with self.assertRaises(ValueError): inspector.inspect({"title": "Notes", "url": "http://example.com"})
            with self.assertRaises(ValueError): inspector.inspect({"title": "Notes", "url": "https://example.com", "extra": True})

    def test_standalone_creation_cannot_replace_plugin_owned_card(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); database=RuntimeDatabase(root/"runtime.sqlite3"); database.migrate()
            catalog=CreationCatalogRepository(database)
            catalog.save(StoredCreation("quick-capture","Plugin Card","Owned", "hash",root/"plugin","enabled",0,source_type="plugin_card"),action="install",changed_by="test",reason="plugin")
            lifecycle=CreationLifecycle(catalog,AgentAudienceRouter(AgentAudienceRepository(database)),root/"creations",root/"rollbacks",ImportRecovery(database))
            with self.assertRaisesRegex(ValueError,"owned"):
                lifecycle.preflight(CreationArchiveInspector(root/"quarantine").inspect(_zip("Replacement"),"quick-capture.zip"),audience=AgentAudience.BOTH)


def _zip(title: str) -> bytes:
    payload = BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("index.html", f"<!doctype html><title>{title}</title><meta name='description' content='Capture thoughts'><main>{title}</main>")
        archive.writestr("app.js", "window.addEventListener('scrollUp', () => {});")
    return payload.getvalue()


if __name__ == "__main__":
    unittest.main()
