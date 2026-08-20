"""Quarantined inspection for standard Agent Plugins v1.0.0 packages."""

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
MAX_ENTRIES = 512
MAX_COMPRESSION_RATIO = 100
from resono_runtime.plugins.specification import (
    PluginSpecificationError,
    parse_mcp_document,
    parse_plugin_manifest,
)
from resono_runtime.skills.specification import SkillSpecificationError, parse_skill


class PluginArchiveRejected(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PluginManifest:
    name: str
    version: str | None
    description: str | None
    ignored_fields: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PluginInspection:
    candidate_id: str
    root: Path
    manifest: PluginManifest
    skills: tuple[str, ...]
    invalid_skills: tuple[str, ...]
    mcp_present: bool
    mcp_valid: bool
    mcp_issue: str | None


class PluginArchiveInspector:
    def __init__(self, quarantine_root: Path) -> None:
        self._quarantine_root = quarantine_root

    def inspect(self, payload: bytes, filename: str) -> PluginInspection:
        if not filename or Path(filename).name != filename or len(payload) > MAX_UPLOAD_BYTES or not payload:
            raise PluginArchiveRejected("Plugin upload is invalid.")
        entries = _entries(payload, filename)
        root_name = _root(entries)
        candidate = self._quarantine_root / uuid.uuid4().hex
        root = candidate / root_name
        try:
            for path, content in entries:
                target = candidate.joinpath(*path.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            manifest = _manifest(root / "plugin.json")
            skills, invalid = _skills(root)
            mcp_present, mcp_valid, mcp_issue = _mcp(root / "mcp.json")
            return PluginInspection(candidate.name, root, manifest, skills, invalid, mcp_present, mcp_valid, mcp_issue)
        except Exception:
            shutil.rmtree(candidate, ignore_errors=True)
            raise


def _entries(payload: bytes, filename: str) -> tuple[tuple[PurePosixPath, bytes], ...]:
    try:
        source = zipfile.ZipFile(BytesIO(payload)) if filename.lower().endswith(".zip") else tarfile.open(fileobj=BytesIO(payload), mode="r:*")
    except (zipfile.BadZipFile, tarfile.TarError) as error:
        raise PluginArchiveRejected("Plugin archive cannot be read.") from error
    entries: list[tuple[PurePosixPath, bytes]] = []
    expanded = 0
    with source as archive:
        members = archive.infolist() if isinstance(archive, zipfile.ZipFile) else archive.getmembers()
        for member in members:
            name = member.filename if isinstance(archive, zipfile.ZipFile) else member.name
            is_dir = member.is_dir() if isinstance(archive, zipfile.ZipFile) else member.isdir()
            if is_dir:
                continue
            if len(entries) >= MAX_ENTRIES:
                raise PluginArchiveRejected("Plugin archive has too many entries.")
            path = PurePosixPath(name)
            if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
                raise PluginArchiveRejected("Plugin archive has an unsafe path.")
            if isinstance(archive, zipfile.ZipFile):
                if member.flag_bits & 1 or stat.S_ISLNK(member.external_attr >> 16):
                    raise PluginArchiveRejected("Plugin archive contains an unsupported link or encrypted entry.")
                expanded += member.file_size
                if member.file_size and member.file_size / max(member.compress_size, 1) > MAX_COMPRESSION_RATIO:
                    raise PluginArchiveRejected("Plugin archive compression ratio is unsafe.")
                content = archive.read(member)
            else:
                if not member.isfile():
                    raise PluginArchiveRejected("Plugin archive contains a non-regular file.")
                expanded += member.size
                source_file = archive.extractfile(member)
                content = source_file.read() if source_file else b""
            if expanded > MAX_EXPANDED_BYTES:
                raise PluginArchiveRejected("Plugin archive expands beyond the size limit.")
            entries.append((path, content))
    if len({path.as_posix().casefold() for path, _ in entries}) != len(entries):
        raise PluginArchiveRejected("Plugin archive has duplicate paths.")
    return tuple(entries)


def _root(entries: tuple[tuple[PurePosixPath, bytes], ...]) -> str:
    roots = {path.parts[0] for path, _ in entries}
    if len(roots) != 1:
        raise PluginArchiveRejected("Plugin archive must contain exactly one root directory.")
    root = next(iter(roots))
    if not any(path == PurePosixPath(root, "plugin.json") for path, _ in entries):
        raise PluginArchiveRejected("Plugin archive requires root plugin.json.")
    return root


def _manifest(source: Path) -> PluginManifest:
    try:
        manifest = parse_plugin_manifest(source)
    except PluginSpecificationError as error:
        raise PluginArchiveRejected(str(error)) from error
    return PluginManifest(manifest.name, manifest.version, manifest.description)


def _skills(root: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    directory = root / "skills"
    if not directory.exists():
        return (), ()
    if not directory.is_dir():
        return (), ("skills directory is invalid",)
    valid, invalid = [], []
    for child in directory.iterdir():
        if not child.is_dir():
            continue
        document = child / "SKILL.md"
        try:
            parse_skill(child)
            valid.append(child.name)
        except (OSError, SkillSpecificationError):
            invalid.append(child.name)
    return tuple(sorted(valid)), tuple(sorted(invalid))


def _mcp(source: Path) -> tuple[bool, bool, str | None]:
    if not source.exists():
        return False, False, None
    if not source.is_file():
        return True, False, "mcp.json is not a regular file"
    try:
        document = parse_mcp_document(source)
    except PluginSpecificationError as error:
        return True, False, str(error)
    if document.invalid_servers:
        name, detail = document.invalid_servers[0]
        return True, False, f"MCP server {name} is invalid: {detail}"
    return True, True, None
