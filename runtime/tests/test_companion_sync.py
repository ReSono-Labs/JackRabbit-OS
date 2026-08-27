import json
import tempfile
import unittest
from pathlib import Path

from resono_runtime.companion_sync import CompanionSync


class FakeRepository:
    def __init__(self, tasks):
        self.tasks = list(tasks)
        self.added = []

    def list(self):
        return [type("T", (), {"task_id": t["taskId"], "text": t["text"], "status": "open"})
                for t in self.tasks]

    def add_synced(self, text):
        if not text.strip():
            raise ValueError("text is required.")
        self.added.append(text)
        self.tasks.append({"taskId": f"t{len(self.added)}", "text": text})
        return type("T", (), {"task_id": f"t{len(self.added)}", "text": text, "status": "open"})


class FakeTransport:
    def __init__(self, responses):
        self.responses = dict(responses)
        self.calls = []

    def __call__(self, method, url, body, token):
        key = (method, url.rsplit("/", 1)[-1])
        self.calls.append((method, url, body, token))
        status, payload = self.responses.get(key, (0, {}))
        return status, payload


class CompanionSyncTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self._tmp = Path(tmp.name)

    def _settings_path(self, url, token="secret"):
        path = self._tmp / "companion.json"
        path.write_text(json.dumps({"url": url, "token": token}))
        return path

    def test_disabled_without_settings(self):
        transport = FakeTransport({})
        sync = CompanionSync(FakeRepository([]),
                             settings_path=self._settings_path("", ""),
                             transport=transport, logger=lambda *a, **k: None)
        self.assertFalse(sync.sync_once())
        self.assertEqual([], transport.calls)

    def test_rejects_non_https(self):
        transport = FakeTransport({})
        sync = CompanionSync(FakeRepository([]),
                             settings_path=self._settings_path("http://example.com"),
                             transport=transport, logger=lambda *a, **k: None)
        self.assertFalse(sync.sync_once())
        self.assertEqual([], transport.calls)

    def test_missing_settings_file_is_disabled(self):
        transport = FakeTransport({})
        sync = CompanionSync(FakeRepository([]),
                             settings_path=self._tmp / "missing.json",
                             transport=transport, logger=lambda *a, **k: None)
        self.assertFalse(sync.sync_once())

    def test_full_cycle_push_pull_ack(self):
        repo = FakeRepository([{"taskId": "a1", "text": "existing"}])
        transport = FakeTransport({
            ("POST", "push"): (200, {}),
            ("POST", "pull"): (200, {"additions": [
                {"id": "c1", "text": "buy milk"},
                {"id": "c2", "text": ""},
                {"id": "c3", "text": "valid one"},
            ]}),
            ("POST", "ack"): (200, {}),
        })
        sync = CompanionSync(repo,
                             settings_path=self._settings_path("https://comp.example"),
                             transport=transport, logger=lambda *a, **k: None)
        self.assertTrue(sync.sync_once())

        push = next(c for c in transport.calls if c[1].endswith("/push"))
        self.assertEqual([{"taskId": "a1", "text": "existing", "status": "open"}],
                         push[2]["tasks"])
        self.assertEqual("secret", push[3])

        ack = next(c for c in transport.calls if c[1].endswith("/ack"))
        self.assertEqual(["c1", "c2", "c3"], ack[2]["ids"])
        self.assertEqual(["buy milk", "valid one"], repo.added)


if __name__ == "__main__":
    unittest.main()
