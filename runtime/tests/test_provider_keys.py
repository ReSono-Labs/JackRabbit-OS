"""Slice 2 — provider API-key storage via sealed envelopes (TDD)."""

from __future__ import annotations

from pathlib import Path

import pytest

from resono_runtime.security.credentials import ConnectionCredentialEnvelopes, CredentialUnavailable
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.storage.provider_keys import ProviderKeyRepository

from .conftest import FakeCredentialBridge


def _repo(tmp_path):
    database = RuntimeDatabase(tmp_path / "slice2-keys.db")
    database.migrate()
    return ProviderKeyRepository(database)


def test_provider_key_round_trip(tmp_path):
    repo = _repo(tmp_path)
    envelopes = ConnectionCredentialEnvelopes(FakeCredentialBridge())
    assert repo.get("opencode-go") is None
    repo.put("opencode-go", envelopes.seal_provider_key("opencode-go", "sk-test-123"))
    envelope = repo.get("opencode-go")
    assert envelope is not None
    assert envelopes.open_provider_key("opencode-go", envelope) == "sk-test-123"
    assert repo.delete("opencode-go") is True
    assert repo.get("opencode-go") is None


def test_provider_key_names_are_provider_scoped(tmp_path):
    repo = _repo(tmp_path)
    envelopes = ConnectionCredentialEnvelopes(FakeCredentialBridge())
    repo.put("glm", envelopes.seal_provider_key("glm", "glm-secret"))
    repo.put("kimi", envelopes.seal_provider_key("kimi", "kimi-secret"))
    assert envelopes.open_provider_key("glm", repo.get("glm")) == "glm-secret"
    assert envelopes.open_provider_key("kimi", repo.get("kimi")) == "kimi-secret"


def test_connection_and_provider_records_do_not_collide(tmp_path):
    from resono_runtime.storage.connection_credentials import ConnectionCredentialRepository

    database = RuntimeDatabase(tmp_path / "slice2-keys2.db")
    database.migrate()
    envelopes = ConnectionCredentialEnvelopes(FakeCredentialBridge())
    connection_repo = ConnectionCredentialRepository(database)
    provider_repo = ProviderKeyRepository(database)
    connection_repo.put_envelope("00000000-0000-0000-0000-000000000001",
                                 envelopes.seal("00000000-0000-0000-0000-000000000001", "conn-secret"))
    provider_repo.put("kimi", envelopes.seal_provider_key("kimi", "provider-secret"))
    assert envelopes.open("00000000-0000-0000-0000-000000000001",
                          connection_repo.get_envelope("00000000-0000-0000-0000-000000000001")) == "conn-secret"
    assert envelopes.open_provider_key("kimi", provider_repo.get("kimi")) == "provider-secret"


def test_provider_key_envelope_requires_nonempty(tmp_path):
    envelopes = ConnectionCredentialEnvelopes(FakeCredentialBridge())
    with pytest.raises(ValueError):
        envelopes.seal_provider_key("kimi", "   ")
    with pytest.raises(CredentialUnavailable):
        envelopes.open_provider_key("kimi", "")
