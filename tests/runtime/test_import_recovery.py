from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from resono_runtime.imports import ImportRecovery
from resono_runtime.storage.database import RuntimeDatabase


class ImportRecoveryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database = RuntimeDatabase(self.root / "runtime.sqlite3")
        self.database.migrate()
        self.recovery = ImportRecovery(self.database)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_planned_operation_never_deletes_existing_install(self) -> None:
        target, backup, staged = self._paths()
        target.mkdir(parents=True)
        (target / "value").write_text("current", encoding="utf-8")
        staged.mkdir(parents=True)
        operation = self.recovery.begin(
            resource_kind="skill",
            identity="example",
            candidate_hash="candidate",
            target=target,
            backup=backup,
            staged=staged,
        )

        self.recovery.recover("skill", lambda _: "current")

        self.assertEqual("current", (target / "value").read_text(encoding="utf-8"))
        self.assertFalse(staged.parent.exists())
        self.assertIsNotNone(operation.operation_id)

    def test_activated_uncommitted_candidate_restores_backup(self) -> None:
        target, backup, staged = self._paths()
        backup.mkdir(parents=True)
        (backup / "value").write_text("current", encoding="utf-8")
        target.mkdir(parents=True)
        (target / "value").write_text("candidate", encoding="utf-8")
        staged.mkdir(parents=True)
        operation = self.recovery.begin(
            resource_kind="plugin",
            identity="example",
            candidate_hash="candidate",
            target=target,
            backup=backup,
            staged=staged,
        )
        self.recovery.mark_backup_secured(operation)
        self.recovery.mark_activated(operation)

        self.recovery.recover("plugin", lambda _: "current")

        self.assertEqual("current", (target / "value").read_text(encoding="utf-8"))
        self.assertFalse(backup.exists())

    def test_committed_candidate_keeps_target_and_discards_backup(self) -> None:
        target, backup, staged = self._paths()
        backup.mkdir(parents=True)
        (backup / "value").write_text("current", encoding="utf-8")
        target.mkdir(parents=True)
        (target / "value").write_text("candidate", encoding="utf-8")
        staged.mkdir(parents=True)
        operation = self.recovery.begin(
            resource_kind="creation",
            identity="example",
            candidate_hash="candidate",
            target=target,
            backup=backup,
            staged=staged,
        )
        self.recovery.mark_backup_secured(operation)
        self.recovery.mark_activated(operation)

        self.recovery.recover("creation", lambda _: "candidate")

        self.assertEqual("candidate", (target / "value").read_text(encoding="utf-8"))
        self.assertFalse(backup.exists())

    def _paths(self) -> tuple[Path, Path, Path]:
        return self.root / "installed" / "example", self.root / "rollback" / "example", self.root / "staging" / "run" / "example"


if __name__ == "__main__":
    unittest.main()
