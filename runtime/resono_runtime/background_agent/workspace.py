"""Path-confined, quota-bound storage for one background-agent run."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import threading


class WorkspaceViolation(ValueError):
    pass


class RunWorkspace:
    def __init__(self, root: Path, *, allowed_read: tuple[str, ...], allowed_write: tuple[str, ...], max_files: int, max_file_bytes: int, max_total_bytes: int) -> None:
        self._root = root.resolve()
        self._allowed_read = frozenset(_normal_grant(item) for item in allowed_read)
        self._allowed_write = frozenset(_normal_grant(item) for item in allowed_write)
        self._max_files = max_files
        self._max_file_bytes = max_file_bytes
        self._max_total_bytes = max_total_bytes
        if min(max_files, max_file_bytes, max_total_bytes) <= 0:
            raise ValueError("workspace quotas must be positive")
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def list_files(self) -> tuple[str, ...]:
        return tuple(sorted(str(path.relative_to(self._root)) for path in self._root.rglob("*") if path.is_file() and not path.is_symlink()))

    def read_text(self, ref: str) -> str:
        normalized, path = self._path(ref)
        if normalized not in self._allowed_read and normalized not in self._allowed_write and not self._allowed_prefix(normalized, self._allowed_read | self._allowed_write):
            raise WorkspaceViolation("file is not readable in this workspace")
        if not path.is_file() or path.is_symlink():
            raise WorkspaceViolation("workspace file does not exist")
        return path.read_text(encoding="utf-8")

    def path_for_publication(self, ref: str) -> Path:
        normalized, path = self._path(ref)
        if normalized not in self._allowed_read and normalized not in self._allowed_write and not self._allowed_prefix(normalized, self._allowed_read | self._allowed_write):
            raise WorkspaceViolation("file is not publishable from this workspace")
        if not path.is_file() or path.is_symlink():
            raise WorkspaceViolation("workspace file does not exist")
        return path

    def write_text(self, ref: str, content: str) -> None:
        normalized, path = self._path(ref)
        if normalized not in self._allowed_write and not self._allowed_prefix(normalized, self._allowed_write):
            raise WorkspaceViolation("file is not writable in this workspace")
        payload = content.encode("utf-8")
        if len(payload) > self._max_file_bytes:
            raise WorkspaceViolation("file exceeds the workspace file limit")
        existing = {item for item in self._root.rglob("*") if item.is_file() and not item.is_symlink()}
        if not path.exists() and len(existing) >= self._max_files:
            raise WorkspaceViolation("workspace file count limit reached")
        prior_size = path.stat().st_size if path.is_file() and not path.is_symlink() else 0
        total = sum(item.stat().st_size for item in existing) - prior_size + len(payload)
        if total > self._max_total_bytes:
            raise WorkspaceViolation("workspace storage limit reached")
        path.parent.mkdir(parents=True, exist_ok=True)
        self._deny_symlink_chain(path)
        fd, temporary = tempfile.mkstemp(prefix=".write-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _path(self, ref: str) -> tuple[str, Path]:
        normalized = _normal_ref(ref)
        path = (self._root / normalized).resolve(strict=False)
        try:
            path.relative_to(self._root)
        except ValueError as error:
            raise WorkspaceViolation("path leaves the run workspace") from error
        self._deny_symlink_chain(path)
        return normalized, path

    def _deny_symlink_chain(self, path: Path) -> None:
        current = self._root
        for part in path.relative_to(self._root).parts:
            current = current / part
            if current.is_symlink():
                raise WorkspaceViolation("workspace symlinks are not allowed")

    @staticmethod
    def _allowed_prefix(ref: str, allowed: frozenset[str]) -> bool:
        return any(item.endswith("/") and ref.startswith(item) for item in allowed)


class RunWorkspaceRegistry:
    """Owns temporary workspaces for active background runs."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._items: dict[str, RunWorkspace] = {}
        self._lock = threading.Lock()
        self._root.mkdir(parents=True, exist_ok=True)

    def create(self, run_id: str, *, max_total_bytes: int) -> RunWorkspace:
        path = self._run_path(run_id)
        workspace = RunWorkspace(
            path, allowed_read=("work/",), allowed_write=("work/",),
            max_files=max_total_bytes, max_file_bytes=max_total_bytes,
            max_total_bytes=max_total_bytes,
        )
        with self._lock:
            if run_id in self._items:
                raise RuntimeError("run workspace already exists")
            self._items[run_id] = workspace
        return workspace

    def release(self, run_id: str) -> None:
        """Forget and delete only this run's temporary workspace.

        Published artifacts live under DurableWorkspace and are never beneath
        this registry root. Repeated cleanup is intentionally harmless.
        """
        path = self._run_path(run_id)
        with self._lock:
            self._items.pop(run_id, None)
        if path.is_symlink():
            raise WorkspaceViolation("run workspace symlinks are not allowed")
        if path.exists():
            shutil.rmtree(path)

    def get(self, run_id: str) -> RunWorkspace:
        with self._lock:
            workspace = self._items.get(run_id)
        if workspace is None:
            path = self._run_path(run_id)
            if not path.is_dir() or path.is_symlink():
                raise KeyError(run_id)
            workspace = RunWorkspace(path, allowed_read=("work/",), allowed_write=("work/",),
                                     max_files=256 * 1024 * 1024,
                                     max_file_bytes=256 * 1024 * 1024,
                                     max_total_bytes=256 * 1024 * 1024)
        return workspace

    def _run_path(self, run_id: str) -> Path:
        if not isinstance(run_id, str) or not run_id or Path(run_id).name != run_id:
            raise WorkspaceViolation("run ID is invalid")
        path = (self._root / run_id).resolve(strict=False)
        try:
            path.relative_to(self._root)
        except ValueError as error:
            raise WorkspaceViolation("run workspace leaves its root") from error
        return path


def _normal_ref(ref: str) -> str:
    if not isinstance(ref, str) or not ref or "\x00" in ref or "\\" in ref:
        raise WorkspaceViolation("invalid workspace path")
    value = PurePosixPath(ref)
    if value.is_absolute() or any(part in {"", ".", ".."} for part in value.parts):
        raise WorkspaceViolation("workspace path must be relative and normalized")
    return value.as_posix()


def _normal_grant(ref: str) -> str:
    normalized = _normal_ref(ref)
    return normalized + "/" if ref.endswith("/") else normalized
