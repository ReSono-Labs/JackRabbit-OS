"""Standard Agent Plugin package lifecycle and component handoff."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import secrets
import shutil
from uuid import NAMESPACE_URL, uuid5

from ..agents import AgentAudience, AgentAudienceRouter, AudienceResource, AudienceResourceKind
from ..imports import ImportPreflightError, ImportPreflightRegistry, ImportRecovery
from ..mcp.lifecycle import McpLifecycle
from ..storage.plugin_components import PluginComponent, PluginComponentRepository
from ..storage.plugins import PluginCatalogRepository, StoredPlugin
from ..storage.skills import SkillCatalogRepository
from .archives import PluginInspection
from .specification import PluginSpecificationError, parse_mcp_document
from .card_lifecycle import PluginCardLifecycle, PluginCardLifecycleError


class PluginLifecycleError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PluginPreflight:
    token: str
    state: str
    name: str
    content_hash: str
    current: StoredPlugin | None
    audience: AgentAudience


class PluginLifecycle:
    def __init__(self, catalog: PluginCatalogRepository, audiences: AgentAudienceRouter, plugins_root: Path, rollback_root: Path, components: PluginComponentRepository, skills: SkillCatalogRepository | None = None, mcp: McpLifecycle | None = None, recovery: ImportRecovery | None = None, cards: PluginCardLifecycle | None = None) -> None:
        self._catalog = catalog
        self._audiences = audiences
        self._plugins_root = plugins_root
        self._rollback_root = rollback_root
        self._components = components
        self._skills = skills
        self._mcp = mcp
        self._recovery = recovery
        self._cards = cards
        self._preflights: ImportPreflightRegistry[PluginInspection] = ImportPreflightRegistry()

    def preflight(self, inspection: PluginInspection, *, audience: AgentAudience = AgentAudience.VOICE) -> PluginPreflight:
        for expired in self._preflights.discard_expired():
            shutil.rmtree(expired.payload.root.parent, ignore_errors=True)
        digest = _hash_tree(inspection.root)
        current = self._catalog.get(inspection.manifest.name)
        if self._cards is not None:
            try:
                self._cards.validate(inspection.manifest.name, inspection.card)
            except PluginCardLifecycleError as error:
                raise PluginLifecycleError(str(error)) from error
        for name in inspection.skills:
            if self._skills is not None and self._skills.get(name) is not None:
                raise PluginLifecycleError(f"Plugin Skill '{name}' conflicts with an installed Skill.")
            owner = self._components.skill_owner(name, excluding_plugin=inspection.manifest.name)
            if owner:
                raise PluginLifecycleError(f"Plugin Skill '{name}' is already owned by Plugin '{owner}'.")
        record = self._preflights.issue(identity=inspection.manifest.name, candidate_hash=digest, current_hash=current.content_hash if current else None, audience=audience, payload=inspection)
        return PluginPreflight(record.token, record.state, record.identity, digest, current, audience)

    def confirm(self, token: str, *, replace: bool, changed_by: str, reason: str, audience: AgentAudience | None = None) -> StoredPlugin:
        del audience
        try:
            preview = self._preflights.peek(token)
            current = self._catalog.get(preview.identity)
            record = self._preflights.consume(token, current_hash=current.content_hash if current else None, replace=replace)
        except ImportPreflightError as error:
            raise PluginLifecycleError(str(error)) from error
        inspection = record.payload
        previous_card_ids = self._components.card_ids(inspection.manifest.name)
        previous_mcp_ids = set(self._mcp_ids(current)) if current is not None else set()
        target = self._plugins_root / inspection.manifest.name
        rollback = self._rollback_root / inspection.manifest.name
        staged = self._plugins_root / ".staging" / secrets.token_hex(16) / inspection.manifest.name
        staged.parent.mkdir(parents=True, exist_ok=False)
        shutil.copytree(inspection.root, staged)
        operation = self._recovery.begin(resource_kind="plugin", identity=inspection.manifest.name, candidate_hash=record.candidate_hash, target=target, backup=rollback, staged=staged) if self._recovery else None
        moved = False
        try:
            if target.exists():
                if rollback.exists():
                    shutil.rmtree(rollback)
                rollback.parent.mkdir(parents=True, exist_ok=True)
                os.replace(target, rollback)
                moved = True
            if operation is not None:
                self._recovery.mark_backup_secured(operation)
            os.replace(staged, target)
            if operation is not None:
                self._recovery.mark_activated(operation)
            item = self._catalog.save(StoredPlugin(inspection.manifest.name, record.candidate_hash, target, "installed"), action="replace" if current else "install", changed_by=changed_by, reason=reason)
            self._components.replace_for_plugin(item.name, _components(item.name, inspection))
            if self._cards is not None:
                self._cards.replace(item.name, inspection.card, previous_card_ids, state=item.lifecycle_state, changed_by=changed_by, reason=reason)
            self._audiences.set_audience(_resource(item.name), record.audience, changed_by=changed_by, reason=reason)
            self._install_mcp(item, record.audience, changed_by, reason)
            if self._mcp:
                current_mcp_ids = set(self._mcp_ids(item))
                for connection_id in previous_mcp_ids - current_mcp_ids:
                    self._mcp.remove(connection_id, changed_by=changed_by, reason="Plugin component removed by replacement")
            if operation is not None:
                self._recovery.complete(operation)
            return item
        except Exception:
            if moved and target.exists():
                shutil.rmtree(target)
                os.replace(rollback, target)
            raise
        finally:
            if staged.exists():
                shutil.rmtree(staged, ignore_errors=True)
            shutil.rmtree(inspection.root.parent, ignore_errors=True)

    def list(self) -> tuple[StoredPlugin, ...]: return self._catalog.list()
    def inspect(self, name: str) -> StoredPlugin | None: return self._catalog.get(name)
    def components(self, name: str) -> tuple[PluginComponent, ...]: return self._components.list_for_plugin(name)

    def recover(self) -> None:
        if self._recovery:
            self._recovery.recover("plugin", lambda name: (item.content_hash if (item := self._catalog.get(name)) else None))

    def enable(self, name: str, *, changed_by: str, reason: str) -> StoredPlugin:
        item = self._required(name)
        if not item.install_path.is_dir(): raise PluginLifecycleError("Installed Plugin files are missing.")
        binding = self._audiences.binding_for(_resource(name))
        if binding is None: raise PluginLifecycleError("Installed Plugin has no agent audience.")
        self._audiences.set_audience(_resource(name), binding.audience, changed_by=changed_by, reason=reason)
        if self._cards is not None: self._cards.set_enabled(name, True, changed_by=changed_by, reason=reason)
        return self._catalog.save(StoredPlugin(name, item.content_hash, item.install_path, "enabled"), action="enable", changed_by=changed_by, reason=reason)

    def disable(self, name: str, *, changed_by: str, reason: str) -> StoredPlugin:
        item = self._required(name)
        self._audiences.deactivate(_resource(name), changed_by=changed_by, reason=reason)
        if self._mcp:
            for connection_id in self._mcp_ids(item):
                if self._mcp.get(connection_id): self._mcp.set_enabled(connection_id, False, changed_by=changed_by, reason="Plugin disabled")
        if self._cards is not None: self._cards.set_enabled(name, False, changed_by=changed_by, reason=reason)
        return self._catalog.save(StoredPlugin(name, item.content_hash, item.install_path, "disabled"), action="disable", changed_by=changed_by, reason=reason)

    def delete(self, name: str, *, changed_by: str, reason: str) -> StoredPlugin:
        item = self._required(name)
        card_ids = self._components.card_ids(name)
        self.disable(name, changed_by=changed_by, reason="disable before delete")
        if self._mcp:
            for connection_id in self._mcp_ids(item): self._mcp.remove(connection_id, changed_by=changed_by, reason="Plugin removed")
        self._audiences.remove_resource(_resource(name), changed_by=changed_by, reason=reason)
        if self._cards is not None: self._cards.remove(name, card_ids, changed_by=changed_by, reason=reason)
        shutil.rmtree(item.install_path, ignore_errors=True)
        shutil.rmtree(self._rollback_root / name, ignore_errors=True)
        removed = self._catalog.remove(name, changed_by=changed_by, reason=reason)
        if removed is None: raise PluginLifecycleError("Installed Plugin no longer exists.")
        return removed

    def _install_mcp(self, item: StoredPlugin, audience: AgentAudience, changed_by: str, reason: str) -> None:
        source = item.install_path / "mcp.json"
        if not self._mcp or not source.is_file(): return
        try:
            document = parse_mcp_document(source)
        except PluginSpecificationError:
            return
        for server in document.servers:
            try:
                self._mcp.install(connection_id=_mcp_id(item.name, server.name), display_name=f"{item.name}: {server.name}", configuration=server.configuration, audience=audience, changed_by=changed_by, reason=reason, source_owner=f"plugin:{item.name}")
            except (TypeError, ValueError):
                continue

    def _mcp_ids(self, item: StoredPlugin) -> tuple[str, ...]:
        source = item.install_path / "mcp.json"
        if not source.is_file():
            return ()
        try:
            return tuple(_mcp_id(item.name, server.name) for server in parse_mcp_document(source).servers)
        except PluginSpecificationError:
            return ()

    def _required(self, name: str) -> StoredPlugin:
        item = self._catalog.get(name)
        if item is None: raise PluginLifecycleError("Installed Plugin does not exist.")
        return item


def _resource(name: str) -> AudienceResource: return AudienceResource(AudienceResourceKind.PLUGIN, name)
def _mcp_id(plugin: str, server: str) -> str: return str(uuid5(NAMESPACE_URL, f"resono:plugin:{plugin}:mcp:{server}"))


def _hash_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file(): digest.update(path.relative_to(root).as_posix().encode()); digest.update(path.read_bytes())
    return digest.hexdigest()


def _components(plugin: str, inspection: PluginInspection) -> tuple[PluginComponent, ...]:
    records = [PluginComponent(plugin, "skill", name, "valid", None) for name in inspection.skills]
    records += [PluginComponent(plugin, "skill", name, "invalid", "Skill validation failed") for name in inspection.invalid_skills]
    if inspection.mcp_present: records.append(PluginComponent(plugin, "mcp", "mcp.json", "valid" if inspection.mcp_valid else "invalid", inspection.mcp_issue))
    if inspection.card is not None: records.append(PluginComponent(plugin, "card", inspection.card.card_id, "valid", None))
    return tuple(records)
