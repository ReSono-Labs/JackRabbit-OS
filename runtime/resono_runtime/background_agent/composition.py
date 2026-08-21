"""Sole construction point for provider, MCP, and recipe execution internals."""

from __future__ import annotations

from ..providers.openai import OpenAISubscription, openai_provider_access
from ..security.credentials import ProviderCredentials
from ..storage.agent_runs import AgentRunRepository
from ..storage.background_agent_settings import BackgroundAgentSettingsRepository
from ..storage.provider_settings import ProviderSettingsRepository
from .mcp_gateway import BackgroundMcpGateway
from .run_contract import AgentRunRequest
from .execution import BackgroundAgentExecution
from .sdk_executor import AgentsSdkExecutor, AsyncExecutionRuntime, ExecutionBudget
from .service import PreparedRun
from .workspace import RunWorkspaceRegistry
from ..agents.context_builder import PrimaryContextBuilder


class BackgroundRunFactory:
    def __init__(self, *, credentials: ProviderCredentials,
                 provider_settings: ProviderSettingsRepository,
                 background_settings: BackgroundAgentSettingsRepository,
                 subscription: OpenAISubscription | None, runs: AgentRunRepository,
                 gateway: BackgroundMcpGateway, local_api_url: str,
                 local_api_token: str, workspaces: RunWorkspaceRegistry,
                 contexts: PrimaryContextBuilder) -> None:
        self._credentials = credentials
        self._provider_settings = provider_settings
        self._background_settings = background_settings
        self._subscription = subscription
        self._runs = runs
        self._gateway = gateway
        self._local_api_url = local_api_url.rstrip("/")
        self._local_api_token = local_api_token
        self._workspaces = workspaces
        self._contexts = contexts
    def prepare(self, request: AgentRunRequest) -> PreparedRun:
        self._workspaces.create(request.run_id, max_total_bytes=request.limits.max_workspace_bytes)
        access = openai_provider_access(
            credentials=self._credentials, settings=self._provider_settings,
            subscription=self._subscription,
        )
        selection = self._provider_settings.selection()
        if not selection.text_model:
            raise RuntimeError("Choose a text model before enabling delegated work")
        settings = self._background_settings.get()
        budget = ExecutionBudget(
            max_seconds=request.limits.max_seconds,
            max_turns=request.limits.max_model_turns,
        )
        async_runtime = AsyncExecutionRuntime()
        self._gateway.open(request)
        try:
            worker = AgentsSdkExecutor(
                api_key=access.api_key, model=selection.text_model,
                base_url=access.base_url, reasoning_effort=settings.reasoning_effort,
                mcp_url=f"{self._local_api_url}/v1/background-agent/mcp/{request.run_id}",
                local_api_token=self._local_api_token,
                timeout_seconds=request.limits.max_seconds, run_id=request.run_id,
                runs=self._runs,
                budget=budget,
                async_runtime=async_runtime,
            )
            context = self._contexts.background_goal(
                run_id=request.run_id, origin_id=request.origin_id,
                instruction_profile=request.instruction_profile,
            )
            self._runs.record_event(request.run_id, "context_frozen", {
                "version": context.context_version,
                "toolIds": list(context.tool_ids), "skillIds": list(context.skill_ids),
                "memoryReferences": list(context.memory_references),
            })
            execution = BackgroundAgentExecution(
                repository=self._runs, executor=worker, context=context,
            )
        except Exception:
            self._gateway.close(request.run_id)
            async_runtime.close()
            raise
        def close() -> None:
            self._gateway.close(request.run_id)
            async_runtime.close()
        return PreparedRun(execution, close)

    def close(self) -> None:
        """Per-run SDK loops are released by their prepared-run owner."""
