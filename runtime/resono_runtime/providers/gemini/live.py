"""Gemini Live (WebSocket realtime voice) session semantics for slice 3.

The runtime does not own the audio socket — the native Android voice peer does.
This module owns the parts the runtime must build and understand:

- the WebSocket URL (BidiGenerateContent) and auth posture
- the setup message (model, voice, system instruction, tools -> functionDeclarations,
  VAD mode, audio formats)
- client frame builders (realtime audio input, audioStreamEnd, tool responses)
- server frame parsing into normalized events

Protocol reference: Google Generative Language API, BidiGenerateContent
(generativelanguage.googleapis.com); verified 2026-08-26.
"""

from __future__ import annotations

from urllib.parse import urlencode

LIVE_SERVICE_PATH = (
    "/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
)
AUDIO_IN_MIME = "audio/pcm;rate=16000"
AUDIO_OUT_MIME = "audio/pcm;rate=24000"

_DEFAULT_VOICE = "Kore"


def session_url(api_key: str) -> str:
    """WebSocket URL for an API-key-authenticated Live session."""
    if not api_key or not api_key.strip():
        raise ValueError("Gemini API key is required.")
    return (
        "wss://generativelanguage.googleapis.com"
        + LIVE_SERVICE_PATH
        + "?"
        + urlencode({"key": api_key.strip()})
    )


def build_setup(
    *,
    model: str,
    instructions: str,
    voice: str = _DEFAULT_VOICE,
    tool_definitions: tuple[dict[str, object], ...] = (),
    vad: str = "SERVER_AUTOMATIC",
) -> dict[str, object]:
    """The first client message, wire-shaped: ``{"setup": {...}}`` (tools map to functionDeclarations)."""
    if not model:
        raise ValueError("model is required.")
    if vad not in ("SERVER_AUTOMATIC", "CLIENT_AUTOMATIC"):
        raise ValueError("vad must be SERVER_AUTOMATIC or CLIENT_AUTOMATIC.")
    speech_config: dict[str, object] = {
        "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}},
    }
    if vad == "CLIENT_AUTOMATIC":
        speech_config["audioVad"] = {"useClientImprovedAudioVad": True}
    setup: dict[str, object] = {
        # BidiGenerateContent requires the "models/" resource prefix.
        "model": model if model.startswith("models/") else f"models/{model}",
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": speech_config,
        },
        "systemInstruction": {"parts": [{"text": instructions}]} if instructions else None,
    }
    declarations = function_declarations(tool_definitions)
    if declarations:
        setup["tools"] = [{"functionDeclarations": declarations}]
    return {"setup": setup}


def function_declarations(tool_definitions: tuple[dict[str, object], ...]) -> list[dict[str, object]]:
    """Map normalized tool definitions (name/description/input_schema) to Gemini functionDeclarations."""
    declarations: list[dict[str, object]] = []
    seen: set[str] = set()
    for tool in tool_definitions:
        name = tool.get("name")
        if not isinstance(name, str) or not name:
            continue
        if name in seen:
            continue
        seen.add(name)
        declaration: dict[str, object] = {"name": name}
        description = tool.get("description")
        if isinstance(description, str) and description.strip():
            declaration["description"] = description.strip()[:1024]
        schema = tool.get("input_schema")
        if isinstance(schema, dict) and schema.get("type"):
            declaration["parameters"] = schema
        declarations.append(declaration)
    return declarations


def realtime_audio_frame(chunk_b64: str, *, mime: str = AUDIO_IN_MIME) -> dict[str, object]:
    """One realtime audio input frame (Blob shape; mediaChunks is deprecated)."""
    return {
        "realtimeInput": {
            "audio": {"mimeType": mime, "data": chunk_b64}
        }
    }


def audio_stream_end() -> dict[str, object]:
    return {"realtimeInput": {"audioStreamEnd": True}}


def realtime_text_frame(text: str) -> dict[str, object]:
    """Text input over the live channel (real-time text stream)."""
    return {"realtimeInput": {"text": text}}


def tool_response(function_id: str, name: str, response: object) -> dict[str, object]:
    return {
        "toolResponse": {
            "functionResponses": [{"id": function_id, "name": name, "response": response or {}}]
        }
    }


def parse_server_message(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one server frame into a small event vocabulary used by the native peer contract."""
    if not isinstance(payload, dict):
        return {"type": "invalid"}
    if "setupComplete" in payload:
        return {"type": "setup_complete"}
    if "serverContent" in payload:
        content = payload["serverContent"]
        if not isinstance(content, dict):
            return {"type": "invalid"}
        model_turn = content.get("modelTurn")
        parts = model_turn.get("parts", []) if isinstance(model_turn, dict) else []
        if not isinstance(parts, list):
            parts = []
        audio: list[dict[str, str]] = []
        text_parts: list[str] = []
        calls: list[dict[str, object]] = []
        for part in parts:
            if not isinstance(part, dict):
                continue
            inline = part.get("inlineData")
            if isinstance(inline, dict) and isinstance(inline.get("data"), str):
                audio.append({
                    "mimeType": str(inline.get("mimeType") or AUDIO_OUT_MIME),
                    "data": inline["data"],
                })
            if isinstance(part.get("text"), str) and part["text"]:
                text_parts.append(part["text"])
            function_call = part.get("functionCall")
            if isinstance(function_call, dict):
                calls.append({
                    "id": str(function_call.get("id") or ""),
                    "name": str(function_call.get("name") or ""),
                    "args": function_call.get("args") if isinstance(function_call.get("args"), dict) else {},
                })
        interrupted = content.get("interrupted") is True
        turn_complete = content.get("turnComplete") is True
        if interrupted:
            event_type = "interrupted"
        elif turn_complete:
            event_type = "turn_complete"
        else:
            event_type = "turn_partial"
        return {
            "type": event_type,
            "audio": audio,
            "text": "\n".join(text_parts),
            "function_calls": calls,
            "grounding": isinstance(content.get("groundingMetadata"), dict),
        }
    if "sessionResumptionUpdate" in payload:
        details = payload["sessionResumptionUpdate"]
        return {
            "type": "session_resumption",
            "handle": str(details.get("newHandle")) if isinstance(details, dict) else "",
            "resumable": bool(details.get("resumable", False)) if isinstance(details, dict) else False,
        }
    if "goAway" in payload:
        details = payload["goAway"]
        return {
            "type": "go_away",
            "reason": str(details.get("reason")) if isinstance(details, dict) else "",
            "time_left": str(details.get("timeLeft")) if isinstance(details, dict) else "",
        }
    if "error" in payload:
        error = payload["error"]
        return {
            "type": "error",
            "code": str(error.get("code")) if isinstance(error, dict) else "",
            "message": str(error.get("message")) if isinstance(error, dict) else str(error),
        }
    return {"type": "unknown"}
