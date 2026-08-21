from __future__ import annotations

import json
from typing import Any

from ..providers.openai import EmbeddingUnavailable
from ..providers.openai.subscription import OpenAISubscription
from ..security.credentials import ProviderCredentials
from ..storage.memory import MemoryRepository
from ..storage.provider_settings import ProviderSettingsRepository
from .embedding_access import default_embedding_factory, embedding_api_key
from .retrieval import MemoryRetriever, RetrievalMatch
from ..agents.audience import AudienceResource, AudienceResourceKind
from ..storage.sessions import SessionTranscriptRepository
from ..tools.catalog import ToolCatalog
from ..tools.definitions import ToolDefinition, ToolInvocationContext, ToolInvocationResult
from .contracts import REVIEWER_CONTRACT_VERSION


# Donor parity: app/contracts/internal/browser_voice_tools.py defines the
# memory_lookup Realtime function tool with parameters {query (required),
# limit (integer 1..8)} and the description below. The donor dispatches it to
# vault_hybrid_memory_lookup; this standalone store routes the same call to the
# MemoryRetriever cosine path.
MEMORY_LOOKUP_TOOL_NAME = "memory_lookup"
MEMORY_LOOKUP_TOOL_DESCRIPTION = (
    "Search approved prior-conversation memory for user-specific context. "
    "Use this when the user asks about something you do not know that could have "
    "come from a prior conversation. Preamble sample phrase: "
    "'I'm checking your prior context now.'"
)
MEMORY_LOOKUP_PARAMETERS = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "What to search for in approved prior-conversation memory.",
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 8,
            "description": "Maximum number of matches to return.",
        },
    },
    "required": ["query"],
    "additionalProperties": False,
}
MAX_MEMORY_LOOKUP_RESULTS = 8
MEMORY_TOOL_SET = AudienceResource(AudienceResourceKind.DOMAIN_TOOL_SET, "memory")

# OpenAI Realtime session ``tools`` array entry. The voice model sees this tool
# definition and calls it; the Android peer routes the call to the on-device MCP
# server, which dispatches to ``MemoryLookupTool`` (the executor below). This
# mirrors the donor's ``memory_lookup`` Realtime function tool.
MEMORY_LOOKUP_REALTIME_TOOL = {
    "type": "function",
    "name": MEMORY_LOOKUP_TOOL_NAME,
    "description": MEMORY_LOOKUP_TOOL_DESCRIPTION,
    "parameters": MEMORY_LOOKUP_PARAMETERS,
}

# MCP ``tools/list`` entry (uses ``inputSchema`` rather than ``parameters``).
MEMORY_LOOKUP_MCP_TOOL = {
    "name": MEMORY_LOOKUP_TOOL_NAME,
    "description": MEMORY_LOOKUP_TOOL_DESCRIPTION,
    "inputSchema": MEMORY_LOOKUP_PARAMETERS,
}


class MemoryLookupTool:
    """Agents SDK function tool wrapping semantic memory retrieval.

    The tool is callable when the credential the agent paths use (chosen by
    the configured access path: subscription token or Platform key) can call
    the embedding provider and at least one memory is embedded. When
    embeddings are unavailable the tool reports that honestly rather than
    substituting a keyword/hash search, matching the donor's
    ``embeddingSearch`` provenance flag and the build-contract attack rule
    that a hash/keyword/random vector presented as semantic search fails.
    """

    def __init__(
        self,
        *,
        memories: MemoryRepository,
        credentials: ProviderCredentials,
        safety_source: str,
        settings: ProviderSettingsRepository | None = None,
        subscription: OpenAISubscription | None = None,
        embedding_factory=None,
    ) -> None:
        self._memories = memories
        self._credentials = credentials
        self._safety_source = safety_source
        self._settings = settings
        self._subscription = subscription
        self._embedding_factory = embedding_factory or default_embedding_factory

    def name(self) -> str:
        return MEMORY_LOOKUP_TOOL_NAME

    def description(self) -> str:
        return MEMORY_LOOKUP_TOOL_DESCRIPTION

    def parameters(self) -> dict[str, Any]:
        return MEMORY_LOOKUP_PARAMETERS

    @staticmethod
    def realtime_tool() -> dict[str, Any]:
        """OpenAI Realtime ``tools`` array entry for this tool."""
        return MEMORY_LOOKUP_REALTIME_TOOL

    @staticmethod
    def mcp_tool() -> dict[str, Any]:
        """MCP ``tools/list`` entry (``inputSchema`` form) for this tool."""
        return MEMORY_LOOKUP_MCP_TOOL

    def call(self, arguments: str | dict[str, Any]) -> str:
        if isinstance(arguments, str):
            arguments = json.loads(arguments) if arguments.strip() else {}
        query = str(arguments.get("query", "")).strip()
        if not query:
            return json.dumps({"matches": [], "embeddingsAvailable": False, "reason": "empty_query"})
        api_key = embedding_api_key(
            credentials=self._credentials,
            settings=self._settings,
            subscription=self._subscription,
        )
        limit = _coerce_limit(arguments.get("limit"))
        embedder = None
        if api_key is not None:
            try:
                embedder = self._embedding_factory(api_key, self._safety_source)
            except EmbeddingUnavailable:
                embedder = None
        retriever = MemoryRetriever(memories=self._memories, embedder=embedder)
        try:
            matches = retriever.retrieve(query, limit=limit)
        except EmbeddingUnavailable:
            return json.dumps(
                {"matches": [], "embeddingsAvailable": False,
                 "reason": "embedding_provider_unavailable"}
            )
        return json.dumps(
            {
                "matches": [_match_payload(match) for match in matches[:MAX_MEMORY_LOOKUP_RESULTS]],
                "matchCount": len(matches),
                "embeddingsAvailable": embedder is not None,
            }
        )


class MemoryToolPackage:
    """One versioned Voice/Text package for the complete memory lifecycle."""

    def __init__(self, *, lookup: MemoryLookupTool, memories: MemoryRepository,
                 sessions: SessionTranscriptRepository) -> None:
        self._lookup = lookup
        self._memories = memories
        self._sessions = sessions

    def register(self, catalog: ToolCatalog) -> None:
        catalog.register(ToolDefinition(
            tool_id="builtin.memory-lookup.v2", name="memory_lookup",
            description=MEMORY_LOOKUP_TOOL_DESCRIPTION, input_schema=MEMORY_LOOKUP_PARAMETERS,
            handler=lambda arguments: ToolInvocationResult(self._lookup.call(arguments)),
            audience_resource=MEMORY_TOOL_SET,
        ))
        catalog.register(ToolDefinition(
            tool_id="builtin.memory-explain.v1", name="memory_explain",
            description="Explain one stored memory and the session evidence supporting it.",
            input_schema=_object_schema({"memoryId": {"type": "string"}}, ("memoryId",)),
            handler=self._explain, audience_resource=MEMORY_TOOL_SET,
        ))
        catalog.register(ToolDefinition(
            tool_id="builtin.memory-remember-intent.v1", name="memory_remember_intent",
            description="Mark the user's current statement as an explicit remember request for post-session review.",
            input_schema=_object_schema({}, ()), handler=lambda _: ToolInvocationResult("context required"),
            context_handler=self._remember_intent, effect_class="write",
            audience_resource=MEMORY_TOOL_SET,
        ))
        catalog.register(ToolDefinition(
            tool_id="builtin.memory-prepare-correction.v1", name="memory_prepare_correction",
            description="Prepare a correction and return the exact old/new values for user confirmation.",
            input_schema=_object_schema({"memoryId": {"type": "string"},
                                         "newContent": {"type": "string", "maxLength": 4096}},
                                        ("memoryId", "newContent")),
            handler=lambda _: ToolInvocationResult("context required"),
            context_handler=self._prepare_correction, effect_class="write",
            audience_resource=MEMORY_TOOL_SET,
        ))
        catalog.register(ToolDefinition(
            tool_id="builtin.memory-prepare-forget.v1", name="memory_prepare_forget",
            description="Prepare forgetting one memory and return its exact content for user confirmation.",
            input_schema=_object_schema({"memoryId": {"type": "string"}}, ("memoryId",)),
            handler=lambda _: ToolInvocationResult("context required"),
            context_handler=self._prepare_forget, effect_class="delete",
            audience_resource=MEMORY_TOOL_SET,
        ))
        catalog.register(ToolDefinition(
            tool_id="builtin.memory-confirm-action.v1", name="memory_confirm_action",
            description="Apply a prepared memory correction or deletion only after a later user confirmation.",
            input_schema=_object_schema({"actionId": {"type": "string"}}, ("actionId",)),
            handler=lambda _: ToolInvocationResult("context required"),
            context_handler=self._confirm, effect_class="write",
            audience_resource=MEMORY_TOOL_SET,
        ))

    def _explain(self, arguments: dict[str, object]) -> ToolInvocationResult:
        memory_id = str(arguments.get("memoryId", "")).strip()
        memory = self._memories.domain_memory(memory_id)
        if memory is None:
            return _result({"found": False}, error=True)
        return _result({
            "found": True, "memoryId": memory.memory_id, "domain": memory.domain,
            "memoryType": memory.memory_type, "content": memory.content_text,
            "confidence": memory.confidence, "status": memory.status,
            "evidence": list(self._memories.evidence_for(memory_id)),
        })

    def _remember_intent(self, context: ToolInvocationContext,
                         _: dict[str, object]) -> ToolInvocationResult:
        if not context.voice_session_id or not context.user_utterance:
            return _result({"recorded": False, "reason": "voice_context_required"}, error=True)
        entry = self._sessions.append(
            session_id=context.voice_session_id, role="user",
            event_type="memory.intent.remember", text_content=context.user_utterance,
        )
        return _result({"recorded": True, "sessionId": entry.session_id,
                        "entryIndex": entry.entry_index})

    def _prepare_correction(self, context: ToolInvocationContext,
                            arguments: dict[str, object]) -> ToolInvocationResult:
        memory_id = str(arguments.get("memoryId", "")).strip()
        new_content = str(arguments.get("newContent", "")).strip()
        memory = self._memories.domain_memory(memory_id)
        if memory is None or not new_content:
            return _result({"prepared": False, "reason": "invalid_memory_or_content"}, error=True)
        action_id = self._memories.prepare_action(
            action_kind="correct", memory_id=memory_id, proposed_content=new_content,
            voice_session_id=context.voice_session_id,
            prepared_utterance_id=context.user_utterance_id,
        )
        return _result({"prepared": True, "actionId": action_id,
                        "oldContent": memory.content_text, "newContent": new_content,
                        "confirmationRequired": True})

    def _prepare_forget(self, context: ToolInvocationContext,
                        arguments: dict[str, object]) -> ToolInvocationResult:
        memory_id = str(arguments.get("memoryId", "")).strip()
        memory = self._memories.domain_memory(memory_id)
        if memory is None:
            return _result({"prepared": False, "reason": "memory_not_found"}, error=True)
        action_id = self._memories.prepare_action(
            action_kind="forget", memory_id=memory_id, proposed_content=None,
            voice_session_id=context.voice_session_id,
            prepared_utterance_id=context.user_utterance_id,
        )
        return _result({"prepared": True, "actionId": action_id,
                        "content": memory.content_text, "confirmationRequired": True})

    def _confirm(self, context: ToolInvocationContext,
                 arguments: dict[str, object]) -> ToolInvocationResult:
        action = self._memories.consume_action(
            action_id=str(arguments.get("actionId", "")).strip(),
            voice_session_id=context.voice_session_id,
            confirmation_utterance_id=context.user_utterance_id,
        )
        if action is None:
            return _result({"applied": False, "reason": "new_user_confirmation_required"}, error=True)
        memory_id = str(action["memoryId"])
        if action["actionKind"] == "forget":
            return _result({"applied": self._memories.delete_memory(memory_id),
                            "action": "forgotten", "memoryId": memory_id})
        current = self._memories.domain_memory(memory_id)
        if current is None:
            return _result({"applied": False, "reason": "memory_not_found"}, error=True)
        content = str(action["proposedContent"] or "").strip()
        updated = self._memories.reconcile_memory(
            session_id=context.voice_session_id or "voice-confirmation",
            subject_id=current.subject_id, domain=current.domain,
            memory_type=current.memory_type, memory_key=current.memory_key,
            content_text=content, confidence="high", sensitivity=current.sensitivity,
            intent="correct", reviewer_model="voice-confirmation",
            reviewer_contract_version=REVIEWER_CONTRACT_VERSION,
            evidence=((None, "explicit_memory_intent", "user_asserted",
                       context.user_utterance or "User confirmed correction."),),
        )
        return _result({"applied": True, "action": "corrected",
                        "memoryId": updated.memory_id, "content": updated.content_text})


def _object_schema(properties: dict[str, object], required: tuple[str, ...]) -> dict[str, object]:
    return {"type": "object", "properties": properties, "required": list(required),
            "additionalProperties": False}


def _result(value: dict[str, object], *, error: bool = False) -> ToolInvocationResult:
    return ToolInvocationResult(json.dumps(value, separators=(",", ":")), value, error)


def _match_payload(match: RetrievalMatch) -> dict[str, Any]:
    memory = match.memory
    return {
        "memoryClass": memory.memory_class,
        "domain": memory.domain,
        "memoryType": memory.memory_type,
        "memoryKey": memory.memory_key,
        "content": memory.content_text,
        "confidence": memory.confidence,
        "score": match.score,
        "matchMethods": list(match.match_methods),
        "validFrom": memory.valid_from,
        "validTo": memory.valid_to,
    }


def _coerce_limit(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return MAX_MEMORY_LOOKUP_RESULTS
    return max(1, min(parsed, MAX_MEMORY_LOOKUP_RESULTS))
