from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderDescriptor:
    provider_id: str
    name: str
    base_url: str | None = None
    api_style: str = "chat"
    key_required: bool = True
    voice: str = "none"
    auth_header: str | None = None


class ProviderCatalogRepository:
    """
    Persistent provider metadata and default model catalog.

    This stays intentionally minimal so the runtime can support a multi-provider
    future without changing the contract shape.
    """

    def __init__(self, database: object) -> None:
        # Keep imports lightweight to avoid circular module references.
        from .database import RuntimeDatabase

        if not isinstance(database, RuntimeDatabase):
            raise TypeError("database must be a RuntimeDatabase")
        self._database = database

    def providers(self) -> tuple[ProviderDescriptor, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT provider_id, provider_name, base_url, api_style, key_required, voice, auth_header "
                "FROM provider_directory WHERE enabled = 1 "
                "ORDER BY sort_order ASC, provider_id ASC"
            ).fetchall()
        return tuple(_descriptor(row) for row in rows)

    def descriptor(self, provider_id: str) -> ProviderDescriptor | None:
        normalized = _normalize_provider(provider_id)
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT provider_id, provider_name, base_url, api_style, key_required, voice, auth_header "
                "FROM provider_directory WHERE enabled = 1 AND provider_id = ?",
                (normalized,),
            ).fetchone()
        return _descriptor(row) if row is not None else None

    def provider_exists(self, provider_id: str) -> bool:
        normalized = _normalize_provider(provider_id)
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM provider_directory WHERE enabled = 1 AND provider_id = ?",
                (normalized,),
            ).fetchone()
        return row is not None

    def models(
        self,
        provider_id: str,
        access_path: str,
        model_kind: str,
    ) -> tuple[str, ...]:
        normalized_provider = _normalize_provider(provider_id)
        normalized_kind = model_kind.strip().lower()
        normalized_access = access_path.strip().lower()
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT model_id FROM provider_model_catalog
                WHERE provider_id = ? AND access_path = ? AND model_kind = ?
                    AND enabled = 1
                ORDER BY sort_order ASC, model_id ASC
                """,
                (normalized_provider, normalized_access, normalized_kind),
            ).fetchall()
        return tuple(str(row["model_id"]) for row in rows)

    def bootstrap_defaults(self) -> None:
        """
        Seed the catalog once. If entries exist, this is a no-op.
        """
        with self._database.connect() as connection:
            count = connection.execute(
                "SELECT COUNT(1) AS total FROM provider_directory WHERE enabled = 1"
            ).fetchone()
            if count is None or int(count["total"]) > 0:
                return

            upsert_provider = """
                INSERT INTO provider_directory(provider_id, provider_name, sort_order, enabled, updated_at)
                VALUES(?, ?, ?, 1, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            """
            upsert_model = """
                INSERT INTO provider_model_catalog(
                    provider_id, access_path, model_kind, model_id, model_label, sort_order, enabled, updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, 1, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            """
            connection.execute(upsert_provider, ("openai", "OpenAI", 0))
            self._seed_openai_models(connection, upsert_model)
            connection.commit()

    def _seed_openai_models(self, connection: object, statement: str) -> None:
        for order, (access_path, model_kind, model_id, model_label) in enumerate(
            self._openai_defaults(), start=0
        ):
            connection.execute(
                statement,
                ("openai", access_path, model_kind, model_id, model_label, order),
            )

    @staticmethod
    def _openai_defaults() -> tuple[tuple[str, str, str, str], ...]:
        return (
            ("subscription", "text", "gpt-5.6-sol", "GPT-5.6 Sol"),
            ("subscription", "text", "gpt-5.6-terra", "GPT-5.6 Terra"),
            ("subscription", "text", "gpt-5.6-luna", "GPT-5.6 Luna"),
            ("subscription", "realtime", "gpt-realtime-2.1", "GPT-Realtime 2.1"),
            ("subscription", "realtime", "gpt-realtime-2.1-mini", "GPT-Realtime 2.1 Mini"),
            ("subscription", "realtime", "gpt-live-1", "GPT-Live 1"),
        )


def _normalize_provider(value: str) -> str:
    return value.strip().lower()


def _descriptor(row: object) -> ProviderDescriptor:
    return ProviderDescriptor(
        str(row["provider_id"]),
        str(row["provider_name"]),
        row["base_url"],
        str(row["api_style"]),
        bool(row["key_required"]),
        str(row["voice"]),
        row["auth_header"],
    )
