"""SQLite owner for the one-canonical-item standard Skill catalog."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from resono_runtime.storage.database import RuntimeDatabase


@dataclass(frozen=True, slots=True)
class StoredSkill:
    name: str
    description: str
    content_hash: str
    install_path: Path
    source_filename: str
    lifecycle_state: str
    created_at: str
    updated_at: str


class SkillCatalogRepository:
    """Stores one current Skill per standard Skill name and an audit trail."""

    def __init__(self, database: RuntimeDatabase) -> None:
        self._database = database

    def get(self, name: str) -> StoredSkill | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT skill_name, description, content_hash, install_path, source_filename, lifecycle_state, created_at, updated_at FROM skill_catalog WHERE skill_name = ?",
                (name,),
            ).fetchone()
        return _stored_skill(row)

    def list(self) -> list[StoredSkill]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT skill_name, description, content_hash, install_path, source_filename, lifecycle_state, created_at, updated_at FROM skill_catalog ORDER BY skill_name"
            ).fetchall()
        return [_stored_skill(row) for row in rows if row is not None]

    def save_current(
        self,
        *,
        name: str,
        description: str,
        content_hash: str,
        install_path: Path,
        source_filename: str,
        state: str,
        action: str,
        changed_by: str,
        reason: str,
    ) -> StoredSkill:
        previous = self.get(name)
        now = _timestamp()
        created_at = previous.created_at if previous else now
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO skill_catalog (
                    skill_name, description, content_hash, install_path, source_filename,
                    lifecycle_state, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(skill_name) DO UPDATE SET
                    description = excluded.description,
                    content_hash = excluded.content_hash,
                    install_path = excluded.install_path,
                    source_filename = excluded.source_filename,
                    lifecycle_state = excluded.lifecycle_state,
                    updated_at = excluded.updated_at
                """,
                (name, description, content_hash, str(install_path), source_filename, state, created_at, now),
            )
            connection.execute(
                """
                INSERT INTO skill_catalog_audit (
                    skill_name, action, previous_hash, current_hash,
                    changed_at, changed_by, change_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (name, action, previous.content_hash if previous else None, content_hash, now, changed_by, reason),
            )
            connection.commit()
        return StoredSkill(name, description, content_hash, install_path, source_filename, state, created_at, now)

    def remove(self, name: str, *, changed_by: str, reason: str) -> StoredSkill | None:
        previous = self.get(name)
        if previous is None:
            return None
        now = _timestamp()
        with self._database.connect() as connection:
            connection.execute("DELETE FROM skill_catalog WHERE skill_name = ?", (name,))
            connection.execute(
                """
                INSERT INTO skill_catalog_audit (
                    skill_name, action, previous_hash, current_hash,
                    changed_at, changed_by, change_reason
                ) VALUES (?, 'remove', ?, NULL, ?, ?, ?)
                """,
                (name, previous.content_hash, now, changed_by, reason),
            )
            connection.commit()
        return previous


def _stored_skill(row: object) -> StoredSkill | None:
    if row is None:
        return None
    return StoredSkill(
        name=row[0],
        description=row[1],
        content_hash=row[2],
        install_path=Path(row[3]),
        source_filename=row[4],
        lifecycle_state=row[5],
        created_at=row[6],
        updated_at=row[7],
    )


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()
