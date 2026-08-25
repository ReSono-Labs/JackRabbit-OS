from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from typing import Callable, Protocol

from .core.logging import runtime_logger


class _TaskRepositoryLike(Protocol):
    def list(self) -> tuple: ...

    def add_synced(self, text: str): ...


class _Transport(Protocol):
    def __call__(self, method: str, url: str, body: dict[str, object] | None,
                 token: str) -> tuple[int, dict[str, object]]: ...


def _urllib_transport(method: str, url: str, body: dict[str, object] | None,
                      token: str) -> tuple[int, dict[str, object]]:
    request = urllib.request.Request(
        url,
        data=None if body is None else json.dumps(body).encode(),
        method=method,
        headers={
            "Content-Type": "application/json",
            "X-Companion-Token": token,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read(262_144)
            payload = json.loads(raw.decode()) if raw else {}
            return int(response.status), payload if isinstance(payload, dict) else {}
    except urllib.error.HTTPError as error:
        return int(error.code), {}
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return 0, {}


class CompanionSync:
    """Bidirectional Tasks sync with the companion server over outbound HTTP.

    The device only ever makes outbound requests; the companion server queues
    additions and mirrors the open-task snapshot so its own tools (e.g. an
    OpenAI connector) can read and extend the list.
    """

    def __init__(self, repository: _TaskRepositoryLike, *, settings_path,
                 logger=None, transport: _Transport | None = None,
                 interval_seconds: float = 60.0) -> None:
        self._repository = repository
        self._settings_path = settings_path
        self._log = logger or runtime_logger()
        self._transport: _Transport = transport or _urllib_transport
        self._interval = max(15.0, float(interval_seconds))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="resono-companion-sync", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._thread = None

    def _settings(self) -> tuple[str, str]:
        try:
            payload = json.loads(self._settings_path.read_text())
            url = str(payload.get("url", "")).strip().rstrip("/")
            token = str(payload.get("token", "")).strip()
            if url.startswith("https://") and token:
                return url, token
        except (OSError, json.JSONDecodeError):
            pass
        return "", ""

    def sync_once(self) -> bool:
        base_url, token = self._settings()
        if not base_url:
            return False
        tasks = [{"taskId": item.task_id, "text": item.text, "status": item.status}
                 for item in self._repository.list()]
        status, _ = self._transport("POST", f"{base_url}/tasks/sync/push", {"tasks": tasks}, token)
        if status != 200:
            return False
        status, payload = self._transport("POST", f"{base_url}/tasks/sync/pull", {}, token)
        if status != 200:
            return False
        additions = payload.get("additions")
        if not isinstance(additions, list):
            return True
        done: list[str] = []
        for addition in additions:
            if not isinstance(addition, dict):
                continue
            text = str(addition.get("text", "")).strip()
            client_id = str(addition.get("id", "")).strip()
            if not text or not client_id or len(text) > 500:
                done.append(client_id)
                continue
            try:
                task = self._repository.add_synced(text)
                if task is not None:
                    done.append(client_id)
            except ValueError:
                done.append(client_id)
        if done:
            self._transport("POST", f"{base_url}/tasks/sync/ack", {"ids": done}, token)
        return True

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.sync_once()
            except Exception:  # noqa: BLE001 — a bad cycle must never kill the thread
                pass
            self._stop.wait(self._interval)
