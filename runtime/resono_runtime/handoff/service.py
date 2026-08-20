from __future__ import annotations
from collections.abc import Callable
from hashlib import sha256
from pathlib import Path
import re, secrets
from .inspection import OpenAIHandoffInspection
from .repository import HandoffRepository, StoredHandoff
from ..storage.provider_settings import ProviderSettingsRepository

class DirectHandoffError(RuntimeError):
    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message); self.code, self.status = code, status

class DirectHandoffService:
    MAX_IMAGE_BYTES = 8 * 1024 * 1024
    def __init__(self, root: Path, repository: HandoffRepository, inspector: OpenAIHandoffInspection,
                 settings: ProviderSettingsRepository, session_is_active: Callable[[str], bool]) -> None:
        self._root, self._repository, self._inspector = root, repository, inspector
        self._settings, self._session_is_active = settings, session_is_active
    def inspect(self, session: str, filename: str, mime: str, note: str, content: bytes) -> dict[str, object]:
        session = session.strip()
        if not self._session_is_active(session): raise DirectHandoffError("stale_voice_session", "The Voice session is no longer active.", 409)
        if not content or len(content) > self.MAX_IMAGE_BYTES: raise DirectHandoffError("invalid_image_size", "The image must be between 1 byte and 8 MiB.")
        detected = _mime(content)
        if detected is None or detected != mime.split(";", 1)[0].strip().lower(): raise DirectHandoffError("invalid_image", "The selected file is not a supported image.")
        filename = _filename(filename, detected); note = " ".join(note.split())[:2000]
        digest, question = sha256(content).hexdigest(), sha256(note.encode()).hexdigest()
        model = self._settings.selection().text_model
        if not model: raise DirectHandoffError("model_required", "Choose a text model first.", 409)
        cached = self._repository.cached(digest, question, model)
        handoff_id = secrets.token_hex(16); extension = {"image/jpeg":"jpg","image/png":"png","image/webp":"webp"}[detected]
        relative = Path(session[:12]) / f"{handoff_id}.{extension}"; destination = self._root / relative
        destination.parent.mkdir(parents=True, exist_ok=True); destination.write_bytes(content)
        try:
            inspection, used_model = (cached.inspection_markdown, cached.model_key) if cached else self._inspector.inspect(content=content, mime_type=detected, filename=filename, note=note)
            item = self._repository.save(StoredHandoff(handoff_id, session, relative.as_posix(), filename, detected, digest, question, used_model, inspection, _utc_now()))
        except Exception:
            destination.unlink(missing_ok=True); raise
        transcript = f"{note}\n[Image handoff: {filename}]" if note else f"[Image handoff: {filename}]"
        note_line = f"User note: {note}\n\n" if note else ""
        provider = ("The user handed off an image into this live voice session.\nUse the server-side inspection below as visual context for the next response.\nIf contact details appear, confirm with the user before saving or using them.\n\n" f"Original filename: {filename}\nWorkspace file key: {item.file_key}\n\n{note_line}Inspection:\n{inspection}")
        return {"handoffId": handoff_id, "fileKey": item.file_key, "transcriptText": transcript, "providerText": provider, "cached": cached is not None}

def _mime(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff"): return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"): return "image/png"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP": return "image/webp"
    return None
def _filename(value: str, mime: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip(".-")[:140]
    return cleaned or {"image/jpeg":"handoff.jpg","image/png":"handoff.png","image/webp":"handoff.webp"}[mime]
def _utc_now() -> str:
    from datetime import UTC, datetime
    return datetime.now(UTC).isoformat()
