"""In-process fake Gemini BidiGenerateContent WebSocket server (websockets 16)."""

from __future__ import annotations

import asyncio
import json
import threading
import time

import websockets


class FakeGeminiWsServer:
    """Minimal Live-protocol server: setup -> setupComplete; realtimeInput -> echo turn."""

    def __init__(self) -> None:
        self.frames: list[dict] = []
        self._loop: asyncio.AbstractEventLoop | None = None
        self._server = None
        self.port = 0

    def start(self) -> None:
        self._loop = asyncio.new_event_loop()
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()
        for _ in range(100):
            if self.port:
                return
            time.sleep(0.02)
        raise RuntimeError("fake ws server did not start")

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)

        async def handler(socket) -> None:
            async for raw in socket:
                try:
                    message = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                self.frames.append(message)
                if "setup" in message:
                    await socket.send(json.dumps({"setupComplete": {}}))
                elif "realtimeInput" in message:
                    await socket.send(json.dumps({
                        "serverContent": {
                            "modelTurn": {
                                "parts": [{"text": "echo:audio-received"}],
                                "groundingMetadata": {},
                            },
                            "turnComplete": True,
                        }
                    }))
                elif "toolResponse" in message:
                    await socket.send(json.dumps({
                        "serverContent": {
                            "modelTurn": {"parts": [{"text": "echo:tool-result"}]},
                            "turnComplete": True,
                        }
                    }))

        async def main() -> None:
            self._server = await websockets.serve(handler, "127.0.0.1", 0, max_size=2_000_000)
            self.port = self._server.sockets[0].getsockname()[1]

        self._loop.run_until_complete(main())
        self._loop.run_forever()

    def stop(self) -> None:
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._server is not None:
            time.sleep(0.05)

    @property
    def url(self) -> str:
        return f"ws://127.0.0.1:{self.port}"
