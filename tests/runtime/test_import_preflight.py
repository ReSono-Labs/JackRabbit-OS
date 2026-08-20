from __future__ import annotations

from datetime import UTC, datetime, timedelta
import unittest

from resono_runtime.agents import AgentAudience
from resono_runtime.imports import ImportPreflightError, ImportPreflightRegistry


class ImportPreflightRegistryTest(unittest.TestCase):
    def test_binds_identity_hash_and_audience_until_one_successful_confirmation(self) -> None:
        registry: ImportPreflightRegistry[str] = ImportPreflightRegistry()
        issued = registry.issue(
            identity="planning",
            candidate_hash="candidate",
            current_hash="current",
            audience=AgentAudience.TEXT,
            payload="candidate-path",
        )

        self.assertEqual("conflict", issued.state)
        self.assertEqual(AgentAudience.TEXT, registry.peek(issued.token).audience)
        consumed = registry.consume(issued.token, current_hash="current", replace=True)

        self.assertEqual("planning", consumed.identity)
        with self.assertRaisesRegex(ImportPreflightError, "already used"):
            registry.peek(issued.token)

    def test_stale_current_hash_does_not_consume_the_reviewed_record(self) -> None:
        registry: ImportPreflightRegistry[str] = ImportPreflightRegistry()
        issued = registry.issue(
            identity="planning",
            candidate_hash="candidate",
            current_hash="reviewed",
            audience=AgentAudience.VOICE,
            payload="candidate-path",
        )

        with self.assertRaisesRegex(ImportPreflightError, "changed after preflight"):
            registry.consume(issued.token, current_hash="changed", replace=True)

        self.assertEqual("planning", registry.peek(issued.token).identity)

    def test_expired_record_cannot_be_confirmed(self) -> None:
        now = [datetime.now(UTC)]
        registry: ImportPreflightRegistry[str] = ImportPreflightRegistry(clock=lambda: now[0])
        issued = registry.issue(
            identity="planning",
            candidate_hash="candidate",
            current_hash=None,
            audience=AgentAudience.BOTH,
            payload="candidate-path",
        )
        now[0] += timedelta(minutes=11)

        with self.assertRaisesRegex(ImportPreflightError, "expired"):
            registry.consume(issued.token, current_hash=None, replace=False)


if __name__ == "__main__":
    unittest.main()
