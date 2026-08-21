from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import json
import re
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
    subject_id: str = "primary"
    domain: str = "personal"
    memory_type: str = "fact"
    current_version: int = 1
    valid_from: str | None = None
    valid_to: str | None = None
    last_confirmed_at: str | None = None


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
                "SELECT * FROM memory_records WHERE memory_id = ?",
                (memory_id,),
            ).fetchone()
        return _record(row) if row else None

    def list_memories(self, *, session_id: str | None = None) -> tuple[MemoryRecord, ...]:
        with self._database.connect() as connection:
            if session_id is None:
                rows = connection.execute(
                    "SELECT * FROM memory_records WHERE status = 'active' "
                    "ORDER BY created_at DESC"
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM memory_records WHERE status = 'active' AND session_id = ? "
                    "ORDER BY created_at DESC",
                    (session_id,),
                ).fetchall()
        return tuple(_record(row) for row in rows)

    def reconcile_memory(
        self,
        *,
        session_id: str,
        subject_id: str,
        domain: str,
        memory_type: str,
        memory_key: str,
        content_text: str,
        confidence: str,
        sensitivity: str,
        intent: str,
        reviewer_model: str,
        reviewer_contract_version: int,
        evidence: tuple[tuple[int | None, str, str, str], ...],
        valid_from: str | None = None,
        valid_to: str | None = None,
    ) -> MemoryRecord:
        """Reconcile one validated candidate into a global canonical record."""
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT * FROM memory_records WHERE subject_id = ? AND domain = ? "
                "AND memory_type = ? AND memory_key = ? AND status IN ('active','conflicted') "
                "ORDER BY updated_at DESC, created_at DESC",
                (subject_id, domain, memory_type, memory_key),
            ).fetchall()
            current = rows[0] if rows else None
            now = "strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"
            if current is None:
                memory_id = secrets.token_hex(12)
                version = 1
                status = "conflicted" if intent == "conflict" else "active"
                connection.execute(
                    "INSERT INTO memory_records(memory_id, session_id, memory_class, memory_key, "
                    "content_text, confidence, sensitivity, status, metadata_json, created_at, "
                    "updated_at, subject_id, domain, memory_type, current_version, valid_from, "
                    "valid_to, last_confirmed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '{}', "
                    f"{now}, {now}, ?, ?, ?, ?, ?, ?, {now})",
                    (memory_id, session_id, memory_type, memory_key, content_text, confidence,
                     sensitivity, status, subject_id, domain, memory_type, version,
                     valid_from, valid_to),
                )
            else:
                memory_id = str(current["memory_id"])
                previous_content = str(current["content_text"])
                version = int(current["current_version"] or 1)
                if previous_content == content_text and intent not in ("correct", "conflict"):
                    connection.execute(
                        f"UPDATE memory_records SET last_confirmed_at={now}, updated_at={now}, "
                        "confidence=? WHERE memory_id=?",
                        (confidence, memory_id),
                    )
                else:
                    version += 1
                    status = "active" if intent == "correct" else "conflicted"
                    connection.execute(
                        f"UPDATE memory_records SET session_id=?, content_text=?, confidence=?, "
                        "sensitivity=?, status=?, current_version=?, valid_from=?, valid_to=?, "
                        f"last_confirmed_at={now}, updated_at={now} WHERE memory_id=?",
                        (session_id, content_text, confidence, sensitivity, status, version,
                         valid_from, valid_to, memory_id),
                    )
            for duplicate in rows[1:]:
                duplicate_id = str(duplicate["memory_id"])
                connection.execute(
                    f"UPDATE memory_records SET status='superseded', valid_to=COALESCE(valid_to, {now}), "
                    f"updated_at={now} WHERE memory_id=?",
                    (duplicate_id,),
                )
                connection.execute(
                    "DELETE FROM memory_embeddings WHERE source_id=? AND source_type='memory'",
                    (duplicate_id,),
                )
            connection.execute(
                "INSERT OR IGNORE INTO memory_record_versions(memory_id, version_number, content_text, "
                "confidence, sensitivity, status, valid_from, valid_to, reviewer_model, "
                "reviewer_contract_version, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
                f"{now})",
                (memory_id, version, content_text, confidence, sensitivity,
                 (("conflicted" if intent == "conflict" else "active") if current is None
                  else ("active" if intent == "correct" else "conflicted")),
                 valid_from, valid_to,
                 reviewer_model, reviewer_contract_version),
            )
            for entry_index, source_type, source_authority, excerpt in evidence:
                connection.execute(
                    "INSERT OR IGNORE INTO memory_evidence(evidence_id, memory_id, version_number, "
                    "session_id, entry_index, source_type, source_authority, supporting_excerpt, "
                    f"created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, {now})",
                    (secrets.token_hex(12), memory_id, version, session_id, entry_index,
                     source_type, source_authority, excerpt[:1024]),
                )
            connection.commit()
        record = self.domain_memory(memory_id)
        assert record is not None
        return record

    def domain_memory(self, memory_id: str) -> MemoryRecord | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM memory_records WHERE memory_id=?", (memory_id,)
            ).fetchone()
        return _record(row) if row else None

    def profile_memories(self, *, limit: int = 8) -> tuple[MemoryRecord, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM memory_records WHERE status='active' AND confidence IN ('medium','high') "
                "AND (sensitivity='normal') AND domain IN "
                "('identity','personal','relationship','environment','project','device','platform') "
                "ORDER BY CASE domain WHEN 'identity' THEN 0 WHEN 'personal' THEN 1 "
                "WHEN 'relationship' THEN 2 WHEN 'environment' THEN 3 "
                "WHEN 'platform' THEN 4 WHEN 'project' THEN 5 ELSE 6 END, "
                "last_confirmed_at DESC, updated_at DESC LIMIT ?",
                (max(1, min(int(limit), 32)),),
            ).fetchall()
        return tuple(_record(row) for row in rows)

    def lexical_memories(self, query: str, *, limit: int = 25) -> tuple[MemoryRecord, ...]:
        stop_words = {
            "and", "are", "for", "from", "has", "have", "how", "the", "this",
            "that", "was", "what", "when", "where", "which", "who", "with", "your",
        }
        terms = [
            term for term in re.findall(r"[a-z0-9]+", query.lower())
            if len(term) >= 3 and term not in stop_words
        ][:8]
        if not terms:
            return ()
        clauses = " OR ".join("LOWER(content_text) LIKE ?" for _ in terms)
        with self._database.connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM memory_records WHERE status='active' AND ({clauses}) "
                "ORDER BY last_confirmed_at DESC, updated_at DESC LIMIT ?",
                tuple(f"%{term}%" for term in terms) + (max(1, min(int(limit), 50)),),
            ).fetchall()
        return tuple(_record(row) for row in rows)

    def ingestion_completed(self, session_id: str, contract_version: int,
                            transcript_fingerprint: str) -> bool:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT state, transcript_fingerprint FROM memory_ingestions "
                "WHERE session_id=? AND reviewer_contract_version=?",
                (session_id, contract_version),
            ).fetchone()
        return bool(row and row["state"] == "completed" and
                    row["transcript_fingerprint"] == transcript_fingerprint)

    def start_ingestion(self, session_id: str, contract_version: int,
                        transcript_fingerprint: str, reviewer_model: str) -> None:
        with self._database.connect() as connection:
            connection.execute(
                "INSERT INTO memory_ingestions(session_id, reviewer_contract_version, "
                "transcript_fingerprint, state, reviewer_model, created_at) VALUES (?, ?, ?, "
                "'running', ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) ON CONFLICT(session_id, "
                "reviewer_contract_version) DO UPDATE SET transcript_fingerprint=excluded.transcript_fingerprint, "
                "state='running', reviewer_model=excluded.reviewer_model, error_code=NULL, completed_at=NULL",
                (session_id, contract_version, transcript_fingerprint, reviewer_model),
            )
            connection.commit()

    def complete_ingestion(self, session_id: str, contract_version: int,
                           candidate_count: int, stored_count: int) -> None:
        with self._database.connect() as connection:
            connection.execute(
                "UPDATE memory_ingestions SET state='completed', candidate_count=?, stored_count=?, "
                "completed_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE session_id=? "
                "AND reviewer_contract_version=?",
                (candidate_count, stored_count, session_id, contract_version),
            )
            connection.commit()

    def evidence_for(self, memory_id: str, *, limit: int = 8) -> tuple[dict[str, object], ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT session_id, entry_index, source_type, source_authority, "
                "supporting_excerpt, created_at FROM memory_evidence WHERE memory_id=? "
                "ORDER BY created_at DESC LIMIT ?",
                (memory_id, max(1, min(int(limit), 25))),
            ).fetchall()
        return tuple({
            "sessionId": str(row["session_id"]),
            "entryIndex": int(row["entry_index"]) if row["entry_index"] is not None else None,
            "sourceType": str(row["source_type"]),
            "sourceAuthority": str(row["source_authority"]),
            "excerpt": str(row["supporting_excerpt"]),
            "createdAt": str(row["created_at"]),
        } for row in rows)

    def prepare_action(self, *, action_kind: str, memory_id: str,
                       proposed_content: str | None, voice_session_id: str | None,
                       prepared_utterance_id: int | None) -> str:
        if action_kind not in ("correct", "forget"):
            raise ValueError("unsupported memory action")
        if self.domain_memory(memory_id) is None:
            raise ValueError("memory does not exist")
        action_id = secrets.token_hex(12)
        with self._database.connect() as connection:
            connection.execute(
                "INSERT INTO memory_pending_actions(action_id, action_kind, memory_id, "
                "proposed_content, voice_session_id, prepared_utterance_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))",
                (action_id, action_kind, memory_id, proposed_content, voice_session_id,
                 prepared_utterance_id),
            )
            connection.commit()
        return action_id

    def consume_action(self, *, action_id: str, voice_session_id: str | None,
                       confirmation_utterance_id: int | None) -> dict[str, object] | None:
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM memory_pending_actions WHERE action_id=? AND state='pending'",
                (action_id,),
            ).fetchone()
            if row is None:
                connection.rollback()
                return None
            prepared_id = row["prepared_utterance_id"]
            if row["voice_session_id"] and row["voice_session_id"] != voice_session_id:
                connection.rollback()
                return None
            if prepared_id is not None and (
                confirmation_utterance_id is None or int(confirmation_utterance_id) <= int(prepared_id)
            ):
                connection.rollback()
                return None
            connection.execute(
                "UPDATE memory_pending_actions SET state='consumed' WHERE action_id=?",
                (action_id,),
            )
            connection.commit()
        return {
            "actionKind": str(row["action_kind"]),
            "memoryId": str(row["memory_id"]),
            "proposedContent": (str(row["proposed_content"])
                                if row["proposed_content"] is not None else None),
        }

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
        """Remove one session's evidence without deleting globally supported memory."""
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT DISTINCT memory_id FROM memory_evidence WHERE session_id=? "
                "UNION SELECT memory_id FROM memory_records WHERE session_id=?",
                (session_id, session_id),
            ).fetchall()
            affected = tuple(str(row["memory_id"]) for row in rows)
            connection.execute("DELETE FROM memory_evidence WHERE session_id=?", (session_id,))
            deleted: list[str] = []
            for memory_id in affected:
                evidence = connection.execute(
                    "SELECT 1 FROM memory_evidence WHERE memory_id=? LIMIT 1", (memory_id,)
                ).fetchone()
                record = connection.execute(
                    "SELECT session_id FROM memory_records WHERE memory_id=?", (memory_id,)
                ).fetchone()
                if evidence is None and record is not None and record["session_id"] == session_id:
                    connection.execute("DELETE FROM memory_embeddings WHERE source_id=?", (memory_id,))
                    connection.execute("DELETE FROM memory_records WHERE memory_id=?", (memory_id,))
                    deleted.append(memory_id)
            connection.execute("DELETE FROM memory_ingestions WHERE session_id=?", (session_id,))
            connection.commit()
        return len(deleted)

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
    keys = set(row.keys())
    memory_class = str(row["memory_class"])
    compatibility_domain = {
        "preference": "personal", "relationship": "relationship", "environment": "environment"
    }.get(memory_class, "personal")
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
        subject_id=str(row["subject_id"]) if "subject_id" in keys else "primary",
        domain=str(row["domain"]) if "domain" in keys else compatibility_domain,
        memory_type=str(row["memory_type"]) if "memory_type" in keys else memory_class,
        current_version=int(row["current_version"]) if "current_version" in keys else 1,
        valid_from=str(row["valid_from"]) if "valid_from" in keys and row["valid_from"] else None,
        valid_to=str(row["valid_to"]) if "valid_to" in keys and row["valid_to"] else None,
        last_confirmed_at=(str(row["last_confirmed_at"])
                           if "last_confirmed_at" in keys and row["last_confirmed_at"] else None),
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
