"""Paired management routes for the two canonical R1 SKILLS.MD documents."""
from __future__ import annotations
from typing import TYPE_CHECKING
from resono_runtime.security.pairing import PairingAuthority
from resono_runtime.skills.documents import AgentInstructionDocuments, AgentInstructionsError, InstructionDocument
if TYPE_CHECKING:
    from .routes import RouteRequest

class SkillRoutes:
    def __init__(self, documents: AgentInstructionDocuments) -> None: self._documents = documents
    def handle_get(self, req: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        if req.path.split("?", 1)[0] != "/v1/management/skills": return False
        if not self._session(req, pairing, mutation=False): return True
        req.respond_json(200, {"skills": [_view(item) for item in self._documents.list()]}); return True
    def handle_post(self, req: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        path = req.path.split("?", 1)[0]
        if path not in {"/v1/management/skills/preflight", "/v1/management/skills/confirm"}: return False
        if not self._session(req, pairing, mutation=True): return True
        try:
            if path.endswith("/preflight"):
                payload = req.request_bytes(max_bytes=256 * 1024)
                if payload is None: return True
                result = self._documents.preflight(payload, filename=req.headers.get("X-ReSono-Skill-Filename", ""), destination=req.headers.get("X-ReSono-Agent-Audience", ""))
                req.respond_json(200, {"state": result.state, "preflightToken": result.token,
                    "candidate": {"name": "SKILLS.MD", "description": _label(result.destination), "contentHash": result.content_hash, "destination": result.destination, "byteSize": result.byte_size},
                    "current": _view(self._documents.get(result.destination)) if result.state == "conflict" else None})
                return True
            body = req.request_json(max_bytes=4096)
            if body is None: return True
            item = self._documents.confirm(str(body.get("preflightToken", "")), replace=body.get("replace") is True)
            req.respond_json(201, _view(item))
        except AgentInstructionsError as error:
            req.respond_json(409, {"error": {"code": "instruction_document_conflict", "message": str(error)}})
        return True
    def handle_delete(self, req: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        path = req.path.split("?", 1)[0]
        if not path.startswith("/v1/management/skills/"): return False
        if not self._session(req, pairing, mutation=True): return True
        destination = path.rsplit("/", 1)[-1]
        try: self._documents.delete(destination); req.respond_json(200, {"name": destination, "deleted": True})
        except AgentInstructionsError as error: req.respond_json(404, {"error": {"code": "instruction_document_not_found", "message": str(error)}})
        return True
    @staticmethod
    def _session(req: "RouteRequest", pairing: PairingAuthority | None, *, mutation: bool) -> bool:
        if pairing is None:
            req.respond_json(503, {"error": {"code": "management_unavailable", "message": "Management pairing is unavailable."}}); return False
        return req.browser_session(pairing, mutation=mutation) is not None

def _label(destination: str) -> str: return "Voice instructions" if destination == "voice" else "Background Agent instructions"
def _view(item: InstructionDocument | None) -> dict[str, object] | None:
    if item is None: return None
    return {"name": item.destination, "displayName": _label(item.destination), "description": "Canonical SKILLS.MD", "contentHash": item.content_hash, "sourceFilename": "SKILLS.MD", "state": "enabled", "byteSize": item.byte_size}
