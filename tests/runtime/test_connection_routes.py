from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from resono_runtime.api.connection_routes import ConnectionRoutes
from resono_runtime.connections import ConnectionRepository
from resono_runtime.storage.database import RuntimeDatabase


class ConnectionRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        database = RuntimeDatabase(Path(self.temporary.name) / "runtime.sqlite3")
        database.migrate()
        self.repository = ConnectionRepository(database)
        self.routes = ConnectionRoutes(self.repository)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_projection_requires_pairing_and_never_returns_credentials(self) -> None:
        connection_id = str(uuid4())
        self.repository.save(
            connection_id=connection_id,
            kind="mcp",
            label="Example",
            enabled=False,
            health_state="disabled",
        )
        denied = _Request("/v1/management/connections", authenticated=False)
        self.assertTrue(self.routes.handle_get(denied, None))
        self.assertEqual(503, denied.status)

        allowed = _Request("/v1/management/connections", authenticated=True)
        self.assertTrue(self.routes.handle_get(allowed, object()))
        self.assertEqual(200, allowed.status)
        view = allowed.payload["connections"][0]
        self.assertEqual(connection_id, view["connectionId"])
        self.assertFalse(view["credentialPresent"])
        self.assertNotIn("credential", view)
        self.assertNotIn("envelope", view)


class _Request:
    def __init__(self, path: str, *, authenticated: bool) -> None:
        self.path = path
        self.headers = {}
        self.authenticated = authenticated
        self.status = 0
        self.payload = {}

    def browser_session(self, authority: object, *, mutation: bool):
        del authority, mutation
        return object() if self.authenticated else None

    def respond_json(self, status: int, payload: dict[str, object], *, headers=None) -> None:
        del headers
        self.status = status
        self.payload = payload


if __name__ == "__main__":
    unittest.main()
