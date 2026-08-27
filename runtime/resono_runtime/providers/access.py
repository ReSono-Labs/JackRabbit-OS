"""Provider-neutral credential/base-URL resolution for agent consumers."""

from __future__ import annotations

from dataclasses import dataclass

from ..security.credentials import (
    ConnectionCredentialEnvelopes,
    CredentialUnavailable,
    ProviderCredentials,
)
from ..storage.provider_catalog import ProviderCatalogRepository
from ..storage.provider_keys import ProviderKeyRepository
from ..storage.provider_settings import ProviderSettingsRepository
from .openai import openai_provider_access
from .openai.platform import OpenAIProviderError
from .openai.subscription import OpenAISubscription


@dataclass(frozen=True, slots=True)
class ProviderAccess:
    """Resolved credential for one active provider access path."""

    api_key: str
    base_url: str | None
    use_responses: bool
    provider: str


def provider_access(
    *,
    credentials: ProviderCredentials,
    settings: ProviderSettingsRepository,
    subscription: OpenAISubscription | None,
    catalog: ProviderCatalogRepository | None,
    envelopes: ConnectionCredentialEnvelopes,
    keys: ProviderKeyRepository,
) -> ProviderAccess:
    """Resolve the API key, base URL, and API style for the active provider.

    OpenAI keeps its existing platform/subscription decision untouched. Any
    other catalog provider resolves through its sealed API key and configured
    base URL; ``api_style`` decides whether the Agents SDK uses the Responses
    API (``use_responses=True``) or chat completions (``False``).
    """
    selection = settings.selection()
    provider = selection.provider.strip().lower()
    if provider == "openai":
        access = openai_provider_access(
            credentials=credentials,
            settings=settings,
            subscription=subscription,
        )
        return ProviderAccess(access.api_key, access.base_url, True, "openai")

    descriptor = catalog.descriptor(provider) if catalog is not None else None
    if descriptor is None or not descriptor.base_url:
        raise OpenAIProviderError(
            "provider_unavailable", "Provider is not configured.", status=400
        )
    envelope = keys.get(provider)
    if envelope is None:
        raise OpenAIProviderError(
            "credential_unavailable", f"Connect {provider} first.", status=409
        )
    try:
        api_key = envelopes.open_provider_key(provider, envelope)
    except CredentialUnavailable as error:
        raise OpenAIProviderError(
            "credential_unavailable", f"Connect {provider} first.", status=409
        ) from error
    return ProviderAccess(
        api_key,
        descriptor.base_url,
        descriptor.api_style == "responses",
        provider,
    )
