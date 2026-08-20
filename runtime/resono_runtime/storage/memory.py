from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import json
import secrets
import struct
from typing import Any

from .database import RuntimeDatabase


_EMBEDDING_FLOAT_FORMAT = "<f"


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    memory_id: str
    session_id: str | None
    memory_class: str
    memory_key: str
    content_text: str
    confidence: str
    sensitivity: str
    status: str
    metadata: dict[str, Any]
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class MemoryEmbedding:
    source_id: str
    source_type: str
    embedding_model_key: str
    dimensions: int
    embedding: list[float]
    content_text: str
    created_at: str


class MemoryRepository:
    """Canonical local memory records and their real provider embeddings."""

    def __init__(self, database: RuntimeDatabase) -> None:
        self._database = database

    def store_memory(
        self,
        *,
        session_id: str | None,
        memory_class: str,
        memory_key: str,
        content_text: str,
        confidence: str = "medium",
        sensitivity: str = "normal",
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        normalized_class = memory_class.strip().lower()
        normalized_key = memory_key.strip().lower()
        content = content_text.strip()
        if not normalized_class or not normalized_key or not content:
            raise ValueError("memory_class, memory_key, and content_text are required")
        if len(content) > 4_096:
            raise ValueError("content_text must be 4,096 characters or fewer")
        normalized_confidence = confidence.strip().lower() if confidence else "medium"
        if normalized_confidence not in ("low", "medium", "high"):
            raise ValueError("confidence must be low, medium, or high")
        normalized_sensitivity = sensitivity.strip().lower() if sensitivity else "normal"
        if normalized_sensitivity not in ("normal", "sensitive"):
            raise ValueError("sensitivity must be normal or sensitive")
        metadata_json = json.dumps(metadata or {}, separators=(",", ":"))
        memory_id = secrets.token_hex(12)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT memory_id FROM memory_records "
                "WHERE session_id IS ? AND memory_class = ? AND memory_key = ?",
                (session_id, normalized_class, normalized_key),
            ).fetchone()
            if existing:
                memory_id = str(existing["memory_id"])
                connection.execute(
                    "UPDATE memory_records SET content_text = ?, confidence = ?, "
                    "sensitivity = ?, metadata_json = ?, "
                    "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
                    "WHERE memory_id = ?",
                    (content, normalized_confidence, normalized_sensitivity, metadata_json, memory_id),
                )
            else:
                connection.execute(
                    "INSERT INTO memory_records("
                    "memory_id, session_id, memory_class, memory_key, content_text, "
                    "confidence, sensitivity, status, metadata_json, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, "
                    "strftime('%Y-%m-%dT%H:%M:%fZ', 'now'), strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))",
                    (
                        memory_id,
                        session_id,
                        normalized_class,
                        normalized_key,
                        content,
                        normalized_confidence,
                        normalized_sensitivity,
                        metadata_json,
                    ),
                )
            connection.commit()
        record = self.memory(memory_id)
        assert record is not None
        return record

    def memory(self, memory_id: str) -> MemoryRecord | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT memory_id, session_id, memory_class, memory_key, content_text, "
                "confidence, sensitivity, status, metadata_json, created_at, updated_at "
                "FROM memory_records WHERE memory_id = ?",
                (memory_id,),
            ).fetchone()
        return _record(row) if row else None

    def list_memories(self, *, session_id: str | None = None) -> tuple[MemoryRecord, ...]:
        with self._database.connect() as connection:
            if session_id is None:
                rows = connection.execute(
                    "SELECT memory_id, session_id, memory_class, memory_key, content_text, "
                    "confidence, sensitivity, status, metadata_json, created_at, updated_at "
                    "FROM memory_records WHERE status = 'active' "
                    "ORDER BY created_at DESC"
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT memory_id, session_id, memory_class, memory_key, content_text, "
                    "confidence, sensitivity, status, metadata_json, created_at, updated_at "
                    "FROM memory_records WHERE status = 'active' AND session_id = ? "
                    "ORDER BY created_at DESC",
                    (session_id,),
                ).fetchall()
        return tuple(_record(row) for row in rows)

    def store_embedding(
        self,
        *,
        source_id: str,
        source_type: str,
        embedding_model_key: str,
        dimensions: int,
        embedding: list[float],
        content_text: str,
    ) -> None:
        if len(embedding) != dimensions:
            raise ValueError("embedding length must match dimensions")
        blob = struct.pack(_pack_format(dimensions), *embedding)
        with self._database.connect() as connection:
            connection.execute(
                "INSERT INTO memory_embeddings("
                "source_id, source_type, embedding_model_key, dimensions, "
                "embedding, content_text, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) "
                "ON CONFLICT(source_id, source_type) DO UPDATE SET "
                "embedding_model_key=excluded.embedding_model_key, "
                "dimensions=excluded.dimensions, embedding=excluded.embedding, "
                "content_text=excluded.content_text, created_at=excluded.created_at",
                (
                    source_id,
                    source_type,
                    embedding_model_key,
                    int(dimensions),
                    blob,
                    content_text,
                ),
            )
            connection.commit()

    def embeddings_for(self, *, source_type: str, model_key: str | None = None) -> tuple[MemoryEmbedding, ...]:
        with self._database.connect() as connection:
            if source_type == "memory":
                if model_key is None:
                    rows = connection.execute(
                        "SELECT e.source_id, e.source_type, e.embedding_model_key, e.dimensions, "
                        "e.embedding, e.content_text, e.created_at "
                        "FROM memory_embeddings e "
                        "JOIN memory_records m ON m.memory_id = e.source_id "
                        "WHERE e.source_type = ? AND m.status = 'active'",
                        (source_type,),
                    ).fetchall()
                else:
                    rows = connection.execute(
                        "SELECT e.source_id, e.source_type, e.embedding_model_key, e.dimensions, "
                        "e.embedding, e.content_text, e.created_at "
                        "FROM memory_embeddings e "
                        "JOIN memory_records m ON m.memory_id = e.source_id "
                        "WHERE e.source_type = ? AND e.embedding_model_key = ? AND m.status = 'active'",
                        (source_type, model_key),
                    ).fetchall()
            else:
                if model_key is None:
                    rows = connection.execute(
                        "SELECT source_id, source_type, embedding_model_key, dimensions, "
                        "embedding, content_text, created_at "
                        "FROM memory_embeddings WHERE source_type = ?",
                        (source_type,),
                    ).fetchall()
                else:
                    rows = connection.execute(
                        "SELECT source_id, source_type, embedding_model_key, dimensions, "
                        "embedding, content_text, created_at "
                        "FROM memory_embeddings WHERE source_type = ? AND embedding_model_key = ?",
                        (source_type, model_key),
                    ).fetchall()
        return tuple(_embedding(row) for row in rows)

    def embedding(self, source_id: str, *, source_type: str) -> MemoryEmbedding | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT source_id, source_type, embedding_model_key, dimensions, "
                "embedding, content_text, created_at "
                "FROM memory_embeddings WHERE source_id = ? AND source_type = ?",
                (source_id, source_type),
            ).fetchone()
        return _embedding(row) if row else None

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory and its embedding."""
        with self._database.connect() as connection:
            existing = connection.execute(
                "SELECT 1 FROM memory_records WHERE memory_id = ?", (memory_id,)
            ).fetchone()
            if existing is None:
                return False
            connection.execute("DELETE FROM memory_embeddings WHERE source_id = ?", (memory_id,))
            connection.execute("DELETE FROM memory_records WHERE memory_id = ?", (memory_id,))
            connection.commit()
        return True

    def delete_session_memories(self, session_id: str) -> int:
        """Delete all memories and embeddings for a session. Returns count deleted."""
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT memory_id FROM memory_records WHERE session_id = ?", (session_id,)
            ).fetchall()
            memory_ids = tuple(str(row["memory_id"]) for row in rows)
            if memory_ids:
                placeholders = ",".join("?" for _ in memory_ids)
                connection.execute(
                    f"DELETE FROM memory_embeddings WHERE source_id IN ({placeholders})",
                    memory_ids,
                )
                connection.execute(
                    f"DELETE FROM memory_records WHERE memory_id IN ({placeholders})",
                    memory_ids,
                )
                connection.commit()
        return len(memory_ids)

    def delete_session_summary_embedding(self, session_id: str) -> None:
        """Delete the summary embedding for a session."""
        with self._database.connect() as connection:
            connection.execute(
                "DELETE FROM memory_embeddings WHERE source_id = ? AND source_type = 'summary'",
                (session_id,),
            )
            connection.commit()


def _pack_format(dimensions: int) -> str:
    return "<" + "f" * int(dimensions)


def _record(row: object) -> MemoryRecord:
    metadata_raw = row["metadata_json"]
    metadata: dict[str, Any] = {}
    if metadata_raw:
        try:
            decoded = json.loads(str(metadata_raw))
            if isinstance(decoded, dict):
                metadata = decoded
        except json.JSONDecodeError:
            metadata = {}
    return MemoryRecord(
        memory_id=str(row["memory_id"]),
        session_id=str(row["session_id"]) if row["session_id"] else None,
        memory_class=str(row["memory_class"]),
        memory_key=str(row["memory_key"]),
        content_text=str(row["content_text"]),
        confidence=str(row["confidence"]),
        sensitivity=str(row["sensitivity"]),
        status=str(row["status"]),
        metadata=metadata,
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _embedding(row: object) -> MemoryEmbedding:
    dimensions = int(row["dimensions"])
    blob = row["embedding"]
    floats = struct.unpack(_pack_format(dimensions), bytes(blob)) if blob else ()
    return MemoryEmbedding(
        source_id=str(row["source_id"]),
        source_type=str(row["source_type"]),
        embedding_model_key=str(row["embedding_model_key"]),
        dimensions=dimensions,
        embedding=list(floats),
        content_text=str(row["content_text"]),
        created_at=str(row["created_at"]),
    )
