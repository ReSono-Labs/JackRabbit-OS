"""One-canonical-item Skill import, replacement, and lifecycle coordination."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import secrets
import shutil

from resono_runtime.agents import AgentAudience, AgentAudienceRouter, AudienceResource, AudienceResourceKind
from resono_runtime.imports import ImportPreflightError, ImportPreflightRegistry, ImportRecovery
from resono_runtime.skills.archives import SkillArchiveInspection
from resono_runtime.skills.specification import SkillDocument, SkillSpecificationError, parse_skill_document
from resono_runtime.storage.skills import SkillCatalogRepository, StoredSkill


class SkillLifecycleError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SkillPreflight:
    token: str | None
    state: str
    document: SkillDocument | None
    content_hash: str | None
    current: StoredSkill | None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class _PendingSkill:
    candidate: SkillArchiveInspection
    document: SkillDocument
    source_root: Path


class SkillLifecycle:
    """Owns Skill state transitions; transport and UI remain outside this module."""

    def __init__(
        self,
        *,
        catalog: SkillCatalogRepository,
        audiences: AgentAudienceRouter,
        skills_root: Path,
        rollback_root: Path,
        recovery: ImportRecovery | None = None,
    ) -> None:
        self._catalog = catalog
        self._audiences = audiences
        self._skills_root = skills_root
        self._rollback_root = rollback_root
        self._recovery = recovery
        self._preflights: ImportPreflightRegistry[_PendingSkill] = ImportPreflightRegistry()

    def preflight(self, candidate: SkillArchiveInspection, *, audience: AgentAudience) -> SkillPreflight:
        self._clean_expired_preflights()
        try:
            document, source_root = _document_and_root(candidate)
        except SkillSpecificationError as error:
            _remove_candidate(candidate)
            return SkillPreflight(None, "blocked", None, None, None, str(error))
        content_hash = _content_hash(source_root)
        current = self._catalog.get(document.name)
        record = self._preflights.issue(
            identity=document.name,
            candidate_hash=content_hash,
            current_hash=current.content_hash if current is not None else None,
            audience=audience,
            payload=_PendingSkill(
                candidate=candidate,
                document=document,
                source_root=source_root,
            ),
        )
        return SkillPreflight(record.token, record.state, document, content_hash, current)

    def list(self) -> list[StoredSkill]:
        return self._catalog.list()

    def inspect(self, name: str) -> StoredSkill | None:
        return self._catalog.get(name)

    def confirm(
        self,
        token: str,
        *,
        replace: bool,
        changed_by: str,
        reason: str,
    ) -> StoredSkill:
        pending_record = self._consume_preflight(token, replace=replace)
        pending = pending_record.payload
        current = self._catalog.get(pending.document.name)

        target = self._skills_root / pending.document.name
        staged = self._stage(pending)
        backup = self._rollback_root / pending.document.name
        operation = self._recovery.begin(
            resource_kind="skill",
            identity=pending.document.name,
            candidate_hash=pending_record.candidate_hash,
            target=target,
            backup=backup,
            staged=staged,
        ) if self._recovery is not None else None
        replaced_path = False
        try:
            if target.exists():
                if backup.exists():
                    shutil.rmtree(backup)
                backup.parent.mkdir(parents=True, exist_ok=True)
                os.replace(target, backup)
                replaced_path = True
            if operation is not None:
                self._recovery.mark_backup_secured(operation)
            os.replace(staged, target)
            if operation is not None:
                self._recovery.mark_activated(operation)
            stored = self._catalog.save_current(
                name=pending.document.name,
                description=pending.document.description,
                content_hash=pending_record.candidate_hash,
                install_path=target,
                source_filename=pending.candidate.source_filename,
                state="enabled",
                action="replace" if current is not None else "install",
                changed_by=changed_by,
                reason=reason,
            )
            self._audiences.set_audience(
                _skill_resource(pending.document.name),
                pending_record.audience,
                changed_by=changed_by,
                reason=reason,
            )
            if operation is not None:
                self._recovery.complete(operation)
            return stored
        except Exception:
            if target.exists() and replaced_path:
                shutil.rmtree(target)
                os.replace(backup, target)
            raise
        finally:
            if staged.exists():
                shutil.rmtree(staged, ignore_errors=True)
            _remove_candidate(pending.candidate)

    def enable(self, name: str, *, changed_by: str, reason: str) -> StoredSkill:
        current = self._required(name)
        if not (current.install_path / "SKILL.md").is_file():
            raise SkillLifecycleError("The installed Skill files are missing.")
        binding = self._audiences.binding_for(_skill_resource(name))
        if binding is None:
            raise SkillLifecycleError("The installed Skill has no selected agent audience.")
        self._audiences.set_audience(
            _skill_resource(name),
            binding.audience,
            changed_by=changed_by,
            reason=reason,
        )
        return self._catalog.save_current(
            name=current.name,
            description=current.description,
            content_hash=current.content_hash,
            install_path=current.install_path,
            source_filename=current.source_filename,
            state="enabled",
            action="enable",
            changed_by=changed_by,
            reason=reason,
        )

    def recover(self) -> None:
        if self._recovery is not None:
            self._recovery.recover(
                "skill",
                lambda name: (item.content_hash if (item := self._catalog.get(name)) is not None else None),
            )

    def disable(self, name: str, *, changed_by: str, reason: str) -> StoredSkill:
        current = self._required(name)
        self._audiences.deactivate(_skill_resource(name), changed_by=changed_by, reason=reason)
        return self._catalog.save_current(
            name=current.name,
            description=current.description,
            content_hash=current.content_hash,
            install_path=current.install_path,
            source_filename=current.source_filename,
            state="disabled",
            action="disable",
            changed_by=changed_by,
            reason=reason,
        )

    def delete(self, name: str, *, changed_by: str, reason: str) -> StoredSkill:
        current = self.disable(name, changed_by=changed_by, reason="disable before delete")
        self._audiences.remove_resource(_skill_resource(name), changed_by=changed_by, reason=reason)
        if current.install_path.exists():
            shutil.rmtree(current.install_path)
        rollback = self._rollback_root / name
        if rollback.exists():
            shutil.rmtree(rollback)
        removed = self._catalog.remove(name, changed_by=changed_by, reason=reason)
        if removed is None:
            raise SkillLifecycleError("The installed Skill no longer exists.")
        return removed

    def _consume_preflight(self, token: str, *, replace: bool):
        try:
            preview = self._preflights.peek(token)
            current = self._catalog.get(preview.identity)
            current_hash = current.content_hash if current is not None else None
            record = self._preflights.consume(token, current_hash=current_hash, replace=replace)
        except ImportPreflightError as error:
            raise SkillLifecycleError(str(error)) from error
        return record

    def _clean_expired_preflights(self) -> None:
        for record in self._preflights.discard_expired():
            _remove_candidate(record.payload.candidate)

    def _stage(self, pending: _PendingSkill) -> Path:
        self._skills_root.mkdir(parents=True, exist_ok=True)
        staging_parent = self._skills_root / ".staging"
        staging_parent.mkdir(parents=True, exist_ok=True)
        staged = staging_parent / secrets.token_hex(16) / pending.document.name
        staged.parent.mkdir(parents=True, exist_ok=False)
        shutil.copytree(pending.source_root, staged)
        source_document = staged / pending.candidate.source_document.relative_to(pending.source_root)
        canonical_document = staged / "SKILL.md"
        if source_document != canonical_document:
            source_document.replace(canonical_document)
        return staged

    def _required(self, name: str) -> StoredSkill:
        current = self._catalog.get(name)
        if current is None:
            raise SkillLifecycleError("The installed Skill does not exist.")
        return current


def _document_and_root(candidate: SkillArchiveInspection) -> tuple[SkillDocument, Path]:
    relative = candidate.source_document.relative_to(candidate.content_root)
    source_root = candidate.source_document.parent if len(relative.parts) == 2 else candidate.content_root
    expected_directory = source_root.name if source_root != candidate.content_root else None
    return parse_skill_document(candidate.source_document, expected_directory=expected_directory), source_root


def _content_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        content = path.read_bytes()
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _skill_resource(name: str) -> AudienceResource:
    return AudienceResource(AudienceResourceKind.SKILL, name)


def _remove_candidate(candidate: SkillArchiveInspection) -> None:
    shutil.rmtree(candidate.quarantine_root, ignore_errors=True)
