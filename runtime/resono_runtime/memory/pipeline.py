from __future__ import annotations

from dataclasses import dataclass

from ..agents.memory_reviewer import MemoryReviewRunner
from ..api.events import RuntimeEventStream
from ..providers.openai import EmbeddingUnavailable
from ..providers.openai.subscription import OpenAISubscription
from ..security.credentials import ProviderCredentials
from ..storage.memory import MemoryRepository
from ..storage.provider_settings import ProviderSettingsRepository
from ..storage.sessions import SessionTranscriptRepository
from .embedding_access import default_embedding_factory, embedding_api_key


@dataclass(frozen=True, slots=True)
class FinalizeResult:
    session_id: str
    summary: str
    memory_count: int
    embedded_count: int
    model: str
    embeddings_available: bool


class MemoryPipeline:
    """Runs the post-session review/memory flow and persists provenance-linked memory.

    Transcript -> review agent -> summary + memories -> real provider embeddings.
    Embeddings run on the same credential the review agent uses (the configured
    access path decides: subscription token or Platform key); without a usable
    credential, memories are still stored and inspectable but semantic search
    degrades to "no semantic match" rather than faking a vector result.
    """

    def __init__(
        self,
        *,
        sessions: SessionTranscriptRepository,
        memories: MemoryRepository,
        reviewer: MemoryReviewRunner,
        credentials: ProviderCredentials,
        safety_source: str,
        events: RuntimeEventStream,
        settings: ProviderSettingsRepository | None = None,
        subscription: OpenAISubscription | None = None,
        embedding_factory=None,
    ) -> None:
        self._sessions = sessions
        self._memories = memories
        self._reviewer = reviewer
        self._credentials = credentials
        self._safety_source = safety_source
        self._events = events
        self._settings = settings
        self._subscription = subscription
        self._embedding_factory = embedding_factory or default_embedding_factory

    def finalize(self, session_id: str) -> FinalizeResult:
        transcript = self._sessions.transcript_text(session_id)
        if not transcript.strip():
            raise ValueError("Session has no transcript to review.")
        review = self._reviewer.review(transcript)
        self._sessions.store_summary(
            session_id=session_id,
            summary_status="completed",
            summarizer_model_key=review.model or None,
            transcript_text=transcript,
            summary_text=review.summary,
            extracted_memory_count=len(review.memories),
        )
        stored_memory_ids: list[str] = []
        for candidate in review.memories:
            record = self._memories.store_memory(
                session_id=session_id,
                memory_class=candidate.memory_class,
                memory_key=candidate.memory_key,
                content_text=candidate.content_text,
                confidence=candidate.confidence,
                sensitivity=candidate.sensitivity,
                metadata={"summary_excerpt": review.summary[:256]},
            )
            stored_memory_ids.append(record.memory_id)

        embedded = 0
        api_key = embedding_api_key(
            credentials=self._credentials,
            settings=self._settings,
            subscription=self._subscription,
        )
        embeddings_available = api_key is not None
        if embeddings_available:
            embedder = self._embedding_factory(api_key, self._safety_source)
            
            # Embed the session summary first (donor parity)
            if review.summary.strip():
                try:
                    summary_vector = embedder.embed(review.summary)
                    self._memories.store_embedding(
                        source_id=session_id,
                        source_type="summary",
                        embedding_model_key=embedder.model_key,
                        dimensions=embedder.dimensions,
                        embedding=summary_vector,
                        content_text=review.summary,
                    )
                    embedded += 1
                except EmbeddingUnavailable:
                    pass
            
            # Then embed each memory
            for memory_id in stored_memory_ids:
                memory = self._memories.memory(memory_id)
                if memory is None:
                    continue
                try:
                    vector = embedder.embed(memory.content_text)
                except EmbeddingUnavailable:
                    continue
                self._memories.store_embedding(
                    source_id=memory_id,
                    source_type="memory",
                    embedding_model_key=embedder.model_key,
                    dimensions=embedder.dimensions,
                    embedding=vector,
                    content_text=memory.content_text,
                )
                embedded += 1
        self._events.publish(
            "memory.finalized",
            {
                "sessionId": session_id,
                "memoryCount": len(stored_memory_ids),
                "embeddedCount": embedded,
            },
        )
        return FinalizeResult(
            session_id=session_id,
            summary=review.summary,
            memory_count=len(stored_memory_ids),
            embedded_count=embedded,
            model=review.model or "",
            embeddings_available=embeddings_available,
        )
