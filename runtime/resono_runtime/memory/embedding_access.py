from __future__ import annotations

from ..providers.openai import (
    OpenAIEmbeddings,
    OpenAIProviderError,
    openai_provider_access,
)
from ..providers.openai.subscription import OpenAISubscription
from ..security.credentials import ProviderCredentials
from ..storage.provider_settings import ProviderSettingsRepository


def embedding_api_key(
    *,
    credentials: ProviderCredentials,
    settings: ProviderSettingsRepository | None = None,
    subscription: OpenAISubscription | None = None,
) -> str | None:
    """Resolve the credential allowed to call the embedding provider.

    Delegates to the single platform-wide access decision
    (``openai_provider_access``) so embeddings always ride the same token as
    every agent. When no selection is available (tests, tooling), falls back
    to the Platform key, then the subscription token. Returns None when no
    usable credential exists so callers degrade honestly instead of faking a
    vector result.
    """
    if settings is not None:
        try:
            return openai_provider_access(
                credentials=credentials,
                settings=settings,
                subscription=subscription,
            ).api_key
        except OpenAIProviderError:
            return None
    if credentials.has_platform_key():
        return credentials.platform_key()
    if subscription is not None and credentials.has_subscription():
        try:
            return subscription.access_token()
        except OpenAIProviderError:
            return None
    return None


def default_embedding_factory(api_key: str, safety_source: str) -> OpenAIEmbeddings:
    return OpenAIEmbeddings(api_key, safety_source=safety_source)
