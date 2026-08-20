from __future__ import annotations

from datetime import UTC, datetime
import threading

from .repository import CalendarRepository
from .service import CalendarService


class CalendarSyncScheduler:
    def __init__(self, repository: CalendarRepository, service: CalendarService) -> None:
        self._repository = repository
        self._service = service
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None: return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="resono-calendar-sync", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None: self._thread.join(timeout=5)
        self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            for account in self._repository.due_accounts(datetime.now(UTC).isoformat()):
                if self._stop.is_set(): return
                try: self._service.sync(account.configuration.account_id)
                except Exception: pass
            self._stop.wait(15)
