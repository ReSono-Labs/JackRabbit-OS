from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    foreign_keys = connection.execute("PRAGMA foreign_key_list(plugin_components)").fetchall()
    if foreign_keys:
        return
    connection.executescript(
        """
        ALTER TABLE plugin_components RENAME TO plugin_components_v009;
        CREATE TABLE plugin_components (
            plugin_name TEXT NOT NULL,
            component_type TEXT NOT NULL CHECK(component_type IN ('skill','mcp')),
            component_key TEXT NOT NULL,
            validation_state TEXT NOT NULL CHECK(validation_state IN ('valid','invalid')),
            detail TEXT,
            PRIMARY KEY(plugin_name, component_type, component_key),
            FOREIGN KEY(plugin_name) REFERENCES plugin_catalog(plugin_name) ON DELETE CASCADE
        );
        INSERT INTO plugin_components SELECT * FROM plugin_components_v009;
        DROP TABLE plugin_components_v009;
        """
    )
