# Build Contract 06 — Sessions, Memory, and Agents SDK Review

**Identity:** `R1-BUILD-CONTRACT-06-v0.1`
**Grounding:** `GROUNDING-BASELINE-v0.5`
**Delivery slice:** 5
**Status:** Frozen and active
**Opened:** 2026-08-16 after owner closed Slice 4 open gates (TLS trust accepted; `gpt-live-1` remains owner-deferred) and resolved U-04.

## Outcome

A real completed session transcript is stored locally, reviewed through the single OpenAI Agents SDK runner, and produces provenance-linked memory that can be retrieved by semantic vector search and deleted correctly. Voice and text paths can later run the same memory/vector searches against the canonical local store.

This is the smallest working memory slice. It does not implement later product breadth (External AI capture, ChatGPT context save, or multi-domain personal data).

## U-04 resolution (entry gate)

U-04 — "Smallest adequate local vector implementation" — is resolved by owner decision 2026-08-16:

- **Candidate selected:** SQLite BLOB storage of real provider embeddings + cosine ranking in Python.
- **Embedding model:** OpenAI `text-embedding-3-small` (real semantic embeddings). The donor's `vault_local_hash_embedding_v1` hash-bag is explicitly **not** used; it is the "hash fallback presented as semantic search" the grounding forbids.
- **Search mechanism:** load candidate embeddings from SQLite and rank with cosine similarity in pure Python. No native vector extension is added; no new Android native-packaging gate is opened.
- **Rationale:** identical to the donor's proven retrieval logic (`app/vault_runtime/runtime_memory/retrieval.py` ranks via `_cosine_similarity` in Python, no pgvector); SQL-backed so voice/agent paths can query it; adequate at personal-device memory scale; zero new native dependencies.

## Included

- Provider-neutral session/transcript persistence in SQLite.
- One Agents SDK memory-review runner that reads a transcript and produces a summary plus extracted memory candidates with provenance back to the session. This runner is the text model's only memory role: summarization. The conversational text agent is memory-free.
- Real OpenAI embedding of memories (`text-embedding-3-small`) and embedding storage in SQLite.
- Cosine semantic retrieval over stored embeddings with provenance-linked matches and a similarity floor.
- Voice session-start memory context: at voice Realtime session creation the runtime mints the session id, builds the recalled context (most recent active memories and the previous session's completed summary, excluding the current session), and appends it to the Realtime instructions. Mirrors the donor's startup context packet. The text agent does not receive this context — it does not carry memory across turns.
- A `memory_lookup` Realtime function tool exposed to the **voice** model so it can search approved prior-conversation memory mid-session; dispatched through the on-device MCP server to the same cosine retriever as the management search. The text agent's MCP filter keeps it to `get_device_status` only, so `memory_lookup` is voice-only.
- Voice transcript capture: the native peer captures the user turn (`conversation.item.input_audio_transcription.completed`) and assistant turn (`response.audio_transcript.done`) transcripts it already receives, and posts them against the server-minted session id at session close via `/v1/voice/sessions/finalize`.
- Voice finalize-on-close: the runtime appends the posted transcript entries, then runs the single review/memory/embedding flow synchronously (donor close→finalize), so a completed voice session produces provenance-linked memory available to the next session's startup context.
- Memory inspection, semantic search, deletion, and stale-index recovery (reindex) over the canonical store.
- Paired management HTTP routes and real web/native inspection and deletion controls.

## Excluded

- A separate finalize REST surface for text turns; text remains a stateless conversational path. (The transcript intake is provider-neutral, so text turns can finalize later without redesign if memory-from-text is ever required.)
- External AI / ChatGPT context capture and outbox (Slice 9).
- A separate ChatGPT vector store, hash-based semantic search, wholesale Vault memory port, additional embedding providers, and personal-data domains (Mail/Calendar/Contacts/Reminders).

### Correction 2026-08-16 — memory belongs to the voice path

An earlier draft of this slice wired session-start memory context and the `memory_lookup` tool into the Agents SDK **text** runner. That was a misplacement: the donor's `memory_lookup` is a Voice Realtime function tool (`browser_voice_tools.py`), session-start context is injected at Realtime session start, and the text model's memory role is the post-session review/summarization agent, not a conversational agent that carries memory across turns. The text-runner memory wiring was removed; session-start context and `memory_lookup` were moved to the voice Realtime path, and voice transcript capture + finalize-on-close were added (previously listed as Excluded). The previous-session ordering key was also corrected: it was `ORDER BY session_id DESC` on random hex, which selected an arbitrary session; it now orders finalized sessions by `summary updated_at DESC, created_at DESC` (donor parity).

## Donor freeze

All source projects remain read-only. Adaptations occur only inside this repository.

| Concern | Read-only source | Destination |
|---|---|---|
| Transcript/summary/memory schema | `migrations/versions/0026_runtime_memory_store.py`; `0034_runtime_memory_embeddings.py` | `runtime/resono_runtime/storage/database.py` (SQLite migration v4) |
| Semantic retrieval logic | `app/vault_runtime/runtime_memory/retrieval.py` (`_cosine_similarity`, candidate load + rank, similarity floor, provenance payload) | `runtime/resono_runtime/memory/retrieval.py` |
| Memory review agent | `app/vault_runtime/agent_packages/runners/openai_agents.py` (single `Runner.run`, tracing disabled, bounded turns, final-output extraction) | `runtime/resono_runtime/agents/memory_reviewer.py` |
| Provider embeddings | `app/vault_runtime/embeddings.py` (`embed_vault_text`, model key + dimensions) | `runtime/resono_runtime/providers/openai/embeddings.py` |
| Session-start memory context | `app/vault_runtime/session_context_builder.py` (startup memory limit 8, previous-session-summary section, support-safe context packet) | `runtime/resono_runtime/memory/session_context.py` |
| `memory_lookup` agent tool | `app/contracts/internal/browser_voice_tools.py` (`memory_lookup_tool_definition`: `{query, limit 1..8}`, target `memory.lookup`); dispatch via `app/vault_runtime/agent_packages/brokers/memory.py` (`search_user_memory` → `vault_hybrid_memory_lookup`) | `runtime/resono_runtime/memory/tools.py` (function tool wrapping the cosine retriever) |

Before each copy, the source hash and destination are appended to `docs/DONOR_CODE_REFERENCE_MAP.md`. The hash-bag `runtime_memory/embeddings.py` is reviewed and **rejected** as a forbidden hash fallback; it is not copied.

## Dependency checkpoints

1. **Schema.** Migration v4 adds `session_transcript_entries`, `session_summaries`, `memory_records`, and `memory_embeddings` to the on-device SQLite. Proven by migration + health check.
2. **Transcript persistence.** A completed session's transcript is stored provider-neutrally with role, event type, content, and ordering. Proven by append/read/list/delete tests.
3. **Review agent.** The single Agents SDK runner reads a transcript and returns a summary plus extracted memory candidates. Reuses the existing credential/selection; no parallel agent loop. Proven with an injectable executor plus a credential-required denial.
4. **Embeddings.** Real `text-embedding-3-small` vectors are produced for each memory and stored as BLOBs with model key and dimensions. Proven with an injectable executor and an unavailable-embedding degradation test.
5. **Retrieval.** A query is embedded and ranked by cosine similarity against stored embeddings, returning provenance-linked matches above the similarity floor. Proven by a real-vector retrieval test and a no-match test.
6. **Deletion and reindex.** Deleting a memory removes its record and embedding; deleting a session cascades to its transcript, summary, memories, and embeddings; stale embeddings are recovered by reindex. Proven by deletion/cleanup tests.
7. **Session-start context (voice).** At voice Realtime session creation the runtime mints the session id and appends the most recent active memories (limit 8) and the previous session's completed summary to the Realtime instructions, excluding the current session; the previous session is the most recently *finalized* session ordered by summary `updated_at DESC, created_at DESC` (donor parity — never ordered by the random session id). Required evidence: `SessionContextTest` in `tests/runtime/test_memory_sessions.py` (loads memories + previous summary, excludes current session, empty store yields empty context).
8. **`memory_lookup` voice tool.** The **voice** model can call `memory_lookup(query, limit 1..8)` mid-session, dispatched through the on-device MCP server to the cosine retriever; it reports `embeddingsAvailable=false` honestly when no platform key is configured and never substitutes a keyword/hash search. The conversational text agent does not receive this tool (its MCP filter keeps it to `get_device_status`). Required evidence: `MemoryLookupToolTest` in `tests/runtime/test_memory_sessions.py` (matches + clamped limit, empty query, unavailable-without-credentials).
9. **Voice transcript capture and finalize-on-close.** The native peer captures the user and assistant transcript turns it already receives and posts them against the server-minted session id at session close; the runtime appends them and runs the single review/memory/embedding flow synchronously. Required evidence: voice finalize tests in `tests/runtime/test_memory_sessions.py` (finalize appends posted transcript then produces memory+embeddings; empty capture is rejected).
10. **Connected UI.** Real web controls inspect memories, run a semantic search, finalize a session, reindex, and delete, backed by the implemented routes. The native R1 480x640 settings screen is a status-only surface (matching the donor, which has no on-device memory panel); the web management UI is the canonical memory inspection surface. The Android runtime-host proxy forwards the new `/v1/management/memory/*` routes (prefix-matched for dynamic IDs) with a long timeout for finalize. No disconnected screen.

## Required evidence

- Offline tests for transcript-to-memory provenance, retrieval, idempotent finalization, deletion/index cleanup, unavailable embeddings, malformed extraction, stale-index recovery, session-start context, and the `memory_lookup` agent tool (`tests/runtime/test_memory_sessions.py`).
- Android build/boundary/package checks and no donor modification.
- Real credential-backed memory review + retrieval proof with redacted identifiers (physical checkpoint; deferred until owner resumes it, like the donor's Platform proof).
- Exact candidate APK path, size, SHA-256, installed version, rollback command, and owner acceptance.

## Internal attack and stop rules

- A hash, keyword, or random vector presented as semantic search fails.
- A memory with no provenance back to a stored session fails.
- A second agent loop or a parallel memory extraction path fails.
- Memory text sent anywhere other than the configured embedding provider fails.
- A deleted memory that remains retrievable fails.
- A beautiful memory screen with no live retrieval behind it fails.
- Adding later-slice features (External AI, ChatGPT capture, personal-data domains) stops the build.

## Rollback

The installed version-9 APK remains the runtime rollback; version 26 remains the accepted working product base. A failed memory feature is disabled without changing the proven runtime lifecycle, provider, or Voice path. Migration v4 is additive only; reverting drops the four new tables without affecting prior data.

## Exit

The contract exits only when the real memory vertical passes offline and physical evidence and the owner accepts it. Tests or inspection screens alone cannot close it.

## Material Decision Gates

### BC06-MDG-01 — Session source for the first memory vertical

- **Question:** Prove the memory vertical with a Voice session transcript, a text-turn transcript, or block until Voice transcript capture exists?
- **Authority/evidence:** Grounding scenario 8 ("Save the session locally and run the real Agents SDK post-session memory flow"); Slice 5 exit = scenario 8; P-MDG-04 (contract with its first real vertical path); no-mockup rule.
- **Alternatives:** Block Slice 5 until Voice transcript event capture exists; use a synthetic/mock transcript; use a real completed text-turn transcript persisted provider-neutrally.
- **Selection/function:** Persist a real completed Agents SDK text-turn transcript provider-neutrally and run the review/memory flow over it. The transcript intake is provider-neutral (`role`, `event_type`, `content`, ordering) so a Voice transcript attaches later without redesigning the memory contract.
- **Counterexample:** A fake transcript exercises the pipeline, or the memory schema can only accept Voice-shaped events.
- **Dependents:** Review agent, embeddings, retrieval, UI.
- **Result:** `CONTINUE`.

### BC06-MDG-02 — Vector mechanism (U-04)

- **Question:** pgvector, a native SQLite vector extension, or SQLite BLOB + Python cosine?
- **Authority/evidence:** U-04 ("smallest adequate local vector implementation", "SQLite-compatible"); F-11 (one memory/vector pipeline); donor `retrieval.py` (pure-Python cosine, no pgvector); owner decision 2026-08-16.
- **Alternatives:** `sqlite-vec` native extension (new arm64-Android packaging gate); SQLite BLOB + Python cosine (donor logic, no new native dependency).
- **Selection/function:** Store real provider embeddings as SQLite BLOBs and rank candidates by cosine similarity in Python. Real semantic quality comes from the `text-embedding-3-small` embedding model, not the storage mechanism.
- **Counterexample:** A hash/random vector is stored and called semantic search, or a native extension is added without an open packaging gate.
- **Dependents:** Retrieval, embeddings, reindex, UI search.
- **Result:** `CONTINUE` (U-04 resolved).

---

## Donor Session Close Flow Research (2026-08-19)

This section documents the exact session close → memory ingestion flow from the Voice/Vault donor codebase. The donor flow should be mirrored closely in the R1 implementation.

### 1. Session Close Trigger

**File:** `app/modules/device_runtime/realtime_proxy_service.py`

The `close_proxy()` method (lines 379-401) orchestrates session teardown in three ordered phases:

```python
async def close_proxy(*, handle: OpenAIRealtimeProxyHandle) -> None:
    async with handle.state.close_lock:
        # Phase 1: Close upstream provider connection
        if not handle.state.provider_closed:
            await handle.connection.close()
            handle.state.provider_closed = True
        
        # Phase 2: Mark voice session closed in database
        if not handle.state.voice_record_closed:
            await run_in_threadpool(self._close_voice_runtime_record, handle=handle)
            handle.state.voice_record_closed = True
        
        # Phase 3: Run post-session memory finalization
        if not handle.state.post_session_finalized:
            await run_in_threadpool(self._finalize_post_session_memory, handle=handle)
            handle.state.post_session_finalized = True
```

**Key insight:** The close is synchronous and blocking. Each phase completes before the next begins. The finalization runs in a threadpool but the async method waits for it.

### 2. Transcript Capture (During Live Session)

**File:** `app/modules/device_runtime/realtime_proxy_service.py` (lines 621-657)

Transcripts are captured in real-time as OpenAI Realtime events flow through the proxy:

```python
def _capture_transcript_event(*, handle, event) -> None:
    event_type = event.get("type")
    
    # User transcript (speech-to-text result)
    if event_type in {
        "conversation.item.input_audio_transcription.completed",
        "conversation.item.input_audio_transcript.completed",
    }:
        transcript = event.get("transcript")
        if isinstance(transcript, str):
            RuntimeMemoryService(db).capture_transcript_entry(
                voice_realtime_session_id=handle.voice_realtime_session_id,
                account_id=handle.actor_id,
                workspace_id=handle.workspace_id,
                role="user",
                event_type=event_type,
                text_content=transcript,
            )
    
    # Assistant transcript (response text)
    if event_type in {
        "response.audio_transcript.done",
        "response.output_audio_transcript.done",
    }:
        transcript = event.get("transcript")
        if isinstance(transcript, str):
            RuntimeMemoryService(db).capture_transcript_entry(
                voice_realtime_session_id=handle.voice_realtime_session_id,
                account_id=handle.actor_id,
                workspace_id=handle.workspace_id,
                role="assistant",
                event_type=event_type,
                text_content=transcript,
            )
```

**Storage location:** Transcripts are stored in `session_transcript_entries` table with:
- `voice_realtime_session_id` (foreign key to session)
- `account_id`, `workspace_id` (ownership)
- `role` ("user" or "assistant")
- `event_type` (the specific OpenAI event that produced it)
- `text_content` (the actual transcript text)
- `created_at` (ordering)

### 3. Finalization Coordinator

**File:** `app/modules/runtime_memory/finalization_coordinator.py`

The `execute_runtime_memory_finalization()` function (lines 41-139) is the orchestrator:

```python
def execute_runtime_memory_finalization(
    *,
    session_factory: RuntimeMemorySessionFactory,
    voice_realtime_session_id: str,
    account_id: str,
    workspace_id: str,
    route_context: dict | None = None,
    summary_invoker: RuntimeMemorySummaryInvoker | None = None,
    embedding_invoker: RuntimeMemoryEmbeddingInvoker | None = None,
    completion_callback: RuntimeMemoryCompletionCallback | None = None,
) -> RuntimeMemorySummaryResult:
```

**Three-phase flow:**

1. **Prepare** (`_prepare_finalization`): 
   - Opens a DB session
   - Calls `RuntimeMemoryService.prepare_closed_voice_session_finalization()`
   - Loads all transcript entries for the session
   - Joins them into a single `transcript_text` string (bounded by character limit)
   - Claims a finalization lease (idempotency)
   - Returns `RuntimeMemoryFinalizationPreparation` with status `ready`, `already_completed`, `empty`, or `in_progress`

2. **Invoke** (LLM call):
   - Constructs `OpenAIRuntimeMemorySummaryInvoker` (or uses injected one)
   - Calls the model with the transcript text
   - Model returns JSON with `summary` and `memories` array

3. **Persist** (`persist_closed_voice_session_finalization`):
   - Saves session summary record
   - Saves memory record for each extracted memory
   - Generates embeddings for summary + each memory
   - Saves embedding records with vectors
   - Records usage metrics
   - Calls completion callback (for downstream hooks)

**Critical insight:** The entire flow is **synchronous** from the caller's perspective. The `close_proxy` awaits the threadpool, and the finalization coordinator runs all three phases in sequence before returning.

### 4. Memory Summarization Agent

**File:** `app/modules/runtime_memory/service.py` (lines 1765-1779)

The prompt is static and defined in `_summarizer_instructions()`:

```python
@staticmethod
def _summarizer_instructions() -> str:
    return (
        "You summarize completed user-assistant voice sessions for a platform-owned memory system. "
        "Return JSON only with keys summary and memories. "
        "summary must be a short plain-English recap of the completed session. "
        "memories must be an array of durable user facts worth storing across future sessions. "
        "Only store stable preferences, relationship facts, or environment facts. "
        "If the user explicitly says to remember something, save something to memory, or remember it for future sessions, treat the requested fact as high-priority durable memory unless it is unsafe or inappropriate to store. "
        "Do not store secrets, credentials, payment data, one-time requests, transient plans, or sensitive data unless the user explicitly framed it as durable personal context. "
        "Each memory item must contain memoryClass, memoryKey, content, confidence, sensitivity, and shouldStore. "
        "memoryClass must be one of preference, relationship, environment. "
        "confidence must be one of low, medium, high. "
        "sensitivity must be one of normal or sensitive. "
        "Set shouldStore false for anything that should not become durable memory."
    )
```

**Output format expected:**
```json
{
  "summary": "Short recap of the session...",
  "memories": [
    {
      "memoryClass": "preference",
      "memoryKey": "preferred-name",
      "content": "User prefers to be called Alex",
      "confidence": "high",
      "sensitivity": "normal",
      "shouldStore": true
    }
  ]
}
```

**Validation** (`runtime_memory_model.py` lines 169-183):
- Forbidden markers are rejected: "api key", "credit card", "cvv", "password", "passcode", "private key", "secret key", "seed phrase", "social security", "ssn"
- Memory class must be one of: `preference`, `relationship`, `environment`
- Confidence defaults to `medium` if invalid
- Sensitivity defaults to `normal` if invalid
- Character limits are enforced

### 5. Embedding Generation

**File:** `app/vault_runtime/handlers/runtime_memory.py` (lines 297-374)

Embeddings are generated for:
1. **Session summary text** (if not empty)
2. **Each memory content text** (if not empty)

```python
def _embedding_items(
    *,
    account_id: str,
    workspace_id: str,
    summary_item: VaultMigrationExportItem,
    memory_items: tuple[VaultMigrationExportItem, ...],
) -> tuple[VaultMigrationExportItem, ...]:
    items: list[VaultMigrationExportItem] = []
    
    # Embed the session summary
    summary_text = _optional_text(summary_item.payload.get("summaryText"))
    if summary_text:
        item = _embedding_item(
            account_id=account_id,
            workspace_id=workspace_id,
            installed_skill_id=None,
            source_type="summary",
            source_id=summary_item.source_id,
            content_text=summary_text,
        )
        if item is not None:
            items.append(item)
    
    # Embed each memory
    for memory_item in memory_items:
        content_text = _optional_text(memory_item.payload.get("contentText"))
        if content_text is None:
            continue
        item = _embedding_item(
            account_id=account_id,
            workspace_id=workspace_id,
            installed_skill_id=_optional_text(memory_item.payload.get("installedSkillId")),
            source_type="memory",
            source_id=memory_item.source_id,
            content_text=content_text,
        )
        if item is not None:
            items.append(item)
    
    return tuple(items)
```

**Embedding call** (`app/vault_runtime/embeddings.py`):
- Uses `text-embedding-3-small` (1536 dimensions)
- Stores vector as BLOB in SQLite
- Records model key and dimensions for future compatibility

### 6. Database Schema

**From migration files** (`0026_runtime_memory_store.py`, `0034_runtime_memory_embeddings.py`):

**Table: `session_transcript_entries`**
- `id` (primary key)
- `voice_realtime_session_id` (foreign key)
- `account_id`, `workspace_id`
- `role` ("user" | "assistant")
- `event_type` (string)
- `text_content` (text)
- `created_at` (timestamp)

**Table: `session_summaries`**
- `id` (primary key)
- `voice_realtime_session_id` (unique foreign key)
- `account_id`, `workspace_id`
- `summary_status` ("pending" | "completed" | "empty" | "failed")
- `transcript_text` (text, bounded)
- `summary_text` (text, bounded)
- `extracted_memory_count` (int)
- `summarizer_provider_key`, `summarizer_model_key`
- `created_at`, `updated_at` (timestamps)

**Table: `memory_records`**
- `id` (primary key)
- `account_id`, `workspace_id`
- `voice_realtime_session_id` (provenance link)
- `memory_class` ("preference" | "relationship" | "environment")
- `memory_key` (string, slugified)
- `content_text` (text)
- `confidence` ("low" | "medium" | "high")
- `sensitivity` ("normal" | "sensitive")
- `status` ("active" | "deleted")
- `metadata` (JSON, includes extractor, source session, provenance)
- `created_at`, `updated_at` (timestamps)

**Table: `memory_embeddings`**
- `id` (primary key)
- `account_id`, `workspace_id`
- `source_type` ("summary" | "memory")
- `source_id` (foreign key to summary or memory)
- `content_text` (the text that was embedded)
- `embedding_model_key` (e.g., "text-embedding-3-small")
- `embedding_dimensions` (e.g., 1536)
- `embedding` (BLOB, the actual vector)
- `created_at`, `updated_at` (timestamps)

### 7. Session-Start Memory Context (For Next Session)

**File:** `app/vault_runtime/session_context_builder.py` (lines 115-269)

When a new Voice session starts, context is built and injected:

```python
def create_context_packet(self, payload: Mapping[str, Any]) -> dict[str, Any]:
    # ... authorization ...
    
    # Load active memories (limit 8, filtered)
    memory_records = _startup_memory_records(
        self._store.list_active_memory_records(
            account_id=account_id,
            workspace_id=workspace_id,
            limit=STARTUP_MEMORY_RECORD_FETCH_LIMIT,  # 64
        )
    )
    
    # Load the immediately prior session summary
    session_summaries = _exact_previous_session_summaries(
        store=self._store,
        account_id=account_id,
        workspace_id=workspace_id,
        current_voice_realtime_session_id=voice_realtime_session_id,
    )
    
    # Build context packet
    packet = {
        "packetType": "resono-vault-session-context-packet-v1",
        "sections": [
            {
                "sectionType": "approved_memory",
                "items": [_memory_context_item(record) for record in memory_records],
            },
            {
                "sectionType": "previous_session_summary",
                "items": [_session_summary_context_item(summary) for summary in session_summaries],
                "status": "available" if session_summaries else "unavailable",
            },
        ],
    }
```

**Previous session selection** (lines 330-369):

Critical detail: The prior session is selected by **summary updated_at DESC, created_at DESC**, NOT by session_id:

```python
def _exact_previous_session_summaries(...) -> list[dict[str, Any]]:
    # First try: get latest prior provider session
    prior_session = store.get_latest_prior_provider_session(
        account_id=account_id,
        workspace_id=workspace_id,
        current_voice_realtime_session_id=current_voice_realtime_session_id,
    )
    
    # If found and has completed summary, return it
    if _completed_summary_with_text(summary):
        return [summary]
    
    # Fallback: list completed summaries by updated_at DESC
    for summary in store.list_completed_session_summaries(
        account_id=account_id,
        workspace_id=workspace_id,
        limit=STARTUP_MEMORY_RECORD_LIMIT,  # 8
    ):
        # Skip current session
        if _record_text(summary, "voiceRealtimeSessionId") == current_voice_realtime_session_id:
            continue
        if _completed_summary_with_text(summary):
            return [summary]
    
    return []
```

**Key insight:** The donor explicitly orders by `updated_at DESC, created_at DESC` to get the **most recently finalized** session, not an arbitrary one. Session IDs are random hex strings, so ordering by them would be meaningless.

### 8. How the Agent is Triggered

**In the donor:** The `_finalize_post_session_memory` method in `realtime_proxy_service.py` (lines 701-732) calls:

```python
def _finalize_post_session_memory(*, handle: OpenAIRealtimeProxyHandle) -> None:
    def complete_finalization(db: Session, summary_result: RuntimeMemorySummaryResult) -> None:
        # Hook for downstream services
        PlatformLearningService(db).enqueue_session_analysis(...)
        AgentHubService(db).enqueue_session_review(...)
    
    try:
        execute_runtime_memory_finalization(
            session_factory=self._session_factory,
            voice_realtime_session_id=handle.voice_realtime_session_id,
            account_id=handle.actor_id,
            workspace_id=handle.workspace_id,
            completion_callback=complete_finalization,
        )
    except Exception:
        logger.exception("post-session memory finalization failed")
```

**The trigger chain:**
1. User closes session (native UI action or transport disconnect)
2. Native client calls `close_proxy()` on the runtime proxy
3. `close_proxy()` calls `_finalize_post_session_memory()` in threadpool
4. `execute_runtime_memory_finalization()` orchestrates the flow
5. `OpenAIRuntimeMemorySummaryInvoker` calls the LLM with the transcript
6. Model returns summary + memories JSON
7. Results are persisted to database
8. Embeddings are generated for summary + each memory
9. Completion callback fires for downstream hooks

**In the R1 implementation:** The flow should be nearly identical, but the trigger comes from:
- Native peer posts transcript entries during session
- Native peer calls `/v1/voice/sessions/finalize` at session close
- Runtime appends entries and runs the single review/memory/embedding flow synchronously

### 9. Critical Differences to Preserve

1. **Synchronous finalization:** The donor waits for the full flow to complete. If the LLM call fails, the exception propagates and the session summary is marked failed.

2. **Idempotency:** The finalization coordinator claims a lease before running. If called again for the same session, it returns `already_completed` or `in_progress`.

3. **Transcript bounds:** The transcript is bounded by both entry count (512) and character count (100,000) before being sent to the model.

4. **Memory validation:** Extracted memories are validated against allowed classes, confidence levels, and forbidden markers.

5. **Provenance chain:** Every memory links back to `voice_realtime_session_id`, `account_id`, and `workspace_id`. The embedding links back to the memory or summary.

6. **Semantic retrieval:** Uses pure Python cosine similarity on BLOB-stored vectors. No native vector extension.

7. **Session-start ordering:** Previous session is the most recently *finalized* session, ordered by `summary updated_at DESC, created_at DESC`, not by random session ID.

### 10. Files to Study for Implementation

| Concern | Donor File | R1 Target |
|---------|-----------|-----------|
| Session close orchestration | `app/modules/device_runtime/realtime_proxy_service.py` | `runtime/resono_runtime/providers/openai/platform.py` + `api/http_server.py` |
| Transcript capture | `realtime_proxy_service.py:_capture_transcript_event` | `platform.py` (event handling) |
| Finalization coordinator | `app/modules/runtime_memory/finalization_coordinator.py` | `runtime/resono_runtime/memory/pipeline.py` |
| Memory service | `app/modules/runtime_memory/service.py` | `runtime/resono_runtime/memory/service.py` |
| Summarizer prompt | `service.py:_summarizer_instructions` | Same prompt in R1 |
| Vault-local handler | `app/vault_runtime/handlers/runtime_memory.py` | `runtime/resono_runtime/agents/memory_reviewer.py` |
| Model invoker | `app/vault_runtime/handlers/runtime_memory_model.py` | Same in R1 |
| Embedding generation | `app/vault_runtime/embeddings.py` | `runtime/resono_runtime/providers/openai/embeddings.py` |
| Session-start context | `app/vault_runtime/session_context_builder.py` | `runtime/resono_runtime/memory/session_context.py` |
| Semantic retrieval | `app/vault_runtime/runtime_memory/retrieval.py` | `runtime/resono_runtime/memory/retrieval.py` |

---

## Addendum 2026-08-20 — Finalize-chain repair and platform-wide credential consolidation

Physical evaluation of the memory vertical found the agent side of the session-close flow failing on device while transcript capture worked. The donor flow in this contract was re-verified against the R1 implementation (the donor project itself was not re-opened; this contract's Donor Session Close Flow Research was the reference). The following corrections were made inside this repository only. No donor, review-clone, or other project files were modified. Offline suite: 56/57 pass (the single failure is the pre-existing host Python 3.11 vs expected 3.13 environment assertion, unrelated). Android `:runtime-host` and `:feature:voice` modules compile under the project Chaquopy toolchain. Physical credential-backed proof remains the open exit gate.

### Root causes found and corrections applied

1. **Native finalize timeout was too short for a synchronous review.** `RuntimeVoiceClient` used a 10s read timeout for `/v1/voice/sessions/finalize`, while the route runs the full review agent plus embeddings synchronously. Raised to 65s, matching the management proxy's existing timeout for the same operation (`ManagementRuntimeProxy`). **Files:** `android/runtime-host/.../RuntimeVoiceClient.java`.

2. **Finalization fired only on the explicit stop path.** `fail()` (provider/peer/runtime errors) and `close()` (view teardown) discarded captured transcript entries without finalizing, diverging from the donor's close→finalize-on-transport-close. Finalize dispatch is now one method, `VoicePageView.dispatchPendingFinalize()`, invoked on explicit stop, failure, and teardown; a following session can no longer be stranded (the `isFinalizing` early-return was removed). **Files:** `android/feature/voice/.../VoicePageView.java`.

3. **Embeddings were gated on the Platform key only.** Subscription-only setups stored memories without vectors, silently disabling semantic search. Embeddings now use the same credential as every agent via the new canonical resolver (item 5), applied to the finalize pipeline, management search/reindex, and the `memory_lookup` voice tool. **Files:** `runtime/resono_runtime/memory/embedding_access.py` (new), `memory/pipeline.py`, `memory/service.py`, `memory/tools.py`, `application.py` wiring.

4. **Failures were invisible end-to-end.** Finalize failures are now logged with reason on Android (`VoicePageView`/`RuntimeVoiceClient` logcat) and in the runtime; unexpected exceptions in both finalize routes return a logged 500 (`finalize_failed`) instead of dropping the connection. **Files:** `RuntimeVoiceClient.java`, `VoicePageView.java`, `api/routes.py`.

5. **Credential logic was duplicated per consumer.** New `runtime/resono_runtime/providers/openai/access.py` (`openai_provider_access`) is the single platform-wide access-path → token/base-URL decision. The text runner and memory reviewer had their own inline copies; both were deleted and now call the resolver. `memory/embedding_access.py` delegates to it (agents raise 409; memory paths degrade to `None`). Every future agent resolves its credential here. **Files:** `providers/openai/access.py` (new), `providers/openai/__init__.py`, `agents/runner.py`, `agents/memory_reviewer.py`.

6. **Structural consolidation (acceptance condition).** One Agents SDK execution path: `agents/sdk_runner.py` (`run_agent_turn`/`run_agent_turn_sync`) replaced the duplicated async boilerplate in both runners. The runtime API was split into transport (`api/http_server.py`: bind, threads, bearer auth, request/response mechanics) and routing (`api/routes.py`: `RuntimeRoutes`, one method per verb, route order/guards/payloads preserved verbatim, shared `_finalize_view`). `runtime/README.md` records the three ownership rules. **Files:** `agents/sdk_runner.py` (new), `agents/__init__.py`, `api/http_server.py` (rewritten), `api/routes.py` (new), `runtime/README.md`.

7. **Stale test expectation.** The donor-parity summary embedding (summary + each memory) made the provenance test's expected embedded count 3, not 2; the failure predated this session. Updated with a comment. **Files:** `tests/runtime/test_memory_sessions.py`.

### Contract notes

- The embedding endpoint for subscription credentials is `api.openai.com/v1/embeddings` with the OAuth access token, per owner confirmation that this works in their other projects; physical proof will confirm.
- No schema changes; migration v4 is untouched. No new tables, no new dependencies, no donor modification. Boundary checks (`check_boundaries.sh`, `check_runtime_package.sh`) pass.
- Rollback posture is unchanged: version 26 remains the accepted working product base.
- Change index row: `docs/CHANGE-INDEX.md` (2026-08-20, "BC-06 memory finalize chain repaired").

## Addendum 2026-08-20 - Native Realtime response ownership correction

Repeated physical Voice sessions exposed `conversation_already_has_active_response`
after asynchronous tool calls. The failure was not WebRTC, authorization, or the
tool provider: native code had multiple independent producers of
`response.create`, boolean-only provider state, and concurrent tool callbacks.
The attempted 150 ms delay after `response.done` was not donor-equivalent and
did not resolve the race.

Source now assigns every client-originated `response.create` to
`RealtimeResponseCoordinator`. Greeting, tool continuation, and Direct Handoff
request a response through that owner; server VAD remains unchanged and may
still create responses automatically. `RealtimeToolCallQueue` serializes native
tool execution. The coordinator marks a client response active before sending,
retains one pending continuation while a provider response is active, releases
it from `response.done`, cancels pending work on session close, and treats the
provider's active-response rejection as recoverable rather than terminating the
Voice session.

This source correction preserves the existing WebRTC, audio/VAD profile,
greeting wording, tool APIs, image payload, transcript capture, and session
finalization boundaries. Build and physical acceptance evidence must be
recorded separately.
