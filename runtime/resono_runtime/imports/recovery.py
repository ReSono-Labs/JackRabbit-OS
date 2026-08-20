"""Durable reconciliation for interrupted Skill and Plugin directory swaps."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
import os
import shutil
from uuid import uuid4

from ..storage.database import RuntimeDatabase


@dataclass(frozen=True, slots=True)
class ImportOperation:
    operation_id: str
    resource_kind: str
    identity: str
    candidate_hash: str
    target: Path
    backup: Path
    staged: Path
    phase: str = "planned"


class ImportRecovery:
    def __init__(self, database: RuntimeDatabase) -> None:
        self._database = database

    def begin(self, *, resource_kind: str, identity: str, candidate_hash: str, target: Path, backup: Path, staged: Path) -> ImportOperation:
        operation = ImportOperation(str(uuid4()), resource_kind, identity, candidate_hash, target, backup, staged)
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO import_operations(
                    operation_id, resource_kind, identity, candidate_hash,
                    target_path, backup_path, staged_path, started_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (operation.operation_id, resource_kind, identity, candidate_hash, str(target), str(backup), str(staged), datetime.now(UTC).isoformat()),
            )
            connection.commit()
        return operation

    def complete(self, operation: ImportOperation) -> None:
        with self._database.connect() as connection:
            connection.execute("DELETE FROM import_operations WHERE operation_id = ?", (operation.operation_id,))
            connection.commit()

    def mark_backup_secured(self, operation: ImportOperation) -> None:
        self._set_phase(operation, "backup_secured")

    def mark_activated(self, operation: ImportOperation) -> None:
        self._set_phase(operation, "activated")

    def recover(self, resource_kind: str, current_hash: Callable[[str], str | None]) -> None:
        for operation in self._list(resource_kind):
            committed = current_hash(operation.identity) == operation.candidate_hash
            if committed:
                shutil.rmtree(operation.backup, ignore_errors=True)
            elif operation.phase == "activated":
                if operation.target.exists():
                    shutil.rmtree(operation.target, ignore_errors=True)
                if operation.backup.exists():
                    operation.target.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(operation.backup, operation.target)
            elif operation.phase == "backup_secured" and operation.backup.exists():
                operation.target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(operation.backup, operation.target)
            shutil.rmtree(operation.staged.parent, ignore_errors=True)
            self.complete(operation)

    def _set_phase(self, operation: ImportOperation, phase: str) -> None:
        with self._database.connect() as connection:
            connection.execute(
                "UPDATE import_operations SET phase = ? WHERE operation_id = ?",
                (phase, operation.operation_id),
            )
            connection.commit()

    def _list(self, resource_kind: str) -> tuple[ImportOperation, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT operation_id, resource_kind, identity, candidate_hash, target_path, backup_path, staged_path, phase FROM import_operations WHERE resource_kind = ?",
                (resource_kind,),
            ).fetchall()
        return tuple(ImportOperation(row[0], row[1], row[2], row[3], Path(row[4]), Path(row[5]), Path(row[6]), row[7]) for row in rows)
