from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from resono_runtime.core.release_supervisor import ReleaseSupervisor, RuntimeRelease


class ReleaseSupervisorTest(unittest.TestCase):
    def test_healthy_activation_becomes_last_good(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            supervisor = ReleaseSupervisor(Path(directory))
            supervisor.prepare()
            candidate = RuntimeRelease("runtime-0.3.1", 1)

            self.assertTrue(supervisor.activate(candidate, lambda release: True))
            self.assertEqual(candidate, supervisor.active())

            restarted = ReleaseSupervisor(Path(directory))
            self.assertEqual(candidate, restarted.prepare())

    def test_unhealthy_activation_rolls_back(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            supervisor = ReleaseSupervisor(Path(directory))
            baseline = supervisor.prepare()

            self.assertFalse(supervisor.activate(
                RuntimeRelease("broken", 1),
                lambda release: False,
            ))
            self.assertEqual(baseline, supervisor.active())

    def test_interrupted_activation_recovers_last_good(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            supervisor = ReleaseSupervisor(root)
            baseline = supervisor.prepare()
            (root / "active.json").write_text(
                '{"contractVersion":1,"releaseId":"interrupted"}',
                encoding="utf-8",
            )

            self.assertEqual(baseline, ReleaseSupervisor(root).prepare())
            self.assertEqual(baseline, ReleaseSupervisor(root).active())

    def test_release_identifier_cannot_escape_release_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            supervisor = ReleaseSupervisor(Path(directory))
            supervisor.prepare()
            with self.assertRaisesRegex(ValueError, "identifier"):
                supervisor.activate(RuntimeRelease("../outside", 1), lambda release: True)

    def test_truncated_active_pointer_recovers_last_good(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            supervisor = ReleaseSupervisor(root)
            baseline = supervisor.prepare()
            (root / "active.json").write_text("", encoding="utf-8")

            self.assertEqual(baseline, ReleaseSupervisor(root).prepare())
            self.assertEqual(baseline, ReleaseSupervisor(root).active())


if __name__ == "__main__":
    unittest.main()
