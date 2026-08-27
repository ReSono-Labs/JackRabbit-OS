"""OpenAI-compatible provider backend for third-party text providers."""

from __future__ import annotations

import http.client
import json
import ssl
from urllib.parse import urlsplit

REQUEST_TIMEOUT = 5.0
MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class CompatibleProviderError(RuntimeError):
    def __init__(self, code: str, message: str, *, status: int = 502) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


class CompatibleProvider:
    """Client for any OpenAI-compatible chat-completions provider.

    Used for key validation (``GET {base_url}/models``) and live model listing.
    The conversational agent turn itself runs through the Agents SDK with the
    same base URL and key (see ``agents/sdk_runner.py``).
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None,
        *,
        api_style: str = "chat",
        timeout: float = REQUEST_TIMEOUT,
    ) -> None:
        parsed = urlsplit(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise CompatibleProviderError("invalid_configuration", "Provider base URL is invalid.", status=400)
        if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise CompatibleProviderError(
                "invalid_configuration", "Non-loopback provider endpoints require HTTPS.", status=400
            )
        self._parsed = parsed
        self._api_key = api_key
        self._timeout = timeout

    def list_models(self) -> tuple[str, ...]:
        connection = self._connection()
        headers = {"Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        try:
            connection.request("GET", self._path("/models"), headers=headers)
            response = connection.getresponse()
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        except OSError as error:
            raise CompatibleProviderError(
                "provider_unreachable", "The provider endpoint could not be reached.", status=502
            ) from error
        finally:
            connection.close()
        if response.status == 401 or response.status == 403:
            raise CompatibleProviderError(
                "invalid_key", "The provider rejected the API key.", status=response.status
            )
        if response.status >= 400:
            raise CompatibleProviderError(
                "provider_error", f"The provider rejected the request.", status=response.status
            )
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as error:
            raise CompatibleProviderError("provider_error", "The provider returned invalid JSON.", status=502) from error
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise CompatibleProviderError("provider_error", "The provider response is invalid.", status=502)
        models = tuple(sorted(str(item["id"]) for item in payload["data"] if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"]))
        if not models:
            raise CompatibleProviderError("provider_error", "The provider returned no models.", status=502)
        return models

    def _connection(self) -> http.client.HTTPConnection:
        port = self._parsed.port or (443 if self._parsed.scheme == "https" else 80)
        if self._parsed.scheme == "https":
            return http.client.HTTPSConnection(self._parsed.hostname, port, timeout=self._timeout,
                                               context=ssl.create_default_context())
        return http.client.HTTPConnection(self._parsed.hostname, port, timeout=self._timeout)

    def _path(self, suffix: str) -> str:
        path = (self._parsed.path or "").rstrip("/")
        return path + suffix + (f"?{self._parsed.query}" if self._parsed.query else "")
