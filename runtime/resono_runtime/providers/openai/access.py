from __future__ import annotations

from dataclasses import dataclass

from ...security.credentials import CredentialUnavailable, ProviderCredentials
from ...storage.provider_settings import ProviderSettingsRepository
from .platform import OpenAIProviderError
from .subscription import OpenAISubscription

SUBSCRIPTION_BASE_URL = "https://chatgpt.com/backend-api/codex"


@dataclass(frozen=True, slots=True)
class ProviderAccess:
    """Resolved credential for one OpenAI access path."""

    api_key: str
    base_url: str | None


def openai_provider_access(
    *,
    credentials: ProviderCredentials,
    settings: ProviderSettingsRepository,
    subscription: OpenAISubscription | None,
) -> ProviderAccess:
    """Resolve the API key and base URL every OpenAI consumer must use.

    This is the single platform-wide credential decision: the configured
    access path wins — the ChatGPT subscription access token (Codex base URL)
    when the subscription path is selected, the Keystore Platform key
    otherwise. Text agents, the memory review agent, embeddings, and any
    future agent or provider path resolve their credential here so the whole
    runtime always rides one token; no consumer re-implements the choice.
    """
    selection = settings.selection()
    if selection.access_path == "subscription":
        if subscription is None:
            raise OpenAIProviderError(
                "credential_unavailable", "Connect ChatGPT first.", status=409
            )
        return ProviderAccess(
            api_key=subscription.access_token(),
            base_url=SUBSCRIPTION_BASE_URL,
        )
    try:
        api_key = credentials.platform_key()
    except CredentialUnavailable as error:
        raise OpenAIProviderError(
            "credential_unavailable", "Connect OpenAI first.", status=409
        ) from error
    return ProviderAccess(api_key=api_key, base_url=None)
