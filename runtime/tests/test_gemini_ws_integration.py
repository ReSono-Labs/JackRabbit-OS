"""Slice 3 — real WebSocket round-trip against the fake Gemini server."""

from __future__ import annotations

import asyncio
import base64
import json

import pytest
import websockets

from resono_runtime.providers.gemini.live import (
    build_setup,
    parse_server_message,
    realtime_audio_frame,
    tool_response,
)

from .fake_gemini_ws_server import FakeGeminiWsServer


@pytest.fixture
def server():
    instance = FakeGeminiWsServer()
    instance.start()
    yield instance
    instance.stop()


def test_websocket_setup_audio_and_tool_round_trip(server):
    async def run():
        async with websockets.connect(server.url, max_size=2_000_000) as socket:
            setup = build_setup(model="gemini-3.1-flash-live-preview", instructions="Be terse.")
            await socket.send(json.dumps(setup))
            first = parse_server_message(json.loads(await socket.recv()))
            assert first["type"] == "setup_complete"

            audio = base64.b64encode(b"\x00" * 320).decode()
            await socket.send(json.dumps(realtime_audio_frame(audio)))
            turn = parse_server_message(json.loads(await socket.recv()))
            assert turn["type"] == "turn_complete"
            assert turn["text"] == "echo:audio-received"

            await socket.send(json.dumps(tool_response("f1", "get_device_status", {"ok": True})))
            tool_turn = parse_server_message(json.loads(await socket.recv()))
            assert tool_turn["text"] == "echo:tool-result"

    asyncio.run(run())
    assert len(server.frames) == 3

