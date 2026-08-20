from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from resono_runtime.agents import AgentAudience, AgentAudienceRouter
from resono_runtime.plugins.archives import PluginArchiveInspector
from resono_runtime.plugins.lifecycle import PluginLifecycle
from resono_runtime.plugins.bundled_install import BundledPluginInstaller
from resono_runtime.storage.agent_audiences import AgentAudienceRepository
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.storage.plugins import PluginCatalogRepository
from resono_runtime.storage.plugin_components import PluginComponentRepository
from resono_runtime.storage.creations import CreationCatalogRepository
from resono_runtime.plugins.card_lifecycle import PluginCardLifecycle


class PluginLifecycleTest(unittest.TestCase):
    def test_bundled_mail_plugin_uses_standard_lifecycle_and_respects_delete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = RuntimeDatabase(root / "db.sqlite")
            database.migrate()
            catalog = PluginCatalogRepository(database)
            components = PluginComponentRepository(database)
            lifecycle = PluginLifecycle(
                catalog,
                AgentAudienceRouter(AgentAudienceRepository(database)),
                root / "plugins",
                root / "rollbacks",
                components,
            )
            installer = BundledPluginInstaller(
                lifecycle,
                catalog,
                PluginArchiveInspector(root / "quarantine"),
            )
            bundled = Path(__file__).resolve().parents[2] / "runtime" / "resono_runtime" / "plugins" / "bundled" / "resono-mail"

            installer.install_once(bundled)
            self.assertEqual("enabled", catalog.get("resono-mail").lifecycle_state)
            self.assertEqual(("voice-mail",), tuple(
                item.component_key for item in components.list_for_plugin("resono-mail")
                if item.component_type == "skill"
            ))

            lifecycle.delete("resono-mail", changed_by="owner", reason="remove bundled plugin")
            installer.install_once(bundled)
            self.assertIsNone(catalog.get("resono-mail"))

    def test_same_name_replacement_keeps_one_catalog_item(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); db=RuntimeDatabase(root/"db.sqlite"); db.migrate()
            components=PluginComponentRepository(db)
            life=PluginLifecycle(PluginCatalogRepository(db),AgentAudienceRouter(AgentAudienceRepository(db)),root/"plugins",root/"rollbacks",components)
            first=life.preflight(_inspection(root,"one")); life.confirm(first.token,audience=AgentAudience.VOICE,replace=False,changed_by="owner",reason="install")
            second=life.preflight(_inspection(root,"two")); self.assertEqual("conflict",second.state)
            item=life.confirm(second.token,audience=AgentAudience.TEXT,replace=True,changed_by="owner",reason="replace")
            self.assertEqual("demo",item.name)
            self.assertIn("two",(item.install_path/"data.txt").read_text())
            self.assertEqual(("plan",), tuple(item.component_key for item in components.list_for_plugin("demo")))

    def test_plugin_card_follows_enable_disable_replace_and_delete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); db=RuntimeDatabase(root/"db.sqlite"); db.migrate()
            components=PluginComponentRepository(db); cards=CreationCatalogRepository(db)
            life=PluginLifecycle(PluginCatalogRepository(db),AgentAudienceRouter(AgentAudienceRepository(db)),root/"plugins",root/"rollbacks",components,cards=PluginCardLifecycle(cards,components))
            first=life.preflight(_inspection(root,"one",card=True)); life.confirm(first.token,replace=False,changed_by="owner",reason="install")
            self.assertEqual("installed",cards.get("demo").lifecycle_state)
            life.enable("demo",changed_by="owner",reason="enable")
            self.assertEqual("enabled",cards.get("demo").lifecycle_state)
            life.disable("demo",changed_by="owner",reason="disable")
            self.assertEqual("disabled",cards.get("demo").lifecycle_state)
            replacement=life.preflight(_inspection(root,"two",card=False)); life.confirm(replacement.token,replace=True,changed_by="owner",reason="replace")
            self.assertIsNone(cards.get("demo"))
            life.delete("demo",changed_by="owner",reason="delete")


def _inspection(root: Path, value: str, card: bool = False):
    import io, zipfile
    raw=io.BytesIO()
    with zipfile.ZipFile(raw,"w") as archive:
        archive.writestr("demo/plugin.json",'{"$schema":"https://agent-plugins.org/schemas/1.0.0/plugin.schema.json","name":"demo"}')
        archive.writestr("demo/data.txt",value)
        archive.writestr("demo/skills/plan/SKILL.md","---\nname: plan\ndescription: Plan.\n---\nPlan.")
        if card:
            archive.writestr("demo/com.resonolabs.cards/card.json",'{"$schema":"https://resono.local/schemas/cards/1.0/card.schema.json","schemaVersion":"1.0","cardId":"demo","title":"Demo","description":"Real demo data","entrypoint":"index.html"}')
            archive.writestr("demo/com.resonolabs.cards/index.html","<!doctype html><title>Demo</title>")
    return PluginArchiveInspector(root/"quarantine").inspect(raw.getvalue(),"demo.zip")
