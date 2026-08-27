"""Composition-root smoke: RuntimeApplication must wire with fakes (TDD).

Host tests never instantiated the full application until a device boot --
twice -- exposed wiring mistakes (a phantom local variable reference and
mislocated kwargs) that 86 isolated tests could not see. This test composes
the whole root with the fake credential bridge so wiring errors die in CI.
"""

from __future__ import annotations

from pathlib import Path

from resono_runtime.application import RuntimeApplication
from resono_runtime.config import RuntimeConfig

from .conftest import FakeCredentialBridge


def test_application_composition_root_wires_with_fake_bridge(tmp_path):
    root = tmp_path / "app"
    config = RuntimeConfig.create(str(root), "t" * 40)
    config.prepare_directories()
    application = RuntimeApplication(
        config,
        credential_bridge=FakeCredentialBridge(),
        telephony_bridge=None,
    )
    assert application is not None
    # the provider controller must own its key repository and envelopes
    assert application._providers._provider_keys is not None
    assert application._providers._credential_envelopes is not None
    assert application._text_runner._provider_keys is not None
