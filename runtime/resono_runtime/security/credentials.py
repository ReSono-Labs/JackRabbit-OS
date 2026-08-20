from __future__ import annotations

from typing import Protocol


class CredentialBridge(Protocol):
    def hasOpenAiPlatformKey(self) -> bool: ...
    def getOpenAiPlatformKey(self) -> str | None: ...
    def putOpenAiPlatformKey(self, value: str) -> None: ...
    def deleteOpenAiPlatformKey(self) -> None: ...
    def hasOpenAiSubscriptionTokens(self) -> bool: ...
    def getOpenAiSubscriptionTokens(self) -> str | None: ...
    def putOpenAiSubscriptionTokens(self, value: str) -> None: ...
    def deleteOpenAiSubscriptionTokens(self) -> None: ...
    def sealConnectionCredential(self, record_name: str, plaintext: str) -> str: ...
    def openConnectionCredential(self, record_name: str, envelope: str) -> str: ...


class ProviderCredentials:
    def __init__(self, bridge: CredentialBridge) -> None:
        self._bridge = bridge

    def has_platform_key(self) -> bool:
        return bool(self._bridge.hasOpenAiPlatformKey())

    def platform_key(self) -> str:
        value = self._bridge.getOpenAiPlatformKey()
        if not value:
            raise CredentialUnavailable("OpenAI Platform is not connected.")
        return str(value)

    def connect_platform(self, value: str) -> None:
        self._bridge.putOpenAiPlatformKey(value)

    def disconnect_platform(self) -> None:
        self._bridge.deleteOpenAiPlatformKey()

    def has_subscription(self) -> bool:
        return bool(self._bridge.hasOpenAiSubscriptionTokens())

    def subscription_tokens(self) -> str:
        value = self._bridge.getOpenAiSubscriptionTokens()
        if not value:
            raise CredentialUnavailable("ChatGPT subscription is not connected.")
        return str(value)

    def connect_subscription(self, value: str) -> None:
        self._bridge.putOpenAiSubscriptionTokens(value)

    def disconnect_subscription(self) -> None:
        self._bridge.deleteOpenAiSubscriptionTokens()


class CredentialUnavailable(RuntimeError):
    pass


class ConnectionCredentialEnvelopes:
    """The only Python adapter allowed to seal or open connection credentials."""

    def __init__(self, bridge: CredentialBridge) -> None:
        self._bridge = bridge

    def seal(self, connection_id: str, plaintext: str) -> str:
        if not plaintext:
            raise ValueError("Connection credential cannot be empty.")
        return str(self._bridge.sealConnectionCredential(_record_name(connection_id), plaintext))

    def open(self, connection_id: str, envelope: str) -> str:
        if not envelope:
            raise CredentialUnavailable("Connection credential is unavailable.")
        value = self._bridge.openConnectionCredential(_record_name(connection_id), envelope)
        if not value:
            raise CredentialUnavailable("Connection credential is unavailable.")
        return str(value)


def _record_name(connection_id: str) -> str:
    from uuid import UUID

    normalized = str(UUID(connection_id))
    if normalized != connection_id:
        raise ValueError("Connection ID must be a canonical UUID.")
    return f"connection:{normalized}:credential"
