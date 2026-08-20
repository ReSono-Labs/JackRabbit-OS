"""Safe intake of one standard Agent Skill document or archive into quarantine."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath
import shutil
import stat
import tarfile
import uuid
import zipfile


MAX_UPLOAD_BYTES = 16 * 1024 * 1024
MAX_EXPANDED_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 256
MAX_COMPRESSION_RATIO = 100
CANONICAL_SKILL_DOCUMENT = "SKILL.md"
ACCEPTED_SKILL_DOCUMENT_NAMES = frozenset({"SKILL.md", "SKILLS.MD", "skills.md"})


class SkillArchiveRejected(ValueError):
    """A candidate was rejected before it could enter the Skill lifecycle."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code


@dataclass(frozen=True, slots=True)
class SkillArchiveInspection:
    candidate_id: str
    archive_format: str
    source_filename: str
    quarantine_root: Path
    content_root: Path
    source_document: Path
    canonical_document_name: str
    retained_paths: tuple[str, ...]
    uploaded_bytes: int
    expanded_bytes: int


@dataclass(frozen=True, slots=True)
class _ArchiveEntry:
    path: PurePosixPath
    size: int
    compressed_size: int
    reader: object


class SkillArchiveInspector:
    """Validates archive structure before writing one quarantined candidate."""

    def __init__(self, quarantine_root: Path) -> None:
        self._quarantine_root = quarantine_root

    def inspect(self, payload: bytes, source_filename: str) -> SkillArchiveInspection:
        filename = _validated_filename(source_filename)
        if not payload:
            raise SkillArchiveRejected("empty_upload", "The uploaded Skill is empty.")
        if len(payload) > MAX_UPLOAD_BYTES:
            raise SkillArchiveRejected("upload_too_large", "The uploaded Skill exceeds the size limit.")
        if filename in ACCEPTED_SKILL_DOCUMENT_NAMES:
            return self._quarantine_document(payload, filename)
        archive_format = _archive_format(filename)
        entries = _read_archive(payload, archive_format)
        _validate_entries(entries, archive_bytes=len(payload), archive_format=archive_format)
        document = _find_skill_document(entries)
        return self._quarantine_archive(entries, document, archive_format, filename, len(payload))

    def _quarantine_document(self, payload: bytes, filename: str) -> SkillArchiveInspection:
        candidate_root, content_root = self._new_candidate_root()
        document = content_root / filename
        document.write_bytes(payload)
        return SkillArchiveInspection(
            candidate_id=candidate_root.name,
            archive_format="document",
            source_filename=filename,
            quarantine_root=candidate_root,
            content_root=content_root,
            source_document=document,
            canonical_document_name=CANONICAL_SKILL_DOCUMENT,
            retained_paths=(filename,),
            uploaded_bytes=len(payload),
            expanded_bytes=len(payload),
        )

    def _quarantine_archive(
        self,
        entries: tuple[_ArchiveEntry, ...],
        document: _ArchiveEntry,
        archive_format: str,
        filename: str,
        uploaded_bytes: int,
    ) -> SkillArchiveInspection:
        candidate_root, content_root = self._new_candidate_root()
        try:
            for entry in entries:
                target = content_root.joinpath(*entry.path.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                _write_entry(entry, target)
        except Exception:
            shutil.rmtree(candidate_root, ignore_errors=True)
            raise
        source_document = content_root.joinpath(*document.path.parts)
        return SkillArchiveInspection(
            candidate_id=candidate_root.name,
            archive_format=archive_format,
            source_filename=filename,
            quarantine_root=candidate_root,
            content_root=content_root,
            source_document=source_document,
            canonical_document_name=CANONICAL_SKILL_DOCUMENT,
            retained_paths=tuple(entry.path.as_posix() for entry in entries),
            uploaded_bytes=uploaded_bytes,
            expanded_bytes=sum(entry.size for entry in entries),
        )

    def _new_candidate_root(self) -> tuple[Path, Path]:
        candidate_root = self._quarantine_root / uuid.uuid4().hex
        content_root = candidate_root / "content"
        content_root.mkdir(parents=True, exist_ok=False)
        return candidate_root, content_root


def _validated_filename(value: str) -> str:
    if not value or value != Path(value).name:
        raise SkillArchiveRejected("invalid_filename", "The upload filename is invalid.")
    return value


def _archive_format(filename: str) -> str:
    lowered = filename.lower()
    if lowered.endswith(".zip"):
        return "zip"
    if lowered.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz")):
        return "tar"
    raise SkillArchiveRejected("unsupported_format", "Upload a Skill document, ZIP, or TAR archive.")


def _read_archive(payload: bytes, archive_format: str) -> tuple[_ArchiveEntry, ...]:
    try:
        if archive_format == "zip":
            return _zip_entries(payload)
        return _tar_entries(payload)
    except (OSError, tarfile.TarError, zipfile.BadZipFile) as error:
        raise SkillArchiveRejected("invalid_archive", "The uploaded archive cannot be read.") from error


def _zip_entries(payload: bytes) -> tuple[_ArchiveEntry, ...]:
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        entries: list[_ArchiveEntry] = []
        for info in archive.infolist():
            if info.is_dir():
                continue
            if info.flag_bits & 0x1:
                raise SkillArchiveRejected("encrypted_archive", "Encrypted Skill archives are not supported.")
            if stat.S_ISLNK(info.external_attr >> 16):
                raise SkillArchiveRejected("link_entry", "Skill archives cannot contain links.")
            entries.append(
                _ArchiveEntry(
                    _safe_path(info.filename),
                    info.file_size,
                    info.compress_size,
                    ("zip", payload, info.filename),
                )
            )
    return tuple(entries)


def _tar_entries(payload: bytes) -> tuple[_ArchiveEntry, ...]:
    with tarfile.open(fileobj=BytesIO(payload), mode="r:*") as archive:
        entries: list[_ArchiveEntry] = []
        for member in archive.getmembers():
            if member.isdir():
                continue
            if not member.isfile():
                raise SkillArchiveRejected("special_entry", "Skill archives can contain regular files only.")
            entries.append(
                _ArchiveEntry(
                    _safe_path(member.name),
                    member.size,
                    member.size,
                    ("tar", payload, member.name),
                )
            )
    return tuple(entries)


def _validate_entries(
    entries: tuple[_ArchiveEntry, ...],
    *,
    archive_bytes: int,
    archive_format: str,
) -> None:
    if not entries:
        raise SkillArchiveRejected("empty_archive", "The Skill archive contains no files.")
    if len(entries) > MAX_ARCHIVE_ENTRIES:
        raise SkillArchiveRejected("too_many_entries", "The Skill archive contains too many files.")
    seen: set[str] = set()
    expanded = 0
    for entry in entries:
        normalized = entry.path.as_posix().casefold()
        if normalized in seen:
            raise SkillArchiveRejected("duplicate_path", "The Skill archive contains duplicate paths.")
        seen.add(normalized)
        expanded += entry.size
        if expanded > MAX_EXPANDED_BYTES:
            raise SkillArchiveRejected("expanded_too_large", "The Skill archive expands beyond the size limit.")
        if entry.size and entry.size / max(entry.compressed_size, 1) > MAX_COMPRESSION_RATIO:
            raise SkillArchiveRejected("compression_ratio", "The Skill archive compression ratio is unsafe.")
        if _looks_like_nested_archive(entry.path.name):
            raise SkillArchiveRejected("nested_archive", "Nested archives are not accepted in a Skill package.")
    if archive_format == "tar" and expanded / max(archive_bytes, 1) > MAX_COMPRESSION_RATIO:
        raise SkillArchiveRejected("compression_ratio", "The Skill archive compression ratio is unsafe.")


def _find_skill_document(entries: tuple[_ArchiveEntry, ...]) -> _ArchiveEntry:
    documents = [entry for entry in entries if entry.path.name in ACCEPTED_SKILL_DOCUMENT_NAMES]
    if len(documents) != 1:
        raise SkillArchiveRejected(
            "skill_document_ambiguous",
            "The archive must contain exactly one accepted Skill document.",
        )
    document = documents[0]
    if len(document.path.parts) != 2:
        raise SkillArchiveRejected(
            "skill_root_invalid",
            "An archived Skill must contain one top-level Skill directory.",
        )
    root = document.path.parts[0]
    if any(entry.path.parts[0] != root for entry in entries):
        raise SkillArchiveRejected(
            "multiple_roots",
            "The Skill archive must contain exactly one top-level Skill directory.",
        )
    return document


def _safe_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise SkillArchiveRejected("unsafe_path", "The Skill archive contains an unsafe path.")
    return path


def _write_entry(entry: _ArchiveEntry, target: Path) -> None:
    kind, payload, name = entry.reader
    if kind == "zip":
        with zipfile.ZipFile(BytesIO(payload)) as archive, archive.open(name) as source, target.open("wb") as destination:
            shutil.copyfileobj(source, destination)
        return
    with tarfile.open(fileobj=BytesIO(payload), mode="r:*") as archive:
        source = archive.extractfile(name)
        if source is None:
            raise SkillArchiveRejected("archive_changed", "The Skill archive changed during inspection.")
        with source, target.open("wb") as destination:
            shutil.copyfileobj(source, destination)


def _looks_like_nested_archive(filename: str) -> bool:
    lowered = filename.casefold()
    return lowered.endswith((".zip", ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz"))
