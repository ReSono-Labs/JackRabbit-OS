from __future__ import annotations

from dataclasses import dataclass
import json
import secrets
import threading
import time
from typing import Any, Callable

from ...security.credentials import CredentialUnavailable, ProviderCredentials
from .platform import OpenAIProviderError


CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
ISSUER = "https://auth.openai.com"
DEVICE_REDIRECT_URL = "https://auth.openai.com/deviceauth/callback"
TOKEN_URL = "https://auth.openai.com/oauth/token"
VERIFICATION_URL = "https://auth.openai.com/codex/device"
AUTH_LIFETIME_SECONDS = 15 * 60
REFRESH_LEEWAY_SECONDS = 5 * 60

DeviceTransport = Callable[[str, dict[str, Any]], tuple[int, dict[str, Any]]]
TokenTransport = Callable[[str, dict[str, str], bool], dict[str, Any]]


@dataclass(frozen=True, slots=True)
class SubscriptionAuthStart:
    auth_session_id: str
    verification_url: str
    user_code: str
    expires_at: int
    poll_interval_seconds: int


@dataclass(slots=True)
class _PendingAuth:
    device_auth_id: str
    user_code: str
    expires_at: int
    poll_interval_seconds: int


class OpenAISubscription:
    """Single-device adaptation of the proven Codex device authorization flow."""

    def __init__(
        self,
        credentials: ProviderCredentials,
        *,
        clock: Callable[[], float] = time.time,
        device_transport: DeviceTransport | None = None,
        token_transport: TokenTransport | None = None,
    ) -> None:
        self._credentials = credentials
        self._clock = clock
        self._device_transport = device_transport or _post_json_status
        self._token_transport = token_transport or _post_token
        self._pending: dict[str, _PendingAuth] = {}
        self._lock = threading.Lock()

    def status(self) -> dict[str, object]:
        connected = self._credentials.has_subscription()
        expires_at: int | None = None
        if connected:
            try:
                payload = json.loads(self._credentials.subscription_tokens())
                expires_at = _positive_int(payload.get("_resono_expires_at"))
            except (CredentialUnavailable, json.JSONDecodeError, AttributeError):
                connected = False
        return {
            "connected": connected,
            "authFlow": "codex_device",
            "verificationUrl": VERIFICATION_URL,
            "tokenExpiresAt": expires_at,
        }

    def start_auth(self) -> SubscriptionAuthStart:
        status, payload = self._device_transport(
            f"{ISSUER}/api/accounts/deviceauth/usercode", {"client_id": CLIENT_ID}
        )
        if status >= 400:
            raise OpenAIProviderError(
                "subscription_auth_start_failed", "ChatGPT login could not be started.", status=502
            )
        device_auth_id = payload.get("device_auth_id")
        user_code = payload.get("user_code") or payload.get("usercode")
        if not isinstance(device_auth_id, str) or not device_auth_id:
            raise OpenAIProviderError(
                "subscription_auth_invalid", "ChatGPT login returned an invalid response.", status=502
            )
        if not isinstance(user_code, str) or not user_code:
            raise OpenAIProviderError(
                "subscription_auth_invalid", "ChatGPT login returned an invalid response.", status=502
            )
        interval = min(30, max(1, _positive_int(payload.get("interval")) or 5))
        expires_at = int(self._clock()) + AUTH_LIFETIME_SECONDS
        session_id = secrets.token_urlsafe(24)
        with self._lock:
            self._discard_expired()
            self._pending[session_id] = _PendingAuth(
                device_auth_id=device_auth_id,
                user_code=user_code,
                expires_at=expires_at,
                poll_interval_seconds=interval,
            )
        return SubscriptionAuthStart(
            auth_session_id=session_id,
            verification_url=VERIFICATION_URL,
            user_code=user_code,
            expires_at=expires_at,
            poll_interval_seconds=interval,
        )

    def poll_auth(self, auth_session_id: str) -> dict[str, object]:
        with self._lock:
            self._discard_expired()
            pending = self._pending.get(auth_session_id)
        if pending is None:
            raise OpenAIProviderError(
                "subscription_auth_not_found", "ChatGPT login session expired or was not found.", status=404
            )
        status, payload = self._device_transport(
            f"{ISSUER}/api/accounts/deviceauth/token",
            {"device_auth_id": pending.device_auth_id, "user_code": pending.user_code},
        )
        if status in (403, 404):
            return {"authSessionId": auth_session_id, "status": "auth_pending"}
        if status >= 400:
            with self._lock:
                self._pending.pop(auth_session_id, None)
            raise OpenAIProviderError(
                "subscription_auth_failed", "ChatGPT login could not be completed.", status=502
            )
        authorization_code = payload.get("authorization_code")
        code_verifier = payload.get("code_verifier")
        if not isinstance(authorization_code, str) or not authorization_code:
            raise OpenAIProviderError(
                "subscription_auth_invalid", "ChatGPT login returned an invalid response.", status=502
            )
        if not isinstance(code_verifier, str) or not code_verifier:
            raise OpenAIProviderError(
                "subscription_auth_invalid", "ChatGPT login returned an invalid response.", status=502
            )
        token_payload = self._token_transport(
            TOKEN_URL,
            {
                "grant_type": "authorization_code",
                "code": authorization_code,
                "redirect_uri": DEVICE_REDIRECT_URL,
                "client_id": CLIENT_ID,
                "code_verifier": code_verifier,
            },
            False,
        )
        self._store_tokens(token_payload)
        with self._lock:
            self._pending.pop(auth_session_id, None)
        return {
            "authSessionId": auth_session_id,
            "status": "completed",
            "runtime": self.status(),
        }

    def access_token(self) -> str:
        try:
            payload = json.loads(self._credentials.subscription_tokens())
        except (CredentialUnavailable, json.JSONDecodeError) as error:
            raise OpenAIProviderError(
                "subscription_reconnect_required", "Reconnect ChatGPT before continuing.", status=409
            ) from error
        expires_at = _positive_int(payload.get("_resono_expires_at"))
        if expires_at is not None and expires_at <= int(self._clock()) + REFRESH_LEEWAY_SECONDS:
            refresh_token = payload.get("refresh_token")
            if not isinstance(refresh_token, str) or not refresh_token:
                raise OpenAIProviderError(
                    "subscription_reconnect_required", "Reconnect ChatGPT before continuing.", status=409
                )
            refreshed = self._token_transport(
                TOKEN_URL,
                {"grant_type": "refresh_token", "client_id": CLIENT_ID, "refresh_token": refresh_token},
                True,
            )
            if "refresh_token" not in refreshed:
                refreshed["refresh_token"] = refresh_token
            self._store_tokens(refreshed)
            payload = refreshed
        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise OpenAIProviderError(
                "subscription_reconnect_required", "Reconnect ChatGPT before continuing.", status=409
            )
        return access_token

    def disconnect(self) -> dict[str, object]:
        self._credentials.disconnect_subscription()
        with self._lock:
            self._pending.clear()
        return self.status()

    def _store_tokens(self, payload: dict[str, Any]) -> None:
        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise OpenAIProviderError(
                "subscription_token_invalid", "ChatGPT login returned no access token.", status=502
            )
        stored = dict(payload)
        expires_in = _positive_int(stored.get("expires_in"))
        if expires_in is not None:
            stored["_resono_expires_at"] = int(self._clock()) + expires_in
        self._credentials.connect_subscription(json.dumps(stored, separators=(",", ":")))

    def _discard_expired(self) -> None:
        now = int(self._clock())
        self._pending = {
            session_id: pending
            for session_id, pending in self._pending.items()
            if pending.expires_at > now
        }


def _positive_int(value: object) -> int | None:
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _post_json_status(url: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    try:
        import httpx

        response = httpx.post(
            url,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            json=payload,
            timeout=30.0,
        )
        body = response.json()
        return int(response.status_code), body if isinstance(body, dict) else {}
    except Exception as error:
        raise OpenAIProviderError(
            "subscription_unavailable", "ChatGPT login is currently unreachable.", status=503
        ) from error


def _post_token(url: str, payload: dict[str, str], refresh: bool) -> dict[str, Any]:
    try:
        import httpx

        kwargs = {"json": payload} if refresh else {"data": payload}
        response = httpx.post(url, headers={"Accept": "application/json"}, timeout=30.0, **kwargs)
        if response.status_code >= 400:
            raise OpenAIProviderError(
                "subscription_token_rejected",
                "ChatGPT login was rejected.",
                status=int(response.status_code),
            )
        body = response.json()
        if not isinstance(body, dict):
            raise ValueError("token response is not an object")
        return body
    except OpenAIProviderError:
        raise
    except Exception as error:
        raise OpenAIProviderError(
            "subscription_unavailable", "ChatGPT login is currently unreachable.", status=503
        ) from error
