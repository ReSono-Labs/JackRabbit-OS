from __future__ import annotations

from io import BytesIO
from pathlib import Path
import tarfile
import tempfile
import unittest
import zipfile

from resono_runtime.skills.archives import SkillArchiveInspector, SkillArchiveRejected


class SkillArchiveInspectorTest(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.inspector = SkillArchiveInspector(Path(self._temporary.name) / "quarantine")

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def test_accepts_standalone_compatibility_filename(self) -> None:
        result = self.inspector.inspect(b"---\nname: planning\ndescription: Plan well.\n---\n", "SKILLS.MD")

        self.assertEqual("document", result.archive_format)
        self.assertEqual("SKILL.md", result.canonical_document_name)
        self.assertEqual("SKILLS.MD", result.source_document.name)

    def test_accepts_one_skill_document_in_zip(self) -> None:
        result = self.inspector.inspect(_zip({"planning/SKILL.md": b"instructions"}), "planning.zip")

        self.assertEqual(("planning/SKILL.md",), result.retained_paths)
        self.assertTrue(result.source_document.is_file())

    def test_rejects_path_traversal(self) -> None:
        with self.assertRaisesRegex(SkillArchiveRejected, "unsafe path"):
            self.inspector.inspect(_zip({"../SKILL.md": b"instructions"}), "planning.zip")

    def test_rejects_multiple_skill_documents(self) -> None:
        with self.assertRaisesRegex(SkillArchiveRejected, "exactly one"):
            self.inspector.inspect(
                _zip({"one/SKILL.md": b"a", "two/skills.md": b"b"}),
                "planning.zip",
            )

    def test_rejects_unrelated_sibling_root(self) -> None:
        with self.assertRaisesRegex(SkillArchiveRejected, "one top-level"):
            self.inspector.inspect(
                _zip({"planning/SKILL.md": b"instructions", "unrelated/data.txt": b"data"}),
                "planning.zip",
            )

    def test_rejects_nested_archive(self) -> None:
        with self.assertRaisesRegex(SkillArchiveRejected, "Nested archives"):
            self.inspector.inspect(
                _zip({"planning/SKILL.md": b"instructions", "planning/payload.zip": b"not used"}),
                "planning.zip",
            )

    def test_rejects_tar_link(self) -> None:
        payload = BytesIO()
        with tarfile.open(fileobj=payload, mode="w") as archive:
            link = tarfile.TarInfo("planning/SKILL.md")
            link.type = tarfile.SYMTYPE
            link.linkname = "/outside"
            archive.addfile(link)

        with self.assertRaisesRegex(SkillArchiveRejected, "regular files only"):
            self.inspector.inspect(payload.getvalue(), "planning.tar")


def _zip(files: dict[str, bytes]) -> bytes:
    payload = BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return payload.getvalue()


if __name__ == "__main__":
    unittest.main()
