"""Projects Plugin-owned Card extensions into the dynamic visual catalog."""

from __future__ import annotations

import hashlib

from ..storage.creations import CreationCatalogRepository, StoredCreation
from ..storage.plugin_components import PluginComponentRepository
from .cards import PluginCardInspection


class PluginCardLifecycleError(ValueError):
    pass


class PluginCardLifecycle:
    def __init__(self, catalog: CreationCatalogRepository, components: PluginComponentRepository) -> None:
        self._catalog = catalog
        self._components = components

    def validate(self, plugin_name: str, card: PluginCardInspection | None) -> None:
        if card is None:
            return
        current = self._catalog.get(card.card_id)
        if current is None:
            return
        owner = self._components.card_owner(card.card_id)
        if current.source_type != "plugin_card" or owner != plugin_name:
            raise PluginCardLifecycleError(f"Card '{card.card_id}' is already installed by another source.")

    def replace(self, plugin_name: str, card: PluginCardInspection | None, previous_card_ids: tuple[str, ...], *, state: str, changed_by: str, reason: str) -> None:
        current_id = card.card_id if card is not None else None
        for card_id in previous_card_ids:
            if card_id != current_id:
                self._remove_owned(plugin_name, card_id, changed_by=changed_by, reason="Plugin replacement removed its Card")
        if card is None:
            return
        self._catalog.save(
            StoredCreation(
                creation_id=card.card_id,
                title=card.title,
                description=card.description,
                content_hash=_hash_tree(card.root),
                install_path=card.root,
                lifecycle_state=state,
                generation=0,
                source_type="plugin_card",
                theme_color=card.accent,
            ),
            action="replace" if card.card_id in previous_card_ids else "install",
            changed_by=changed_by,
            reason=reason,
        )

    def set_enabled(self, plugin_name: str, enabled: bool, *, changed_by: str, reason: str) -> None:
        for card_id in self._components.card_ids(plugin_name):
            item = self._catalog.get(card_id)
            if item is None or item.source_type != "plugin_card":
                continue
            self._catalog.save(
                StoredCreation(item.creation_id, item.title, item.description, item.content_hash, item.install_path, "enabled" if enabled else "disabled", item.generation, item.source_type, item.entry_url, item.icon_url, item.theme_color),
                action="enable" if enabled else "disable",
                changed_by=changed_by,
                reason=reason,
            )

    def remove(self, plugin_name: str, card_ids: tuple[str, ...], *, changed_by: str, reason: str) -> None:
        for card_id in card_ids:
            self._remove_owned(plugin_name, card_id, changed_by=changed_by, reason=reason)

    def _remove_owned(self, plugin_name: str, card_id: str, *, changed_by: str, reason: str) -> None:
        item = self._catalog.get(card_id)
        owner = self._components.card_owner(card_id)
        if item is not None and item.source_type == "plugin_card" and owner == plugin_name:
            self._catalog.remove(card_id, changed_by=changed_by, reason=reason)


def _hash_tree(root) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()
