from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import secrets

from .database import RuntimeDatabase


@dataclass(frozen=True, slots=True)
class TranscriptEntry:
    session_id: str
    entry_index: int
    role: str
    event_type: str
    text_content: str
    created_at: str


@dataclass(frozen=True, slots=True)
class SessionSummary:
    session_id: str
    summary_status: str
    summarizer_model_key: str | None
    transcript_text: str | None
    summary_text: str | None
    extracted_memory_count: int
    created_at: str
    updated_at: str


class SessionTranscriptRepository:
    """Provider-neutral persistence of a completed session's transcript and review summary."""

    def __init__(self, database: RuntimeDatabase) -> None:
        self._database = database

    def new_session_id(self) -> str:
        return secrets.token_hex(12)

    def append(
        self,
        *,
        session_id: str,
        role: str,
        event_type: str,
        text_content: str,
    ) -> TranscriptEntry:
        normalized_role = role.strip().lower()
        if normalized_role not in ("user", "assistant", "system", "tool"):
            raise ValueError("role must be user, assistant, system, or tool")
        content = text_content.strip()
        if not content or len(content) > 16_384:
            raise ValueError("text_content must be between 1 and 16,384 characters")
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT COALESCE(MAX(entry_index), -1) AS next_index "
                "FROM session_transcript_entries WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            entry_index = int(row["next_index"]) + 1
            connection.execute(
                "INSERT INTO session_transcript_entries("
                "session_id, entry_index, role, event_type, text_content, created_at) "
                "VALUES (?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))",
                (session_id, entry_index, normalized_role, event_type.strip(), content),
            )
            connection.commit()
        entries = self.entries(session_id)
        return entries[-1]

    def entries(self, session_id: str) -> tuple[TranscriptEntry, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT session_id, entry_index, role, event_type, text_content, created_at "
                "FROM session_transcript_entries WHERE session_id = ? "
                "ORDER BY entry_index ASC",
                (session_id,),
            ).fetchall()
        return tuple(_entry(row) for row in rows)

    def transcript_text(self, session_id: str) -> str:
        return "\n".join(
            f"{entry.role}: {entry.text_content}" for entry in self.entries(session_id)
        )

    def list_sessions(self) -> tuple[str, ...]:
        """All session ids that have a transcript, most recently active first.

        session_id is random hex (``secrets.token_hex``), so it is NOT a
        chronological key; ordering by it is meaningless. We order by the
        latest transcript entry timestamp instead.
        """
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT session_id, MAX(created_at) AS last_at "
                "FROM session_transcript_entries "
                "GROUP BY session_id "
                "ORDER BY last_at DESC"
            ).fetchall()
        return tuple(str(row["session_id"]) for row in rows)

    def list_finalized_sessions(self) -> tuple[str, ...]:
        """Session ids with a completed summary, most recently finalized first.

        Mirrors the donor's ``list_completed_session_summaries`` ordering
        (``updated_at DESC, created_at DESC``), used to select the previous
        session's summary at session start. Only sessions whose review
        produced a non-empty summary text are considered.
        """
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT s.session_id AS session_id "
                "FROM session_summaries s "
                "WHERE s.summary_status = 'completed' "
                "AND s.summary_text IS NOT NULL AND s.summary_text != '' "
                "ORDER BY s.updated_at DESC, s.created_at DESC"
            ).fetchall()
        return tuple(str(row["session_id"]) for row in rows)

    def summary(self, session_id: str) -> SessionSummary | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT session_id, summary_status, summarizer_model_key, transcript_text, "
                "summary_text, extracted_memory_count, created_at, updated_at "
                "FROM session_summaries WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return _summary(row) if row else None

    def store_summary(
        self,
        *,
        session_id: str,
        summary_status: str,
        summarizer_model_key: str | None,
        transcript_text: str,
        summary_text: str | None,
        extracted_memory_count: int,
    ) -> SessionSummary:
        with self._database.connect() as connection:
            connection.execute(
                "INSERT INTO session_summaries("
                "session_id, summary_status, summarizer_model_key, transcript_text, "
                "summary_text, extracted_memory_count, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, "
                "strftime('%Y-%m-%dT%H:%M:%fZ', 'now'), strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) "
                "ON CONFLICT(session_id) DO UPDATE SET "
                "summary_status=excluded.summary_status, "
                "summarizer_model_key=excluded.summarizer_model_key, "
                "transcript_text=excluded.transcript_text, "
                "summary_text=excluded.summary_text, "
                "extracted_memory_count=excluded.extracted_memory_count, "
                "updated_at=excluded.updated_at",
                (
                    session_id,
                    summary_status.strip().lower(),
                    summarizer_model_key,
                    transcript_text,
                    summary_text,
                    int(extracted_memory_count),
                ),
            )
            connection.commit()
        summary = self.summary(session_id)
        assert summary is not None
        return summary

    def delete_session(self, session_id: str) -> None:
        """Remove a session's transcript and summary. Memory records/embeddings are owned by MemoryRepository."""
        with self._database.connect() as connection:
            connection.execute(
                "DELETE FROM session_transcript_entries WHERE session_id = ?", (session_id,)
            )
            connection.execute(
                "DELETE FROM session_summaries WHERE session_id = ?", (session_id,)
            )
            connection.commit()


def _entry(row: object) -> TranscriptEntry:
    return TranscriptEntry(
        session_id=str(row["session_id"]),
        entry_index=int(row["entry_index"]),
        role=str(row["role"]),
        event_type=str(row["event_type"]),
        text_content=str(row["text_content"]),
        created_at=str(row["created_at"]),
    )


def _summary(row: object) -> SessionSummary:
    return SessionSummary(
        session_id=str(row["session_id"]),
        summary_status=str(row["summary_status"]),
        summarizer_model_key=str(row["summarizer_model_key"]) if row["summarizer_model_key"] else None,
        transcript_text=str(row["transcript_text"]) if row["transcript_text"] else None,
        summary_text=str(row["summary_text"]) if row["summary_text"] else None,
        extracted_memory_count=int(row["extracted_memory_count"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )
