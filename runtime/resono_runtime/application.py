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
from .memory import MemoryLookupTool, MemoryPipeline, MemoryService, SessionContextBuilder
from .providers.openai import OpenAISubscription
from .storage.provider_catalog import ProviderCatalogRepository
from .core.logging import runtime_logger
from .tools import DEVICE_STATUS_TOOL_SET, MEMORY_TOOL_SET, ToolCatalog, register_device_status, register_memory_lookup
from .skills import SkillActivation
from .skills.archives import SkillArchiveInspector
from .skills.lifecycle import SkillLifecycle
from .api.skill_routes import SkillRoutes
from .api.mail_routes import MailRoutes
from .api.mcp_routes import McpRoutes
from .api.tool_routes import ToolRoutes
from .api.plugin_routes import PluginRoutes
from .plugins.archives import PluginArchiveInspector
from .plugins.lifecycle import PluginLifecycle
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
from .storage.connection_credentials import ConnectionCredentialRepository
from .storage.mcp_connections import McpConnectionRepository
from .connections.records import ConnectionRepository
from .providers.openai.web_search import OpenAIWebSearch
from .tools.web_search import WEB_SEARCH_TOOL_SET, register_web_search
from .api.connection_routes import ConnectionRoutes
from .plugins.bundled_install import BundledPluginInstaller
from .handoff import DirectHandoffService, HandoffRepository, OpenAIHandoffInspection
from .api.handoff_routes import HandoffRoutes


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
        self._tools = ToolCatalog(audience_router=self._audience_router)
        register_device_status(self._tools, self.health)
        register_memory_lookup(self._tools, self._memory_lookup_tool)
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
        self._connections = ConnectionRepository(self._database)
        self._connection_routes = ConnectionRoutes(self._connections)
        register_mail_tools(self._tools, self._mail_repository, self._mail_service)
        register_web_search(self._tools, OpenAIWebSearch(credentials, provider_settings, self._subscription))
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
        self._plugin_lifecycle = PluginLifecycle(
            self._plugins,
            self._audience_router,
            config.plugins_path,
            config.plugin_rollback_path,
            self._plugin_components,
            self._skills,
            self._outbound_mcp,
            import_recovery,
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
            CreationCatalogRepository(self._database),
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
            voice_tools=self._tools.realtime_definitions,
            voice_skill_instructions=self._skill_activation.voice_instructions,
        )
        self._handoff_routes = HandoffRoutes(DirectHandoffService(
            config.direct_handoffs_path, HandoffRepository(self._database),
            OpenAIHandoffInspection(credentials, provider_settings, self._subscription), provider_settings,
            self._providers.is_active_realtime_session,
        ))
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
                AgentAudience.VOICE,
                changed_by="runtime-bootstrap",
                reason="preserve accepted Voice memory availability",
            )
        if self._audience_router.binding_for(MAIL_TOOL_SET) is None:
            self._audience_router.set_audience(
                MAIL_TOOL_SET,
                AgentAudience.VOICE,
                changed_by="runtime-bootstrap",
                reason="enable the built-in Voice Mail capability",
            )
        if self._audience_router.binding_for(WEB_SEARCH_TOOL_SET) is None:
            self._audience_router.set_audience(
                WEB_SEARCH_TOOL_SET,
                AgentAudience.VOICE,
                changed_by="runtime-bootstrap",
                reason="enable the built-in Voice web search capability",
            )
        self._catalog.bootstrap_defaults()
        self._skill_lifecycle.recover()
        self._plugin_lifecycle.recover()
        self._creation_lifecycle.recover()
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
            outbound_mcp=self._mcp_routes,
            tools=self._tool_routes,
            plugins=self._plugin_routes,
            creations=self._creation_routes,
            connections=self._connection_routes,
            handoffs=self._handoff_routes,
        )
        self._server.start()
        self._mail_scheduler.start()
        self._events.publish(
            "runtime.ready",
            {"status": "ready", "startCount": int(record.value)},
        )
        self._log.info("runtime.ready", extra={"start_count": int(record.value)})

    def stop(self) -> None:
        self._events.publish("runtime.stopping", {"status": "stopping"})
        self._mail_scheduler.stop()
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
