from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..api.events import RuntimeEventStream
from ..providers.openai import OpenAIProviderError, openai_provider_access
from ..providers.openai.subscription import OpenAISubscription
from ..security.credentials import ProviderCredentials
from ..storage.provider_settings import ProviderSettingsRepository
from .sdk_runner import run_agent_turn_sync


ALLOWED_MEMORY_CLASSES = frozenset({"preference", "relationship", "environment"})
ALLOWED_CONFIDENCE = frozenset({"low", "medium", "high"})
ALLOWED_SENSITIVITY = frozenset({"normal", "sensitive"})

FINALIZATION_TRANSCRIPT_CHARACTER_LIMIT = 100_000
FINALIZATION_CANDIDATE_LIMIT = 32
FINALIZATION_CANDIDATE_CHARACTER_LIMIT = 4_096
FINALIZATION_SUMMARY_CHARACTER_LIMIT = 20_000
MEMORY_KEY_CHARACTER_LIMIT = 120

FORBIDDEN_MEMORY_MARKERS = (
    "api key",
    "credit card",
    "cvv",
    "password",
    "passcode",
    "private key",
    "secret key",
    "seed phrase",
    "social security",
    "ssn",
)


@dataclass(frozen=True, slots=True)
class MemoryCandidate:
    memory_class: str
    memory_key: str
    content_text: str
    confidence: str
    sensitivity: str


@dataclass(frozen=True, slots=True)
class ReviewResult:
    summary: str
    memories: tuple[MemoryCandidate, ...]
    model: str


ReviewExecutor = Callable[..., str]


class MemoryReviewRunner:
    """Single Agents SDK runner that reviews a transcript into a summary plus memories.

    Reuses the existing credential, access-path, and model selection, and the donor's
    exact memory-summary contract: instruction text, JSON payload parsing (with
    fenced-code-block stripping), allowed memory classes/confidence/sensitivity,
    shouldStore gating, forbidden-secret rejection, and donor character limits.
    No parallel agent loop and no MCP tools: review is summarization and extraction.
    """

    def __init__(
        self,
        *,
        credentials: ProviderCredentials,
        settings: ProviderSettingsRepository,
        events: RuntimeEventStream,
        local_api_token: str,
        subscription: OpenAISubscription | None = None,
        executor: ReviewExecutor | None = None,
    ) -> None:
        self._credentials = credentials
        self._settings = settings
        self._events = events
        self._local_api_token = local_api_token
        self._subscription = subscription
        self._executor = executor or _run_review_with_agents_sdk

    def review(self, transcript: str) -> ReviewResult:
        text = transcript.strip()
        if not text:
            raise OpenAIProviderError(
                "invalid_transcript", "A transcript is required for review.", status=400
            )
        transcript_text = text[:FINALIZATION_TRANSCRIPT_CHARACTER_LIMIT]
        selection = self._settings.selection()
        access = openai_provider_access(
            credentials=self._credentials,
            settings=self._settings,
            subscription=self._subscription,
        )
        api_key = access.api_key
        base_url = access.base_url
        model = selection.text_model
        if not model:
            raise OpenAIProviderError("model_required", "Choose a text model first.", status=409)

        self._events.publish("memory.review.started", {"provider": "openai", "model": model})
        try:
            raw = self._executor(
                api_key=api_key,
                model=model,
                transcript=transcript_text,
                local_api_token=self._local_api_token,
                base_url=base_url,
                reasoning_effort=selection.reasoning_effort,
            )
        except OpenAIProviderError:
            raise
        except Exception as error:
            failure = _review_failure(error)
            self._events.publish(
                "memory.review.failed",
                {"provider": "openai", "model": model, "reason": failure.code},
            )
            raise failure from error

        result = _parse_review(raw, model)
        self._events.publish(
            "memory.review.completed",
            {"provider": "openai", "model": model, "memoryCount": len(result.memories)},
        )
        return result


def _review_failure(error: Exception) -> OpenAIProviderError:
    """Map an executor failure to a truthful provider error.

    A provider 429 / usage-limit rejection is surfaced distinctly (with the
    reset hint when the provider body carries one) so logs and the finalize
    response say *why* the review could not run instead of collapsing every
    failure into a generic 502.
    """
    message = str(error)
    status_code = getattr(error, "status_code", None)
    if status_code == 429 or "usage_limit_reached" in message:
        reset_hint = ""
        reset_match = re.search(r"resets_in_seconds[\"']?\s*:\s*(\d+)", message)
        if reset_match:
            hours = int(reset_match.group(1)) / 3600
            reset_hint = f" Resets in about {hours:.1f} hours."
        return OpenAIProviderError(
            "usage_limit_reached",
            f"The OpenAI usage limit has been reached.{reset_hint}",
            status=429,
        )
    return OpenAIProviderError(
        "review_failed", "The review agent could not complete this review.", status=502
    )


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


def _parse_summary_payload(output_text: str | None) -> dict[str, Any]:
    if output_text is None:
        return {"summary": None, "memories": []}
    cleaned = output_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
        cleaned = cleaned.strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return {"summary": cleaned, "memories": []}
    if not isinstance(parsed, dict):
        return {"summary": cleaned, "memories": []}
    parsed.setdefault("memories", [])
    return parsed


def _parse_review(output_text: str, model: str) -> ReviewResult:
    parsed = _parse_summary_payload(output_text)
    summary_text = _bounded_normalized_text(
        parsed.get("summary"), max_characters=FINALIZATION_SUMMARY_CHARACTER_LIMIT
    ) or _bounded_normalized_text(
        (output_text or "").strip(), max_characters=FINALIZATION_SUMMARY_CHARACTER_LIMIT
    )
    if not summary_text:
        raise OpenAIProviderError("review_empty", "The review agent returned no summary.", status=502)
    raw_candidates = parsed.get("memories")
    if raw_candidates is None:
        raw_candidates = []
    if not isinstance(raw_candidates, list):
        raise OpenAIProviderError(
            "review_malformed", "The review memories must be a list.", status=502
        )
    memories: list[MemoryCandidate] = []
    for raw_candidate in raw_candidates[:FINALIZATION_CANDIDATE_LIMIT]:
        candidate = _normalize_finalization_candidate(raw_candidate)
        if candidate is None:
            continue
        if _contains_forbidden_memory_marker(candidate.content_text):
            continue
        memories.append(candidate)
    return ReviewResult(summary=summary_text, memories=tuple(memories), model=model)


def _normalize_finalization_candidate(value: object) -> MemoryCandidate | None:
    if not isinstance(value, dict) or not value.get("shouldStore", True):
        return None
    memory_class = _normalize_memory_class(value.get("memoryClass"))
    memory_key = _normalize_memory_key(value.get("memoryKey"))
    content_text = _bounded_normalized_text(
        value.get("content"), max_characters=FINALIZATION_CANDIDATE_CHARACTER_LIMIT
    )
    if memory_class is None or memory_key is None or content_text is None:
        return None
    return MemoryCandidate(
        memory_class=memory_class,
        memory_key=memory_key,
        content_text=content_text,
        confidence=_normalize_confidence(value.get("confidence")),
        sensitivity=_normalize_sensitivity(value.get("sensitivity")),
    )


def _normalize_memory_class(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized if normalized in ALLOWED_MEMORY_CLASSES else None


def _normalize_memory_key(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = re.sub(r"[^a-z0-9._-]+", "-", value.strip().lower()).strip("-")
    if not normalized or len(normalized) > MEMORY_KEY_CHARACTER_LIMIT:
        return None
    return normalized


def _normalize_confidence(value: Any) -> str:
    if not isinstance(value, str):
        return "medium"
    normalized = value.strip().lower()
    return normalized if normalized in ALLOWED_CONFIDENCE else "medium"


def _normalize_sensitivity(value: Any) -> str:
    if not isinstance(value, str):
        return "normal"
    normalized = value.strip().lower()
    return normalized if normalized in ALLOWED_SENSITIVITY else "normal"


def _normalize_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _bounded_normalized_text(value: Any, *, max_characters: int) -> str | None:
    normalized = _normalize_text(value)
    if normalized is None:
        return None
    return normalized[:max_characters]


def _contains_forbidden_memory_marker(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in FORBIDDEN_MEMORY_MARKERS)


def _run_review_with_agents_sdk(
    *,
    api_key: str,
    model: str,
    transcript: str,
    local_api_token: str,
    base_url: str | None,
    reasoning_effort: str,
) -> str:
    return run_agent_turn_sync(
        api_key=api_key,
        model=model,
        instructions=_summarizer_instructions(),
        input_text=transcript,
        base_url=base_url,
        reasoning_effort=reasoning_effort,
        max_turns=4,
        agent_name="ReSono R1 Memory Review",
    )
