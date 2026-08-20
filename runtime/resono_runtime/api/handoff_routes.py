from __future__ import annotations
from base64 import b64decode
from binascii import Error as Base64Error
from ..handoff import DirectHandoffError, DirectHandoffService
from ..providers.openai import OpenAIProviderError

class HandoffRoutes:
    def __init__(self, service: DirectHandoffService) -> None: self._service = service
    def handle_post(self, req: object) -> bool:
        if req.path.split("?", 1)[0] != "/v1/host/direct-handoffs/inspect": return False
        content = req.request_bytes(max_bytes=DirectHandoffService.MAX_IMAGE_BYTES)
        if content is None: return True
        try:
            req.respond_json(200, self._service.inspect(req.headers.get("X-ReSono-Voice-Session", ""), _decode(req.headers.get("X-ReSono-Filename-B64"), "handoff-image", 500), req.headers.get("Content-Type", ""), _decode(req.headers.get("X-ReSono-Handoff-Note-B64"), "", 2000), content))
        except DirectHandoffError as error: req.respond_json(error.status, {"error":{"code":error.code,"message":str(error)}})
        except OpenAIProviderError as error: req.provider_error(error)
        return True
def _decode(value: str | None, fallback: str, limit: int) -> str:
    try: return (b64decode(value or "", validate=True).decode().strip()[:limit] or fallback)
    except (Base64Error, UnicodeDecodeError): return fallback
