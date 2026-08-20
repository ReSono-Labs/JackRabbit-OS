import unittest

from resono_runtime.api.connection_routes import ConnectionRoutes
from resono_runtime.api.creation_routes import CreationRoutes
from resono_runtime.api.mail_routes import MailRoutes
from resono_runtime.api.mcp_routes import McpRoutes
from resono_runtime.api.plugin_routes import PluginRoutes
from resono_runtime.api.skill_routes import SkillRoutes
from resono_runtime.api.tool_routes import ToolRoutes


class Build07ApiAuthenticationTest(unittest.TestCase):
    def test_every_management_route_rejects_unpaired_access(self) -> None:
        owner = object()
        cases = (
            (SkillRoutes(owner, owner), "/v1/management/skills", True),
            (MailRoutes(owner, owner), "/v1/management/mail/accounts", True),
            (PluginRoutes(owner, owner), "/v1/management/plugins", True),
            (McpRoutes(owner), "/v1/management/mcp/connections", True),
            (CreationRoutes(owner, owner, owner), "/v1/management/creations", True),
            (CreationRoutes(owner, owner, owner), "/v1/management/creations/qr/preflight", True),
            (ToolRoutes(owner), "/v1/management/tools", False),
            (ConnectionRoutes(owner), "/v1/management/connections", False),
        )
        for routes, path, mutating in cases:
            with self.subTest(path=path, method="GET"):
                request = _Request(path)
                self.assertTrue(routes.handle_get(request, None))
                self.assertEqual(503, request.status)
            if not mutating:
                continue
            with self.subTest(path=path, method="POST"):
                request = _Request(path)
                self.assertTrue(routes.handle_post(request, None))
                self.assertEqual(503, request.status)
            delete_path = path + "/example"
            with self.subTest(path=delete_path, method="DELETE"):
                request = _Request(delete_path)
                self.assertTrue(routes.handle_delete(request, None))
                self.assertEqual(503, request.status)


class _Request:
    def __init__(self, path: str) -> None:
        self.path = path
        self.headers = {}
        self.status = 0

    def browser_session(self, authority: object, *, mutation: bool):
        raise AssertionError("Pairing authority is absent; session lookup must not run.")

    def respond_json(self, status: int, payload: dict[str, object], *, headers=None) -> None:
        del payload, headers
        self.status = status


if __name__ == "__main__":
    unittest.main()
