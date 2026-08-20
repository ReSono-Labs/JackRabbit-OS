"""Authenticated management routes for standard Agent Plugin packages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..agents import AgentAudience
from ..plugins.archives import PluginArchiveInspector, PluginArchiveRejected
from ..plugins.lifecycle import PluginLifecycle, PluginLifecycleError
from ..security.pairing import PairingAuthority

if TYPE_CHECKING:
    from .routes import RouteRequest


class PluginRoutes:
    def __init__(self, lifecycle: PluginLifecycle, inspector: PluginArchiveInspector) -> None:
        self._lifecycle = lifecycle
        self._inspector = inspector

    def handle_get(self, request: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        path = request.path.split("?", 1)[0]
        if path != "/v1/management/plugins" and not path.startswith("/v1/management/plugins/"):
            return False
        if not _session(request, pairing, mutation=False):
            return True
        if path == "/v1/management/plugins":
            request.respond_json(200, {"plugins": [_view(item, self._lifecycle) for item in self._lifecycle.list()]})
            return True
        item = self._lifecycle.inspect(path.rsplit("/", 1)[-1])
        if item is None:
            _error(request, 404, "plugin_not_found", "Plugin not found.")
        else:
            request.respond_json(200, _view(item, self._lifecycle))
        return True

    def handle_post(self, request: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        path = request.path.split("?", 1)[0]
        if not path.startswith("/v1/management/plugins"):
            return False
        if not _session(request, pairing, mutation=True):
            return True
        try:
            if path == "/v1/management/plugins/preflight":
                payload = request.request_bytes(max_bytes=16 * 1024 * 1024)
                if payload is None:
                    return True
                inspection = self._inspector.inspect(payload, request.headers.get("X-ReSono-Plugin-Filename", ""))
                result = self._lifecycle.preflight(
                    inspection,
                    audience=AgentAudience(request.headers.get("X-ReSono-Agent-Audience", "")),
                )
                request.respond_json(200, {
                    "state": result.state,
                    "preflightToken": result.token,
                    "candidate": {"name": result.name, "contentHash": result.content_hash},
                    "current": _view(result.current, self._lifecycle) if result.current else None,
                })
                return True
            payload = request.request_json(max_bytes=4096)
            if payload is None:
                return True
            if path == "/v1/management/plugins/confirm":
                item = self._lifecycle.confirm(
                    str(payload.get("preflightToken", "")),
                    replace=payload.get("replace") is True,
                    changed_by="management-api",
                    reason="confirmed Plugin import",
                )
                request.respond_json(201, _view(item, self._lifecycle))
                return True
            name, action = _name_action(path)
            if action == "enable":
                item = self._lifecycle.enable(name, changed_by="management-api", reason="enabled from management")
            elif action == "disable":
                item = self._lifecycle.disable(name, changed_by="management-api", reason="disabled from management")
            else:
                raise PluginLifecycleError("Plugin action is unsupported.")
            request.respond_json(200, _view(item, self._lifecycle))
        except (PluginArchiveRejected, PluginLifecycleError, ValueError) as error:
            _error(request, 409, "plugin_import_conflict", str(error))
        return True

    def handle_delete(self, request: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        path = request.path.split("?", 1)[0]
        if not path.startswith("/v1/management/plugins/"):
            return False
        if not _session(request, pairing, mutation=True):
            return True
        name = path.rsplit("/", 1)[-1]
        try:
            self._lifecycle.delete(name, changed_by="management-api", reason="deleted from management")
        except PluginLifecycleError as error:
            _error(request, 404, "plugin_not_found", str(error))
            return True
        request.respond_json(200, {"name": name, "deleted": True})
        return True


def _view(item: object, lifecycle: PluginLifecycle) -> dict[str, object]:
    return {
        "name": item.name,
        "contentHash": item.content_hash,
        "state": item.lifecycle_state,
        "components": [
            {"type": component.component_type, "key": component.component_key, "state": component.validation_state, "detail": component.detail}
            for component in lifecycle.components(item.name)
        ],
    }


def _name_action(path: str) -> tuple[str, str]:
    parts = path.rsplit("/", 2)
    return (parts[1], parts[2]) if len(parts) == 3 else ("", "")


def _session(request: "RouteRequest", pairing: PairingAuthority | None, *, mutation: bool) -> bool:
    if pairing is None:
        _error(request, 503, "management_unavailable", "Management pairing is unavailable.")
        return False
    return request.browser_session(pairing, mutation=mutation) is not None


def _error(request: "RouteRequest", status: int, code: str, message: str) -> None:
    request.respond_json(status, {"error": {"code": code, "message": message}})
