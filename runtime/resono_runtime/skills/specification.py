from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import yaml


_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class SkillSpecificationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SkillDocument:
    name: str
    description: str
    instructions: str
    license: str | None
    compatibility: str | None
    metadata: dict[str, str]
    allowed_tools: str | None


def parse_skill(root: Path) -> SkillDocument:
    """Parse one standards-conformant Agent Skill without granting capabilities."""
    skill_root = root.resolve(strict=True)
    source = skill_root / "SKILL.md"
    if not source.is_file():
        raise SkillSpecificationError("SKILL.md is required")
    return parse_skill_document(source, expected_directory=skill_root.name)


def parse_skill_document(source: Path, *, expected_directory: str | None = None) -> SkillDocument:
    """Parse one Skill document before a canonical install directory exists."""
    skill_source = source.resolve(strict=True)
    try:
        raw = skill_source.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise SkillSpecificationError("SKILL.md must be UTF-8") from error
    frontmatter, instructions = _split_frontmatter(raw)
    try:
        parsed = yaml.safe_load(frontmatter)
    except yaml.YAMLError as error:
        raise SkillSpecificationError("SKILL.md frontmatter is invalid YAML") from error
    if not isinstance(parsed, dict):
        raise SkillSpecificationError("SKILL.md frontmatter must be an object")
    return SkillDocument(
        name=_name(parsed.get("name"), expected_directory),
        description=_bounded_string(parsed.get("description"), "description", 1024, required=True),
        instructions=instructions,
        license=_optional_string(parsed.get("license"), "license"),
        compatibility=_optional_string(parsed.get("compatibility"), "compatibility", maximum=500),
        metadata=_metadata(parsed.get("metadata")),
        allowed_tools=_optional_string(parsed.get("allowed-tools"), "allowed-tools"),
    )


def _split_frontmatter(raw: str) -> tuple[str, str]:
    if not raw.startswith("---\n"):
        raise SkillSpecificationError("SKILL.md must begin with YAML frontmatter")
    end = raw.find("\n---\n", 4)
    if end < 0:
        raise SkillSpecificationError("SKILL.md frontmatter is not closed")
    return raw[4:end], raw[end + 5 :]


def _name(value: object, directory_name: str | None) -> str:
    if not isinstance(value, str) or not _NAME.fullmatch(value) or len(value) > 64:
        raise SkillSpecificationError("name must be 1-64 lowercase letters, digits, or hyphens")
    if directory_name is not None and value != directory_name:
        raise SkillSpecificationError("name must match the Skill directory")
    return value


def _bounded_string(value: object, field: str, maximum: int, *, required: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        if required:
            raise SkillSpecificationError(f"{field} is required")
        raise SkillSpecificationError(f"{field} must be a non-empty string")
    result = value.strip()
    if len(result) > maximum:
        raise SkillSpecificationError(f"{field} exceeds {maximum} characters")
    return result


def _optional_string(value: object, field: str, *, maximum: int | None = None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise SkillSpecificationError(f"{field} must be a non-empty string")
    result = value.strip()
    if maximum is not None and len(result) > maximum:
        raise SkillSpecificationError(f"{field} exceeds {maximum} characters")
    return result


def _metadata(value: object) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict) or any(not isinstance(key, str) or not isinstance(item, str) for key, item in value.items()):
        raise SkillSpecificationError("metadata must map strings to strings")
    return dict(value)
