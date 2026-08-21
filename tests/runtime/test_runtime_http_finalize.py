from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from resono_runtime.agents import MemoryReviewRunner
from resono_runtime.api.events import RuntimeEventStream
from resono_runtime.api.http_server import RuntimeHttpServer
from resono_runtime.security.credentials import ProviderCredentials
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.storage.lifecycle_repository import LifecycleRepository
from resono_runtime.storage.memory import MemoryRepository
from resono_runtime.storage.provider_settings import ProviderSettingsRepository
from resono_runtime.storage.sessions import SessionTranscriptRepository
from resono_runtime.memory.pipeline import MemoryPipeline
from resono_runtime.memory.service import MemoryService


class _CredentialBridge:
    def __init__(self, value: str | None) -> None:
        self._value = value

    def hasOpenAiPlatformKey(self) -> bool:
        return self._value is not None

    def getOpenAiPlatformKey(self) -> str | None:
        return self._value

    def putOpenAiPlatformKey(self, value: str) -> None:
        self._value = value

    def deleteOpenAiPlatformKey(self) -> None:
        self._value = None

    def hasOpenAiSubscriptionTokens(self) -> bool:
        return False

    def getOpenAiSubscriptionTokens(self) -> str | None:
        return None

    def putOpenAiSubscriptionTokens(self, value: str) -> None:
        pass

    def deleteOpenAiSubscriptionTokens(self) -> None:
        pass


class _FakeEmbedder:
    model_key = "text-embedding-3-small"
    dimensions = 2

    def embed(self, _text: str) -> list[float]:
        return [0.1, 0.1]


def _fake_embedding_factory(_credentials: ProviderCredentials, _safety_source: str) -> _FakeEmbedder:
    return _FakeEmbedder()


class _FakeReviewExecutor:
    def __init__(self, summary: str) -> None:
        self._summary = summary

    def __call__(self, **_: object) -> str:  # noqa: ANN001
        return json.dumps({"summary": self._summary, "memories": []})


def _make_server(temp_dir: Path) -> RuntimeHttpServer:
    database = RuntimeDatabase(temp_dir / "runtime.sqlite3")
    database.migrate()

    events = RuntimeEventStream()
    lifecycle = LifecycleRepository(database)

    credentials = ProviderCredentials(_CredentialBridge("sk-test"))
    settings = ProviderSettingsRepository(database)
    settings.save(text_model="gpt-5.4-mini", realtime_model="gpt-realtime-2.1-mini")

    sessions = SessionTranscriptRepository(database)
    memories = MemoryRepository(database)

    reviewer = MemoryReviewRunner(
        credentials=credentials,
        settings=settings,
        events=events,
        local_api_token="t" * 43,
        executor=_FakeReviewExecutor("Session summary is persisted."),
    )
    pipeline = MemoryPipeline(
        sessions=sessions,
        memories=memories,
        reviewer=reviewer,
        credentials=credentials,
        safety_source="t" * 43,
        events=events,
        embedding_factory=_fake_embedding_factory,
    )
    memory = MemoryService(
        sessions=sessions,
        memories=memories,
        pipeline=pipeline,
        credentials=credentials,
        safety_source="t" * 43,
        embedding_factory=_fake_embedding_factory,
    )

    server = RuntimeHttpServer(
        host="127.0.0.1",
        port=0,
        token="t" * 43,
        health=lambda: {"contractVersion": 1, "status": "ready", "database": database.health()},
        lifecycle=lifecycle,
        events=events,
        sessions=sessions,
        memory=memory,
    )
    server.start()
    return server


class RuntimeVoiceFinalizeApiTest(unittest.TestCase):
    def test_finalize_endpoint_accepts_transcript_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            server = _make_server(Path(directory))
            try:
                base = f"http://127.0.0.1:{server.port}"
                headers = {"Authorization": "Bearer " + "t" * 43}
                payload = {
                    "sessionId": "session-001",
                    "entries": [
                        {
                            "role": "user",
                            "eventType": "conversation.item.input_audio_transcription.completed",
                            "text": "Hello from the mic.",
                        },
                        {
                            "role": "assistant",
                            "eventType": "response.audio_transcript.done",
                            "text": "Hi there, how can I help?",
                        },
                    ],
                }
                request = Request(
                    base + "/v1/voice/sessions/finalize",
                    data=json.dumps(payload).encode("utf-8"),
                    method="POST",
                    headers={**headers, "Content-Type": "application/json"},
                )
                with urlopen(request, timeout=2) as response:
                    self.assertEqual(200, response.status)
                    result = json.loads(response.read())
                self.assertEqual("session-001", result["sessionId"])
                self.assertEqual(0, result["memoryCount"])
                self.assertEqual("Session summary is persisted.", result["summary"])
            finally:
                server.stop()

    def test_finalize_endpoint_rejects_empty_transcript(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            server = _make_server(Path(directory))
            try:
                base = f"http://127.0.0.1:{server.port}"
                headers = {"Authorization": "Bearer " + "t" * 43}
                payload = {"sessionId": "session-001", "entries": []}
                request = Request(
                    base + "/v1/voice/sessions/finalize",
                    data=json.dumps(payload).encode("utf-8"),
                    method="POST",
                    headers={**headers, "Content-Type": "application/json"},
                )
                with self.assertRaises(HTTPError) as error:
                    with urlopen(request, timeout=2):
                        pass
                self.assertEqual(409, error.exception.code)
            finally:
                server.stop()


if __name__ == "__main__":
    unittest.main()
