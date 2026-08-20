from __future__ import annotations

import json
from pathlib import Path
import tempfile
import threading
import unittest
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from resono_runtime.api.events import RuntimeEventStream
from resono_runtime.api.http_server import RuntimeHttpServer
from resono_runtime.security.pairing import PairingAuthority, PairingDenied
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.storage.lifecycle_repository import LifecycleRepository


class ManagementPairingTest(unittest.TestCase):
    def test_code_is_one_time_and_session_is_bound_to_exact_origin(self) -> None:
        now = [1_000]
        authority = PairingAuthority(clock=lambda: now[0])
        code = authority.current_code()
        session = authority.pair(code.value, "https://r1.local:8443", "https://r1.local:8443")

        authority.authorize(session.token, "https://r1.local:8443")
        with self.assertRaises(PairingDenied):
            authority.pair(code.value, "https://r1.local:8443", "https://r1.local:8443")
        with self.assertRaises(PairingDenied):
            authority.authorize(session.token, "https://other.local:8443")

        now[0] = session.expires_at
        with self.assertRaises(PairingDenied):
            authority.authorize(session.token, "https://r1.local:8443")

    def test_mutation_requires_origin_and_csrf(self) -> None:
        authority = PairingAuthority()
        code = authority.current_code()
        session = authority.pair(code.value, "https://r1.local:8443", "https://r1.local:8443")

        with self.assertRaises(PairingDenied):
            authority.authorize(
                session.token,
                session.origin,
                request_origin=session.origin,
                csrf_token="wrong",
                mutation=True,
            )
        authority.authorize(
            session.token,
            session.origin,
            request_origin=session.origin,
            csrf_token=session.csrf_token,
            mutation=True,
        )

    def test_http_pair_status_and_restart_are_real(self) -> None:
        token = "t" * 43
        origin = "https://r1.local:8443"
        restarted = threading.Event()
        with tempfile.TemporaryDirectory() as directory:
            database = RuntimeDatabase(Path(directory) / "runtime.sqlite3")
            database.migrate()
            lifecycle = LifecycleRepository(database)
            lifecycle.record_start()
            pairing = PairingAuthority()
            text_runner = SimpleNamespace(
                run=lambda value, session_id=None: SimpleNamespace(text=f"Reply: {value}", model="gpt-5.4-mini")
            )
            server = RuntimeHttpServer(
                host="127.0.0.1",
                port=0,
                token=token,
                health=lambda: {"contractVersion": 1, "status": "ready", "database": database.health()},
                lifecycle=lifecycle,
                events=RuntimeEventStream(),
                pairing=pairing,
                text_runner=text_runner,
                restart_request=restarted.set,
            )
            server.start()
            try:
                base = f"http://127.0.0.1:{server.port}"
                local_headers = {"Authorization": f"Bearer {token}"}
                with urlopen(Request(base + "/v1/management/pairing", headers=local_headers), timeout=2) as response:
                    code = json.loads(response.read())["code"]

                pair_request = Request(
                    base + "/v1/management/pair",
                    data=json.dumps({"code": code}).encode(),
                    headers={
                        **local_headers,
                        "Content-Type": "application/json",
                        "X-ReSono-Forwarded-Origin": origin,
                        "Origin": origin,
                    },
                    method="POST",
                )
                with urlopen(pair_request, timeout=2) as response:
                    paired = json.loads(response.read())
                    cookie = response.headers["Set-Cookie"].split(";", 1)[0]

                browser_headers = {
                    **local_headers,
                    "Cookie": cookie,
                    "X-ReSono-Forwarded-Origin": origin,
                }
                with urlopen(Request(base + "/v1/management/status", headers=browser_headers), timeout=2) as response:
                    self.assertEqual("ready", json.loads(response.read())["status"])

                text_turn = Request(
                    base + "/v1/management/text/turns",
                    data=json.dumps({"input": "Hello"}).encode(),
                    headers={
                        **browser_headers,
                        "Origin": origin,
                        "X-CSRF-Token": paired["csrfToken"],
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with urlopen(text_turn, timeout=2) as response:
                    text_payload = json.loads(response.read())
                self.assertEqual("Reply: Hello", text_payload["text"])
                self.assertEqual("gpt-5.4-mini", text_payload["model"])

                denied_restart = Request(
                    base + "/v1/management/restart",
                    data=b"{}",
                    headers={**browser_headers, "Origin": origin, "X-CSRF-Token": "wrong"},
                    method="POST",
                )
                with self.assertRaises(HTTPError) as denied:
                    urlopen(denied_restart, timeout=2)
                self.assertEqual(403, denied.exception.code)

                restart = Request(
                    base + "/v1/management/restart",
                    data=b"{}",
                    headers={
                        **browser_headers,
                        "Origin": origin,
                        "X-CSRF-Token": paired["csrfToken"],
                    },
                    method="POST",
                )
                with urlopen(restart, timeout=2) as response:
                    self.assertEqual(202, response.status)
                self.assertTrue(restarted.wait(timeout=1))
            finally:
                server.stop()


if __name__ == "__main__":
    unittest.main()
