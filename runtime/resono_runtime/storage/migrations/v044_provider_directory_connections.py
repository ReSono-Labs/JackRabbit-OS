from __future__ import annotations

import sqlite3

_NOW = "strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"


def apply(connection: sqlite3.Connection) -> None:
    columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(provider_directory)").fetchall()}
    additions = (
        ("base_url", "TEXT"),
        ("api_style", "TEXT NOT NULL DEFAULT 'chat'"),
        ("key_required", "INTEGER NOT NULL DEFAULT 1"),
    )
    for name, declaration in additions:
        if name not in columns:
            connection.execute(f"ALTER TABLE provider_directory ADD COLUMN {name} {declaration}")

    connection.executescript(
        f"""
        INSERT OR IGNORE INTO provider_directory(
            provider_id, provider_name, sort_order, enabled, updated_at,
            base_url, api_style, key_required
        ) VALUES
            ('openai', 'OpenAI', 0, 1, {_NOW}, NULL, 'responses', 1),
            ('opencode-go', 'OpenCode Go', 10, 1, {_NOW}, 'https://opencode.ai/zen/go/v1', 'chat', 1),
            ('opencode-zen', 'OpenCode Zen', 20, 1, {_NOW}, 'https://opencode.ai/zen/v1', 'chat', 1),
            ('openrouter', 'OpenRouter', 30, 1, {_NOW}, 'https://openrouter.ai/api/v1', 'chat', 1),
            ('glm', 'GLM (Zhipu)', 40, 1, {_NOW}, 'https://open.bigmodel.cn/api/paas/v4', 'chat', 1),
            ('kimi', 'Kimi (Moonshot)', 50, 1, {_NOW}, 'https://api.moonshot.cn/v1', 'chat', 1),
            ('local', 'Local LLM (Ollama)', 60, 1, {_NOW}, 'http://127.0.0.1:11434/v1', 'chat', 0);
        """
    )
    connection.execute("UPDATE provider_directory SET api_style = 'responses' WHERE provider_id = 'openai'")
    connection.execute("UPDATE provider_directory SET base_url = NULL WHERE provider_id = 'openai'")

    models = (
        ("opencode-go", "deepseek-v4-pro", "DeepSeek V4 Pro", 0),
        ("opencode-go", "deepseek-v4-flash", "DeepSeek V4 Flash", 1),
        ("opencode-go", "kimi-k2.7-code", "Kimi K2.7 Code", 2),
        ("opencode-go", "glm-5.2", "GLM-5.2", 3),
        ("opencode-go", "qwen3.7-max", "Qwen3.7 Max", 4),
        ("opencode-go", "minimax-m3", "MiniMax-M3", 5),
        ("opencode-zen", "claude-opus-4-8", "Claude Opus 4.8", 0),
        ("opencode-zen", "gpt-5.6-terra", "GPT-5.6 Terra", 1),
        ("opencode-zen", "gemini-3.1-pro", "Gemini 3.1 Pro Preview", 2),
        ("opencode-zen", "glm-4.7", "GLM-4.7", 3),
        ("opencode-zen", "kimi-k2.7-code", "Kimi K2.7 Code", 4),
        ("opencode-zen", "minimax-m2.5-free", "MiniMax-M2.5 Free", 5),
    )
    for provider_id, model_id, label, order in models:
        connection.execute(
            f"""
            INSERT OR IGNORE INTO provider_model_catalog(
                provider_id, access_path, model_kind, model_id, model_label,
                sort_order, enabled, updated_at
            ) VALUES (?, 'key', 'text', ?, ?, ?, 1, {_NOW})
            """,
            (provider_id, model_id, label, order),
        )
