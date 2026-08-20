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
        if api_key is None:
            return json.dumps(
                {"matches": [], "embeddingsAvailable": False, "reason": "connect_openai"}
            )
        limit = _coerce_limit(arguments.get("limit"))
        try:
            embedder = self._embedding_factory(api_key, self._safety_source)
        except EmbeddingUnavailable:
            return json.dumps(
                {"matches": [], "embeddingsAvailable": False, "reason": "embedding_provider_unavailable"}
            )
        retriever = MemoryRetriever(memories=self._memories, embedder=embedder)
        try:
            matches = retriever.retrieve(query, limit=limit)
        except EmbeddingUnavailable:
            return json.dumps(
                {"matches": [], "embeddingsAvailable": False, "reason": "embedding_provider_unavailable"}
            )
        return json.dumps(
            {
                "matches": [_match_payload(match) for match in matches[:MAX_MEMORY_LOOKUP_RESULTS]],
                "matchCount": len(matches),
                "embeddingsAvailable": True,
            }
        )


def _match_payload(match: RetrievalMatch) -> dict[str, Any]:
    memory = match.memory
    return {
        "memoryClass": memory.memory_class,
        "memoryKey": memory.memory_key,
        "content": memory.content_text,
        "confidence": memory.confidence,
        "score": match.score,
    }


def _coerce_limit(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return MAX_MEMORY_LOOKUP_RESULTS
    return max(1, min(parsed, MAX_MEMORY_LOOKUP_RESULTS))
