from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from resono_runtime.storage.connection_credentials import ConnectionCredentialRepository
from resono_runtime.storage.database import RuntimeDatabase


@dataclass(frozen=True, slots=True)
class ConnectionRecord:
    connection_id: str
    kind: str
    label: str
    enabled: bool
    health_state: str
    health_detail: str | None
    source_owner: str | None
    credential_present: bool
    created_at: str
    updated_at: str


class ConnectionRepository:
    """Cross-domain connection read model; domain owners control mutation."""

    def __init__(self, database: RuntimeDatabase) -> None:
        self._database = database
        self._credentials = ConnectionCredentialRepository(database)

    def get(self, connection_id: str) -> ConnectionRecord | None:
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT connection_id, kind, label, enabled, health_state, health_detail,
                       source_owner, created_at, updated_at
                FROM connections WHERE connection_id = ?
                """,
                (connection_id,),
            ).fetchone()
        return self._record(row)

    def list(self) -> tuple[ConnectionRecord, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT connection_id, kind, label, enabled, health_state, health_detail,
                       source_owner, created_at, updated_at
                FROM connections ORDER BY kind, label, connection_id
                """
            ).fetchall()
        return tuple(record for row in rows if (record := self._record(row)) is not None)

    def save(
        self,
        *,
        connection_id: str,
        kind: str,
        label: str,
        enabled: bool,
        health_state: str,
        health_detail: str | None = None,
        source_owner: str | None = None,
    ) -> ConnectionRecord:
        now = datetime.now(UTC).isoformat()
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO connections(
                    connection_id, kind, label, enabled, health_state, health_detail,
                    source_owner, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(connection_id) DO UPDATE SET
                    kind = excluded.kind,
                    label = excluded.label,
                    enabled = excluded.enabled,
                    health_state = excluded.health_state,
                    health_detail = excluded.health_detail,
                    source_owner = excluded.source_owner,
                    updated_at = excluded.updated_at
                """,
                (
                    connection_id,
                    kind,
                    label,
                    int(enabled),
                    health_state,
                    health_detail,
                    source_owner,
                    now,
                    now,
                ),
            )
            connection.commit()
        record = self.get(connection_id)
        if record is None:
            raise RuntimeError("Connection record was not persisted.")
        return record

    def remove(self, connection_id: str) -> bool:
        with self._database.connect() as connection:
            cursor = connection.execute("DELETE FROM connections WHERE connection_id = ?", (connection_id,))
            connection.commit()
        return cursor.rowcount > 0

    def _record(self, row: object) -> ConnectionRecord | None:
        if row is None:
            return None
        connection_id = str(row[0])
        return ConnectionRecord(
            connection_id=connection_id,
            kind=str(row[1]),
            label=str(row[2]),
            enabled=bool(row[3]),
            health_state=str(row[4]),
            health_detail=str(row[5]) if row[5] is not None else None,
            source_owner=str(row[6]) if row[6] is not None else None,
            credential_present=self._credentials.get_envelope(connection_id) is not None,
            created_at=str(row[7]),
            updated_at=str(row[8]),
        )
