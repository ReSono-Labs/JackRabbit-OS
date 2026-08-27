from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass

from ..api.events import RuntimeEventStream
from ..providers.access import provider_access
from ..providers.openai import OpenAIProviderError
from ..providers.openai.subscription import OpenAISubscription
from ..security.credentials import ConnectionCredentialEnvelopes, ProviderCredentials
from ..storage.provider_catalog import ProviderCatalogRepository
from ..storage.provider_keys import ProviderKeyRepository
from ..storage.provider_settings import ProviderSettingsRepository
from .sdk_runner import run_agent_turn


@dataclass(frozen=True, slots=True)
class TextTurnResult:
    text: str
    model: str


class AgentsSdkTextRunner:
    """Conversational text agent backed only by the OpenAI Agents SDK.

    This runner is intentionally memory-free. Memory work is owned by the
    voice path (session-start context + the ``memory_lookup`` Realtime tool)
    and by the post-session review agent (``MemoryReviewRunner``), which
    summarizes a transcript into provenance-linked memories. The text agent
    only answers the user's message and may call the device status MCP tool.
    """

    def __init__(
        self,
        *,
        credentials: ProviderCredentials,
        settings: ProviderSettingsRepository,
        events: RuntimeEventStream,
        local_api_token: str,
        subscription: OpenAISubscription | None = None,
        executor: Callable[..., str] | None = None,
        catalog: ProviderCatalogRepository | None = None,
        credential_envelopes: ConnectionCredentialEnvelopes | None = None,
        provider_keys: ProviderKeyRepository | None = None,
    ) -> None:
        self._credentials = credentials
        self._settings = settings
        self._events = events
        self._local_api_token = local_api_token
        self._subscription = subscription
        self._executor = executor or _run_with_agents_sdk
        self._catalog = catalog
        self._credential_envelopes = credential_envelopes
        self._provider_keys = provider_keys

    def run(self, user_input: str) -> TextTurnResult:
        prompt = user_input.strip()
        if not prompt or len(prompt) > 16_384:
            raise OpenAIProviderError(
                "invalid_text_input", "Enter a message between 1 and 16,384 characters.", status=400
            )
        selection = self._settings.selection()
        access = provider_access(
            credentials=self._credentials,
            settings=self._settings,
            subscription=self._subscription,
            catalog=self._catalog,
            envelopes=self._credential_envelopes,
            keys=self._provider_keys,
        )
        api_key = access.api_key
        base_url = access.base_url
        model = selection.text_model
        if not model:
            raise OpenAIProviderError(
                "model_required", "Choose a text model first.", status=409
            )
        reasoning_effort = (
            "none" if access.provider != "openai" else selection.reasoning_effort
        )

        self._events.publish("text.started", {"provider": access.provider, "model": model})
        try:
            output = self._executor(
                api_key=api_key,
                model=model,
                user_input=prompt,
                local_api_token=self._local_api_token,
                base_url=base_url,
                reasoning_effort=reasoning_effort,
                use_responses=access.use_responses,
            ).strip()
        except OpenAIProviderError:
            raise
        except Exception as error:
            self._events.publish("text.failed", {"provider": access.provider, "model": model})
            raise OpenAIProviderError(
                "agent_turn_failed", "The text agent could not complete this turn.", status=502
            ) from error
        if not output:
            raise OpenAIProviderError(
                "agent_output_empty", "The text agent returned no result.", status=502
            )
        self._events.publish("text.completed", {"provider": access.provider, "model": model})
        return TextTurnResult(text=output, model=model)


def _run_with_agents_sdk(
    *,
    api_key: str,
    model: str,
    user_input: str,
    local_api_token: str,
    base_url: str | None,
    reasoning_effort: str,
    use_responses: bool,
) -> str:
    return asyncio.run(
        _run_with_mcp(
            api_key=api_key,
            model=model,
            user_input=user_input,
            local_api_token=local_api_token,
            base_url=base_url,
            reasoning_effort=reasoning_effort,
            use_responses=use_responses,
        )
    )


async def _run_with_mcp(
    *,
    api_key: str,
    model: str,
    user_input: str,
    local_api_token: str,
    base_url: str | None,
    reasoning_effort: str,
    use_responses: bool,
) -> str:
    from agents.mcp import MCPServerStreamableHttp

    mcp_server = MCPServerStreamableHttp(
        params={
            "url": "http://127.0.0.1:8765/v1/mcp",
            "headers": {"Authorization": f"Bearer {local_api_token}"},
            "terminate_on_close": False,
        },
        name="resono-r1-device",
        cache_tools_list=True,
        tool_filter={"allowed_tool_names": ["get_device_status"]},
        require_approval="never",
        use_structured_content=True,
    )
    async with mcp_server:
        return await run_agent_turn(
            api_key=api_key,
            model=model,
            instructions=(
                "You are the concise text assistant on a ReSono R1. Use the device MCP tool "
                "when the user asks about this device or its runtime. Never invent device state."
            ),
            input_text=user_input,
            base_url=base_url,
            reasoning_effort=reasoning_effort,
            max_turns=10,
            agent_name="ReSono R1",
            mcp_server=mcp_server,
            use_responses=use_responses,
        )
