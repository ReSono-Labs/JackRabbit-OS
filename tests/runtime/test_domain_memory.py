from __future__ import annotations

from pathlib import Path

from resono_runtime.memory.retrieval import MemoryRetriever
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.storage.memory import MemoryRepository


def _repository(tmp_path: Path) -> MemoryRepository:
    database = RuntimeDatabase(tmp_path / "resono.sqlite3")
    database.migrate()
    return MemoryRepository(database)


def test_domain_memory_reconciles_repeated_fact_without_duplicate(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    first = repository.reconcile_memory(
        session_id="session-a", subject_id="primary", domain="project",
        memory_type="decision", memory_key="resono.memory.boundary",
        content_text="Use post-session ingestion.", confidence="high",
        sensitivity="normal", intent="create", reviewer_model="test",
        reviewer_contract_version=2,
        evidence=((0, "user_statement", "user_asserted", "Use post-session ingestion."),),
    )
    second = repository.reconcile_memory(
        session_id="session-b", subject_id="primary", domain="project",
        memory_type="decision", memory_key="resono.memory.boundary",
        content_text="Use post-session ingestion.", confidence="high",
        sensitivity="normal", intent="confirm", reviewer_model="test",
        reviewer_contract_version=2,
        evidence=((1, "user_statement", "user_asserted", "Keep that decision."),),
    )
    assert second.memory_id == first.memory_id
    assert second.current_version == 1
    assert len(repository.evidence_for(first.memory_id)) == 2


def test_unapproved_changed_value_becomes_conflicted(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    first = repository.reconcile_memory(
        session_id="session-a", subject_id="primary", domain="personal",
        memory_type="preference", memory_key="response.style", content_text="Concise.",
        confidence="high", sensitivity="normal", intent="create", reviewer_model="test",
        reviewer_contract_version=2,
        evidence=((0, "user_statement", "user_asserted", "Keep answers concise."),),
    )
    changed = repository.reconcile_memory(
        session_id="session-b", subject_id="primary", domain="personal",
        memory_type="preference", memory_key="response.style", content_text="Detailed.",
        confidence="medium", sensitivity="normal", intent="create", reviewer_model="test",
        reviewer_contract_version=2,
        evidence=((0, "user_statement", "user_asserted", "Use detailed answers."),),
    )
    assert changed.memory_id == first.memory_id
    assert changed.status == "conflicted"
    assert changed.current_version == 2
    assert changed.memory_id not in {item.memory_id for item in repository.profile_memories()}


def test_hybrid_retrieval_keeps_lexical_search_without_embedder(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    memory = repository.reconcile_memory(
        session_id="session-a", subject_id="primary", domain="device",
        memory_type="constraint", memory_key="camera.acceptance",
        content_text="Camera remains a final hardware acceptance requirement.",
        confidence="high", sensitivity="normal", intent="create", reviewer_model="test",
        reviewer_contract_version=2,
        evidence=((0, "user_statement", "user_asserted", "Camera is final acceptance."),),
    )
    matches = MemoryRetriever(memories=repository, embedder=None).retrieve("camera acceptance")
    assert matches[0].memory.memory_id == memory.memory_id
    assert "lexical" in matches[0].match_methods


def test_ingestion_completion_is_bound_to_transcript_fingerprint(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    repository.start_ingestion("session-a", 2, "fingerprint-a", "test-model")
    repository.complete_ingestion("session-a", 2, 1, 1)
    assert repository.ingestion_completed("session-a", 2, "fingerprint-a")
    assert not repository.ingestion_completed("session-a", 2, "fingerprint-b")

