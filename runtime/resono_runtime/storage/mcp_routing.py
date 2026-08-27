"""Per-audience active MCP connection routing (persisted selection)."""

from __future__ import annotations

from datetime import UTC, datetime

from ..agents.audience import AgentAudience

from .database import RuntimeDatabase

_AUDIENCES = {"voice", "text", "both"}


class McpRoutingRepository:
    """Stores which MCP connection is active for each agent audience."""

    def __init__(self, database: RuntimeDatabase) -> None:
        self._database = database

    def active(self, audience: AgentAudience) -> str | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT connection_id FROM mcp_connection_routing WHERE audience = ?",
                (_audience_value(audience),),
            ).fetchone()
        return str(row["connection_id"]) if row is not None else None

    def select(self, audience: AgentAudience, connection_id: str) -> str:
        value = _audience_value(audience)
        if not connection_id:
            raise ValueError("connection_id is required.")
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO mcp_connection_routing(audience, connection_id, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(audience) DO UPDATE SET
                    connection_id = excluded.connection_id,
                    updated_at = excluded.updated_at
                """,
                (value, connection_id, datetime.now(UTC).isoformat()),
            )
            connection.commit()
        return connection_id

    def unselect(self, audience: AgentAudience) -> bool:
        with self._database.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM mcp_connection_routing WHERE audience = ?",
                (_audience_value(audience),),
            )
            connection.commit()
        return cursor.rowcount > 0

    def audiences_for(self, connection_id: str) -> tuple[AgentAudience, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT audience FROM mcp_connection_routing WHERE connection_id = ? ORDER BY audience",
                (connection_id,),
            ).fetchall()
        return tuple(AgentAudience(str(row["audience"])) for row in rows)

    def remove_connection(self, connection_id: str) -> int:
        with self._database.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM mcp_connection_routing WHERE connection_id = ?",
                (connection_id,),
            )
            connection.commit()
        return cursor.rowcount


def _audience_value(audience: AgentAudience) -> str:
    if not isinstance(audience, AgentAudience):
        raise ValueError("audience must be an AgentAudience.")
    return audience.value
