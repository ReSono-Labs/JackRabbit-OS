from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..providers.openai import EmbeddingUnavailable
from ..providers.openai.subscription import OpenAISubscription
from ..security.credentials import ProviderCredentials
from ..storage.memory import MemoryRecord, MemoryRepository
from ..storage.provider_settings import ProviderSettingsRepository
from ..storage.sessions import SessionSummary, SessionTranscriptRepository, TranscriptEntry
from .embedding_access import default_embedding_factory, embedding_api_key
from .pipeline import FinalizeResult, MemoryPipeline
from .retrieval import MemoryRetriever, RetrievalMatch


@dataclass(frozen=True, slots=True)
class SearchResult:
    matches: tuple[dict[str, Any], ...]
    embeddings_available: bool


class MemoryService:
    """Single owner for the memory surface exposed to the runtime API."""

    def __init__(
        self,
        *,
        sessions: SessionTranscriptRepository,
        memories: MemoryRepository,
        pipeline: MemoryPipeline,
        credentials: ProviderCredentials,
        safety_source: str,
        settings: ProviderSettingsRepository | None = None,
        subscription: OpenAISubscription | None = None,
        embedding_factory=None,
    ) -> None:
        self._sessions = sessions
        self._memories = memories
        self._pipeline = pipeline
        self._credentials = credentials
        self._safety_source = safety_source
        self._settings = settings
        self._subscription = subscription
        self._embedding_factory = embedding_factory or default_embedding_factory

    def finalize(self, session_id: str) -> FinalizeResult:
        return self._pipeline.finalize(session_id)

    def list_sessions(self) -> tuple[str, ...]:
        return self._sessions.list_sessions()

    def session_entries(self, session_id: str) -> tuple[TranscriptEntry, ...]:
        return self._sessions.entries(session_id)

    def session_summary(self, session_id: str) -> SessionSummary | None:
        return self._sessions.summary(session_id)

    def list_memories(self, *, session_id: str | None = None) -> tuple[MemoryRecord, ...]:
        return self._memories.list_memories(session_id=session_id)

    def memory(self, memory_id: str) -> MemoryRecord | None:
        return self._memories.memory(memory_id)

    def delete_memory(self, memory_id: str) -> bool:
        return self._memories.delete_memory(memory_id)

    def delete_session(self, session_id: str) -> int:
        memory_count = self._memories.delete_session_memories(session_id)
        self._memories.delete_session_summary_embedding(session_id)
        self._sessions.delete_session(session_id)
        return memory_count

    def search(self, query: str, *, limit: int = 8) -> SearchResult:
        api_key = embedding_api_key(
            credentials=self._credentials,
            settings=self._settings,
            subscription=self._subscription,
        )
        embedder = None
        if api_key:
            try:
                embedder = self._embedding_factory(api_key, self._safety_source)
            except EmbeddingUnavailable:
                embedder = None
        retriever = MemoryRetriever(memories=self._memories, embedder=embedder)
        matches = retriever.retrieve(query, limit=limit)
        return SearchResult(
            matches=tuple(_match_payload(match) for match in matches),
            embeddings_available=embedder is not None,
        )

    def reindex(self) -> int:
        """Re-embed every active memory with the current embedding model."""
        api_key = embedding_api_key(
            credentials=self._credentials,
            settings=self._settings,
            subscription=self._subscription,
        )
        if api_key is None:
            return 0
        embedder = self._embedding_factory(api_key, self._safety_source)
        count = 0
        for memory in self._memories.list_memories():
            try:
                vector = embedder.embed(memory.content_text)
            except EmbeddingUnavailable:
                continue
            self._memories.store_embedding(
                source_id=memory.memory_id,
                source_type="memory",
                embedding_model_key=embedder.model_key,
                dimensions=embedder.dimensions,
                embedding=vector,
                content_text=memory.content_text,
            )
            count += 1
        return count


def _match_payload(match: RetrievalMatch) -> dict[str, Any]:
    memory = match.memory
    return {
        "memoryId": memory.memory_id,
        "sessionId": memory.session_id,
        "memoryClass": memory.memory_class,
        "domain": memory.domain,
        "memoryType": memory.memory_type,
        "memoryKey": memory.memory_key,
        "content": memory.content_text,
        "confidence": memory.confidence,
        "sensitivity": memory.sensitivity,
        "score": match.score,
        "matchMethods": list(match.match_methods),
        "updatedAt": memory.updated_at,
    }
