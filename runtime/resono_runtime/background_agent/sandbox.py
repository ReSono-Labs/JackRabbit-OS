"""Fail-closed sandbox contract; initial backend exposes no process execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .workspace import RunWorkspace


class SandboxUnavailable(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class WorkspacePolicy:
    allowed_read: tuple[str, ...]
    allowed_write: tuple[str, ...]
    max_files: int = 64
    max_file_bytes: int = 2 * 1024 * 1024
    max_total_bytes: int = 8 * 1024 * 1024


class WorkspaceSandbox:
    """Capability sandbox for host-owned file tools, never arbitrary commands."""

    backend_name = "workspace-only-v1"
    supports_process_execution = False

    def create(self, root: Path, policy: WorkspacePolicy) -> RunWorkspace:
        return RunWorkspace(
            root,
            allowed_read=policy.allowed_read,
            allowed_write=policy.allowed_write,
            max_files=policy.max_files,
            max_file_bytes=policy.max_file_bytes,
            max_total_bytes=policy.max_total_bytes,
        )

    def command(self, *_: object, **__: object) -> None:
        raise SandboxUnavailable("command execution has no approved R1 sandbox backend")
