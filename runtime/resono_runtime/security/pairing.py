from __future__ import annotations

from dataclasses import dataclass
import hmac
import secrets
import threading
import time
from collections.abc import Callable
from urllib.parse import urlsplit


class PairingDenied(Exception):
    pass


@dataclass(frozen=True, slots=True)
class PairingCode:
    value: str
    expires_at: int


@dataclass(frozen=True, slots=True)
class BrowserSession:
    token: str
    csrf_token: str
    origin: str
    expires_at: int


class PairingAuthority:
    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.time,
        pairing_lifetime_seconds: int = 300,
        session_lifetime_seconds: int = 1800,
    ) -> None:
        self._clock = clock
        self._pairing_lifetime = pairing_lifetime_seconds
        self._session_lifetime = session_lifetime_seconds
        self._lock = threading.Lock()
        self._pairing: PairingCode | None = None
        self._sessions: dict[str, BrowserSession] = {}

    def current_code(self) -> PairingCode:
        with self._lock:
            now = int(self._clock())
            if self._pairing is None or self._pairing.expires_at <= now:
                self._pairing = PairingCode(
                    value=f"{secrets.randbelow(1_000_000):06d}",
                    expires_at=now + self._pairing_lifetime,
                )
            return self._pairing

    def pair(self, code: str, origin: str, request_origin: str | None = None) -> BrowserSession:
        normalized_origin = _https_origin(origin)
        if request_origin is None or _https_origin(request_origin) != normalized_origin:
            raise PairingDenied("request origin is invalid")
        with self._lock:
            now = int(self._clock())
            pairing = self._pairing
            if (
                pairing is None
                or pairing.expires_at <= now
                or not hmac.compare_digest(str(code), pairing.value)
            ):
                raise PairingDenied("pairing code is invalid or expired")
            self._pairing = None
            self._discard_expired(now)
            session = BrowserSession(
                token=secrets.token_urlsafe(32),
                csrf_token=secrets.token_urlsafe(32),
                origin=normalized_origin,
                expires_at=now + self._session_lifetime,
            )
            self._sessions[session.token] = session
            return session

    def authorize(
        self,
        session_token: str,
        forwarded_origin: str,
        *,
        request_origin: str | None = None,
        csrf_token: str | None = None,
        mutation: bool = False,
    ) -> BrowserSession:
        normalized_origin = _https_origin(forwarded_origin)
        with self._lock:
            now = int(self._clock())
            self._discard_expired(now)
            session = self._sessions.get(session_token)
            if session is None or not hmac.compare_digest(session.origin, normalized_origin):
                raise PairingDenied("browser session is invalid or expired")
            if mutation:
                if request_origin is None or _https_origin(request_origin) != session.origin:
                    raise PairingDenied("request origin is invalid")
                if csrf_token is None or not hmac.compare_digest(csrf_token, session.csrf_token):
                    raise PairingDenied("CSRF proof is invalid")
            return session

    def _discard_expired(self, now: int) -> None:
        self._sessions = {
            token: session
            for token, session in self._sessions.items()
            if session.expires_at > now
        }


def _https_origin(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise PairingDenied("HTTPS origin is required")
    host = parsed.hostname.lower()
    port = parsed.port
    authority = f"[{host}]" if ":" in host else host
    if port is not None and port != 443:
        authority = f"{authority}:{port}"
    return f"https://{authority}"
