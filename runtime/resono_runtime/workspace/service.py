"""Confined atomic file operations for the durable user workspace."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import secrets
import tempfile

from ..storage.workspace import WorkspaceRepository
from .contract import WORKSPACE_DIRECTORIES, WorkspaceEntry, WorkspaceError, normalized_ref


class DurableWorkspace:
    def __init__(self, root: Path, repository: WorkspaceRepository, *, max_file_bytes: int = 16 * 1024 * 1024) -> None:
        self._root = root.resolve()
        self._repository = repository
        self._max_file_bytes = max_file_bytes
        for name in WORKSPACE_DIRECTORIES:
            (self._root / name).mkdir(parents=True, exist_ok=True)

    def list(self, *, directory: str | None = None, limit: int = 100) -> tuple[WorkspaceEntry, ...]:
        prefix = f"workspace://{directory}/" if directory else None
        if directory is not None and directory not in WORKSPACE_DIRECTORIES:
            raise WorkspaceError("workspace directory is invalid")
        return self._repository.list(prefix=prefix, limit=limit)

    def read(self, reference: str) -> bytes:
        relative = normalized_ref(reference)
        self._repository.get(reference)
        path = self._safe_path(relative)
        if not path.is_file() or path.is_symlink():
            raise WorkspaceError("workspace file does not exist")
        return path.read_bytes()

    def publish(self, source: Path, destination: str, *, media_type: str,
                origin_run_id: str, artifact_role: str) -> WorkspaceEntry:
        relative = normalized_ref(destination)
        target = self._safe_path(relative)
        if target.exists():
            raise FileExistsError("workspace destination already exists")
        if not source.is_file() or source.is_symlink():
            raise WorkspaceError("publication source is invalid")
        payload = source.read_bytes()
        if len(payload) > self._max_file_bytes:
            raise WorkspaceError("workspace file exceeds the size limit")
        target.parent.mkdir(parents=True, exist_ok=True)
        self._deny_symlinks(target)
        fd, temporary = tempfile.mkstemp(prefix=".publish-", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
            return self._repository.save(
                workspace_id=secrets.token_hex(16), reference=destination,
                display_name=target.name, media_type=media_type, byte_size=len(payload),
                content_hash=hashlib.sha256(payload).hexdigest(), origin="background_goal",
                origin_run_id=origin_run_id, artifact_role=artifact_role,
            )
        except Exception:
            if target.exists():
                target.unlink()
            raise
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _safe_path(self, relative: str) -> Path:
        path = (self._root / relative).resolve(strict=False)
        try:
            path.relative_to(self._root)
        except ValueError as error:
            raise WorkspaceError("workspace path escapes its root") from error
        self._deny_symlinks(path)
        return path

    def _deny_symlinks(self, path: Path) -> None:
        current = self._root
        for part in path.relative_to(self._root).parts:
            current = current / part
            if current.is_symlink():
                raise WorkspaceError("workspace symlinks are not allowed")
