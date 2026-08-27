"""Correct third-party provider endpoints after real-account verification.

The v044 seeds used the public/legacy endpoints. Real-account smoke tests
(2026-08-26) verified the working endpoints:
- GLM coding plan: https://api.z.ai/api/coding/paas/v4 (Z.ai, not open.bigmodel.cn)
- Kimi Code API:   https://api.kimi.com/coding/v1 (not api.moonshot.cn)
OpenCode Zen: prefer deepseek-v4-pro (claude-*/gpt-* models 500 on that plan).
"""

from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        UPDATE provider_directory SET base_url = 'https://api.z.ai/api/coding/paas/v4'
            WHERE provider_id = 'glm';
        UPDATE provider_directory SET base_url = 'https://api.kimi.com/coding/v1'
            WHERE provider_id = 'kimi';
        UPDATE provider_model_catalog SET sort_order = 0
            WHERE provider_id = 'opencode-zen' AND model_id = 'deepseek-v4-pro';
        UPDATE provider_model_catalog SET sort_order = 1
            WHERE provider_id = 'opencode-zen' AND model_id = 'claude-opus-4-8';
        """
    )
