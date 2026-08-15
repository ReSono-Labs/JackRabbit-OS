from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import secrets
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True, slots=True)
class ProviderModels:
    text: tuple[str, ...]
    realtime: tuple[str, ...]


class OpenAIProviderError(RuntimeError):
    def __init__(self, code: str, message: str, *, status: int = 502) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


class OpenAIPlatform:
    API_ROOT = "https://api.openai.com/v1"

    def __init__(self, api_key: str, *, safety_source: str) -> None:
        self._api_key = api_key
        self._safety_id = hashlib.sha256(
            f"resono-r1:{safety_source}".encode()
        ).hexdigest()

    def list_models(self) -> ProviderModels:
        payload = json.loads(self._request("GET", "/models").decode())
        identifiers = sorted(
            str(item.get("id", ""))
            for item in payload.get("data", [])
            if isinstance(item, dict) and item.get("id")
        )
        realtime = tuple(item for item in identifiers if item.startswith("gpt-realtime"))
        text = tuple(item for item in identifiers if _is_text_model(item))
        return ProviderModels(text=text, realtime=realtime)

    def create_realtime_call(self, *, offer_sdp: str, model: str) -> str:
        if not offer_sdp.startswith("v=0") or len(offer_sdp) > 262_144:
            raise OpenAIProviderError("invalid_sdp", "The WebRTC offer is invalid.", status=400)
        if not (model.startswith("gpt-realtime") or model == "gpt-live-1") or len(model) > 128:
            raise OpenAIProviderError("unsupported_model", "Select an available Realtime model.", status=400)
        boundary = f"resono-{secrets.token_hex(16)}"
        session = json.dumps(_realtime_session(model), separators=(",", ":"))
        body = _multipart(boundary, (("sdp", offer_sdp), ("session", session)))
        answer = self._request(
            "POST",
            "/realtime/calls",
            body=body,
            content_type=f"multipart/form-data; boundary={boundary}",
        ).decode()
        if not answer.startswith("v=0"):
            raise OpenAIProviderError("invalid_answer", "OpenAI returned an invalid WebRTC answer.")
        return answer

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        content_type: str | None = None,
    ) -> bytes:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json, application/sdp, text/plain",
            "OpenAI-Safety-Identifier": self._safety_id,
        }
        if content_type:
            headers["Content-Type"] = content_type
        request = Request(self.API_ROOT + path, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=25) as response:
                return response.read(524_288)
        except HTTPError as error:
            status = int(error.code)
            code = "credential_rejected" if status in (401, 403) else "provider_rejected"
            message = (
                "OpenAI rejected this credential."
                if code == "credential_rejected"
                else "OpenAI could not start this session."
            )
            raise OpenAIProviderError(code, message, status=status) from error
        except (URLError, TimeoutError, OSError) as error:
            raise OpenAIProviderError(
                "provider_unavailable", "OpenAI is currently unreachable.", status=503
            ) from error


def _is_text_model(identifier: str) -> bool:
    if not identifier.startswith(("gpt-5", "gpt-4.1", "gpt-4o")):
        return False
    excluded = ("realtime", "audio", "transcribe", "tts", "image", "search")
    return not any(part in identifier for part in excluded)


def _realtime_session(model: str) -> dict[str, object]:
    """Small on-device adaptation of the proven Voice device Realtime contract."""
    return {
        "type": "realtime",
        "model": model,
        "instructions": "You are ReSono Voice. Be concise, natural, and helpful.",
        "output_modalities": ["audio"],
        "audio": {
            "input": {
                "format": {"type": "audio/pcm", "rate": 24_000},
                "noise_reduction": {"type": "near_field"},
                "transcription": {"model": "gpt-4o-mini-transcribe"},
                "turn_detection": {
                    "type": "server_vad",
                    "create_response": True,
                    "interrupt_response": False,
                    "threshold": 0.92,
                    "prefix_padding_ms": 500,
                    "silence_duration_ms": 1_200,
                },
            },
            "output": {
                "format": {"type": "audio/pcm", "rate": 24_000},
                "voice": "marin",
            },
        },
        "tools": [
            {
                "type": "function",
                "name": "get_device_status",
                "description": "Read the current health of this ReSono R1 on-device runtime.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            }
        ],
        "tool_choice": "auto",
    }


def _multipart(boundary: str, fields: tuple[tuple[str, str], ...]) -> bytes:
    chunks: list[bytes] = []
    for name, value in fields:
        chunks.extend(
            (
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode(),
                b"\r\n",
            )
        )
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks)
