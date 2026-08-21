"""Delivery state kept separate from canonical background-run state."""

from __future__ import annotations

from dataclasses import dataclass
import json

from .database import RuntimeDatabase


@dataclass(frozen=True, slots=True)
class AgentRunDelivery:
    run_id: str
    channel: str
    state: str
    context_json: str
    updated_at: str


class AgentRunDeliveryRepository:
    def __init__(self, database: RuntimeDatabase) -> None:
        self._database = database

    def create(self, *, run_id: str, channel: str, state: str, context_json: str) -> None:
        with self._database.connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO background_agent_deliveries(run_id, channel, state, context_json, updated_at) VALUES (?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'))",
                (run_id, channel, state, context_json),
            )
            connection.commit()

    def set_state(self, *, run_id: str, channel: str, state: str) -> None:
        with self._database.connect() as connection:
            changed = connection.execute(
                "UPDATE background_agent_deliveries SET state = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE run_id = ? AND channel = ?",
                (state, run_id, channel),
            ).rowcount
            if changed != 1:
                raise KeyError((run_id, channel))
            connection.commit()

    def list_for_run(self, run_id: str) -> tuple[AgentRunDelivery, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM background_agent_deliveries WHERE run_id = ? ORDER BY channel", (run_id,)
            ).fetchall()
        return tuple(AgentRunDelivery(str(row["run_id"]), str(row["channel"]), str(row["state"]),
                                      str(row["context_json"]), str(row["updated_at"])) for row in rows)

    def claim_voice(self, session_id: str) -> AgentRunDelivery | None:
        """Lease one completion for its exact originating live Voice session."""
        if not session_id:
            return None
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT * FROM background_agent_deliveries WHERE channel = 'voice' "
                "AND (state = 'pending' OR (state = 'delivering' AND updated_at < "
                "strftime('%Y-%m-%dT%H:%M:%fZ','now','-30 seconds'))) ORDER BY updated_at LIMIT 32"
            ).fetchall()
            selected = None
            for row in rows:
                try:
                    context = json.loads(str(row["context_json"]))
                except (TypeError, ValueError):
                    continue
                if context.get("originSessionId") == session_id:
                    selected = row
                    break
            if selected is None:
                connection.rollback()
                return None
            changed = connection.execute(
                "UPDATE background_agent_deliveries SET state = 'delivering', "
                "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') "
                "WHERE run_id = ? AND channel = 'voice' AND state IN ('pending','delivering')",
                (str(selected["run_id"]),),
            ).rowcount
            if changed != 1:
                connection.rollback()
                return None
            connection.commit()
        return AgentRunDelivery(
            str(selected["run_id"]), "voice", "delivering",
            str(selected["context_json"]), str(selected["updated_at"]),
        )

    def acknowledge_voice(self, *, run_id: str, session_id: str) -> bool:
        if not run_id or not session_id:
            return False
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT context_json, state FROM background_agent_deliveries "
                "WHERE run_id = ? AND channel = 'voice'", (run_id,),
            ).fetchone()
            if row is None or str(row["state"]) != "delivering":
                connection.rollback()
                return False
            try:
                context = json.loads(str(row["context_json"]))
            except (TypeError, ValueError):
                connection.rollback()
                return False
            if context.get("originSessionId") != session_id:
                connection.rollback()
                return False
            connection.execute(
                "UPDATE background_agent_deliveries SET state = 'delivered', "
                "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') "
                "WHERE run_id = ? AND channel = 'voice'", (run_id,),
            )
            connection.commit()
            return True
