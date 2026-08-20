from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .database import RuntimeDatabase


@dataclass(frozen=True, slots=True)
class StoredCreation:
    creation_id: str
    title: str
    description: str
    content_hash: str
    install_path: Path
    lifecycle_state: str
    generation: int
    source_type: str = "local_archive"
    entry_url: str | None = None
    icon_url: str | None = None
    theme_color: str = "#79f2dd"


class CreationCatalogRepository:
    def __init__(self, database: RuntimeDatabase) -> None:
        self._database = database

    def get(self, creation_id: str) -> StoredCreation | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT creation_id,title,description,content_hash,install_path,lifecycle_state,generation,source_type,entry_url,icon_url,theme_color FROM creation_catalog WHERE creation_id=?", (creation_id,)).fetchone()
        return _item(row)

    def list(self) -> tuple[StoredCreation, ...]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT creation_id,title,description,content_hash,install_path,lifecycle_state,generation,source_type,entry_url,icon_url,theme_color FROM creation_catalog ORDER BY creation_id").fetchall()
        return tuple(item for row in rows if (item := _item(row)) is not None)

    def generation(self) -> int:
        with self._database.connect() as connection:
            return int(connection.execute("SELECT generation FROM creation_catalog_state WHERE singleton=1").fetchone()[0])

    def save(self, item: StoredCreation, *, action: str, changed_by: str, reason: str) -> StoredCreation:
        previous = self.get(item.creation_id)
        now = datetime.now(UTC).isoformat()
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            generation = int(connection.execute("UPDATE creation_catalog_state SET generation=generation+1 WHERE singleton=1 RETURNING generation").fetchone()[0])
            connection.execute(
                """INSERT INTO creation_catalog(creation_id,title,description,content_hash,install_path,lifecycle_state,generation,created_at,updated_at,source_type,entry_url,icon_url,theme_color)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(creation_id) DO UPDATE SET title=excluded.title,description=excluded.description,content_hash=excluded.content_hash,install_path=excluded.install_path,lifecycle_state=excluded.lifecycle_state,generation=excluded.generation,updated_at=excluded.updated_at,source_type=excluded.source_type,entry_url=excluded.entry_url,icon_url=excluded.icon_url,theme_color=excluded.theme_color""",
                (item.creation_id, item.title, item.description, item.content_hash, str(item.install_path), item.lifecycle_state, generation, now, now, item.source_type, item.entry_url, item.icon_url, item.theme_color),
            )
            connection.execute("INSERT INTO creation_catalog_audit(creation_id,action,previous_hash,current_hash,changed_at,changed_by,change_reason) VALUES(?,?,?,?,?,?,?)", (item.creation_id, action, previous.content_hash if previous else None, item.content_hash, now, changed_by, reason))
            connection.commit()
        return StoredCreation(item.creation_id, item.title, item.description, item.content_hash, item.install_path, item.lifecycle_state, generation, item.source_type, item.entry_url, item.icon_url, item.theme_color)

    def remove(self, creation_id: str, *, changed_by: str, reason: str) -> StoredCreation | None:
        previous = self.get(creation_id)
        if previous is None:
            return None
        now = datetime.now(UTC).isoformat()
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM creation_catalog WHERE creation_id=?", (creation_id,))
            connection.execute("UPDATE creation_catalog_state SET generation=generation+1 WHERE singleton=1")
            connection.execute("INSERT INTO creation_catalog_audit(creation_id,action,previous_hash,current_hash,changed_at,changed_by,change_reason) VALUES(?,'remove',?,NULL,?,?,?)", (creation_id, previous.content_hash, now, changed_by, reason))
            connection.commit()
        return previous


def _item(row: object) -> StoredCreation | None:
    return StoredCreation(str(row[0]), str(row[1]), str(row[2]), str(row[3]), Path(row[4]), str(row[5]), int(row[6]), str(row[7]), str(row[8]) if row[8] is not None else None, str(row[9]) if row[9] is not None else None, str(row[10])) if row else None
