from __future__ import annotations

import unittest

from types import ModuleType

from resono_runtime.core.runtime_environment import agent_runtime_status, standard_library_status


class RuntimeEnvironmentTest(unittest.TestCase):
    def test_required_standard_library_modules_import(self) -> None:
        status = standard_library_status()

        self.assertEqual("ready", status["status"])
        self.assertEqual(["asyncio", "http.server", "sqlite3", "ssl"], status["imports"])
        self.assertTrue(status["pythonVersion"].startswith("3.13."))
        self.assertTrue(status["sqliteVersion"])
        self.assertIn("OpenSSL", status["opensslVersion"])

    def test_agent_runtime_requires_every_packaged_module(self) -> None:
        available = {name: ModuleType(name) for name in ("jiter", "pydantic_core", "rpds", "openai", "agents")}

        ready = agent_runtime_status(available.__getitem__)
        self.assertEqual("ready", ready["status"])
        self.assertEqual(["jiter", "pydantic_core", "rpds", "openai", "agents"], ready["imports"])

        def missing(name: str) -> ModuleType:
            if name == "openai":
                raise ImportError("missing")
            return available[name]

        unavailable = agent_runtime_status(missing)
        self.assertEqual("not_ready", unavailable["status"])
        self.assertEqual(["jiter", "pydantic_core", "rpds"], unavailable["imports"])
