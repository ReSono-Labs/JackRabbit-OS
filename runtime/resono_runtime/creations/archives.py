"""Safe static-site ZIP inspection for Rabbit Creations SDK artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
from uuid import uuid4
import zipfile


MAX_UPLOAD_BYTES = 16 * 1024 * 1024
MAX_EXPANDED_BYTES = 64 * 1024 * 1024
MAX_ENTRIES = 512
MAX_COMPRESSION_RATIO = 100
ALLOWED_SUFFIXES = frozenset({".html", ".htm", ".css", ".js", ".json", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".woff", ".woff2", ".ttf", ".ico", ".txt"})


class CreationArchiveRejected(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CreationInspection:
    creation_id: str
    title: str
    description: str
    candidate_root: Path
    content_root: Path
    source_type: str = "local_archive"
    entry_url: str | None = None
    icon_url: str | None = None
    theme_color: str = "#79f2dd"


class CreationArchiveInspector:
    def __init__(self, quarantine_root: Path) -> None:
        self._quarantine_root = quarantine_root

    def inspect(self, payload: bytes, filename: str) -> CreationInspection:
        if not filename.casefold().endswith(".zip") or Path(filename).name != filename:
            raise CreationArchiveRejected("Creation imports must be ZIP files.")
        if not payload or len(payload) > MAX_UPLOAD_BYTES:
            raise CreationArchiveRejected("Creation upload is empty or too large.")
        entries = _entries(payload)
        prefix = _prefix(entries)
        creation_id = creation_slug(prefix or Path(filename).stem)
        candidate = self._quarantine_root / uuid4().hex
        content = candidate / "content"
        content.mkdir(parents=True, exist_ok=False)
        try:
            for path, data in entries:
                relative = PurePosixPath(*path.parts[1:]) if prefix else path
                target = content.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            metadata = _Metadata()
            metadata.feed((content / "index.html").read_text(encoding="utf-8"))
            return CreationInspection(creation_id, metadata.title or creation_id.replace("-", " ").title(), metadata.description or "Imported R1 Creation", candidate, content)
        except Exception:
            shutil.rmtree(candidate, ignore_errors=True)
            raise


def _entries(payload: bytes) -> tuple[tuple[PurePosixPath, bytes], ...]:
    try:
        archive = zipfile.ZipFile(BytesIO(payload))
    except zipfile.BadZipFile as error:
        raise CreationArchiveRejected("Creation ZIP cannot be read.") from error
    result: list[tuple[PurePosixPath, bytes]] = []
    expanded = 0
    with archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            path = PurePosixPath(info.filename)
            if len(result) >= MAX_ENTRIES or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
                raise CreationArchiveRejected("Creation ZIP structure is unsafe.")
            if info.flag_bits & 1 or stat.S_ISLNK(info.external_attr >> 16) or path.suffix.casefold() not in ALLOWED_SUFFIXES:
                raise CreationArchiveRejected("Creation ZIP contains an unsupported file.")
            expanded += info.file_size
            if expanded > MAX_EXPANDED_BYTES:
                raise CreationArchiveRejected("Creation ZIP expands beyond the limit.")
            if info.file_size > 0 and info.compress_size == 0:
                raise CreationArchiveRejected("Creation ZIP has an invalid compressed entry.")
            if info.compress_size > 0 and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
                raise CreationArchiveRejected("Creation ZIP compression ratio is unsafe.")
            data = archive.read(info)
            if len(data) != info.file_size:
                raise CreationArchiveRejected("Creation ZIP entry length is invalid.")
            result.append((path, data))
    if not result or len({path.as_posix().casefold() for path, _ in result}) != len(result):
        raise CreationArchiveRejected("Creation ZIP is empty or has duplicate paths.")
    return tuple(result)


def _prefix(entries: tuple[tuple[PurePosixPath, bytes], ...]) -> str | None:
    if any(path == PurePosixPath("index.html") for path, _ in entries):
        return None
    roots = {path.parts[0] for path, _ in entries}
    if len(roots) != 1:
        raise CreationArchiveRejected("Creation ZIP must contain one static site.")
    root = next(iter(roots))
    if not any(path == PurePosixPath(root, "index.html") for path, _ in entries):
        raise CreationArchiveRejected("Creation ZIP requires index.html.")
    return root


def creation_slug(value: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    if not result or len(result) > 64:
        raise CreationArchiveRejected("Creation identity is invalid.")
    return result


class _Metadata(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.description = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag.casefold() == "title":
            self._in_title = True
        if tag.casefold() == "meta" and values.get("name", "").casefold() == "description":
            self.description = (values.get("content") or "")[:240].strip()

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title = (self.title + data)[:100].strip()
