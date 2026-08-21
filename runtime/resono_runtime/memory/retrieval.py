from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Protocol

from ..storage.memory import MemoryEmbedding, MemoryRecord, MemoryRepository


EMBEDDING_SIMILARITY_FLOOR = 0.20
DEFAULT_RETRIEVAL_LIMIT = 8
MAX_RETRIEVAL_LIMIT = 25


class QueryEmbedder(Protocol):
    def embed(self, text: str) -> list[float]:
        ...


@dataclass(frozen=True, slots=True)
class RetrievalMatch:
    memory: MemoryRecord
    score: float
    match_methods: tuple[str, ...] = ()


class MemoryRetriever:
    """Semantic retrieval over the canonical local memory store.

    Keeps the donor's proven retrieval logic: embed the query with the configured
    provider, load candidate embeddings from local storage, and rank by cosine
    similarity in Python. No hash, keyword, or random vector is substituted for
    semantic search. Unembedded memories are never returned as semantic matches.
    """

    def __init__(
        self,
        *,
        memories: MemoryRepository,
        embedder: QueryEmbedder | None,
        source_type: str = "memory",
        similarity_floor: float = EMBEDDING_SIMILARITY_FLOOR,
    ) -> None:
        self._memories = memories
        self._embedder = embedder
        self._source_type = source_type
        self._floor = similarity_floor

    def retrieve(self, query: str, *, limit: int = DEFAULT_RETRIEVAL_LIMIT) -> list[RetrievalMatch]:
        normalized_limit = max(1, min(int(limit), MAX_RETRIEVAL_LIMIT))
        scores: dict[str, float] = {}
        methods: dict[str, set[str]] = {}
        records: dict[str, MemoryRecord] = {}
        for position, memory in enumerate(self._memories.lexical_memories(query, limit=25)):
            records[memory.memory_id] = memory
            scores[memory.memory_id] = max(scores.get(memory.memory_id, 0.0), 0.55 - position * 0.01)
            methods.setdefault(memory.memory_id, set()).add("lexical")
            if query.strip().lower() in (memory.memory_key.lower(), memory.content_text.lower()):
                scores[memory.memory_id] = max(scores[memory.memory_id], 1.0)
                methods[memory.memory_id].add("exact")
        if self._embedder is not None:
            query_embedding = self._embedder.embed(query)
            candidates = self._memories.embeddings_for(
                source_type=self._source_type,
                model_key=getattr(self._embedder, "model_key", None),
            )
            for candidate in candidates:
                if len(candidate.embedding) != len(query_embedding):
                    continue
                if candidate.embedding_model_key != getattr(
                    self._embedder, "model_key", candidate.embedding_model_key
                ):
                    continue
                score = cosine_similarity(query_embedding, candidate.embedding)
                if score < self._floor:
                    continue
                memory = self._memories.domain_memory(candidate.source_id)
                if memory is None or memory.status != "active":
                    continue
                records[memory.memory_id] = memory
                scores[memory.memory_id] = max(scores.get(memory.memory_id, 0.0), score)
                methods.setdefault(memory.memory_id, set()).add("semantic")
        ranked_ids = sorted(scores, key=lambda item: scores[item], reverse=True)[:normalized_limit]
        return [
            RetrievalMatch(
                memory=records[memory_id],
                score=round(scores[memory_id], 8),
                match_methods=tuple(sorted(methods[memory_id])),
            )
            for memory_id in ranked_ids
        ]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Pure-Python cosine similarity, matching the donor retrieval logic."""
    if not left or not right or len(left) != len(right):
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)
