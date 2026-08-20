from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.storage.provider_catalog import ProviderCatalogRepository


class ProviderCatalogTest(unittest.TestCase):
    def test_bootstrap_creates_openai_defaults(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        database = RuntimeDatabase(Path(temporary.name) / "runtime.sqlite3")
        database.migrate()
        repository = ProviderCatalogRepository(database)

        repository.bootstrap_defaults()

        providers = repository.providers()
        self.assertEqual(1, len(providers))
        self.assertEqual("openai", providers[0].provider_id)
        self.assertEqual("OpenAI", providers[0].name)

        text = repository.models("openai", "subscription", "text")
        realtime = repository.models("openai", "subscription", "realtime")
        self.assertEqual(("gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"), text)
        self.assertEqual(("gpt-realtime-2.1", "gpt-realtime-2.1-mini", "gpt-live-1"), realtime)

        temporary.cleanup()


if __name__ == "__main__":
    unittest.main()
