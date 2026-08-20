from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        ALTER TABLE plugin_components RENAME TO plugin_components_v026;
        CREATE TABLE plugin_components (
            plugin_name TEXT NOT NULL,
            component_type TEXT NOT NULL CHECK(component_type IN ('skill','mcp','card')),
            component_key TEXT NOT NULL,
            validation_state TEXT NOT NULL CHECK(validation_state IN ('valid','invalid')),
            detail TEXT,
            PRIMARY KEY(plugin_name, component_type, component_key),
            FOREIGN KEY(plugin_name) REFERENCES plugin_catalog(plugin_name) ON DELETE CASCADE
        );
        INSERT INTO plugin_components SELECT * FROM plugin_components_v026;
        DROP TABLE plugin_components_v026;

        ALTER TABLE creation_catalog RENAME TO creation_catalog_v026;
        CREATE TABLE creation_catalog (
            creation_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            install_path TEXT NOT NULL,
            lifecycle_state TEXT NOT NULL CHECK (lifecycle_state IN ('installed', 'enabled', 'disabled')),
            generation INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            source_type TEXT NOT NULL DEFAULT 'local_archive' CHECK (source_type IN ('local_archive','rabbit_qr_link','plugin_card')),
            entry_url TEXT,
            icon_url TEXT,
            theme_color TEXT NOT NULL DEFAULT '#79f2dd'
        );
        INSERT INTO creation_catalog SELECT * FROM creation_catalog_v026;
        DROP TABLE creation_catalog_v026;
        """
    )
