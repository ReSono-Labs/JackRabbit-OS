"""Sealed provider API-key envelopes; one canonical owner per provider."""

from __future__ import annotations

from datetime import UTC, datetime

from .database import RuntimeDatabase


class ProviderKeyRepository:
    def __init__(self, database: RuntimeDatabase) -> None:
        self._database = database

    def get(self, provider_id: str) -> str | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT envelope FROM provider_keys WHERE provider_id = ?",
                (provider_id,),
            ).fetchone()
        return str(row["envelope"]) if row is not None else None

    def put(self, provider_id: str, envelope: str) -> None:
        if not provider_id.strip():
            raise ValueError("provider_id is required.")
        if not envelope:
            raise ValueError("Provider key envelope cannot be empty.")
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO provider_keys(provider_id, envelope, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(provider_id) DO UPDATE SET
                    envelope = excluded.envelope,
                    updated_at = excluded.updated_at
                """,
                (provider_id, envelope, datetime.now(UTC).isoformat()),
            )
            connection.commit()

    def delete(self, provider_id: str) -> bool:
        with self._database.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM provider_keys WHERE provider_id = ?",
                (provider_id,),
            )
            connection.commit()
        return cursor.rowcount > 0
