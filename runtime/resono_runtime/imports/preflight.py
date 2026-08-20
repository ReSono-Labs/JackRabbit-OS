"""Exact-state confirmation tokens shared by every importable product type."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import secrets
from collections.abc import Callable
from typing import Generic, TypeVar

from resono_runtime.agents import AgentAudience


Payload = TypeVar("Payload")
PREFLIGHT_LIFETIME = timedelta(minutes=10)


class ImportPreflightError(ValueError):
    """A confirmation token is absent, expired, reused, or no longer exact."""


@dataclass(frozen=True, slots=True)
class ImportPreflight(Generic[Payload]):
    token: str
    identity: str
    candidate_hash: str
    expected_current_hash: str | None
    audience: AgentAudience
    state: str
    expires_at: datetime
    payload: Payload


class ImportPreflightRegistry(Generic[Payload]):
    """Holds short-lived opaque tokens; owning lifecycles still own all mutation."""

    def __init__(self, *, clock: Callable[[], datetime] | None = None) -> None:
        self._records: dict[str, ImportPreflight[Payload]] = {}
        self._clock = clock or _utcnow

    def issue(
        self,
        *,
        identity: str,
        candidate_hash: str,
        current_hash: str | None,
        audience: AgentAudience,
        payload: Payload,
    ) -> ImportPreflight[Payload]:
        if not identity or identity.strip() != identity:
            raise ImportPreflightError("Import identity must be a non-empty trimmed string.")
        if not candidate_hash:
            raise ImportPreflightError("Candidate content hash is required.")
        self.discard_expired()
        state = (
            "new"
            if current_hash is None
            else "identical"
            if current_hash == candidate_hash
            else "conflict"
        )
        record = ImportPreflight(
            token=secrets.token_urlsafe(32),
            identity=identity,
            candidate_hash=candidate_hash,
            expected_current_hash=current_hash,
            audience=audience,
            state=state,
            expires_at=self._clock() + PREFLIGHT_LIFETIME,
            payload=payload,
        )
        self._records[record.token] = record
        return record

    def consume(
        self,
        token: str,
        *,
        current_hash: str | None,
        replace: bool,
    ) -> ImportPreflight[Payload]:
        record = self._records.get(token)
        if record is None:
            raise ImportPreflightError("The import preflight is unknown or was already used.")
        if record.expires_at <= self._clock():
            raise ImportPreflightError("The import preflight expired. Inspect the item again.")
        if current_hash != record.expected_current_hash:
            raise ImportPreflightError("The installed item changed after preflight. Inspect it again.")
        if record.state == "identical":
            raise ImportPreflightError("An identical item is already installed.")
        if record.state == "conflict" and not replace:
            raise ImportPreflightError("Replacement requires explicit confirmation.")
        self._records.pop(token, None)
        return record

    def peek(self, token: str) -> ImportPreflight[Payload]:
        """Return one live record without consuming its single confirmation use."""
        record = self._records.get(token)
        if record is None:
            raise ImportPreflightError("The import preflight is unknown or was already used.")
        if record.expires_at <= self._clock():
            self._records.pop(token, None)
            raise ImportPreflightError("The import preflight expired. Inspect the item again.")
        return record

    def discard_expired(self) -> tuple[ImportPreflight[Payload], ...]:
        now = self._clock()
        expired = tuple(record for record in self._records.values() if record.expires_at <= now)
        for record in expired:
            self._records.pop(record.token, None)
        return expired


def _utcnow() -> datetime:
    return datetime.now(UTC)
