from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..api.events import RuntimeEventStream
from ..providers.openai import OpenAIProviderError
from ..security.credentials import CredentialUnavailable, ProviderCredentials
from ..storage.provider_settings import ProviderSettingsRepository
from ..providers.openai.subscription import OpenAISubscription


@dataclass(frozen=True, slots=True)
class TextTurnResult:
    text: str
    model: str


class AgentsSdkTextRunner:
    """One small text-agent path backed only by the OpenAI Agents SDK."""

    def __init__(
        self,
        *,
        credentials: ProviderCredentials,
        settings: ProviderSettingsRepository,
        events: RuntimeEventStream,
        local_api_token: str,
        subscription: OpenAISubscription | None = None,
        executor: Callable[..., str] | None = None,
    ) -> None:
        self._credentials = credentials
        self._settings = settings
        self._events = events
        self._local_api_token = local_api_token
        self._subscription = subscription
        self._executor = executor or _run_with_agents_sdk

    def run(self, user_input: str) -> TextTurnResult:
        prompt = user_input.strip()
        if not prompt or len(prompt) > 16_384:
            raise OpenAIProviderError(
                "invalid_text_input", "Enter a message between 1 and 16,384 characters.", status=400
            )
        selection = self._settings.selection()
        if selection.access_path == "subscription":
            if self._subscription is None:
                raise OpenAIProviderError("credential_unavailable", "Connect ChatGPT first.", status=409)
            api_key = self._subscription.access_token()
            base_url = "https://chatgpt.com/backend-api/codex"
        else:
            try:
                api_key = self._credentials.platform_key()
            except CredentialUnavailable as error:
                raise OpenAIProviderError(
                    "credential_unavailable", "Connect OpenAI first.", status=409
                ) from error
            base_url = None
        model = selection.text_model
        if not model:
            raise OpenAIProviderError(
                "model_required", "Choose a text model first.", status=409
            )

        self._events.publish("text.started", {"provider": "openai", "model": model})
        try:
            output = self._executor(
                api_key=api_key,
                model=model,
                user_input=prompt,
                local_api_token=self._local_api_token,
                base_url=base_url,
                reasoning_effort=selection.reasoning_effort,
            ).strip()
        except OpenAIProviderError:
            raise
        except Exception as error:
            self._events.publish("text.failed", {"provider": "openai", "model": model})
            raise OpenAIProviderError(
                "agent_turn_failed", "The text agent could not complete this turn.", status=502
            ) from error
        if not output:
            raise OpenAIProviderError(
                "agent_output_empty", "The text agent returned no result.", status=502
            )
        self._events.publish("text.completed", {"provider": "openai", "model": model})
        return TextTurnResult(text=output, model=model)


def _run_with_agents_sdk(
    *,
    api_key: str,
    model: str,
    user_input: str,
    local_api_token: str,
    base_url: str | None,
    reasoning_effort: str,
) -> str:
    return asyncio.run(
        _run_with_agents_sdk_async(
            api_key=api_key,
            model=model,
            user_input=user_input,
            local_api_token=local_api_token,
            base_url=base_url,
            reasoning_effort=reasoning_effort,
        )
    )


async def _run_with_agents_sdk_async(
    *,
    api_key: str,
    model: str,
    user_input: str,
    local_api_token: str,
    base_url: str | None,
    reasoning_effort: str,
) -> str:
    from agents import Agent, ModelSettings, RunConfig, Runner, set_tracing_disabled
    from agents.mcp import MCPServerStreamableHttp
    from agents.models.openai_provider import OpenAIProvider
    from openai.types.shared import Reasoning

    set_tracing_disabled(True)
    provider = OpenAIProvider(api_key=api_key, base_url=base_url, use_responses=True)
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
        model_settings = ModelSettings(
            reasoning=Reasoning(effort=reasoning_effort) if reasoning_effort != "none" else None,
            store=False if base_url else None,
        )
        agent = Agent(
            name="ReSono R1",
            instructions=(
                "You are the concise text assistant on a ReSono R1. Use the device MCP tool "
                "when the user asks about this device or its runtime. Never invent device state."
            ),
            model=model,
            model_settings=model_settings,
            mcp_servers=[mcp_server],
        )
        run_config = RunConfig(model_provider=provider)
        if base_url:
            result = Runner.run_streamed(
                agent,
                input=user_input,
                run_config=run_config,
                max_turns=4,
            )
            async for _event in result.stream_events():
                pass
        else:
            result = await Runner.run(
                agent,
                input=user_input,
                run_config=run_config,
                max_turns=4,
            )
    return str(result.final_output)
