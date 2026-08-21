"""Stable workspace references and metadata contracts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath


WORKSPACE_DIRECTORIES = ("inbox", "documents", "projects", "generated", "downloads", "scratch")


class WorkspaceError(ValueError):
    pass


def normalized_ref(value: str) -> str:
    if not isinstance(value, str) or not value.startswith("workspace://") or "\x00" in value or "\\" in value:
        raise WorkspaceError("workspace reference is invalid")
    relative = value.removeprefix("workspace://")
    path = PurePosixPath(relative)
    if path.is_absolute() or len(path.parts) < 2 or path.parts[0] not in WORKSPACE_DIRECTORIES:
        raise WorkspaceError("workspace reference must use an allowed directory")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise WorkspaceError("workspace reference must be normalized")
    return path.as_posix()


@dataclass(frozen=True, slots=True)
class WorkspaceEntry:
    workspace_id: str
    reference: str
    display_name: str
    media_type: str
    byte_size: int
    content_hash: str
    origin: str
    origin_run_id: str | None
    artifact_role: str
    created_at: str
    updated_at: str
