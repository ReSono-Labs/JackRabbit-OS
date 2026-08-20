from __future__ import annotations

import base64
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..providers.openai import OpenAIProviderError, OpenAISubscription, openai_provider_access
from ..security.credentials import ProviderCredentials
from ..storage.provider_settings import ProviderSettingsRepository


class OpenAIHandoffInspection:
    """One bounded image-to-text transform through the selected OpenAI access path."""

    def __init__(self, credentials: ProviderCredentials, settings: ProviderSettingsRepository,
                 subscription: OpenAISubscription | None) -> None:
        self._credentials, self._settings, self._subscription = credentials, settings, subscription

    def inspect(self, *, content: bytes, mime_type: str, filename: str, note: str) -> tuple[str, str]:
        selection = self._settings.selection()
        if not selection.text_model:
            raise OpenAIProviderError("model_required", "Choose a text model first.", status=409)
        access = openai_provider_access(credentials=self._credentials, settings=self._settings,
                                        subscription=self._subscription)
        endpoint = (access.base_url or "https://api.openai.com/v1").rstrip("/") + "/responses"
        streaming = "/backend-api/codex" in endpoint
        focus = f"\nSpecific user focus: {note}" if note else ""
        prompt = ("Inspect this image handed into the current live Voice conversation.\n"
                  f"Filename: {filename}\nMIME type: {mime_type}\n\n"
                  "Return concise markdown sections: Summary, Visible text, Session notes, "
                  "Possible contact fields, Suggested filename, and Cautions. Do not guess."
                  f"{focus}")
        payload: dict[str, object] = {
            "model": selection.text_model,
            "instructions": ("Ground the answer only in the supplied image. Call out useful details, "
                             "possible contact information, and uncertainty. Do not invent missing fields."),
            "input": [{"role": "user", "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": f"data:{mime_type};base64,{base64.b64encode(content).decode()}", "detail": "high"},
            ]}],
            "store": False,
        }
        if streaming:
            payload["stream"] = True
        request = Request(endpoint, data=json.dumps(payload, separators=(",", ":")).encode(),
                          headers={"Authorization": f"Bearer {access.api_key}", "Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=45) as response:
                raw, content_type = response.read(2 * 1024 * 1024 + 1), response.headers.get_content_type()
        except HTTPError as error:
            code = "credential_rejected" if error.code in (401, 403) else "inspection_rejected"
            raise OpenAIProviderError(code, "OpenAI could not inspect this image.", status=int(error.code)) from error
        except (URLError, TimeoutError, OSError) as error:
            raise OpenAIProviderError("inspection_unavailable", "Image inspection is unavailable.", status=503) from error
        if len(raw) > 2 * 1024 * 1024:
            raise OpenAIProviderError("inspection_too_large", "Image inspection returned too much data.", status=502)
        value = _response(raw, content_type, streaming)
        text = _output_text(value).strip()
        if not text:
            raise OpenAIProviderError("inspection_empty", "Image inspection returned no result.", status=502)
        return text[:16_000], selection.text_model


def _response(raw: bytes, content_type: str, streaming: bool) -> dict[str, object]:
    # The subscription endpoint is requested with stream=true, but the
    # provider may still return a completed JSON Responses object. The HTTP
    # content type, not the endpoint URL, is authoritative for decoding.
    if content_type == "application/json":
        value = json.loads(raw)
        if isinstance(value, dict):
            return value
        raise OpenAIProviderError("inspection_invalid", "Image inspection returned invalid data.", status=502)
    if content_type != "text/event-stream":
        raise OpenAIProviderError("inspection_invalid", "Image inspection returned an invalid stream.", status=502)
    completed = None
    for block in raw.decode().split("\n\n"):
        data = "\n".join(line[5:].lstrip() for line in block.splitlines() if line.startswith("data:"))
        if data and data != "[DONE]":
            event = json.loads(data)
            if isinstance(event, dict) and event.get("type") == "response.completed" and isinstance(event.get("response"), dict):
                completed = event["response"]
    if completed is None:
        raise OpenAIProviderError("inspection_incomplete", "Image inspection did not complete.", status=502)
    return completed


def _output_text(value: dict[str, object]) -> str:
    if isinstance(value.get("output_text"), str):
        return str(value["output_text"])
    parts: list[str] = []
    for item in value.get("output", []) if isinstance(value.get("output"), list) else []:
        if isinstance(item, dict) and item.get("type") == "message":
            for part in item.get("content", []) if isinstance(item.get("content"), list) else []:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    parts.append(part["text"])
    return "\n".join(parts)
