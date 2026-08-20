from __future__ import annotations

from datetime import UTC, datetime

from .database import RuntimeDatabase


class ConnectionCredentialRepository:
    """Stores device-sealed envelopes only; plaintext never crosses this owner."""

    def __init__(self, database: RuntimeDatabase) -> None:
        self._database = database

    def get_envelope(self, connection_id: str) -> str | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT envelope FROM connection_credential_envelopes WHERE connection_id = ?",
                (connection_id,),
            ).fetchone()
        return str(row[0]) if row is not None else None

    def put_envelope(self, connection_id: str, envelope: str) -> None:
        if not envelope:
            raise ValueError("Credential envelope cannot be empty.")
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO connection_credential_envelopes(connection_id, envelope, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(connection_id) DO UPDATE SET
                    envelope = excluded.envelope,
                    updated_at = excluded.updated_at
                """,
                (connection_id, envelope, datetime.now(UTC).isoformat()),
            )
            connection.commit()

    def delete(self, connection_id: str) -> bool:
        with self._database.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM connection_credential_envelopes WHERE connection_id = ?",
                (connection_id,),
            )
            connection.commit()
        return cursor.rowcount > 0
