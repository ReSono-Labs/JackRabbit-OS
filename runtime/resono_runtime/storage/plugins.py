from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .database import RuntimeDatabase


@dataclass(frozen=True, slots=True)
class StoredPlugin:
    name: str
    content_hash: str
    install_path: Path
    lifecycle_state: str


class PluginCatalogRepository:
    def __init__(self, database: RuntimeDatabase) -> None:
        self._database = database

    def get(self, name: str) -> StoredPlugin | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT plugin_name, content_hash, install_path, lifecycle_state FROM plugin_catalog WHERE plugin_name = ?", (name,)).fetchone()
        return StoredPlugin(row[0], row[1], Path(row[2]), row[3]) if row else None

    def list(self) -> tuple[StoredPlugin, ...]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT plugin_name, content_hash, install_path, lifecycle_state FROM plugin_catalog ORDER BY plugin_name").fetchall()
        return tuple(StoredPlugin(row[0], row[1], Path(row[2]), row[3]) for row in rows)

    def was_removed(self, name: str) -> bool:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT action FROM plugin_catalog_audit WHERE plugin_name = ? ORDER BY audit_id DESC LIMIT 1",
                (name,),
            ).fetchone()
        return bool(row and row[0] == "remove")

    def save(self, item: StoredPlugin, *, action: str, changed_by: str, reason: str) -> StoredPlugin:
        previous = self.get(item.name)
        now = datetime.now(UTC).isoformat()
        with self._database.connect() as connection:
            connection.execute("""INSERT INTO plugin_catalog (plugin_name,content_hash,install_path,lifecycle_state,created_at,updated_at)
            VALUES (?,?,?,?,?,?) ON CONFLICT(plugin_name) DO UPDATE SET content_hash=excluded.content_hash,install_path=excluded.install_path,lifecycle_state=excluded.lifecycle_state,updated_at=excluded.updated_at""", (item.name,item.content_hash,str(item.install_path),item.lifecycle_state,now,now))
            connection.execute("INSERT INTO plugin_catalog_audit (plugin_name,action,previous_hash,current_hash,changed_at,changed_by,change_reason) VALUES (?,?,?,?,?,?,?)", (item.name,action,previous.content_hash if previous else None,item.content_hash,now,changed_by,reason))
            connection.commit()
        return item

    def remove(self, name: str, *, changed_by: str, reason: str) -> StoredPlugin | None:
        previous = self.get(name)
        if previous is None:
            return None
        now = datetime.now(UTC).isoformat()
        with self._database.connect() as connection:
            connection.execute("DELETE FROM plugin_components WHERE plugin_name = ?", (name,))
            connection.execute("DELETE FROM plugin_catalog WHERE plugin_name = ?", (name,))
            connection.execute("INSERT INTO plugin_catalog_audit (plugin_name,action,previous_hash,current_hash,changed_at,changed_by,change_reason) VALUES (?,'remove',?,NULL,?,?,?)", (name, previous.content_hash, now, changed_by, reason))
            connection.commit()
        return previous
