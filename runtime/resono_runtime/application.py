from __future__ import annotations

from .api.events import RuntimeEventStream
from .api.http_server import RuntimeHttpServer
from .config import RuntimeConfig
from .core.release_supervisor import ReleaseSupervisor
from .core.runtime_environment import agent_runtime_status, standard_library_status
from .security.pairing import PairingAuthority
from .security.credentials import ProviderCredentials
from .providers.controller import ProviderController
from .mcp import LocalMcpServer
from .storage.database import RuntimeDatabase
from .storage.lifecycle_repository import LifecycleRepository
from .storage.provider_settings import ProviderSettingsRepository
from .storage.profile_settings import UserProfileRepository
from .agents import AgentsSdkTextRunner
from .providers.openai import OpenAISubscription


class RuntimeApplication:
    def __init__(
        self,
        config: RuntimeConfig,
        credential_bridge: object,
        restart_request: object | None = None,
    ) -> None:
        self._config = config
        self._database = RuntimeDatabase(config.database_path)
        self._lifecycle = LifecycleRepository(self._database)
        self._events = RuntimeEventStream()
        self._pairing = PairingAuthority()
        self._releases = ReleaseSupervisor(config.releases_path)
        credentials = ProviderCredentials(credential_bridge)
        provider_settings = ProviderSettingsRepository(self._database)
        self._profile = UserProfileRepository(self._database)
        self._subscription = OpenAISubscription(credentials)
        self._providers = ProviderController(
            credentials=credentials,
            settings=provider_settings,
            events=self._events,
            safety_source=config.local_api_token,
            subscription=self._subscription,
            profile=self._profile,
        )
        self._text_runner = AgentsSdkTextRunner(
            credentials=credentials,
            settings=provider_settings,
            events=self._events,
            local_api_token=config.local_api_token,
            subscription=self._subscription,
        )
        self._mcp = LocalMcpServer(self.health)
        self._restart_request = restart_request
        self._environment = standard_library_status()
        self._agent_environment = agent_runtime_status()
        self._server: RuntimeHttpServer | None = None

    def start(self) -> None:
        self._config.prepare_directories()
        self._releases.prepare()
        self._database.migrate()
        record = self._lifecycle.record_start()
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
            restart_request=self._request_restart,
        )
        self._server.start()
        self._events.publish(
            "runtime.ready",
            {"status": "ready", "startCount": int(record.value)},
        )

    def stop(self) -> None:
        self._events.publish("runtime.stopping", {"status": "stopping"})
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
