"""One-canonical-item lifecycle for imported static R1 Creations."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import secrets
import shutil

from ..agents import AgentAudience, AgentAudienceRouter, AudienceResource, AudienceResourceKind
from ..imports import ImportPreflightError, ImportPreflightRegistry, ImportRecovery
from ..storage.creations import CreationCatalogRepository, StoredCreation
from .archives import CreationInspection


class CreationLifecycleError(ValueError):
    pass


class CreationLifecycle:
    def __init__(self, catalog: CreationCatalogRepository, audiences: AgentAudienceRouter, root: Path, rollback_root: Path, recovery: ImportRecovery) -> None:
        self._catalog = catalog
        self._audiences = audiences
        self._root = root
        self._rollback_root = rollback_root
        self._recovery = recovery
        self._preflights: ImportPreflightRegistry[CreationInspection] = ImportPreflightRegistry()

    def preflight(self, inspection: CreationInspection, *, audience: AgentAudience):
        digest = _hash_tree(inspection.content_root)
        current = self._catalog.get(inspection.creation_id)
        if current is not None and current.source_type == "plugin_card":
            raise CreationLifecycleError("This Card is owned by an installed Plugin.")
        return self._preflights.issue(identity=inspection.creation_id, candidate_hash=digest, current_hash=current.content_hash if current else None, audience=audience, payload=inspection)

    def confirm(self, token: str, *, replace: bool, changed_by: str, reason: str) -> StoredCreation:
        try:
            preview = self._preflights.peek(token)
            current = self._catalog.get(preview.identity)
            record = self._preflights.consume(token, current_hash=current.content_hash if current else None, replace=replace)
        except ImportPreflightError as error:
            raise CreationLifecycleError(str(error)) from error
        inspection = record.payload
        target = self._root / inspection.creation_id
        backup = self._rollback_root / inspection.creation_id
        staged = self._root / ".staging" / secrets.token_hex(16) / inspection.creation_id
        staged.parent.mkdir(parents=True, exist_ok=False)
        shutil.copytree(inspection.content_root, staged)
        operation = self._recovery.begin(resource_kind="creation", identity=inspection.creation_id, candidate_hash=record.candidate_hash, target=target, backup=backup, staged=staged)
        moved = False
        try:
            if target.exists():
                shutil.rmtree(backup, ignore_errors=True)
                backup.parent.mkdir(parents=True, exist_ok=True)
                os.replace(target, backup)
                moved = True
            self._recovery.mark_backup_secured(operation)
            os.replace(staged, target)
            self._recovery.mark_activated(operation)
            item = self._catalog.save(StoredCreation(inspection.creation_id, inspection.title, inspection.description, record.candidate_hash, target, "enabled", 0, inspection.source_type, inspection.entry_url, inspection.icon_url, inspection.theme_color), action="replace" if current else "install", changed_by=changed_by, reason=reason)
            self._audiences.set_audience(_resource(item.creation_id), record.audience, changed_by=changed_by, reason=reason)
            self._recovery.complete(operation)
            return item
        except Exception:
            if moved and target.exists():
                shutil.rmtree(target)
                os.replace(backup, target)
            raise
        finally:
            shutil.rmtree(staged.parent, ignore_errors=True)
            shutil.rmtree(inspection.candidate_root, ignore_errors=True)

    def list(self) -> tuple[StoredCreation, ...]: return self._catalog.list()
    def get(self, creation_id: str) -> StoredCreation | None: return self._catalog.get(creation_id)
    def generation(self) -> int: return self._catalog.generation()

    def set_enabled(self, creation_id: str, enabled: bool, *, changed_by: str, reason: str) -> StoredCreation:
        item = self._required(creation_id)
        binding = self._audiences.binding_for(_resource(creation_id))
        if binding is None: raise CreationLifecycleError("Creation has no selected agent audience.")
        if enabled:
            self._audiences.set_audience(_resource(creation_id), binding.audience, changed_by=changed_by, reason=reason)
        else:
            self._audiences.deactivate(_resource(creation_id), changed_by=changed_by, reason=reason)
        return self._catalog.save(StoredCreation(item.creation_id, item.title, item.description, item.content_hash, item.install_path, "enabled" if enabled else "disabled", item.generation, item.source_type, item.entry_url, item.icon_url, item.theme_color), action="enable" if enabled else "disable", changed_by=changed_by, reason=reason)

    def delete(self, creation_id: str, *, changed_by: str, reason: str) -> StoredCreation:
        item = self._required(creation_id)
        self._audiences.remove_resource(_resource(creation_id), changed_by=changed_by, reason=reason)
        shutil.rmtree(item.install_path, ignore_errors=True)
        shutil.rmtree(self._rollback_root / creation_id, ignore_errors=True)
        removed = self._catalog.remove(creation_id, changed_by=changed_by, reason=reason)
        if removed is None: raise CreationLifecycleError("Creation no longer exists.")
        return removed

    def recover(self) -> None:
        self._recovery.recover("creation", lambda name: (item.content_hash if (item := self._catalog.get(name)) else None))

    def _required(self, creation_id: str) -> StoredCreation:
        item = self._catalog.get(creation_id)
        if item is None: raise CreationLifecycleError("Creation does not exist.")
        return item


def _resource(creation_id: str) -> AudienceResource: return AudienceResource(AudienceResourceKind.CREATION, creation_id)


def _hash_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file(): digest.update(path.relative_to(root).as_posix().encode()); digest.update(path.read_bytes())
    return digest.hexdigest()
