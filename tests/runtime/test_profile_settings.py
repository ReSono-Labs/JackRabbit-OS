from __future__ import annotations

from datetime import datetime
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.storage.profile_settings import UserProfileRepository


class UserProfileRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        database = RuntimeDatabase(Path(self.temporary.name) / "runtime.sqlite3")
        database.migrate()
        self.profile = UserProfileRepository(database)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_name_persists_and_can_be_cleared(self) -> None:
        self.assertIsNone(self.profile.profile().display_name)
        self.assertEqual("Christian", self.profile.save("  Christian  ").display_name)
        self.assertIsNone(self.profile.save("").display_name)

    def test_connect_greeting_matches_browser_voice_contract(self) -> None:
        self.profile.save("Christian")
        local_time = datetime.now().astimezone().replace(hour=9)
        with patch("resono_runtime.storage.profile_settings.datetime") as clock:
            clock.now.return_value.astimezone.return_value = local_time
            event = self.profile.connect_greeting_event()
        self.assertEqual(
            {
                "type": "response.create",
                "response": {
                    "instructions": 'Say exactly: "Good morning Christian, what can I help you with this morning?" Then stop and wait for the user.'
                },
            },
            event,
        )

    def test_invalid_name_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.profile.save("x" * 81)


if __name__ == "__main__":
    unittest.main()
