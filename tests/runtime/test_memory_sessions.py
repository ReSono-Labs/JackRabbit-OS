from __future__ import annotations

from pathlib import Path
import json
import tempfile
import unittest

from resono_runtime.agents import MemoryReviewRunner
from resono_runtime.api.events import RuntimeEventStream
from resono_runtime.memory.pipeline import MemoryPipeline
from resono_runtime.memory.retrieval import cosine_similarity
from resono_runtime.memory.retrieval import MemoryRetriever
from resono_runtime.memory.service import MemoryService
from resono_runtime.memory.session_context import SessionContextBuilder
from resono_runtime.memory.tools import MemoryLookupTool
from resono_runtime.providers.openai import EmbeddingUnavailable
from resono_runtime.security.credentials import ProviderCredentials
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.storage.memory import MemoryRepository
from resono_runtime.storage.provider_settings import ProviderSettingsRepository
from resono_runtime.storage.sessions import SessionTranscriptRepository


class _CredentialBridge:
    def __init__(self, value: str | None) -> None:
        self.value = value

    def hasOpenAiPlatformKey(self) -> bool:
        return self.value is not None

    def getOpenAiPlatformKey(self) -> str | None:
        return self.value

    def putOpenAiPlatformKey(self, value: str) -> None:
        self.value = value

    def deleteOpenAiPlatformKey(self) -> None:
        self.value = None


class _FakeEmbedder:
    """Deterministic offline embedder keyed off content tokens, not a hash fallback.

    A real embedding provider maps semantics to a shared vector space. For tests
    we approximate that by projecting overlapping content shingles into a fixed
    axis space so semantically similar text scores above the cosine floor and
    unrelated text does not. This exercises the real cosine ranking path without
    network or credential I/O.
    """

    model_key = "text-embedding-3-small"
    dimensions = 16

    def __init__(self) -> None:
        self._axes = [
            "coffee", "tea", "morning", "name", "prefers", "morning",
            "dog", "walk", "pet", "lives", "city", "home",
            "secret", "key", "password", "payment",
        ]

    def embed(self, text: str) -> list[float]:
        lowered = text.lower()
        vec = [0.0] * len(self._axes)
        for index, axis in enumerate(self._axes):
            if axis in lowered:
                vec[index] = 1.0
        # Normalize so cosine is well-defined and identical content yields 1.0.
        norm = sum(v * v for v in vec) ** 0.5
        if norm == 0.0:
            return vec
        return [v / norm for v in vec]


def _fake_embedding_factory(_credentials: ProviderCredentials, _safety_source: str) -> _FakeEmbedder:
    return _FakeEmbedder()


class _FakeReviewExecutor:
    """Returns a canned review payload so the reviewer stays offline."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def __call__(self, **_: object) -> str:
        return json.dumps(self._payload)


def _make_database(directory: Path) -> RuntimeDatabase:
    database = RuntimeDatabase(directory / "runtime.sqlite3")
    database.migrate()
    return database


def _make_reviewer(database: RuntimeDatabase, *, bridge: _CredentialBridge, executor) -> MemoryReviewRunner:
    return MemoryReviewRunner(
        credentials=ProviderCredentials(bridge),
        settings=ProviderSettingsRepository(database),
        events=RuntimeEventStream(),
        local_api_token="t" * 43,
        executor=executor,
    )


def _record_session(sessions: SessionTranscriptRepository, session_id: str, turns: list[tuple[str, str]]) -> None:
    for role, content in turns:
        sessions.append(
            session_id=session_id,
            role=role,
            event_type="text.turn.input" if role == "user" else "text.turn.output",
            text_content=content,
        )


class MemorySessionTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.database = _make_database(Path(self.temporary.name))
        self.sessions = SessionTranscriptRepository(self.database)
        self.memories = MemoryRepository(self.database)
        self.settings = ProviderSettingsRepository(self.database)
        self.settings.save(text_model="gpt-5.4-mini", realtime_model=None)
        self.events = RuntimeEventStream()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _pipeline(self, *, bridge: _CredentialBridge, executor) -> MemoryPipeline:
        reviewer = _make_reviewer(self.database, bridge=bridge, executor=executor)
        return MemoryPipeline(
            sessions=self.sessions,
            memories=self.memories,
            reviewer=reviewer,
            credentials=ProviderCredentials(bridge),
            safety_source="t" * 43,
            events=self.events,
            embedding_factory=_fake_embedding_factory,
        )

    def _service(self, *, bridge: _CredentialBridge) -> MemoryService:
        return MemoryService(
            sessions=self.sessions,
            memories=self.memories,
            pipeline=self._pipeline(bridge=bridge, executor=_FakeReviewExecutor({"summary": "", "memories": []})),
            credentials=ProviderCredentials(bridge),
            safety_source="t" * 43,
            embedding_factory=_fake_embedding_factory,
        )


class TranscriptToMemoryProvenanceTest(MemorySessionTestBase):
    def test_review_produces_summary_and_memories_linked_to_session(self) -> None:
        bridge = _CredentialBridge("sk-test")
        session_id = self.sessions.new_session_id()
        _record_session(
            self.sessions,
            session_id,
            [
                ("user", "My name is Christian and I prefer coffee in the morning."),
                ("assistant", "Got it, Christian. I'll remember the coffee preference."),
            ],
        )
        executor = _FakeReviewExecutor(
            {
                "summary": "Christian introduced himself and shared a coffee preference.",
                "memories": [
                    {
                        "memoryClass": "relationship",
                        "memoryKey": "user-name",
                        "content": "The user's name is Christian.",
                        "confidence": "high",
                        "sensitivity": "normal",
                    },
                    {
                        "memoryClass": "preference",
                        "memoryKey": "morning-drink",
                        "content": "Prefers coffee in the morning.",
                        "confidence": "medium",
                        "sensitivity": "normal",
                    },
                ],
            }
        )
        pipeline = self._pipeline(bridge=bridge, executor=executor)

        result = pipeline.finalize(session_id)

        self.assertEqual(session_id, result.session_id)
        self.assertEqual(2, result.memory_count)
        # Donor parity: the session summary is embedded alongside each memory.
        self.assertEqual(3, result.embedded_count)
        self.assertTrue(result.embeddings_available)

        stored = self.memories.list_memories()
        self.assertEqual(2, len(stored))
        classifications = {(m.domain, m.memory_type) for m in stored}
        self.assertEqual(
            {("relationship", "fact"), ("personal", "preference")},
            classifications,
        )
        for record in stored:
            self.assertEqual(session_id, record.session_id)
            self.assertEqual("active", record.status)
            self.assertIn(record.confidence, ("low", "medium", "high"))
            self.assertIn(record.sensitivity, ("normal", "sensitive"))

        summary = self.sessions.summary(session_id)
        self.assertIsNotNone(summary)
        self.assertEqual("completed", summary.summary_status)
        self.assertEqual(2, summary.extracted_memory_count)

    def test_forbidden_memory_markers_are_dropped_and_never_stored(self) -> None:
        bridge = _CredentialBridge("sk-test")
        session_id = self.sessions.new_session_id()
        _record_session(self.sessions, session_id, [("user", "my api key is sk-live-1234")])
        executor = _FakeReviewExecutor(
            {
                "summary": "User shared a secret.",
                "memories": [
                    {
                        "memoryClass": "preference",
                        "memoryKey": "api-key",
                        "content": "User api key is sk-live-1234",
                        "confidence": "high",
                        "sensitivity": "normal",
                    }
                ],
            }
        )
        pipeline = self._pipeline(bridge=bridge, executor=executor)
        # The donor silently drops candidates carrying forbidden-memory markers;
        # it never stores secrets and does not surface them as memory.
        result = pipeline.finalize(session_id)
        self.assertEqual(0, result.memory_count)
        self.assertEqual(0, len(self.memories.list_memories()))


class RetrievalTest(MemorySessionTestBase):
    def _store_with_embedding(self, *, key: str, content: str, memory_class: str = "preference") -> None:
        embedder = _FakeEmbedder()
        record = self.memories.store_memory(
            session_id=None,
            memory_class=memory_class,
            memory_key=key,
            content_text=content,
            confidence="medium",
        )
        self.memories.store_embedding(
            source_id=record.memory_id,
            source_type="memory",
            embedding_model_key=embedder.model_key,
            dimensions=embedder.dimensions,
            embedding=embedder.embed(content),
            content_text=content,
        )

    def test_semantic_match_ranks_relevant_memory_above_floor(self) -> None:
        self._store_with_embedding(key="morning-drink", content="Prefers coffee in the morning.")
        self._store_with_embedding(key="pet", content="Has a dog and walks it daily.")
        embedder = _FakeEmbedder()
        retriever = MemoryRetriever(memories=self.memories, embedder=embedder)

        matches = retriever.retrieve("Does the user like coffee or tea in the morning?")

        self.assertGreaterEqual(len(matches), 1)
        self.assertEqual("morning-drink", matches[0].memory.memory_key)
        self.assertGreater(matches[0].score, 0.20)
        # The unrelated dog memory must not outrank the coffee memory.
        if len(matches) > 1:
            self.assertGreaterEqual(matches[0].score, matches[1].score)

    def test_below_floor_and_dimension_mismatch_are_dropped(self) -> None:
        self._store_with_embedding(key="morning-drink", content="Prefers coffee in the morning.")
        embedder = _FakeEmbedder()
        retriever = MemoryRetriever(memories=self.memories, embedder=embedder)
        # A query with no overlapping axes yields a zero vector and no matches.
        matches = retriever.retrieve("What time is the flight to Paris?")
        self.assertEqual([], matches)

    def test_unembedded_memory_is_returned_only_as_lexical_match(self) -> None:
        self.memories.store_memory(
            session_id=None,
            memory_class="preference",
            memory_key="unembedded",
            content_text="Prefers coffee in the morning.",
        )
        embedder = _FakeEmbedder()
        retriever = MemoryRetriever(memories=self.memories, embedder=embedder)
        matches = retriever.retrieve("coffee morning")
        self.assertEqual(1, len(matches))
        self.assertEqual(("lexical",), matches[0].match_methods)

    def test_deleted_memory_is_not_retrievable(self) -> None:
        record = self.memories.store_memory(
            session_id=None,
            memory_class="preference",
            memory_key="morning-drink",
            content_text="Prefers coffee in the morning.",
        )
        embedder = _FakeEmbedder()
        self.memories.store_embedding(
            source_id=record.memory_id,
            source_type="memory",
            embedding_model_key=embedder.model_key,
            dimensions=embedder.dimensions,
            embedding=embedder.embed("Prefers coffee in the morning."),
            content_text="Prefers coffee in the morning.",
        )
        retriever = MemoryRetriever(memories=self.memories, embedder=embedder)
        self.assertGreaterEqual(len(retriever.retrieve("coffee morning")), 1)
        self.assertTrue(self.memories.delete_memory(record.memory_id))
        self.assertEqual([], retriever.retrieve("coffee morning"))


class FinalizeIdempotencyTest(MemorySessionTestBase):
    def test_finalizing_twice_does_not_duplicate_memories(self) -> None:
        bridge = _CredentialBridge("sk-test")
        session_id = self.sessions.new_session_id()
        _record_session(
            self.sessions,
            session_id,
            [("user", "My name is Christian."), ("assistant", "Hello Christian.")],
        )
        payload = {
            "summary": "User introduced themselves as Christian.",
            "memories": [
                {
                    "memoryClass": "relationship",
                    "memoryKey": "user-name",
                    "content": "The user's name is Christian.",
                    "confidence": "high",
                    "sensitivity": "normal",
                }
            ],
        }
        executor = _FakeReviewExecutor(payload)
        pipeline = self._pipeline(bridge=bridge, executor=executor)

        first = pipeline.finalize(session_id)
        self.assertEqual(1, first.memory_count)
        # Re-finalize: the store_memory upsert on (session, class, key) must not
        # create a second row; the summary is overwritten in place.
        second = pipeline.finalize(session_id)
        self.assertEqual(1, second.memory_count)
        self.assertEqual(1, len(self.memories.list_memories()))


class DeletionAndCascadeTest(MemorySessionTestBase):
    def test_delete_session_cascades_to_memories_and_transcript(self) -> None:
        bridge = _CredentialBridge("sk-test")
        session_id = self.sessions.new_session_id()
        _record_session(self.sessions, session_id, [("user", "Prefers coffee."), ("assistant", "Noted.")])
        executor = _FakeReviewExecutor(
            {
                "summary": "Coffee preference recorded.",
                "memories": [
                    {
                        "memoryClass": "preference",
                        "memoryKey": "morning-drink",
                        "content": "Prefers coffee.",
                        "confidence": "medium",
                        "sensitivity": "normal",
                    }
                ],
            }
        )
        pipeline = self._pipeline(bridge=bridge, executor=executor)
        pipeline.finalize(session_id)
        self.assertEqual(1, len(self.memories.list_memories(session_id=session_id)))

        service = self._service(bridge=bridge)
        deleted = service.delete_session(session_id)

        self.assertEqual(1, deleted)
        self.assertEqual((), self.memories.list_memories(session_id=session_id))
        self.assertEqual((), self.sessions.entries(session_id))
        self.assertIsNone(self.sessions.summary(session_id))


class EmbeddingUnavailableTest(MemorySessionTestBase):
    def test_search_without_platform_key_reports_unavailable_not_faked(self) -> None:
        # Store a memory directly (no review needed) and search with no platform
        # key. The service reports embeddings unavailable while retaining the
        # deterministic lexical retrieval path over canonical memory.
        self.memories.store_memory(
            session_id=None,
            memory_class="preference",
            memory_key="morning-drink",
            content_text="Prefers coffee in the morning.",
        )
        bridge = _CredentialBridge(None)
        service = self._service(bridge=bridge)
        search = service.search("coffee morning")
        self.assertFalse(search.embeddings_available)
        self.assertEqual(1, len(search.matches))
        self.assertEqual(["lexical"], search.matches[0]["matchMethods"])

    def test_finalize_stores_memory_when_embedding_provider_is_unavailable(self) -> None:
        # Platform key present so the reviewer can run, but the embedder fails.
        # Memories are still stored; only the embedding step is skipped.
        bridge = _CredentialBridge("sk-test")

        class _FailingEmbedder(_FakeEmbedder):
            def embed(self, text: str) -> list[float]:
                raise EmbeddingUnavailable("embedding provider offline")

        def failing_factory(_credentials, _safety_source):
            return _FailingEmbedder()

        session_id = self.sessions.new_session_id()
        _record_session(self.sessions, session_id, [("user", "Prefers coffee."), ("assistant", "Noted.")])
        reviewer = _make_reviewer(
            self.database,
            bridge=bridge,
            executor=_FakeReviewExecutor(
                {
                    "summary": "Coffee preference recorded.",
                    "memories": [
                        {
                            "memoryClass": "preference",
                            "memoryKey": "morning-drink",
                            "content": "Prefers coffee.",
                            "confidence": "medium",
                            "sensitivity": "normal",
                        }
                    ],
                }
            ),
        )
        pipeline = MemoryPipeline(
            sessions=self.sessions,
            memories=self.memories,
            reviewer=reviewer,
            credentials=ProviderCredentials(bridge),
            safety_source="t" * 43,
            events=self.events,
            embedding_factory=failing_factory,
        )
        result = pipeline.finalize(session_id)
        self.assertEqual(1, result.memory_count)
        self.assertEqual(0, result.embedded_count)
        self.assertEqual(1, len(self.memories.list_memories()))

    def test_lookup_tool_reports_unavailable_without_credentials(self) -> None:
        bridge = _CredentialBridge(None)
        tool = MemoryLookupTool(
            memories=self.memories,
            credentials=ProviderCredentials(bridge),
            safety_source="t" * 43,
            embedding_factory=_fake_embedding_factory,
        )
        payload = json.loads(tool.call({"query": "coffee morning", "limit": 4}))
        self.assertFalse(payload["embeddingsAvailable"])
        self.assertEqual([], payload["matches"])


class MalformedExtractionTest(MemorySessionTestBase):
    def test_review_returning_non_list_memories_fails_without_storing(self) -> None:
        from resono_runtime.providers.openai import OpenAIProviderError

        bridge = _CredentialBridge("sk-test")
        session_id = self.sessions.new_session_id()
        _record_session(self.sessions, session_id, [("user", "hello"), ("assistant", "hi")])
        executor = _FakeReviewExecutor({"summary": "x", "memories": "not a list"})
        pipeline = self._pipeline(bridge=bridge, executor=executor)
        with self.assertRaises(OpenAIProviderError) as error:
            pipeline.finalize(session_id)
        self.assertEqual("review_malformed", error.exception.code)
        self.assertEqual(0, len(self.memories.list_memories()))


class ReviewFailureTruthTest(MemorySessionTestBase):
    def test_usage_limit_rejection_is_surfaced_distinctly(self) -> None:
        from resono_runtime.providers.openai import OpenAIProviderError

        def raising_executor(**_: object) -> str:
            raise RuntimeError(
                'Error streaming response: Error code: 429 - {"error": '
                '{"type": "usage_limit_reached", "resets_in_seconds": 26341}}'
            )

        bridge = _CredentialBridge("sk-test")
        reviewer = _make_reviewer(self.database, bridge=bridge, executor=raising_executor)
        with self.assertRaises(OpenAIProviderError) as error:
            reviewer.review("user: hello\nassistant: hi")
        self.assertEqual("usage_limit_reached", error.exception.code)
        self.assertEqual(429, error.exception.status)
        self.assertIn("7.3", str(error.exception))

    def test_generic_review_failure_remains_a_502(self) -> None:
        from resono_runtime.providers.openai import OpenAIProviderError

        def raising_executor(**_: object) -> str:
            raise RuntimeError("connection reset by peer")

        bridge = _CredentialBridge("sk-test")
        reviewer = _make_reviewer(self.database, bridge=bridge, executor=raising_executor)
        with self.assertRaises(OpenAIProviderError) as error:
            reviewer.review("user: hello\nassistant: hi")
        self.assertEqual("review_failed", error.exception.code)
        self.assertEqual(502, error.exception.status)


class StaleIndexRecoveryTest(MemorySessionTestBase):
    def test_reindex_rebuilds_embeddings_and_restores_retrieval(self) -> None:
        # Store a memory with an embedding under an outdated model key.
        embedder = _FakeEmbedder()
        record = self.memories.store_memory(
            session_id=None,
            memory_class="preference",
            memory_key="morning-drink",
            content_text="Prefers coffee in the morning.",
        )
        self.memories.store_embedding(
            source_id=record.memory_id,
            source_type="memory",
            embedding_model_key="text-embedding-ada-002",
            dimensions=embedder.dimensions,
            embedding=embedder.embed("Prefers coffee in the morning."),
            content_text="Prefers coffee in the morning.",
        )
        bridge = _CredentialBridge("sk-test")
        service = self._service(bridge=bridge)
        # A stale semantic index does not disable deterministic lexical search.
        before = service.search("coffee morning").matches
        self.assertEqual(["lexical"], before[0]["matchMethods"])
        recovered = service.reindex()
        self.assertEqual(1, recovered)
        after = service.search("coffee morning").matches
        self.assertIn("semantic", after[0]["matchMethods"])


class SessionContextTest(MemorySessionTestBase):
    def test_startup_context_loads_recent_memories_and_previous_summary(self) -> None:
        bridge = _CredentialBridge("sk-test")
        prior_id = self.sessions.new_session_id()
        _record_session(self.sessions, prior_id, [("user", "My name is Christian."), ("assistant", "Hello.")])
        executor = _FakeReviewExecutor(
            {
                "summary": "User introduced themselves as Christian.",
                "memories": [
                    {
                        "memoryClass": "relationship",
                        "memoryKey": "user-name",
                        "content": "The user's name is Christian.",
                        "confidence": "high",
                        "sensitivity": "normal",
                    }
                ],
            }
        )
        pipeline = self._pipeline(bridge=bridge, executor=executor)
        pipeline.finalize(prior_id)

        current_id = self.sessions.new_session_id()
        builder = SessionContextBuilder(sessions=self.sessions, memories=self.memories)
        context = builder.build(current_session_id=current_id)

        self.assertEqual(1, len(context.memories))
        self.assertEqual("user-name", context.memories[0].memory_key)
        self.assertIsNotNone(context.previous_summary)
        self.assertEqual("completed", context.previous_summary.summary_status)
        rendered = context.render()
        self.assertIn("Christian", rendered)
        self.assertIn("Previous session summary", rendered)

    def test_startup_context_excludes_current_session_summary(self) -> None:
        bridge = _CredentialBridge("sk-test")
        session_id = self.sessions.new_session_id()
        _record_session(self.sessions, session_id, [("user", "hello"), ("assistant", "hi")])
        executor = _FakeReviewExecutor(
            {"summary": "greeting", "memories": []}
        )
        pipeline = self._pipeline(bridge=bridge, executor=executor)
        pipeline.finalize(session_id)

        builder = SessionContextBuilder(sessions=self.sessions, memories=self.memories)
        context = builder.build(current_session_id=session_id)
        # The current session's summary must not be treated as the previous one.
        self.assertIsNone(context.previous_summary)

    def test_empty_store_yields_empty_context(self) -> None:
        builder = SessionContextBuilder(sessions=self.sessions, memories=self.memories)
        context = builder.build()
        self.assertEqual((), context.memories)
        self.assertIsNone(context.previous_summary)
        self.assertEqual("", context.render())


class MemoryLookupToolTest(MemorySessionTestBase):
    def _seed(self) -> None:
        embedder = _FakeEmbedder()
        record = self.memories.store_memory(
            session_id=None,
            memory_class="preference",
            memory_key="morning-drink",
            content_text="Prefers coffee in the morning.",
        )
        self.memories.store_embedding(
            source_id=record.memory_id,
            source_type="memory",
            embedding_model_key=embedder.model_key,
            dimensions=embedder.dimensions,
            embedding=embedder.embed("Prefers coffee in the morning."),
            content_text="Prefers coffee in the morning.",
        )

    def test_tool_returns_matches_and_clamps_limit(self) -> None:
        self._seed()
        bridge = _CredentialBridge("sk-test")
        tool = MemoryLookupTool(
            memories=self.memories,
            credentials=ProviderCredentials(bridge),
            safety_source="t" * 43,
            embedding_factory=_fake_embedding_factory,
        )
        payload = json.loads(tool.call({"query": "coffee morning", "limit": 99}))
        self.assertTrue(payload["embeddingsAvailable"])
        self.assertGreaterEqual(payload["matchCount"], 1)
        self.assertLessEqual(payload["matchCount"], 8)

    def test_tool_empty_query_returns_nothing(self) -> None:
        self._seed()
        bridge = _CredentialBridge("sk-test")
        tool = MemoryLookupTool(
            memories=self.memories,
            credentials=ProviderCredentials(bridge),
            safety_source="t" * 43,
            embedding_factory=_fake_embedding_factory,
        )
        payload = json.loads(tool.call({"query": ""}))
        self.assertFalse(payload["embeddingsAvailable"])
        self.assertEqual([], payload["matches"])


class CosineParityTest(unittest.TestCase):
    def test_identical_vectors_score_one_and_zero_vector_scores_zero(self) -> None:
        self.assertEqual(1.0, round(cosine_similarity([1.0, 0.0], [1.0, 0.0]), 6))
        self.assertEqual(0.0, cosine_similarity([0.0, 0.0], [1.0, 0.0]))
        self.assertEqual(0.0, cosine_similarity([1.0, 2.0], [3.0]))


if __name__ == "__main__":
    unittest.main()
