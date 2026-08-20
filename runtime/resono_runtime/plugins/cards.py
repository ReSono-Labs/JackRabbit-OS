"""Validation for the ReSono Agent Plugin Card client extension."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
import re

from jsonschema import Draft202012Validator


CARD_NAMESPACE = "com.resonolabs.cards"
CARD_SCHEMA_ID = "https://resono.local/schemas/cards/1.0/card.schema.json"
_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "standards" / "resono_cards" / "card.schema.json"
_ALLOWED_SUFFIXES = frozenset({".html", ".htm", ".css", ".js", ".json", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".woff", ".woff2", ".ttf", ".ico", ".txt"})
_COLOR = re.compile(r"#[0-9a-fA-F]{6}\Z")


class PluginCardRejected(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PluginCardInspection:
    card_id: str
    title: str
    description: str
    entrypoint: str
    accent: str
    required_tools: tuple[str, ...]
    optional_tools: tuple[str, ...]
    root: Path


def inspect_plugin_card(plugin_root: Path, plugin_name: str) -> PluginCardInspection | None:
    root = plugin_root / CARD_NAMESPACE
    if not root.exists():
        return None
    if not root.is_dir():
        raise PluginCardRejected(f"{CARD_NAMESPACE} must be a directory.")
    manifest_path = root / "card.json"
    if not manifest_path.is_file():
        raise PluginCardRejected(f"{CARD_NAMESPACE}/card.json is required.")
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
        schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PluginCardRejected("Card manifest must be valid UTF-8 JSON.") from error
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda item: list(item.path))
    if errors:
        raise PluginCardRejected(f"card.json is invalid: {errors[0].message}")
    if value["$schema"] != CARD_SCHEMA_ID:
        raise PluginCardRejected("card.json uses an unsupported schema.")
    if value["cardId"] != plugin_name:
        raise PluginCardRejected("Card identity must equal the owning Plugin name.")
    entrypoint = PurePosixPath(value["entrypoint"])
    if entrypoint.is_absolute() or any(part in {"", ".", ".."} for part in entrypoint.parts) or entrypoint.suffix.casefold() not in {".html", ".htm"}:
        raise PluginCardRejected("Card entrypoint is invalid.")
    target = root.joinpath(*entrypoint.parts)
    if not target.is_file() or root.resolve() not in target.resolve().parents:
        raise PluginCardRejected("Card entrypoint is missing or escapes its extension directory.")
    for asset in root.rglob("*"):
        if asset.is_symlink() or (asset.is_file() and asset.suffix.casefold() not in _ALLOWED_SUFFIXES):
            raise PluginCardRejected("Card extension contains an unsupported asset.")
    required = tuple(value.get("requiredTools", ()))
    optional = tuple(value.get("optionalTools", ()))
    if set(required) & set(optional):
        raise PluginCardRejected("A Card tool cannot be both required and optional.")
    accent = value.get("accent", "#79f2dd")
    if not _COLOR.fullmatch(accent):
        raise PluginCardRejected("Card accent must be #RRGGBB.")
    return PluginCardInspection(
        card_id=plugin_name,
        title=value["title"].strip(),
        description=value["description"].strip(),
        entrypoint=entrypoint.as_posix(),
        accent=accent.casefold(),
        required_tools=required,
        optional_tools=optional,
        root=root,
    )
