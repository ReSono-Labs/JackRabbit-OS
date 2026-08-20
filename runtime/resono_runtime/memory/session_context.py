from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..storage.memory import MemoryRecord, MemoryRepository
from ..storage.sessions import SessionSummary, SessionTranscriptRepository


# Donor parity: app/vault_runtime/session_context_builder.py uses
# STARTUP_MEMORY_RECORD_LIMIT = 8 for the approved-memory section injected at
# session start. The donor fetches beyond the limit (64) to skip legacy/fixture
# rows; this standalone store has no legacy extractor, so the active-memory
# query already yields only validated records and we cap at the limit.
STARTUP_MEMORY_LIMIT = 8
STARTUP_MEMORY_CHARACTER_LIMIT = 4_096
STARTUP_SUMMARY_CHARACTER_LIMIT = 4_096


@dataclass(frozen=True, slots=True)
class SessionContext:
    """Context handed to a model at the start of a session.

    Mirrors the donor's startup context packet: the most recent approved memory
    records and the previous session's completed summary. ``render()`` produces
    a single instruction block; an empty render means there is no past context.
    """

    memories: tuple[MemoryRecord, ...]
    previous_summary: SessionSummary | None

    def render(self) -> str:
        sections: list[str] = []
        if self.memories:
            lines = ["Approved memory from prior conversations:"]
            for record in self.memories:
                content = record.content_text.strip()
                if len(content) > STARTUP_MEMORY_CHARACTER_LIMIT:
                    content = content[:STARTUP_MEMORY_CHARACTER_LIMIT] + "…"
                lines.append(
                    f"- ({record.memory_class}) {record.memory_key}: {content} "
                    f"[confidence={record.confidence}]"
                )
            sections.append("\n".join(lines))
        if self.previous_summary is not None and self.previous_summary.summary_text:
            summary = self.previous_summary.summary_text.strip()
            if len(summary) > STARTUP_SUMMARY_CHARACTER_LIMIT:
                summary = summary[:STARTUP_SUMMARY_CHARACTER_LIMIT] + "…"
            sections.append("Previous session summary:\n" + summary)
        if not sections:
            return ""
        return (
            "You begin with the following recalled context about this user. "
            "Use it when relevant; do not mention that you have it unless asked.\n\n"
            + "\n\n".join(sections)
        )


class SessionContextBuilder:
    """Builds the startup memory context for a new session.

    The donor resolves the immediately-prior provider session and falls back to
    the most recent completed summary when that one is still pending. This
    standalone store has no provider-session table, so the previous session is
    the most recently summarized session other than the current one.
    """

    def __init__(
        self,
        *,
        sessions: SessionTranscriptRepository,
        memories: MemoryRepository,
        startup_memory_limit: int = STARTUP_MEMORY_LIMIT,
    ) -> None:
        self._sessions = sessions
        self._memories = memories
        self._limit = startup_memory_limit

    def build(self, *, current_session_id: str | None = None) -> SessionContext:
        memories = self._memories.list_memories()[: self._limit]
        previous_summary = self._previous_completed_summary(current_session_id)
        return SessionContext(memories=memories, previous_summary=previous_summary)

    def _previous_completed_summary(self, current_session_id: str | None) -> SessionSummary | None:
        # Donor parity: the previous session is the most recently *finalized*
        # session other than the current one, ordered by completion time
        # (summary updated_at DESC) — never by the random session_id.
        for session_id in self._sessions.list_finalized_sessions():
            if current_session_id is not None and session_id == current_session_id:
                continue
            summary = self._sessions.summary(session_id)
            if summary is not None and summary.summary_text:
                return summary
        return None


def startup_context_dict(context: SessionContext) -> dict[str, Any]:
    """Support-safe summary of the startup context for inspection/logging."""
    return {
        "memoryCount": len(context.memories),
        "previousSummary": context.previous_summary is not None,
    }
