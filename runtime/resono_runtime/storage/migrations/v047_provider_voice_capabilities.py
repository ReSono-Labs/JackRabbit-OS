"""Voice capability + auth style + Gemini Live provider seeding (slice 3).

Adds per-provider voice transport capability (webrtc/websocket/none) and an
optional auth header override (Gemini REST/WS accept x-goog-api-key; the
OpenAI-compatible clients default to Authorization: Bearer). Seeds the Gemini
provider with Live realtime models for the WebSocket voice connector.
"""

from __future__ import annotations

import sqlite3

_NOW = "strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"


def apply(connection: sqlite3.Connection) -> None:
    columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(provider_directory)").fetchall()}
    if "voice" not in columns:
        connection.execute("ALTER TABLE provider_directory ADD COLUMN voice TEXT NOT NULL DEFAULT 'none'")
    if "auth_header" not in columns:
        connection.execute("ALTER TABLE provider_directory ADD COLUMN auth_header TEXT")

    connection.executescript(
        f"""
        UPDATE provider_directory SET voice = 'webrtc' WHERE provider_id = 'openai';
        UPDATE provider_directory SET voice = 'websocket' WHERE provider_id = 'gemini';
        UPDATE provider_directory SET auth_header = 'x-goog-api-key' WHERE provider_id = 'gemini';
        INSERT OR IGNORE INTO provider_directory(
            provider_id, provider_name, sort_order, enabled, updated_at,
            base_url, api_style, key_required, voice, auth_header
        ) VALUES (
            'gemini', 'Gemini (Google)', 25, 1, {_NOW},
            'https://generativelanguage.googleapis.com/v1beta', 'chat', 1, 'websocket', 'x-goog-api-key'
        );
        """
    )
    models = (
        ("gemini-3.1-flash-live-preview", "Gemini 3.1 Flash Live Preview", 0),
        ("gemini-2.5-flash-native-audio-preview-12-2025", "Gemini 2.5 Flash Native Audio (Dec 2025)", 1),
    )
    for model_id, label, order in models:
        connection.execute(
            f"""
            INSERT OR IGNORE INTO provider_model_catalog(
                provider_id, access_path, model_kind, model_id, model_label,
                sort_order, enabled, updated_at
            ) VALUES ('gemini', 'key', 'realtime', ?, ?, ?, 1, {_NOW})
            """,
            (model_id, label, order),
        )
