from __future__ import annotations

from dataclasses import dataclass

from .database import RuntimeDatabase


_REALTIME_MODEL = "openai.realtime_model"
_TEXT_MODEL = "openai.text_model"
_ACCESS_PATH = "openai.access_path"
_REASONING_EFFORT = "openai.reasoning_effort"
_PROVIDER = "provider.active"

_DEFAULT_PROVIDER = "openai"


@dataclass(frozen=True, slots=True)
class ProviderSelection:
    provider: str
    text_model: str | None
    realtime_model: str | None
    access_path: str
    reasoning_effort: str


class ProviderSettingsRepository:
    def __init__(self, database: RuntimeDatabase) -> None:
        self._database = database

    def selection(self) -> ProviderSelection:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT setting_key, setting_value FROM provider_settings "
                "WHERE setting_key IN (?, ?, ?, ?, ?)",
                (_TEXT_MODEL, _REALTIME_MODEL, _ACCESS_PATH, _REASONING_EFFORT, _PROVIDER),
            ).fetchall()
        values = {str(row["setting_key"]): str(row["setting_value"]) for row in rows}
        return ProviderSelection(
            values.get(_PROVIDER, _DEFAULT_PROVIDER),
            values.get(_TEXT_MODEL),
            values.get(_REALTIME_MODEL),
            values.get(_ACCESS_PATH, "platform"),
            values.get(_REASONING_EFFORT, "none"),
        )

    def save(
        self,
        *,
        provider: str | None = None,
        text_model: str | None,
        realtime_model: str | None,
        reasoning_effort: str | None = None,
    ) -> ProviderSelection:
        if reasoning_effort is not None and reasoning_effort not in ("none", "low", "medium", "high"):
            raise ValueError("Reasoning effort is invalid")
        changes = (
            (_PROVIDER, provider),
            (_TEXT_MODEL, text_model),
            (_REALTIME_MODEL, realtime_model),
            (_REASONING_EFFORT, reasoning_effort),
        )
        with self._database.connect() as connection:
            for key, value in changes:
                if key == _PROVIDER and value is None:
                    continue
                if value is None:
                    continue
                connection.execute(
                    "INSERT INTO provider_settings(setting_key, setting_value, updated_at) "
                    "VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) "
                    "ON CONFLICT(setting_key) DO UPDATE SET "
                    "setting_value=excluded.setting_value, updated_at=excluded.updated_at",
                    (key, value),
                )
            connection.commit()
        return self.selection()

    def save_access_path(self, access_path: str) -> ProviderSelection:
        if access_path not in ("platform", "subscription"):
            raise ValueError("OpenAI access path is invalid")
        with self._database.connect() as connection:
            connection.execute(
                "INSERT INTO provider_settings(setting_key, setting_value, updated_at) "
                "VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) "
                "ON CONFLICT(setting_key) DO UPDATE SET "
                "setting_value=excluded.setting_value, updated_at=excluded.updated_at",
                (_ACCESS_PATH, access_path),
            )
            connection.commit()
        return self.selection()

    def clear(self) -> None:
        with self._database.connect() as connection:
            connection.execute(
                "DELETE FROM provider_settings WHERE setting_key IN (?, ?, ?, ?, ?)",
                (_TEXT_MODEL, _REALTIME_MODEL, _ACCESS_PATH, _REASONING_EFFORT, _PROVIDER),
            )
            connection.commit()

    def set_provider(self, provider: str) -> ProviderSelection:
        value = provider.strip().lower()
        if not value:
            raise ValueError("provider is required")
        return self.save(provider=value, text_model=None, realtime_model=None)
