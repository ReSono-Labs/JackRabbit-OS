"""SQLite metadata repository for the durable user workspace."""

from __future__ import annotations

from ..workspace.contract import WorkspaceEntry
from .database import RuntimeDatabase


class WorkspaceRepository:
    def __init__(self, database: RuntimeDatabase) -> None:
        self._database = database

    def save(self, *, workspace_id: str, reference: str, display_name: str, media_type: str,
             byte_size: int, content_hash: str, origin: str, origin_run_id: str | None,
             artifact_role: str) -> WorkspaceEntry:
        with self._database.connect() as connection:
            connection.execute(
                "INSERT INTO workspace_entries(workspace_id, reference, display_name, media_type, byte_size, content_hash, origin, origin_run_id, artifact_role, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'), strftime('%Y-%m-%dT%H:%M:%fZ','now'))",
                (workspace_id, reference, display_name, media_type, byte_size, content_hash,
                 origin, origin_run_id, artifact_role),
            )
            connection.commit()
        return self.get(reference)

    def get(self, reference: str) -> WorkspaceEntry:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM workspace_entries WHERE reference = ?", (reference,)).fetchone()
        if row is None:
            raise KeyError(reference)
        return _entry(row)

    def list(self, *, prefix: str | None = None, limit: int = 100) -> tuple[WorkspaceEntry, ...]:
        if limit < 1 or limit > 200:
            raise ValueError("workspace limit must be between 1 and 200")
        with self._database.connect() as connection:
            if prefix:
                rows = connection.execute("SELECT * FROM workspace_entries WHERE reference LIKE ? ORDER BY updated_at DESC LIMIT ?", (prefix + "%", limit)).fetchall()
            else:
                rows = connection.execute("SELECT * FROM workspace_entries ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
        return tuple(_entry(row) for row in rows)

    def remove(self, reference: str) -> None:
        with self._database.connect() as connection:
            connection.execute("DELETE FROM workspace_entries WHERE reference = ?", (reference,))
            connection.commit()


def _entry(row) -> WorkspaceEntry:
    return WorkspaceEntry(
        str(row["workspace_id"]), str(row["reference"]), str(row["display_name"]),
        str(row["media_type"]), int(row["byte_size"]), str(row["content_hash"]),
        str(row["origin"]), str(row["origin_run_id"]) if row["origin_run_id"] else None,
        str(row["artifact_role"]), str(row["created_at"]), str(row["updated_at"]),
    )
