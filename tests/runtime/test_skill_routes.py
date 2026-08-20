from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from resono_runtime.agents import AgentAudienceRouter
from resono_runtime.api.skill_routes import SkillRoutes
from resono_runtime.security.pairing import PairingAuthority
from resono_runtime.skills.archives import SkillArchiveInspector
from resono_runtime.skills.lifecycle import SkillLifecycle
from resono_runtime.storage.agent_audiences import AgentAudienceRepository
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.storage.skills import SkillCatalogRepository


class SkillRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        root = Path(self._temporary.name)
        database = RuntimeDatabase(root / "runtime.sqlite3")
        database.migrate()
        lifecycle = SkillLifecycle(
            catalog=SkillCatalogRepository(database),
            audiences=AgentAudienceRouter(AgentAudienceRepository(database)),
            skills_root=root / "skills",
            rollback_root=root / "rollbacks",
        )
        self.routes = SkillRoutes(lifecycle, SkillArchiveInspector(root / "quarantine"))
        self.pairing = PairingAuthority()

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def test_preflight_and_confirm_are_management_configuration_only(self) -> None:
        request = _Request(
            "/v1/management/skills/preflight",
            raw=b"---\nname: planning\ndescription: Plan meetings.\n---\nUse the calendar.",
            headers={
                "X-ReSono-Skill-Filename": "skills.md",
                "X-ReSono-Agent-Audience": "voice",
                "Content-Type": "text/markdown",
            },
        )

        self.assertTrue(self.routes.handle_post(request, self.pairing))
        self.assertEqual(200, request.status)
        self.assertEqual("new", request.payload["state"])
        self.assertNotIn("instructions", str(request.payload))

        confirm = _Request(
            "/v1/management/skills/confirm",
            json_body={"preflightToken": request.payload["preflightToken"], "replace": False},
        )
        self.routes.handle_post(confirm, self.pairing)
        self.assertEqual(201, confirm.status)
        self.assertEqual("planning", confirm.payload["name"])

    def test_unknown_route_is_not_claimed(self) -> None:
        request = _Request("/v1/management/other")
        self.assertFalse(self.routes.handle_get(request, self.pairing))


class _Request:
    def __init__(self, path: str, *, raw: bytes | None = None, json_body: dict[str, object] | None = None, headers: dict[str, str] | None = None) -> None:
        self.path = path
        self.headers = headers or {}
        self._raw = raw
        self._json = json_body
        self.status: int | None = None
        self.payload: dict[str, object] | None = None

    def respond_json(self, status: int, payload: dict[str, object], *, headers: dict[str, str] | None = None) -> None:
        self.status = status
        self.payload = payload

    def respond_empty(self, status: int, *, headers: dict[str, str] | None = None) -> None:
        self.status = status

    def stream_events(self) -> None:
        raise AssertionError("not expected")

    def browser_session(self, authority: PairingAuthority, *, mutation: bool) -> object:
        return object()

    def request_json(self, *, max_bytes: int = 4096) -> dict[str, object] | None:
        return self._json

    def request_bytes(self, *, max_bytes: int) -> bytes | None:
        return self._raw

    def provider_error(self, error: object) -> None:
        raise AssertionError("not expected")
