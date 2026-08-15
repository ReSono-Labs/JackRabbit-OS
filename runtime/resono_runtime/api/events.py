from __future__ import annotations

from dataclasses import dataclass
import json
import queue
import threading
import time


@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    sequence: int
    event_type: str
    payload: dict[str, object]

    def sse_bytes(self) -> bytes:
        body = json.dumps(
            {"sequence": self.sequence, "type": self.event_type, "payload": self.payload},
            separators=(",", ":"),
        )
        return f"id: {self.sequence}\nevent: {self.event_type}\ndata: {body}\n\n".encode()


class RuntimeEventStream:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sequence = 0
        self._latest = RuntimeEvent(0, "runtime.starting", {"status": "starting"})
        self._subscribers: set[queue.Queue[RuntimeEvent]] = set()

    def publish(self, event_type: str, payload: dict[str, object]) -> RuntimeEvent:
        with self._lock:
            self._sequence += 1
            event = RuntimeEvent(self._sequence, event_type, dict(payload))
            self._latest = event
            subscribers = tuple(self._subscribers)
        for subscriber in subscribers:
            try:
                subscriber.put_nowait(event)
            except queue.Full:
                pass
        return event

    def subscribe(self) -> tuple[RuntimeEvent, queue.Queue[RuntimeEvent]]:
        subscriber: queue.Queue[RuntimeEvent] = queue.Queue(maxsize=16)
        with self._lock:
            self._subscribers.add(subscriber)
            latest = self._latest
        return latest, subscriber

    def unsubscribe(self, subscriber: queue.Queue[RuntimeEvent]) -> None:
        with self._lock:
            self._subscribers.discard(subscriber)

    @staticmethod
    def next_event(subscriber: queue.Queue[RuntimeEvent], timeout: float = 15.0) -> RuntimeEvent | None:
        try:
            return subscriber.get(timeout=timeout)
        except queue.Empty:
            return None
