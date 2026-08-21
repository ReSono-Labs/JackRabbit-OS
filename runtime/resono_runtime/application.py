from __future__ import annotations

from pathlib import Path
from .api.events import RuntimeEventStream
from .api.http_server import RuntimeHttpServer
from .config import RuntimeConfig
from .core.release_supervisor import ReleaseSupervisor
from .core.runtime_environment import agent_runtime_status, standard_library_status
from .security.pairing import PairingAuthority
from .security.credentials import ConnectionCredentialEnvelopes, ProviderCredentials
from .providers.controller import ProviderController
from .mcp import LocalMcpServer, McpLifecycle
from .storage.database import RuntimeDatabase
from .storage.agent_audiences import AgentAudienceRepository
from .storage.lifecycle_repository import LifecycleRepository
from .storage.provider_settings import ProviderSettingsRepository
from .storage.profile_settings import UserProfileRepository
from .storage.sessions import SessionTranscriptRepository
from .storage.memory import MemoryRepository
from .storage.skills import SkillCatalogRepository
from .agents import AgentAudience, AgentAudienceRouter, AgentsSdkTextRunner, MemoryReviewRunner
from .agents.context_builder import PrimaryContextBuilder
from .memory.evidence import VoiceToolEvidenceRecorder
from .memory.pipeline import MemoryPipeline
from .memory.service import MemoryService
from .memory.session_context import SessionContextBuilder
from .memory.tools import MemoryLookupTool, MemoryToolPackage
from .providers.openai import OpenAISubscription
from .storage.provider_catalog import ProviderCatalogRepository
from .core.logging import runtime_logger
from .tools import (DEVICE_STATUS_TOOL_SET, MEMORY_TOOL_SET, ToolCatalog,
                    register_device_status, register_memory_tools)
from .skills import SkillActivation
from .skills.archives import SkillArchiveInspector
from .skills.lifecycle import SkillLifecycle
from .api.skill_routes import SkillRoutes
from .api.mail_routes import MailRoutes
from .api.calendar_routes import CalendarRoutes
from .api.mcp_routes import McpRoutes
from .api.tool_routes import ToolRoutes
from .api.plugin_routes import PluginRoutes
from .plugins.archives import PluginArchiveInspector
from .plugins.lifecycle import PluginLifecycle
from .plugins.card_lifecycle import PluginCardLifecycle
from .storage.plugins import PluginCatalogRepository
from .storage.plugin_components import PluginComponentRepository
from .imports import ImportRecovery
from .api.creation_routes import CreationRoutes
from .creations import CreationArchiveInspector, CreationDescriptorInspector, CreationLifecycle
from .storage.creations import CreationCatalogRepository
from .domains.mail.connector import ImapSmtpConnector
from .domains.mail.repository import MailRepository
from .domains.mail.scheduler import MailSyncScheduler
from .domains.mail.service import MailService
from .domains.mail.tools import MAIL_TOOL_SET, register_mail_tools
from .domains.calendar.repository import CalendarRepository
from .domains.calendar.scheduler import CalendarSyncScheduler
from .domains.calendar.service import CalendarService
from .connectors.calendar import CaldavCalendarProviderClient, IcsCalendarProviderClient
from .tools.calendar import CALENDAR_TOOL_SET, CalendarToolPackage
from .domains.tasks import TaskRepository, TaskService
from .tools.tasks import TASKS_TOOL_SET, TasksToolPackage
from .api.task_routes import TaskRoutes
from .storage.connection_credentials import ConnectionCredentialRepository
from .storage.mcp_connections import McpConnectionRepository
from .connections.records import ConnectionRepository
from .providers.openai.web_search import OpenAIWebSearch
from .tools.web_search import WEB_SEARCH_TOOL_SET, register_web_search
from .tools.delegation import GOAL_TOOL_SET, register_goal_tools
from .realtime import VoiceModeService, register_voice_mode_tool
from .api.connection_routes import ConnectionRoutes
from .plugins.bundled_install import BundledPluginInstaller
from .storage.agent_runs import AgentRunRepository
from .storage.background_agent_settings import BackgroundAgentSettingsRepository
from .api.background_agent_routes import BackgroundAgentRoutes
from .background_agent.composition import BackgroundRunFactory
from .background_agent.mcp_gateway import BackgroundMcpGateway
from .background_agent.service import BackgroundAgentService
from .background_agent.completion_dispatch import CompletionDispatcher
from .storage.agent_deliveries import AgentRunDeliveryRepository
from .background_agent.workspace import RunWorkspaceRegistry
from .storage.workspace import WorkspaceRepository
from .workspace.service import DurableWorkspace
from .workspace.tools import WORKSPACE_TOOL_SET, register_workspace_tools


class RuntimeApplication:
    def __init__(
        self,
        config: RuntimeConfig,
        credential_bridge: object,
        restart_request: object | None = None,
    ) -> None:
        self._config = config
        self._database = RuntimeDatabase(config.database_path)
        self._audience_router = AgentAudienceRouter(AgentAudienceRepository(self._database))
        self._lifecycle = LifecycleRepository(self._database)
        self._events = RuntimeEventStream()
        self._pairing = PairingAuthority()
        self._releases = ReleaseSupervisor(config.releases_path)
        credentials = ProviderCredentials(credential_bridge)
        connection_envelopes = ConnectionCredentialEnvelopes(credential_bridge)
        provider_settings = ProviderSettingsRepository(self._database)
        self._profile = UserProfileRepository(self._database)
        self._subscription = OpenAISubscription(credentials)
        self._catalog = ProviderCatalogRepository(self._database)
        self._sessions = SessionTranscriptRepository(self._database)
        self._memories = MemoryRepository(self._database)
        self._skills = SkillCatalogRepository(self._database)
        import_recovery = ImportRecovery(self._database)
        self._plugins = PluginCatalogRepository(self._database)
        self._plugin_components = PluginComponentRepository(self._database)
        self._skill_activation = SkillActivation(
            self._skills,
            self._audience_router,
            self._plugins,
            self._plugin_components,
        )
        self._skill_lifecycle = SkillLifecycle(
            catalog=self._skills,
            audiences=self._audience_router,
            skills_root=config.skills_path,
            rollback_root=config.skill_rollback_path,
            recovery=import_recovery,
        )
        self._skill_routes = SkillRoutes(
            self._skill_lifecycle,
            SkillArchiveInspector(config.skill_quarantine_path),
        )
        self._session_context_builder = SessionContextBuilder(
            sessions=self._sessions,
            memories=self._memories,
        )
        self._memory_lookup_tool = MemoryLookupTool(
            memories=self._memories,
            credentials=credentials,
            safety_source=config.local_api_token,
            settings=provider_settings,
            subscription=self._subscription,
        )
        self._voice_modes = VoiceModeService()
        self._tools = ToolCatalog(audience_router=self._audience_router)
        self._tools.set_invocation_authorizer(self._voice_modes.allows)
        self._tools.set_invocation_observer(VoiceToolEvidenceRecorder(self._sessions))
        register_device_status(self._tools, self.health)
        register_memory_tools(self._tools, MemoryToolPackage(
            lookup=self._memory_lookup_tool,
            memories=self._memories,
            sessions=self._sessions,
        ))
        self._tools.register(self._skill_activation.tool_definition())
        self._mail_repository = MailRepository(self._database)
        self._mail_service = MailService(
            self._mail_repository,
            ConnectionCredentialRepository(self._database),
            connection_envelopes,
            ImapSmtpConnector(),
        )
        self._mail_scheduler = MailSyncScheduler(self._mail_repository, self._mail_service)
        self._mail_routes = MailRoutes(self._mail_repository, self._mail_service)
        self._calendar_repository = CalendarRepository(self._database)
        self._calendar_service = CalendarService(
            self._calendar_repository,
            ConnectionCredentialRepository(self._database),
            connection_envelopes,
            IcsCalendarProviderClient(),
            CaldavCalendarProviderClient(),
        )
        self._calendar_scheduler = CalendarSyncScheduler(self._calendar_repository, self._calendar_service)
        self._calendar_routes = CalendarRoutes(self._calendar_repository, self._calendar_service)
        CalendarToolPackage(self._calendar_service).register(self._tools)
        self._task_repository = TaskRepository(self._database)
        self._task_service = TaskService(self._task_repository)
        self._task_routes = TaskRoutes(self._task_repository)
        TasksToolPackage(self._task_service).register(self._tools)
        self._connections = ConnectionRepository(self._database)
        self._connection_routes = ConnectionRoutes(self._connections)
        register_mail_tools(self._tools, self._mail_repository, self._mail_service)
        register_web_search(self._tools, OpenAIWebSearch(credentials, provider_settings, self._subscription))
        self._background_agent_runs = AgentRunRepository(self._database)
        self._background_agent_settings = BackgroundAgentSettingsRepository(self._database)
        self._run_workspaces = RunWorkspaceRegistry(config.background_runs_path)
        self._workspace = DurableWorkspace(
            config.user_workspace_path,
            WorkspaceRepository(self._database),
        )
        register_workspace_tools(self._tools, self._workspace, self._run_workspaces)
        self._primary_contexts = PrimaryContextBuilder(
            tools=self._tools, skills=self._skill_activation,
            memory=self._session_context_builder,
        )
        self._agent_deliveries = AgentRunDeliveryRepository(self._database)
        self._background_agent_routes = BackgroundAgentRoutes(
            settings=self._background_agent_settings,
            runs=self._background_agent_runs,
            catalog=self._tools,
            deliveries=self._agent_deliveries,
        )
        self._background_agent_gateway = BackgroundMcpGateway(
            health=self.health,
            catalog=self._tools,
            allowed_names=lambda: self._background_agent_settings.get().allowed_tool_names,
            runs=self._background_agent_runs,
        )
        self._background_agent_routes.attach_gateway(self._background_agent_gateway)
        self._background_agent_factory = BackgroundRunFactory(
            credentials=credentials,
            provider_settings=provider_settings,
            background_settings=self._background_agent_settings,
            subscription=self._subscription,
            runs=self._background_agent_runs,
            gateway=self._background_agent_gateway,
            local_api_url=f"http://{config.local_api_host}:{config.local_api_port}",
            local_api_token=config.local_api_token,
            workspaces=self._run_workspaces,
            contexts=self._primary_contexts,
        )
        self._background_agent = BackgroundAgentService(
            settings=self._background_agent_settings,
            runs=self._background_agent_runs,
            loop_factory=self._background_agent_factory.prepare,
            completion_dispatcher=CompletionDispatcher(
                deliveries=self._agent_deliveries,
                voice_session_active=lambda session_id: self._providers.is_active_realtime_session(session_id),
            ),
            shutdown=self._background_agent_factory.close,
        )
        register_goal_tools(self._tools, self._background_agent, self._voice_modes)
        register_voice_mode_tool(self._tools, self._voice_modes)
        self._outbound_mcp = McpLifecycle(
            McpConnectionRepository(self._database),
            self._connections,
            self._audience_router,
            self._tools,
            ConnectionCredentialRepository(self._database),
            connection_envelopes,
        )
        self._mcp_routes = McpRoutes(self._outbound_mcp)
        self._tool_routes = ToolRoutes(self._tools)
        self._card_catalog = CreationCatalogRepository(self._database)
        self._plugin_cards = PluginCardLifecycle(self._card_catalog, self._plugin_components)
        self._plugin_lifecycle = PluginLifecycle(
            self._plugins,
            self._audience_router,
            config.plugins_path,
            config.plugin_rollback_path,
            self._plugin_components,
            self._skills,
            self._outbound_mcp,
            import_recovery,
            self._plugin_cards,
        )
        self._plugin_routes = PluginRoutes(
            self._plugin_lifecycle,
            PluginArchiveInspector(config.plugin_quarantine_path),
        )
        self._bundled_plugins = BundledPluginInstaller(
            self._plugin_lifecycle,
            self._plugins,
            PluginArchiveInspector(config.plugin_quarantine_path),
        )
        self._creation_lifecycle = CreationLifecycle(
            self._card_catalog,
            self._audience_router,
            config.creations_path,
            config.creation_rollback_path,
            import_recovery,
        )
        self._creation_routes = CreationRoutes(
            self._creation_lifecycle,
            CreationArchiveInspector(config.creation_quarantine_path),
            CreationDescriptorInspector(config.creation_quarantine_path),
        )
        self._providers = ProviderController(
            credentials=credentials,
            settings=provider_settings,
            events=self._events,
            safety_source=config.local_api_token,
            subscription=self._subscription,
            profile=self._profile,
            catalog=self._catalog,
            sessions=self._sessions,
            session_context=self._session_context_builder,
            voice_tools=lambda: self._tools.realtime_definitions(
                exclude_names=frozenset({"goal_start"}),
            ),
            goal_intake_tools=lambda: self._tools.realtime_definitions(
                include_names=frozenset({"voice_mode_switch", "goal_start"}),
            ),
            voice_skill_instructions=self._skill_activation.voice_instructions,
            voice_modes=self._voice_modes,
        )
        self._text_runner = AgentsSdkTextRunner(
            credentials=credentials,
            settings=provider_settings,
            events=self._events,
            local_api_token=config.local_api_token,
            subscription=self._subscription,
        )
        self._memory_reviewer = MemoryReviewRunner(
            credentials=credentials,
            settings=provider_settings,
            events=self._events,
            local_api_token=config.local_api_token,
            subscription=self._subscription,
        )
        self._memory_pipeline = MemoryPipeline(
            sessions=self._sessions,
            memories=self._memories,
            reviewer=self._memory_reviewer,
            credentials=credentials,
            safety_source=config.local_api_token,
            events=self._events,
            settings=provider_settings,
            subscription=self._subscription,
        )
        self._memory = MemoryService(
            sessions=self._sessions,
            memories=self._memories,
            pipeline=self._memory_pipeline,
            credentials=credentials,
            safety_source=config.local_api_token,
            settings=provider_settings,
            subscription=self._subscription,
        )
        self._mcp = LocalMcpServer(self.health, catalog=self._tools)
        self._restart_request = restart_request
        self._environment = standard_library_status()
        self._agent_environment = agent_runtime_status()
        self._server: RuntimeHttpServer | None = None
        self._log = runtime_logger()

    def start(self) -> None:
        self._log.info("runtime.start.begin")
        self._releases.prepare()
        self._database.migrate()
        if self._audience_router.binding_for(CALENDAR_TOOL_SET) is None:
            self._audience_router.set_audience(
                CALENDAR_TOOL_SET,
                AgentAudience.BOTH,
                changed_by="runtime-bootstrap",
                reason="built-in Calendar is available to Voice and Text",
            )
        if self._audience_router.binding_for(TASKS_TOOL_SET) is None:
            self._audience_router.set_audience(
                TASKS_TOOL_SET, AgentAudience.BOTH, changed_by="runtime-bootstrap",
                reason="enable built-in Tasks for Voice and Background Agent",
            )
        if self._audience_router.binding_for(DEVICE_STATUS_TOOL_SET) is None:
            self._audience_router.set_audience(
                DEVICE_STATUS_TOOL_SET,
                AgentAudience.BOTH,
                changed_by="runtime-bootstrap",
                reason="preserve accepted device-status availability",
            )
        if self._audience_router.binding_for(MEMORY_TOOL_SET) is None:
            self._audience_router.set_audience(
                MEMORY_TOOL_SET,
                AgentAudience.BOTH,
                changed_by="runtime-bootstrap",
                reason="enable built-in memory for Voice and Background Agent",
            )
        if self._audience_router.binding_for(MAIL_TOOL_SET) is None:
            self._audience_router.set_audience(
                MAIL_TOOL_SET,
                AgentAudience.BOTH,
                changed_by="runtime-bootstrap",
                reason="enable built-in Mail for Voice and Background Agent",
            )
        if self._audience_router.binding_for(WEB_SEARCH_TOOL_SET) is None:
            self._audience_router.set_audience(
                WEB_SEARCH_TOOL_SET,
                AgentAudience.BOTH,
                changed_by="runtime-bootstrap",
                reason="enable built-in web search for Voice and Background Agent",
            )
        if self._audience_router.binding_for(GOAL_TOOL_SET) is None:
            self._audience_router.set_audience(
                GOAL_TOOL_SET,
                AgentAudience.VOICE,
                changed_by="runtime-bootstrap",
                reason="enable the built-in Voice goal delegation capability",
            )
        if self._audience_router.binding_for(WORKSPACE_TOOL_SET) is None:
            self._audience_router.set_audience(
                WORKSPACE_TOOL_SET,
                AgentAudience.BOTH,
                changed_by="runtime-bootstrap",
                reason="enable read-only workspace access for Voice and bounded workspace access for Background Agent",
            )
        self._catalog.bootstrap_defaults()
        self._skill_lifecycle.recover()
        self._plugin_lifecycle.recover()
        self._creation_lifecycle.recover()
        self._background_agent.recover_interrupted()
        self._bundled_plugins.install_once(
            Path(__file__).resolve().parent / "plugins" / "bundled" / "resono-mail"
        )
        self._outbound_mcp.restore()
        record = self._lifecycle.record_start()
        self._log.info(
            "runtime.database_ready",
            extra={"release": str(record.value), "migration": self._config.database_path},
        )
        self._server = RuntimeHttpServer(
            host=self._config.local_api_host,
            port=self._config.local_api_port,
            token=self._config.local_api_token,
            health=self.health,
            lifecycle=self._lifecycle,
            events=self._events,
            pairing=self._pairing,
            providers=self._providers,
            text_runner=self._text_runner,
            subscription=self._subscription,
            mcp=self._mcp,
            profile=self._profile,
            sessions=self._sessions,
            memory=self._memory,
            restart_request=self._request_restart,
            skills=self._skill_routes,
            mail=self._mail_routes,
            calendar=self._calendar_routes,
            tasks=self._task_routes,
            outbound_mcp=self._mcp_routes,
            tools=self._tool_routes,
            plugins=self._plugin_routes,
            creations=self._creation_routes,
            connections=self._connection_routes,
            background_agent=self._background_agent_routes,
        )
        self._server.start()
        self._background_agent.start()
        self._mail_scheduler.start()
        self._calendar_scheduler.start()
        self._events.publish(
            "runtime.ready",
            {"status": "ready", "startCount": int(record.value)},
        )
        self._log.info("runtime.ready", extra={"start_count": int(record.value)})

    def stop(self) -> None:
        self._events.publish("runtime.stopping", {"status": "stopping"})
        self._background_agent.stop()
        self._mail_scheduler.stop()
        self._calendar_scheduler.stop()
        if self._server is not None:
            self._server.stop()
            self._server = None

    def health(self) -> dict[str, object]:
        database = self._database.health()
        status = (
            "ready"
            if database["status"] == "ready" and self._agent_environment["status"] == "ready"
            else "not_ready"
        )
        return {
            "contractVersion": 1,
            "status": status,
            "service": "resono-runtime",
            "database": database,
            "release": self._releases.active().release_id,
            "python": self._environment,
            "agents": self._agent_environment,
        }

    def _request_restart(self) -> None:
        self._events.publish("runtime.restart_requested", {"status": "restarting"})
        callback = self._restart_request
        if callback is not None:
            callback.run()
