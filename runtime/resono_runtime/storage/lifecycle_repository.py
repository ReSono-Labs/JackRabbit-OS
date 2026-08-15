from __future__ import annotations

from dataclasses import dataclass

from .database import RuntimeDatabase


@dataclass(frozen=True, slots=True)
class LifecycleRecord:
    key: str
    value: str
    updated_at: str


class LifecycleRepository:
    def __init__(self, database: RuntimeDatabase) -> None:
        self._database = database

    def record_start(self) -> LifecycleRecord:
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT record_value FROM lifecycle_records WHERE record_key = 'runtime.start_count'"
            ).fetchone()
            value = str(int(row["record_value"]) + 1 if row else 1)
            connection.execute(
                "INSERT INTO lifecycle_records(record_key, record_value, updated_at) "
                "VALUES ('runtime.start_count', ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) "
                "ON CONFLICT(record_key) DO UPDATE SET "
                "record_value = excluded.record_value, updated_at = excluded.updated_at",
                (value,),
            )
            connection.commit()
        return self.get("runtime.start_count")

    def get(self, key: str) -> LifecycleRecord:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT record_key, record_value, updated_at FROM lifecycle_records WHERE record_key = ?",
                (key,),
            ).fetchone()
        if row is None:
            raise KeyError(key)
        return LifecycleRecord(
            key=str(row["record_key"]),
            value=str(row["record_value"]),
            updated_at=str(row["updated_at"]),
        )
