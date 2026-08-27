"""Slice 3 — Gemini Live adapter semantics (TDD, pure protocol shapes)."""

from __future__ import annotations

import base64

from resono_runtime.providers.gemini.live import (
    AUDIO_IN_MIME,
    AUDIO_OUT_MIME,
    LIVE_SERVICE_PATH,
    audio_stream_end,
    build_setup,
    function_declarations,
    parse_server_message,
    realtime_audio_frame,
    session_url,
    tool_response,
)


def test_session_url_embeds_key_and_service_path():
    url = session_url("gk-secret")
    assert url.startswith("wss://generativelanguage.googleapis.com" + LIVE_SERVICE_PATH + "?")
    assert "key=gk-secret" in url


def test_session_url_requires_key():
    try:
        session_url("  ")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_build_setup_shape_with_tools_and_instructions():
    setup = build_setup(
        model="gemini-3.1-flash-live-preview",
        instructions="You are terse.",
        tool_definitions=(
            {"name": "get_device_status", "description": "Device snapshot.", "input_schema": {"type": "object", "properties": {}, "required": []}},
        ),
    )
    inner = setup["setup"]
    assert inner["model"] == "gemini-3.1-flash-live-preview"
    assert inner["generationConfig"]["responseModalities"] == ["AUDIO"]
    assert inner["systemInstruction"]["parts"][0]["text"] == "You are terse."
    assert inner["tools"][0]["functionDeclarations"][0]["name"] == "get_device_status"
    assert inner["tools"][0]["functionDeclarations"][0]["parameters"]["type"] == "object"


def test_build_setup_client_vad_adds_audio_vad_config():
    setup = build_setup(model="m", instructions="", vad="CLIENT_AUTOMATIC")
    speech = setup["setup"]["generationConfig"]["speechConfig"]
    assert speech["audioVad"]["useClientImprovedAudioVad"] is True


def test_function_declarations_dedupes_and_skips_empty():
    declarations = function_declarations((
        {"name": "a", "description": "A", "input_schema": {"type": "object"}},
        {"name": "a", "description": "dup", "input_schema": {"type": "object"}},
        {"name": "b", "description": "", "input_schema": {}},
    ))
    assert [d["name"] for d in declarations] == ["a", "b"]
    assert "parameters" not in declarations[1]


def test_client_frame_builders():
    frame = realtime_audio_frame(base64.b64encode(b"x" * 16).decode())
    assert frame["realtimeInput"]["mediaChunks"][0]["mimeType"] == AUDIO_IN_MIME
    assert audio_stream_end() == {"realtimeInput": {"audioStreamEnd": True}}
    response = tool_response("id-1", "get_device_status", {"ok": True})
    assert response["toolResponse"]["functionResponses"][0]["name"] == "get_device_status"


def test_parse_server_message_events():
    assert parse_server_message({"setupComplete": {}})["type"] == "setup_complete"

    partial = parse_server_message({
        "serverContent": {
            "modelTurn": {
                "parts": [
                    {"text": "hello"},
                    {"inlineData": {"mimeType": AUDIO_OUT_MIME, "data": "AAAA"}},
                ]
            },
            "turnComplete": False,
        }
    })
    assert partial["type"] == "turn_partial"
    assert partial["text"] == "hello"
    assert partial["audio"][0]["mimeType"] == AUDIO_OUT_MIME

    complete = parse_server_message({
        "serverContent": {"modelTurn": {"parts": []}, "turnComplete": True}
    })
    assert complete["type"] == "turn_complete"

    interrupted = parse_server_message({
        "serverContent": {"modelTurn": {"parts": []}, "interrupted": True}
    })
    assert interrupted["type"] == "interrupted"

    call = parse_server_message({
        "serverContent": {
            "modelTurn": {"parts": [{"functionCall": {"id": "f1", "name": "x", "args": {"a": 1}}}]},
            "turnComplete": True,
        }
    })
    assert call["function_calls"] == [{"id": "f1", "name": "x", "args": {"a": 1}}]

    away = parse_server_message({"goAway": {"reason": "SESSION_EXPIRING", "timeLeft": "00:02:00"}})
    assert away["type"] == "go_away" and away["reason"] == "SESSION_EXPIRING"

    error = parse_server_message({"error": {"code": 429, "message": "quota"}})
    assert error["type"] == "error" and error["code"] == "429"
