from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import threading

from .migrations import LATEST_VERSION, MIGRATIONS


MIGRATION_VERSION = LATEST_VERSION


class RuntimeDatabase:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._migration_lock = threading.Lock()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
        finally:
            connection.close()

    def migrate(self) -> None:
        with self._migration_lock, self.connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            row = connection.execute(
                "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1"
            ).fetchone()
            current_version = int(row["version"]) if row else 0
            for migration in MIGRATIONS:
                if migration.version <= current_version:
                    continue
                migration.apply(connection)
                connection.execute(
                    "INSERT OR REPLACE INTO schema_migrations(version, applied_at) "
                    "VALUES (?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))",
                    (migration.version,),
                )
            connection.commit()

    def health(self) -> dict[str, object]:
        try:
            with self.connect() as connection:
                row = connection.execute(
                    "SELECT MAX(version) AS version FROM schema_migrations"
                ).fetchone()
                connection.execute("SELECT 1").fetchone()
            version = int(row["version"] or 0)
        except (OSError, sqlite3.Error):
            return {"status": "not_ready", "migrationVersion": 0}
        return {
            "status": "ready" if version == MIGRATION_VERSION else "not_ready",
            "migrationVersion": version,
        }
