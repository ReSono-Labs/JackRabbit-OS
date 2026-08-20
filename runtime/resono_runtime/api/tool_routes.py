"""Support-safe projection of the canonical runtime tool catalog."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..security.pairing import PairingAuthority
from ..tools import ToolCatalog

if TYPE_CHECKING:
    from .routes import RouteRequest


class ToolRoutes:
    def __init__(self, catalog: ToolCatalog) -> None:
        self._catalog = catalog

    def handle_get(self, request: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        if request.path.split("?", 1)[0] != "/v1/management/tools":
            return False
        if pairing is None or request.browser_session(pairing, mutation=False) is None:
            if pairing is None:
                request.respond_json(503, {"error": {"code": "management_unavailable", "message": "Management pairing is unavailable."}})
            return True
        request.respond_json(200, {"tools": list(self._catalog.management_projection())})
        return True
