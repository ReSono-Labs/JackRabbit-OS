from __future__ import annotations

import json

from ..storage.sessions import SessionTranscriptRepository
from ..tools.definitions import ToolInvocationContext, ToolInvocationResult


class VoiceToolEvidenceRecorder:
    """Persists bounded tool evidence for post-session memory review."""

    def __init__(self, sessions: SessionTranscriptRepository) -> None:
        self._sessions = sessions

    def __call__(self, context: ToolInvocationContext, name: str,
                 arguments: dict[str, object], result: ToolInvocationResult) -> None:
        if not context.voice_session_id:
            return
        payload = json.dumps({
            "tool": name,
            "arguments": _redact(arguments),
            "result": _redact(
                result.structured_content if result.structured_content is not None else result.text
            ),
            "isError": result.is_error,
        }, separators=(",", ":"), ensure_ascii=True)
        self._sessions.append(
            session_id=context.voice_session_id,
            role="tool",
            event_type=f"tool.{name}.{'failed' if result.is_error else 'completed'}",
            text_content=payload[:16_384],
        )


_SECRET_KEYS = frozenset({
    "password", "passcode", "secret", "token", "api_key", "apikey", "authorization",
    "credential", "private_key", "seed_phrase", "cvv",
})


def _redact(value: object) -> object:
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if str(key).lower() in _SECRET_KEYS else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return [_redact(item) for item in value]
    return value
