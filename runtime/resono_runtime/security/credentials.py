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
