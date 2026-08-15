from __future__ import annotations

from pathlib import Path
import json
import tempfile
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from resono_runtime.api.events import RuntimeEventStream
from resono_runtime.api.http_server import RuntimeHttpServer
from resono_runtime.mcp.server import LocalMcpServer, PROTOCOL_VERSION
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.storage.lifecycle_repository import LifecycleRepository


class RuntimeLifecycleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        database = RuntimeDatabase(Path(self.temporary.name) / "runtime.sqlite3")
        database.migrate()
        self.database = database
        self.lifecycle = LifecycleRepository(database)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_start_count_persists_across_repository_instances(self) -> None:
        self.assertEqual("1", self.lifecycle.record_start().value)
        second = LifecycleRepository(self.database)
        self.assertEqual("2", second.record_start().value)

    def test_authenticated_health_and_unknown_route(self) -> None:
        token = "t" * 43
        self.lifecycle.record_start()
        server = RuntimeHttpServer(
            host="127.0.0.1",
            port=0,
            token=token,
            health=lambda: {"status": "ready", "database": self.database.health()},
            lifecycle=self.lifecycle,
            events=RuntimeEventStream(),
        )
        server.start()
        try:
            base = f"http://127.0.0.1:{server.port}"
            with self.assertRaises(HTTPError) as unauthorized:
                urlopen(base + "/v1/health", timeout=2)
            self.assertEqual(401, unauthorized.exception.code)

            wrong = Request(
                base + "/v1/health",
                headers={"Authorization": "Bearer " + ("x" * 43)},
            )
            with self.assertRaises(HTTPError) as wrong_token:
                urlopen(wrong, timeout=2)
            self.assertEqual(401, wrong_token.exception.code)

            request = Request(base + "/v1/health", headers={"Authorization": f"Bearer {token}"})
            with urlopen(request, timeout=2) as response:
                payload = json.loads(response.read())
            self.assertEqual("ready", payload["status"])

            missing = Request(base + "/v1/missing", headers={"Authorization": f"Bearer {token}"})
            with self.assertRaises(HTTPError) as not_found:
                urlopen(missing, timeout=2)
            self.assertEqual(404, not_found.exception.code)

            record = Request(
                base + "/v1/lifecycle-records/runtime.start_count",
                headers={"Authorization": f"Bearer {token}"},
            )
            with urlopen(record, timeout=2) as response:
                record_payload = json.loads(response.read())
            self.assertEqual("runtime.start_count", record_payload["key"])
            self.assertEqual("1", record_payload["value"])
        finally:
            server.stop()

    def test_event_stream_preserves_order(self) -> None:
        events = RuntimeEventStream()
        latest, subscriber = events.subscribe()
        self.assertEqual("runtime.starting", latest.event_type)

        first = events.publish("runtime.ready", {"status": "ready"})
        second = events.publish("runtime.stopping", {"status": "stopping"})

        self.assertEqual(first, events.next_event(subscriber, timeout=0.1))
        self.assertEqual(second, events.next_event(subscriber, timeout=0.1))
        self.assertLess(first.sequence, second.sequence)
        events.unsubscribe(subscriber)

    def test_authenticated_mcp_http_lifecycle_and_tool_call(self) -> None:
        token = "m" * 43
        server = RuntimeHttpServer(
            host="127.0.0.1",
            port=0,
            token=token,
            health=lambda: {
                "status": "ready",
                "service": "resono-runtime",
                "contractVersion": 1,
            },
            lifecycle=self.lifecycle,
            events=RuntimeEventStream(),
            mcp=LocalMcpServer(
                lambda: {
                    "status": "ready",
                    "service": "resono-runtime",
                    "contractVersion": 1,
                }
            ),
        )
        server.start()
        try:
            base = f"http://127.0.0.1:{server.port}/v1/mcp"

            def post(message, *, session_id=None):
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                }
                if session_id:
                    headers["Mcp-Session-Id"] = session_id
                    headers["MCP-Protocol-Version"] = PROTOCOL_VERSION
                request = Request(
                    base,
                    data=json.dumps(message).encode(),
                    headers=headers,
                    method="POST",
                )
                with urlopen(request, timeout=2) as response:
                    body = response.read()
                    return (
                        json.loads(body) if body else None,
                        response.headers.get("Mcp-Session-Id"),
                    )

            initialized, session_id = post(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": PROTOCOL_VERSION,
                        "capabilities": {},
                        "clientInfo": {"name": "http-test", "version": "1"},
                    },
                }
            )
            self.assertEqual(PROTOCOL_VERSION, initialized["result"]["protocolVersion"])
            self.assertTrue(session_id)

            post(
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                session_id=session_id,
            )
            called, _ = post(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "get_device_status", "arguments": {}},
                },
                session_id=session_id,
            )
            self.assertFalse(called["result"]["isError"])
            self.assertEqual("ready", called["result"]["structuredContent"]["status"])
        finally:
            server.stop()

    def test_corrupt_database_reports_not_ready_without_details(self) -> None:
        path = Path(self.temporary.name) / "corrupt.sqlite3"
        path.write_bytes(b"not a sqlite database")

        health = RuntimeDatabase(path).health()

        self.assertEqual({"status": "not_ready", "migrationVersion": 0}, health)

    def test_private_server_rejects_non_loopback_bind(self) -> None:
        with self.assertRaisesRegex(ValueError, "must bind to loopback"):
            RuntimeHttpServer(
                host="0.0.0.0",
                port=0,
                token="t" * 43,
                health=lambda: {"status": "ready"},
                lifecycle=self.lifecycle,
                events=RuntimeEventStream(),
            )


if __name__ == "__main__":
    unittest.main()
