from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import json
from uuid import uuid4

from resono_runtime.storage.database import RuntimeDatabase
from .models import Task

_SELECT = "SELECT task_id, task_text, status, created_at, updated_at, completed_at FROM tasks"


class TaskRepository:
    """Owns canonical Tasks records and single-use reviewed mutations."""

    def __init__(self, database: RuntimeDatabase) -> None:
        self._database = database

    def list(self, *, include_completed: bool = False, limit: int = 100) -> tuple[Task, ...]:
        where = "" if include_completed else "WHERE status = 'open'"
        with self._database.connect() as connection:
            rows = connection.execute(
                f"{_SELECT} {where} ORDER BY created_at, task_id LIMIT ?",
                (max(1, min(limit, 200)),),
            ).fetchall()
        return tuple(_task(row) for row in rows)

    def get(self, task_id: str) -> Task | None:
        with self._database.connect() as connection:
            row = connection.execute(f"{_SELECT} WHERE task_id = ?", (task_id,)).fetchone()
        return _task(row) if row is not None else None

    def prepare(self, *, operation: str, task_id: str | None, payload: dict[str, object],
                voice_session_id: str, tool_call_id: str, utterance_id: int) -> dict[str, object]:
        if operation not in {"add", "edit", "complete", "remove"}:
            raise ValueError("Task operation is invalid.")
        if operation != "add" and (task_id is None or self.get(task_id) is None):
            raise ValueError("Task was not found.")
        if not voice_session_id or not tool_call_id or utterance_id <= 0:
            raise ValueError("A trusted Voice invocation is required for Task changes.")
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        content_hash = hashlib.sha256(canonical.encode()).hexdigest()
        action_id = str(uuid4())
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=10)
        with self._database.connect() as connection:
            connection.execute(
                """INSERT INTO task_pending_actions(
                    action_id, task_id, operation, payload_json, content_hash, state,
                    voice_session_id, tool_call_id, prepared_utterance_id,
                    expires_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'pending_review', ?, ?, ?, ?, ?, ?)""",
                (action_id, task_id, operation, canonical, content_hash, voice_session_id,
                 tool_call_id, utterance_id, expires_at.isoformat(), now.isoformat(), now.isoformat()),
            )
            connection.commit()
        return {"actionId": action_id, "contentHash": content_hash, "operation": operation,
                "taskId": task_id, "proposed": payload, "expiresAt": expires_at.isoformat(),
                "confirmationRequired": True}

    def add_synced(self, text: str) -> Task | None:
        """Insert an open task on behalf of the companion server sync.

        Uses the exact same record shape as the reviewed add flow; only the
        entry point differs because companion additions carry no Voice review.
        """
        value = (text or "").strip()
        if not value:
            raise ValueError("text is required.")
        now = datetime.now(UTC).isoformat()
        task_id = str(uuid4())
        with self._database.connect() as connection:
            connection.execute(
                "INSERT INTO tasks(task_id, task_text, status, created_at, updated_at) VALUES (?, ?, 'open', ?, ?)",
                (task_id, value, now, now),
            )
            connection.commit()
        return self.get(task_id)

    def claim(self, *, action_id: str, content_hash: str, voice_session_id: str,
              approval_utterance_id: int) -> dict[str, object]:
        now = datetime.now(UTC).isoformat()
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """SELECT task_id, operation, payload_json FROM task_pending_actions
                WHERE action_id = ? AND content_hash = ? AND voice_session_id = ?
                  AND state = 'pending_review' AND expires_at >= ? AND prepared_utterance_id < ?""",
                (action_id, content_hash, voice_session_id, now, approval_utterance_id),
            ).fetchone()
            if row is None:
                connection.rollback()
                raise ValueError("The reviewed Task change is stale, changed, expired, or already used.")
            connection.execute(
                "UPDATE task_pending_actions SET state = 'executing', updated_at = ? WHERE action_id = ?",
                (now, action_id),
            )
            connection.commit()
        return {"taskId": row[0], "operation": row[1], "payload": json.loads(row[2])}

    def execute(self, claim: dict[str, object]) -> Task | None:
        operation = str(claim["operation"])
        payload = claim["payload"]
        if not isinstance(payload, dict):
            raise ValueError("Task payload is invalid.")
        now = datetime.now(UTC).isoformat()
        task_id = str(claim["taskId"] or uuid4())
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if operation == "add":
                connection.execute("INSERT INTO tasks(task_id, task_text, status, created_at, updated_at) VALUES (?, ?, 'open', ?, ?)", (task_id, _text(payload), now, now))
            elif operation == "edit":
                connection.execute("UPDATE tasks SET task_text = ?, updated_at = ? WHERE task_id = ?", (_text(payload), now, task_id))
            elif operation == "complete":
                connection.execute("UPDATE tasks SET status = 'completed', completed_at = ?, updated_at = ? WHERE task_id = ?", (now, now, task_id))
            else:
                connection.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            connection.commit()
        return None if operation == "remove" else self.get(task_id)

    def finish(self, action_id: str, *, completed: bool) -> None:
        with self._database.connect() as connection:
            connection.execute("UPDATE task_pending_actions SET state = ?, updated_at = ? WHERE action_id = ?", ("completed" if completed else "failed", datetime.now(UTC).isoformat(), action_id))
            connection.commit()


def _task(row: object) -> Task:
    return Task(str(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4]), str(row[5]) if row[5] is not None else None)


def _text(payload: dict[str, object]) -> str:
    value = payload.get("text")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("text is required.")
    return value.strip()
