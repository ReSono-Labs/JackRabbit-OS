from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .database import RuntimeDatabase


_DISPLAY_NAME = "profile.display_name"


@dataclass(frozen=True, slots=True)
class UserProfile:
    display_name: str | None


class UserProfileRepository:
    def __init__(self, database: RuntimeDatabase) -> None:
        self._database = database

    def profile(self) -> UserProfile:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT setting_value FROM provider_settings WHERE setting_key = ?",
                (_DISPLAY_NAME,),
            ).fetchone()
        return UserProfile(str(row["setting_value"]) if row else None)

    def save(self, display_name: str | None) -> UserProfile:
        value = (display_name or "").strip()
        if len(value) > 80 or any(ord(character) < 32 for character in value):
            raise ValueError("Your name must be 80 characters or fewer.")
        with self._database.connect() as connection:
            if value:
                connection.execute(
                    "INSERT INTO provider_settings(setting_key, setting_value, updated_at) "
                    "VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) "
                    "ON CONFLICT(setting_key) DO UPDATE SET "
                    "setting_value=excluded.setting_value, updated_at=excluded.updated_at",
                    (_DISPLAY_NAME, value),
                )
            else:
                connection.execute(
                    "DELETE FROM provider_settings WHERE setting_key = ?", (_DISPLAY_NAME,)
                )
            connection.commit()
        return self.profile()

    def connect_greeting_text(self) -> str:
        display_name = self.profile().display_name
        if not display_name:
            return ""
        hour = datetime.now().astimezone().hour
        daypart = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"
        return f"Good {daypart} {display_name}, what can I help you with this {daypart}?"

    def connect_greeting_event(self) -> dict[str, object] | None:
        greeting = self.connect_greeting_text()
        if not greeting:
            return None
        return {
            "type": "response.create",
            "response": {
                "instructions": f'Say exactly: "{greeting}" Then stop and wait for the user.'
            },
        }
