from __future__ import annotations

from dataclasses import dataclass
import json
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


LIVE_MODEL = "gpt-live-1"
LIVE_CODEX_MODEL = "gpt-live-1-codex"
LIVE_VOICE = "sol"
CODEX_REALTIME_BASE_URL = "https://chatgpt.com/backend-api/codex"
CODEX_REALTIME_CALLS_PATH = "/realtime/calls"
CODEX_AVAS_QUERY = "intent=quicksilver&architecture=avas"
CODEX_ALPHA_HEADER = "quicksilver=v2"
PRODUCT_REALTIME_CALLS_URL = "https://chatgpt.com/realtime/wm?dcid=0"
PRODUCT_VOICE = "Sol"

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 14; rabbit_r1) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36"
    ),
    "Origin": "https://chatgpt.com",
    "Referer": "https://chatgpt.com/",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
}


def is_live_model(model: str) -> bool:
    return model.strip().lower() == LIVE_MODEL


def codex_realtime_model(model: str) -> str:
    if not is_live_model(model):
        raise ValueError("model is not a GPT-Live model")
    return LIVE_CODEX_MODEL


@dataclass(frozen=True, slots=True)
class LiveRealtimeStart:
    """Wire request accepted by the Codex AVAS realtime broker."""

    transport_type: str
    sdp: str
    model: str = LIVE_CODEX_MODEL

    def payload(self) -> dict[str, object]:
        if self.transport_type != "webrtc":
            raise ValueError("GPT-Live requires WebRTC transport")
        if not self.sdp.startswith("v=0"):
            raise ValueError("WebRTC offer is invalid")
        return {
            "sdp": self.sdp,
            "session": {
                "audio": {"output": {"voice": LIVE_VOICE}},
                "delegation": {"ack_filler": False, "type": "client"},
                "model": self.model,
            },
        }


def live_session_payload(
    *,
    model: str,
    instructions: str = "",
    initial_items: tuple[dict[str, str], ...] = (),
) -> str:
    """Build the AVAS full-duplex session options for the Codex broker."""
    if not is_live_model(model):
        raise ValueError("model is not a GPT-Live model")
    payload: dict[str, object] = {
        "audio": {"output": {"voice": LIVE_VOICE}},
        "delegation": {"ack_filler": False, "type": "client"},
        "model": codex_realtime_model(model),
    }
    if instructions:
        payload["instructions"] = instructions
    if initial_items:
        payload["initial_items"] = list(initial_items)
    return json.dumps(payload, separators=(",", ":"))


def _product_session_payload(
    *,
    voice: str,
    instructions: str,
    timezone: str,
    timezone_offset_min: int,
) -> str:
    """Build the web-Capable Voice session payload for the product wm endpoint."""
    sid = str(uuid.uuid4()).upper()
    payload: dict[str, object] = {
        "backend_reasoning_effort": "instant",
        "language_code": "auto",
        "requested_default_model": "",
        "voice": voice,
        "voice_session_id": sid,
        "voice_status_request_id": sid,
        "timezone_offset_min": timezone_offset_min,
        "timezone": timezone,
        "voice_mode": "standard",
        "model_slug": "",
        "model_slug_advanced": "",
        "client_tools": [],
        "history_and_training_disabled": False,
        "conversation_mode": {"kind": "primary_assistant"},
        "enable_message_streaming": True,
    }
    if instructions:
        payload["instructions"] = instructions
    return json.dumps(payload, separators=(",", ":"))


def _multipart_form(*fields: tuple[str, str]) -> tuple[bytes, str]:
    boundary = "----ResonoBoundary" + uuid.uuid4().hex[:16]
    parts: list[bytes] = []
    for name, value in fields:
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def create_product_live_call(
    *,
    access_token: str,
    offer_sdp: str,
    thread_id: str = "",
    instructions: str = "",
    voice: str = PRODUCT_VOICE,
    timezone: str = "Europe/Berlin",
    timezone_offset_min: int = -120,
) -> str:
    """Call the ChatGPT Voice product backend (/realtime/wm) for GPT-Live-1.

    This is the same endpoint the ChatGPT apps use for Advanced Voice Mode,
    so the speech pipeline and Sol voice match the consumer product exactly.
    """
    if not access_token.strip():
        raise ValueError("access token is required")
    if not offer_sdp.startswith("v=0"):
        raise ValueError("WebRTC offer is invalid")
    session_json = _product_session_payload(
        voice=voice,
        instructions=instructions,
        timezone=timezone,
        timezone_offset_min=timezone_offset_min,
    )
    body, content_type = _multipart_form(("sdp", offer_sdp), ("session", session_json))
    headers: dict[str, str] = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": content_type,
        "Accept": "*/*",
        "OAI-Device-Id": str(uuid.uuid4()),
        "OAI-Language": "en-US",
        **_BROWSER_HEADERS,
    }
    request = Request(
        PRODUCT_REALTIME_CALLS_URL,
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read(524_288)
    except HTTPError as error:
        raw = error.read(524_288)
        try:
            detail = json.loads(raw.decode())
        except (UnicodeDecodeError, json.JSONDecodeError):
            detail = raw.decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"ChatGPT Voice product backend rejected the session (HTTP {error.code}): {detail}"
        ) from error
    except (URLError, TimeoutError, OSError) as error:
        raise RuntimeError("ChatGPT Voice product backend is unreachable.") from error
    except Exception as error:
        raise RuntimeError(f"ChatGPT Voice product transport failed: {error}") from error
    answer = raw.decode("utf-8", errors="replace").strip()
    if not answer.startswith("v=0"):
        raise RuntimeError("ChatGPT Voice product backend returned no WebRTC answer.")
    return answer


def create_codex_live_call(
    *,
    access_token: str,
    offer_sdp: str,
    thread_id: str = "",
    instructions: str = "",
) -> str:
    """Broker a GPT-Live WebRTC offer through the Codex AVAS backend.

    The ChatGPT subscription token is never sent to the public Realtime API.
    The broker owns the Live entitlement and returns the SDP answer.
    """
    if not access_token.strip():
        raise ValueError("access token is required")
    if not offer_sdp.startswith("v=0"):
        raise ValueError("WebRTC offer is invalid")
    session: dict[str, object] = {
        "audio": {"output": {"voice": LIVE_VOICE}},
        "delegation": {"ack_filler": False, "type": "client"},
        "model": LIVE_CODEX_MODEL,
    }
    if instructions:
        session["instructions"] = instructions
    payload: dict[str, object] = {"sdp": offer_sdp, "session": session}
    headers: dict[str, str] = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "OpenAI-Alpha": CODEX_ALPHA_HEADER,
        **_BROWSER_HEADERS,
    }
    if thread_id:
        headers["x-session-id"] = thread_id
    request = Request(
        f"{CODEX_REALTIME_BASE_URL}{CODEX_REALTIME_CALLS_PATH}?{CODEX_AVAS_QUERY}",
        data=json.dumps(payload, separators=(",", ":")).encode(),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read(524_288)
    except HTTPError as error:
        raw = error.read(524_288)
        try:
            detail = json.loads(raw.decode())
        except (UnicodeDecodeError, json.JSONDecodeError):
            detail = raw.decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"Codex Live broker rejected the session (HTTP {error.code}): {detail}"
        ) from error
    except (URLError, TimeoutError, OSError) as error:
        raise RuntimeError("Codex Live broker is unreachable.") from error
    except Exception as error:
        raise RuntimeError(f"Codex Live transport failed: {error}") from error
    answer = raw.decode("utf-8", errors="replace").strip()
    if not answer.startswith("v=0"):
        raise RuntimeError("Codex Live broker returned no WebRTC answer.")
    return answer
