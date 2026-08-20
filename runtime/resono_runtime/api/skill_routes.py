"""Management-only HTTP routes for standard Agent Skill lifecycle control."""

from __future__ import annotations

from typing import TYPE_CHECKING

from resono_runtime.agents import AgentAudience
from resono_runtime.security.pairing import PairingAuthority
from resono_runtime.skills.archives import SkillArchiveInspector, SkillArchiveRejected
from resono_runtime.skills.lifecycle import SkillLifecycle, SkillLifecycleError, SkillPreflight
from resono_runtime.storage.skills import StoredSkill

if TYPE_CHECKING:
    from .routes import RouteRequest


class SkillRoutes:
    """Configuration transport only: it cannot execute Skills or agent tools."""

    def __init__(self, lifecycle: SkillLifecycle, inspector: SkillArchiveInspector) -> None:
        self._lifecycle = lifecycle
        self._inspector = inspector

    def handle_get(self, req: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        path = req.path.split("?", 1)[0]
        if path != "/v1/management/skills" and not path.startswith("/v1/management/skills/"):
            return False
        if not self._session(req, pairing, mutation=False):
            return True
        if path == "/v1/management/skills":
            req.respond_json(200, {"skills": [_skill_view(item) for item in self._lifecycle.list()]})
            return True
        name = path.rsplit("/", 1)[-1]
        item = self._lifecycle.inspect(name)
        if item is None:
            _not_found(req)
        else:
            req.respond_json(200, _skill_view(item))
        return True

    def handle_post(self, req: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        path = req.path.split("?", 1)[0]
        if not path.startswith("/v1/management/skills"):
            return False
        if not self._session(req, pairing, mutation=True):
            return True
        if path == "/v1/management/skills/preflight":
            content_type = req.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type not in {"application/zip", "application/x-tar", "application/gzip", "text/markdown", "application/octet-stream"}:
                _error(req, 415, "unsupported_media_type", "Upload a raw Skill document, ZIP, or TAR archive.")
                return True
            payload = req.request_bytes(max_bytes=16 * 1024 * 1024)
            if payload is None:
                return True
            try:
                candidate = self._inspector.inspect(payload, req.headers.get("X-ReSono-Skill-Filename", ""))
                audience = AgentAudience(req.headers.get("X-ReSono-Agent-Audience", ""))
                result = self._lifecycle.preflight(candidate, audience=audience)
            except (SkillArchiveRejected, ValueError) as error:
                code = error.code if isinstance(error, SkillArchiveRejected) else "invalid_audience"
                _error(req, 400, code, str(error))
                return True
            req.respond_json(200, _preflight_view(result))
            return True
        payload = req.request_json(max_bytes=4096)
        if payload is None:
            return True
        try:
            if path == "/v1/management/skills/confirm":
                result = self._lifecycle.confirm(
                    str(payload.get("preflightToken", "")),
                    replace=payload.get("replace") is True,
                    changed_by="management-api",
                    reason="confirmed Skill import",
                )
                req.respond_json(201, _skill_view(result))
                return True
            name, action = _name_action(path)
            if action == "enable":
                result = self._lifecycle.enable(name, changed_by="management-api", reason="enabled from management")
            elif action == "disable":
                result = self._lifecycle.disable(name, changed_by="management-api", reason="disabled from management")
            else:
                _not_found(req)
                return True
            req.respond_json(200, _skill_view(result))
        except (SkillLifecycleError, ValueError) as error:
            _error(req, 409, "skill_lifecycle_conflict", str(error))
        return True

    def handle_delete(self, req: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        path = req.path.split("?", 1)[0]
        if not path.startswith("/v1/management/skills/"):
            return False
        if not self._session(req, pairing, mutation=True):
            return True
        name = path.rsplit("/", 1)[-1]
        try:
            removed = self._lifecycle.delete(name, changed_by="management-api", reason="deleted from management")
        except SkillLifecycleError as error:
            _error(req, 404, "skill_not_found", str(error))
            return True
        req.respond_json(200, {"name": removed.name, "deleted": True})
        return True

    @staticmethod
    def _session(req: "RouteRequest", pairing: PairingAuthority | None, *, mutation: bool) -> bool:
        if pairing is None:
            _error(req, 503, "management_unavailable", "Management pairing is unavailable.")
            return False
        return req.browser_session(pairing, mutation=mutation) is not None


def _preflight_view(result: SkillPreflight) -> dict[str, object]:
    item = result.current
    document = result.document
    return {
        "state": result.state,
        "preflightToken": result.token,
        "reason": result.reason,
        "candidate": (
            {
                "name": document.name,
                "description": document.description,
                "contentHash": result.content_hash,
            }
            if document is not None
            else None
        ),
        "current": _skill_view(item) if item is not None else None,
    }


def _skill_view(item: StoredSkill) -> dict[str, object]:
    return {
        "name": item.name,
        "description": item.description,
        "contentHash": item.content_hash,
        "sourceFilename": item.source_filename,
        "state": item.lifecycle_state,
        "createdAt": item.created_at,
        "updatedAt": item.updated_at,
    }


def _name_action(path: str) -> tuple[str, str]:
    parts = path.rsplit("/", 2)
    if len(parts) != 3:
        return "", ""
    return parts[1], parts[2]


def _not_found(req: "RouteRequest") -> None:
    _error(req, 404, "not_found", "Skill not found.")


def _error(req: "RouteRequest", status: int, code: str, message: str) -> None:
    req.respond_json(status, {"error": {"code": code, "message": message}})
