from __future__ import annotations

from dataclasses import dataclass
import hashlib

from ..agents.memory_reviewer import MemoryReviewRunner
from ..api.events import RuntimeEventStream
from ..providers.openai import EmbeddingUnavailable
from ..providers.openai.subscription import OpenAISubscription
from ..security.credentials import ProviderCredentials
from ..storage.memory import MemoryRepository
from ..storage.provider_settings import ProviderSettingsRepository
from ..storage.sessions import SessionTranscriptRepository
from .embedding_access import default_embedding_factory, embedding_api_key
from .contracts import REVIEWER_CONTRACT_VERSION


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
        entries = self._sessions.entries(session_id)
        transcript = "\n".join(
            f"[entryIndex={entry.entry_index}] [{entry.event_type}] "
            f"{entry.role}: {entry.text_content}" for entry in entries
        )
        existing_records = self._memories.list_memories()[:64]
        if existing_records:
            transcript += "\n\n[existingCanonicalMemory]\n" + "\n".join(
                f"memoryId={memory.memory_id} domain={memory.domain} "
                f"memoryType={memory.memory_type} key={memory.memory_key} "
                f"content={memory.content_text} status={memory.status}"
                for memory in existing_records
            )
        if not transcript.strip():
            raise ValueError("Session has no transcript to review.")
        fingerprint = hashlib.sha256(transcript.encode("utf-8")).hexdigest()
        existing_summary = self._sessions.summary(session_id)
        if self._memories.ingestion_completed(
            session_id, REVIEWER_CONTRACT_VERSION, fingerprint
        ) and existing_summary is not None:
            return FinalizeResult(
                session_id=session_id,
                summary=existing_summary.summary_text or "",
                memory_count=existing_summary.extracted_memory_count,
                embedded_count=0,
                model=existing_summary.summarizer_model_key or "",
                embeddings_available=embedding_api_key(
                    credentials=self._credentials,
                    settings=self._settings,
                    subscription=self._subscription,
                ) is not None,
            )
        review = self._reviewer.review(transcript)
        self._memories.start_ingestion(
            session_id, REVIEWER_CONTRACT_VERSION, fingerprint, review.model
        )
        self._sessions.store_summary(
            session_id=session_id,
            summary_status="completed",
            summarizer_model_key=review.model or None,
            transcript_text=transcript,
            summary_text=review.summary,
            extracted_memory_count=len(review.memories),
        )
        stored_memory_ids: list[str] = []
        entries_by_index = {entry.entry_index: entry for entry in entries}
        legacy_user_entries = tuple(entry for entry in entries if entry.role == "user")
        for candidate in review.memories:
            cited_entries = tuple(
                entries_by_index[index] for index in candidate.source_entry_indexes
                if index in entries_by_index
            )
            if not cited_entries and review.contract_version == 1:
                # Contract v1 did not expose entry indexes. Preserve imports and
                # older on-device reviews by linking them to the user evidence
                # available in that reviewed session. Contract v2 never falls
                # back: its explicit citations remain mandatory.
                cited_entries = legacy_user_entries
            if not cited_entries:
                continue
            evidence = tuple(
                (
                    entry.entry_index,
                    "tool_result" if entry.role == "tool" else "user_statement"
                    if entry.role == "user" else "assistant_statement",
                    candidate.source_authority,
                    entry.text_content,
                )
                for entry in cited_entries
            )
            record = self._memories.reconcile_memory(
                session_id=session_id,
                subject_id="primary",
                domain=candidate.domain,
                memory_type=candidate.memory_type,
                memory_key=candidate.memory_key,
                content_text=candidate.content_text,
                confidence=candidate.confidence,
                sensitivity=candidate.sensitivity,
                intent=candidate.reconciliation_intent,
                reviewer_model=review.model,
                reviewer_contract_version=REVIEWER_CONTRACT_VERSION,
                evidence=evidence,
                valid_from=candidate.valid_from,
                valid_to=candidate.valid_to,
            )
            if record.status == "active":
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
        self._memories.complete_ingestion(
            session_id, REVIEWER_CONTRACT_VERSION, len(review.memories), len(stored_memory_ids)
        )
        return FinalizeResult(
            session_id=session_id,
            summary=review.summary,
            memory_count=len(stored_memory_ids),
            embedded_count=embedded,
            model=review.model or "",
            embeddings_available=embeddings_available,
        )
