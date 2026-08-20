from __future__ import annotations
from dataclasses import dataclass
from .database import RuntimeDatabase

@dataclass(frozen=True, slots=True)
class PluginComponent:
    plugin_name: str
    component_type: str
    component_key: str
    validation_state: str
    detail: str | None

class PluginComponentRepository:
    """Catalogs Plugin-owned components; it never installs or executes them."""
    def __init__(self, database: RuntimeDatabase) -> None: self._database = database
    def replace_for_plugin(self, name: str, components: tuple[PluginComponent, ...]) -> None:
        with self._database.connect() as connection:
            connection.execute("DELETE FROM plugin_components WHERE plugin_name = ?", (name,))
            connection.executemany("INSERT INTO plugin_components (plugin_name,component_type,component_key,validation_state,detail) VALUES (?,?,?,?,?)", [(c.plugin_name,c.component_type,c.component_key,c.validation_state,c.detail) for c in components])
            connection.commit()
    def list_for_plugin(self, name: str) -> tuple[PluginComponent, ...]:
        with self._database.connect() as connection:
            rows=connection.execute("SELECT plugin_name,component_type,component_key,validation_state,detail FROM plugin_components WHERE plugin_name=? ORDER BY component_type,component_key",(name,)).fetchall()
        return tuple(PluginComponent(*row) for row in rows)

    def skill_owner(self, skill_name: str, *, excluding_plugin: str | None = None) -> str | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT plugin_name FROM plugin_components WHERE component_type='skill' AND component_key=? AND validation_state='valid' AND plugin_name != COALESCE(?, '') LIMIT 1",
                (skill_name, excluding_plugin),
            ).fetchone()
        return str(row[0]) if row else None

    def card_owner(self, card_id: str) -> str | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT plugin_name FROM plugin_components WHERE component_type='card' AND component_key=? AND validation_state='valid' LIMIT 1",
                (card_id,),
            ).fetchone()
        return str(row[0]) if row else None

    def card_ids(self, plugin_name: str) -> tuple[str, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT component_key FROM plugin_components WHERE plugin_name=? AND component_type='card' AND validation_state='valid' ORDER BY component_key",
                (plugin_name,),
            ).fetchall()
        return tuple(str(row[0]) for row in rows)
