"""Authenticated read projection for every configured external Connection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..connections import ConnectionRepository
from ..security.pairing import PairingAuthority

if TYPE_CHECKING:
    from .routes import RouteRequest


class ConnectionRoutes:
    def __init__(self, connections: ConnectionRepository) -> None:
        self._connections = connections

    def handle_get(self, request: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        path = request.path.split("?", 1)[0]
        if path != "/v1/management/connections" and not path.startswith("/v1/management/connections/"):
            return False
        if pairing is None:
            request.respond_json(503, {"error": {"code": "management_unavailable", "message": "Management pairing is unavailable."}})
            return True
        if request.browser_session(pairing, mutation=False) is None:
            return True
        if path == "/v1/management/connections":
            request.respond_json(200, {"connections": [_view(item) for item in self._connections.list()]})
            return True
        item = self._connections.get(path.rsplit("/", 1)[-1])
        if item is None:
            request.respond_json(404, {"error": {"code": "connection_not_found", "message": "Connection not found."}})
        else:
            request.respond_json(200, _view(item))
        return True


def _view(item: object) -> dict[str, object]:
    return {
        "connectionId": item.connection_id,
        "kind": item.kind,
        "label": item.label,
        "enabled": item.enabled,
        "healthState": item.health_state,
        "healthDetail": item.health_detail,
        "sourceOwner": item.source_owner,
        "credentialPresent": item.credential_present,
        "createdAt": item.created_at,
        "updatedAt": item.updated_at,
    }
