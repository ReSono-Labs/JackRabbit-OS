from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re


RELEASE_ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}")


@dataclass(frozen=True, slots=True)
class RuntimeRelease:
    release_id: str
    contract_version: int


class ReleaseSupervisor:
    def __init__(self, releases_path: Path) -> None:
        self._root = releases_path
        self._active = releases_path / "active.json"
        self._last_good = releases_path / "last-good.json"
        self._status = releases_path / "activation-status.json"

    def prepare(self) -> RuntimeRelease:
        self._root.mkdir(parents=True, exist_ok=True)
        if not self._last_good.is_file():
            baseline = RuntimeRelease("embedded-0.3.0", 1)
            self._write_pointer(self._last_good, baseline)
            self._write_pointer(self._active, baseline)
            self._write_status("ready", baseline.release_id)
            return baseline
        last_good = self._read_pointer(self._last_good)
        try:
            active = self._read_pointer(self._active) if self._active.is_file() else None
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            active = None
        if active != last_good:
            self._write_pointer(self._active, last_good)
            self._write_status("rolled_back", last_good.release_id)
        return last_good

    def active(self) -> RuntimeRelease:
        return self._read_pointer(self._active)

    def activate(
        self,
        candidate: RuntimeRelease,
        health_check: Callable[[RuntimeRelease], bool],
    ) -> bool:
        self._validate(candidate)
        previous = self._read_pointer(self._last_good)
        self._write_pointer(self._active, candidate)
        try:
            healthy = bool(health_check(candidate))
        except Exception:
            healthy = False
        if not healthy:
            self._write_pointer(self._active, previous)
            self._write_status("rolled_back", previous.release_id)
            return False
        self._write_pointer(self._last_good, candidate)
        self._write_status("ready", candidate.release_id)
        return True

    def _read_pointer(self, path: Path) -> RuntimeRelease:
        payload = json.loads(path.read_text(encoding="utf-8"))
        release = RuntimeRelease(
            release_id=str(payload["releaseId"]),
            contract_version=int(payload["contractVersion"]),
        )
        self._validate(release)
        return release

    def _write_pointer(self, path: Path, release: RuntimeRelease) -> None:
        self._validate(release)
        self._atomic_json(
            path,
            {"releaseId": release.release_id, "contractVersion": release.contract_version},
        )

    def _write_status(self, status: str, release_id: str) -> None:
        self._atomic_json(self._status, {"status": status, "releaseId": release_id})

    @staticmethod
    def _validate(release: RuntimeRelease) -> None:
        if not RELEASE_ID.fullmatch(release.release_id):
            raise ValueError("runtime release identifier is invalid")
        if release.contract_version != 1:
            raise ValueError("runtime release contract is unsupported")

    @staticmethod
    def _atomic_json(path: Path, payload: dict[str, object]) -> None:
        temporary = path.with_name(path.name + ".next")
        with temporary.open("w", encoding="utf-8") as output:
            json.dump(payload, output, separators=(",", ":"), sort_keys=True)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
