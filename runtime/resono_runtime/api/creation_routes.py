"""Local artifact and paired management routes for static Creations."""
from __future__ import annotations

import mimetypes
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from urllib.parse import unquote

from ..agents import AgentAudience
from ..creations import CreationArchiveInspector, CreationArchiveRejected, CreationDescriptorInspector, CreationLifecycle, CreationLifecycleError
from ..security.pairing import PairingAuthority

if TYPE_CHECKING:
    from .routes import RouteRequest


class CreationRoutes:
    def __init__(self, lifecycle: CreationLifecycle, inspector: CreationArchiveInspector, descriptor_inspector: CreationDescriptorInspector) -> None:
        self._lifecycle = lifecycle
        self._inspector = inspector
        self._descriptor_inspector = descriptor_inspector

    def handle_get(self, request: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        path = unquote(request.path.split("?", 1)[0])
        if path == "/v1/cards/catalog":
            request.respond_json(200, self._catalog(include_plugin_cards=True, key="cards"))
            return True
        if path == "/v1/creations/catalog":
            request.respond_json(200, self._catalog(include_plugin_cards=False, key="creations"))
            return True
        if path.startswith("/v1/creations/") and "/assets/" in path:
            return self._asset(request, path)
        if path != "/v1/management/creations" and not path.startswith("/v1/management/creations/"):
            return False
        if not _session(request, pairing, mutation=False): return True
        if path == "/v1/management/creations":
            request.respond_json(200, self._catalog(include_disabled=True, include_plugin_cards=False, key="creations"))
            return True
        item = self._lifecycle.get(path.rsplit("/", 1)[-1])
        if item is None: _error(request, 404, "creation_not_found", "Creation not found.")
        else: request.respond_json(200, _view(item))
        return True

    def handle_post(self, request: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        path = request.path.split("?", 1)[0]
        if not path.startswith("/v1/management/creations"): return False
        if not _session(request, pairing, mutation=True): return True
        try:
            if path == "/v1/management/creations/qr/preflight":
                payload = request.request_json(max_bytes=16 * 1024)
                if payload is None: return True
                inspection = self._descriptor_inspector.inspect(payload)
                result = self._lifecycle.preflight(inspection, audience=AgentAudience(request.headers.get("X-ReSono-Agent-Audience", "")))
                request.respond_json(200, {"state": result.state, "preflightToken": result.token, "candidate": _inspection_view(inspection, result.candidate_hash), "current": _view(self._lifecycle.get(result.identity)) if self._lifecycle.get(result.identity) else None})
                return True
            if path == "/v1/management/creations/preflight":
                payload = request.request_bytes(max_bytes=16 * 1024 * 1024)
                if payload is None: return True
                inspection = self._inspector.inspect(payload, request.headers.get("X-ReSono-Creation-Filename", ""))
                result = self._lifecycle.preflight(inspection, audience=AgentAudience(request.headers.get("X-ReSono-Agent-Audience", "")))
                request.respond_json(200, {"state": result.state, "preflightToken": result.token, "candidate": {"creationId": result.identity, "title": inspection.title, "description": inspection.description, "contentHash": result.candidate_hash}, "current": _view(self._lifecycle.get(result.identity)) if self._lifecycle.get(result.identity) else None})
                return True
            payload = request.request_json(max_bytes=4096)
            if payload is None: return True
            if path == "/v1/management/creations/confirm":
                item = self._lifecycle.confirm(str(payload.get("preflightToken", "")), replace=payload.get("replace") is True, changed_by="management-api", reason="confirmed Creation import")
                request.respond_json(201, _view(item)); return True
            creation_id, action = _name_action(path)
            if action not in {"enable", "disable"}: raise CreationLifecycleError("Creation action is unsupported.")
            _require_standalone(self._lifecycle, creation_id)
            item = self._lifecycle.set_enabled(creation_id, action == "enable", changed_by="management-api", reason=f"{action}d from management")
            request.respond_json(200, _view(item))
        except (CreationArchiveRejected, CreationLifecycleError, ValueError) as error:
            _error(request, 409, "creation_import_conflict", str(error))
        return True

    def handle_delete(self, request: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        path = request.path.split("?", 1)[0]
        if not path.startswith("/v1/management/creations/"): return False
        if not _session(request, pairing, mutation=True): return True
        creation_id = path.rsplit("/", 1)[-1]
        try:
            _require_standalone(self._lifecycle, creation_id)
            self._lifecycle.delete(creation_id, changed_by="management-api", reason="deleted from management")
        except CreationLifecycleError as error: _error(request, 404, "creation_not_found", str(error)); return True
        request.respond_json(200, {"creationId": creation_id, "deleted": True, "restartRequired": False})
        return True

    def _catalog(self, *, include_disabled: bool = False, include_plugin_cards: bool, key: str) -> dict[str, object]:
        items = [item for item in self._lifecycle.list() if (include_plugin_cards or item.source_type != "plugin_card") and (include_disabled or item.lifecycle_state == "enabled")]
        return {"generation": self._lifecycle.generation(), "restartRequired": False, key: [_view(item, accent=index) for index, item in enumerate(items)]}

    def _asset(self, request: "RouteRequest", path: str) -> bool:
        prefix, relative_value = path.split("/assets/", 1)
        creation_id = prefix.rsplit("/", 1)[-1]
        item = self._lifecycle.get(creation_id)
        relative = PurePosixPath(relative_value)
        if item is None or item.source_type not in {"local_archive", "plugin_card"} or item.lifecycle_state != "enabled" or relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
            _error(request, 404, "creation_asset_not_found", "Creation asset not found."); return True
        target = item.install_path.joinpath(*relative.parts)
        try: data = target.read_bytes()
        except OSError: _error(request, 404, "creation_asset_not_found", "Creation asset not found."); return True
        if len(data) > 8 * 1024 * 1024: _error(request, 413, "creation_asset_too_large", "Creation asset is too large."); return True
        request.respond_bytes(200, data, content_type=mimetypes.guess_type(target.name)[0] or "application/octet-stream")
        return True


def _view(item: object, accent: int = 0) -> dict[str, object]:
    colors = ("#79f2dd", "#ffd166", "#c792ff", "#ff6b6b")
    color = item.theme_color if item.source_type == "rabbit_qr_link" else colors[accent % len(colors)]
    result = {"creationId": item.creation_id, "title": item.title, "description": item.description, "contentHash": item.content_hash, "state": item.lifecycle_state, "generation": item.generation, "sourceType": item.source_type, "iconUrl": item.icon_url, "accent": color}
    if item.source_type == "rabbit_qr_link": result["entryUrl"] = item.entry_url
    else:
        entrypoint = "index.html"
        if item.source_type == "plugin_card":
            try:
                import json
                entrypoint = str(json.loads((item.install_path / "card.json").read_text(encoding="utf-8"))["entrypoint"])
            except (OSError, KeyError, TypeError, ValueError):
                entrypoint = "index.html"
        result["entryAsset"] = f"/v1/creations/{item.creation_id}/assets/{entrypoint}"
    return result


def _inspection_view(item: object, content_hash: str) -> dict[str, object]:
    return {"creationId": item.creation_id, "title": item.title, "description": item.description, "contentHash": content_hash, "sourceType": item.source_type, "entryUrl": item.entry_url, "iconUrl": item.icon_url, "themeColor": item.theme_color}


def _require_standalone(lifecycle: CreationLifecycle, creation_id: str) -> None:
    item = lifecycle.get(creation_id)
    if item is not None and item.source_type == "plugin_card":
        raise CreationLifecycleError("This Card is managed by its owning Plugin.")


def _name_action(path: str) -> tuple[str, str]:
    parts = path.rsplit("/", 2); return (parts[1], parts[2]) if len(parts) == 3 else ("", "")
def _session(request: "RouteRequest", pairing: PairingAuthority | None, *, mutation: bool) -> bool:
    if pairing is None: _error(request, 503, "management_unavailable", "Management pairing is unavailable."); return False
    return request.browser_session(pairing, mutation=mutation) is not None
def _error(request: "RouteRequest", status: int, code: str, message: str) -> None: request.respond_json(status, {"error": {"code": code, "message": message}})
