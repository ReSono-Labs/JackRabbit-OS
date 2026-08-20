"""SQLite persistence and audit history for agent-audience bindings."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from resono_runtime.agents.audience import AgentAudience, AgentKind, AudienceResource, AudienceResourceKind
from resono_runtime.agents.routing import AudienceBinding
from resono_runtime.storage.database import RuntimeDatabase


class AgentAudienceRepository:
    """Persists one audience selection per canonical resource."""

    def __init__(self, database: RuntimeDatabase) -> None:
        self._database = database

    def save(self, resource: AudienceResource, audience: AgentAudience, *, changed_by: str, reason: str) -> AudienceBinding:
        previous = self.get(resource)
        changed_at = _timestamp()
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_audience_bindings (
                    resource_kind, resource_id, audience, active, changed_at, changed_by, change_reason
                ) VALUES (?, ?, ?, 1, ?, ?, ?)
                ON CONFLICT(resource_kind, resource_id) DO UPDATE SET
                    audience = excluded.audience,
                    active = 1,
                    changed_at = excluded.changed_at,
                    changed_by = excluded.changed_by,
                    change_reason = excluded.change_reason
                """,
                (resource.kind.value, resource.stable_id, audience.value, changed_at, changed_by, reason),
            )
            self._audit(connection, resource, previous.audience if previous else None, audience, "set", changed_at, changed_by, reason)
            connection.commit()
        return AudienceBinding(resource, audience, True, changed_at, changed_by, reason)

    def get(self, resource: AudienceResource) -> AudienceBinding | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT audience, active, changed_at, changed_by, change_reason FROM agent_audience_bindings WHERE resource_kind = ? AND resource_id = ?",
                (resource.kind.value, resource.stable_id),
            ).fetchone()
        return _binding(resource, row)

    def list_for(self, agent: AgentKind) -> list[AudienceBinding]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT resource_kind, resource_id, audience, active, changed_at, changed_by, change_reason
                FROM agent_audience_bindings
                WHERE active = 1 AND audience IN (?, ?)
                ORDER BY resource_kind, resource_id
                """,
                (agent.value, AgentAudience.BOTH.value),
            ).fetchall()
        return [
            AudienceBinding(
                AudienceResource(AudienceResourceKind(row[0]), row[1]),
                AgentAudience(row[2]), bool(row[3]), row[4], row[5], row[6],
            )
            for row in rows
        ]

    def deactivate(self, resource: AudienceResource, *, changed_by: str, reason: str) -> AudienceBinding | None:
        previous = self.get(resource)
        if previous is None:
            return None
        changed_at = _timestamp()
        with self._database.connect() as connection:
            connection.execute(
                "UPDATE agent_audience_bindings SET active = 0, changed_at = ?, changed_by = ?, change_reason = ? WHERE resource_kind = ? AND resource_id = ?",
                (changed_at, changed_by, reason, resource.kind.value, resource.stable_id),
            )
            self._audit(connection, resource, previous.audience, previous.audience, "disable", changed_at, changed_by, reason)
            connection.commit()
        return AudienceBinding(resource, previous.audience, False, changed_at, changed_by, reason)

    def remove(self, resource: AudienceResource, *, changed_by: str, reason: str) -> None:
        previous = self.get(resource)
        if previous is None:
            return
        changed_at = _timestamp()
        with self._database.connect() as connection:
            connection.execute(
                "DELETE FROM agent_audience_bindings WHERE resource_kind = ? AND resource_id = ?",
                (resource.kind.value, resource.stable_id),
            )
            self._audit(connection, resource, previous.audience, None, "remove", changed_at, changed_by, reason)
            connection.commit()

    @staticmethod
    def _audit(connection: sqlite3.Connection, resource: AudienceResource, previous: AgentAudience | None, new: AgentAudience | None, action: str, changed_at: str, changed_by: str, reason: str) -> None:
        connection.execute(
            """
            INSERT INTO agent_audience_audit (
                resource_kind, resource_id, previous_audience, new_audience, action,
                changed_at, changed_by, change_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (resource.kind.value, resource.stable_id, previous.value if previous else None, new.value if new else None, action, changed_at, changed_by, reason),
        )


def _binding(resource: AudienceResource, row: sqlite3.Row | None) -> AudienceBinding | None:
    if row is None:
        return None
    return AudienceBinding(resource, AgentAudience(row[0]), bool(row[1]), row[2], row[3], row[4])


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()
