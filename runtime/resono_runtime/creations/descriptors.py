"""Strict Rabbit Creation QR descriptor inspection."""
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from ..security.outbound import UnsafeOutboundHost, validate_public_host
from .archives import CreationArchiveRejected, CreationInspection, creation_slug


_FIELDS = frozenset({"title", "url", "description", "iconUrl", "themeColor"})
_COLOR = re.compile(r"#[0-9a-fA-F]{6}\Z")


class CreationDescriptorInspector:
    def __init__(self, quarantine_root: Path, host_validator=validate_public_host) -> None:
        self._quarantine_root = quarantine_root
        self._host_validator = host_validator

    def inspect(self, value: object) -> CreationInspection:
        if not isinstance(value, dict) or set(value) - _FIELDS:
            raise CreationArchiveRejected("Creation QR descriptor has unsupported fields.")
        title = _text(value.get("title"), "title", required=True, limit=100)
        description = _text(value.get("description"), "description", required=False, limit=240)
        entry_url = self._url(value.get("url"), "url", required=True)
        icon_url = self._url(value.get("iconUrl"), "iconUrl", required=False)
        color = _text(value.get("themeColor"), "themeColor", required=False, limit=7) or "#79f2dd"
        if not _COLOR.fullmatch(color):
            raise CreationArchiveRejected("Creation QR themeColor must be #RRGGBB.")
        normalized = {
            "description": description or "Linked Rabbit Creation",
            "iconUrl": icon_url,
            "themeColor": color.casefold(),
            "title": title,
            "url": entry_url,
        }
        canonical = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        candidate = self._quarantine_root / uuid4().hex
        content = candidate / "content"
        try:
            content.mkdir(parents=True, exist_ok=False)
            (content / "creation.json").write_bytes(canonical)
            return CreationInspection(
                creation_slug(title), title, normalized["description"], candidate, content,
                source_type="rabbit_qr_link", entry_url=entry_url, icon_url=icon_url,
                theme_color=color.casefold(),
            )
        except Exception:
            shutil.rmtree(candidate, ignore_errors=True)
            raise

    def _url(self, raw: object, field: str, *, required: bool) -> str | None:
        value = _text(raw, field, required=required, limit=2048)
        if not value:
            return None
        parsed = urlsplit(value)
        if parsed.scheme.casefold() != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise CreationArchiveRejected(f"Creation QR {field} must be a public HTTPS URL.")
        try:
            port = parsed.port or 443
            host = self._host_validator(parsed.hostname, port)
        except (UnsafeOutboundHost, ValueError) as error:
            raise CreationArchiveRejected(f"Creation QR {field} must resolve publicly.") from error
        return urlunsplit(("https", host + (f":{port}" if port != 443 else ""), parsed.path or "/", parsed.query, ""))


def _text(raw: object, field: str, *, required: bool, limit: int) -> str:
    if raw is None and not required:
        return ""
    if not isinstance(raw, str):
        raise CreationArchiveRejected(f"Creation QR {field} must be text.")
    value = raw.strip()
    if (required and not value) or len(value) > limit:
        raise CreationArchiveRejected(f"Creation QR {field} is invalid.")
    return value
