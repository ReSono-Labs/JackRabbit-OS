# R1 Agent Network, Tailscale Transport, and Link Migration — Placement Review

**Candidate:** `R1-AGENT-NETWORK-PLACEMENT-v0.2`  
**Date:** 2026-08-20  
**Status:** Owner-proposed planning addition; codebase-grounded placement and implementation review; not an active build contract  
**Grounding:** `GROUNDING-BASELINE-v0.5`, `R1-STANDALONE-DELIVERY-PLAN-v0.3`, and `R1-PRIMARY-AGENT-DELEGATION-PLACEMENT-v0.1`  
**Repository state reviewed:** current working tree during active Build Contract 07 Skills/Plugins/MCP work  
**Implementation authority:** none. This document does not authorize code, APK, image, device, or active-contract changes.

> Build Contract 07 is read-only for this review. This candidate does not alter, append to, or reopen it.

## Placement outcome

The supplied design contains three different deliverables and must not be forced into one oversized contract:

```text
current Delivery Slice 7
Calendar + Contacts + Reminders
        ↓
candidate already placed
Primary ReSono identity + delegated Agents SDK jobs
        ↓
NEW FOUNDATION SLICE
Agent Network contract + one physically proven Tailscale transport
+ web-assisted enrollment + one real private-peer request
        ↓
current Delivery Slice 8, amended only after owner acceptance
Built-in A2A client + one Hermes integration
        ↓
NEW INTEGRATION SLICE
One built-in OpenClaw integration over the accepted Agent Network
        ↓
current Delivery Slice 9
External AI HTTPS MCP + ChatGPT
```

Final numbering must wait until all owner-proposed additions are placed and accepted.

The narrowest logical placement is therefore:

1. Add the shared Agent Network/Tailscale foundation **after the proposed internal delegation slice and immediately before current Delivery Slice 8**.
2. Keep A2A and Hermes behavior in current Delivery Slice 8, but make the accepted Agent Network foundation an entry dependency when the baseline and master plan are eventually amended.
3. Add OpenClaw as its own built-in integration slice **after Hermes and before current Delivery Slice 9**. Hermes proves the generic network boundary and A2A first; OpenClaw then proves a second integration without making the first transport slice own application protocols.
4. Reserve Link compatibility in the foundation contract, but do not implement a fake `LinkTransport`, show a selectable Link provider, or claim Link reachability while the Link platform is unavailable.

This ordering preserves the useful architecture while preventing a speculative general router from entering the current Skills/Plugins/MCP contract.

## Authority and conflict with the accepted baseline

The owner explicitly requested this planning addition and authorized a Link placeholder. That is sufficient authority for this candidate document only.

The accepted baseline currently says:

- OD-11: Hermes is the only initially implemented external agent runtime; OpenClaw is documentation only.
- Explicit non-scope: OpenClaw implementation.
- Explicit non-scope: ReSono Labs Link as a dependency or reachability path.
- MDG-08: one Hermes A2A integration, with no OpenClaw internals or general router in the first build.
- Current Delivery Slice 8: no OpenClaw implementation or general router.

This proposal intentionally changes those decisions. Before implementation it requires one owner-accepted amendment to `GROUNDING-BASELINE.md`, the master delivery plan, scenario traceability, and the affected later slice boundaries. Until that happens, this candidate is `CONDITIONAL`.

The amendment must distinguish:

- a small product-owned egress abstraction required by two named first-party integrations;
- one concrete temporary provider, Tailscale;
- the standard A2A protocol;
- the Hermes and OpenClaw application integrations; and
- a reserved Link migration seam that supplies no current Link behavior.

It must not authorize arbitrary remote-agent routing, arbitrary sockets, a plugin-provided VPN, a marketplace network, or a general-purpose overlay-network product.

## Product rules retained from the owner-supplied design

1. A mobile R1 must reach approved private agents while moving between Wi-Fi and cellular and while behind NAT.
2. Application code addresses a stable connection identifier, never a LAN address, Tailscale IP, or Tailscale hostname directly.
3. Tailscale is transport provider 1, not the product architecture.
4. ReSono owns the connection, policy, routing, health, audit, and availability contract above the transport.
5. The OS owns the Wi-Fi/cellular underlay; underlay state and private-agent-network state are separate.
6. Hermes and OpenClaw are first-party integrations, not Agent Plugins.
7. A2A is a built-in standards protocol, not Hermes-owned and not a Plugin.
8. Skills teach agents when and how to use an integration. They do not open routes or receive raw network access.
9. All remote-agent operations pass through capability permission, integration permission, connection permission, network policy, and then transport.
10. Tailscale failure disables only dependent private-agent capabilities. Voice, memory, personal data, OpenAI, and ordinary public HTTPS remain operational.
11. Tailscale is not used as an Internet exit node for OpenAI, web search, or normal public HTTPS.
12. One Tailscale node serves multiple logical connections; do not create one VPN per integration.
13. ReSono device/agent identity is canonical. Tailscale node identity is provider metadata and cannot become the ReSono identity.
14. Link later replaces the transport implementation without changing Voice, Skills, A2A, Hermes, or OpenClaw contracts.

## Corrections from the actual codebase

### 1. There is no Agent Network or A2A implementation yet

The current `runtime/resono_runtime/` tree has no `networking/`, `a2a/`, `integrations/hermes/`, or `integrations/openclaw/` implementation. There is also no Tailscale package, daemon, Android `VpnService`, VPN permission, TUN owner, or system-image integration in this repository.

The supplied directory tree is therefore a proposed target, not a description of current code.

### 2. `RuntimeApplication` is the one Python composition root

`runtime/resono_runtime/application.py` currently composes SQLite, pairing, provider access, memory, Tool Catalog, Skill activation, the Agents SDK paths, MCP, health, and the private HTTP API.

A future Agent Network runtime object is composed there after its lower-level transport host reports ready. Hermes and OpenClaw must receive that same object. Neither integration may construct a transport, database, credential store, or HTTP client independently.

### 3. Android owns the durable process boundary

`android/runtime-host/src/main/java/com/resonolabs/runtime/host/RuntimeService.java` is the accepted direct-boot-aware foreground service. It starts the embedded Python runtime, hosts same-LAN management, applies startup limiting, and restarts Python on request.

`runtime/resono_runtime/core/release_supervisor.py` supervises release activation and rollback; it is not a daemon supervisor. The proposal must not incorrectly attach Tailscale process ownership to `ReleaseSupervisor` or create a second unrelated Android foreground service without a proved lifecycle need.

The selected Tailscale engine/VPN implementation belongs in an isolated Android transport module, while `RuntimeService` composes only its narrow bridge into the existing process. Python owns product routing and policy; the transport module owns provider state and Android VPN lifecycle. Neither `ReleaseSupervisor` nor the Python runtime may invoke raw Tailscale APIs.

### 4. Existing connectivity checks are management-specific

`android/runtime-host/src/main/java/com/resonolabs/runtime/host/RuntimeManagementClient.java` and `ManagementTlsIdentity.java` inspect `ConnectivityManager` only for the accepted same-LAN management behavior. They are not a generic underlay monitor and should not be imported into Python or copied into each integration.

The future underlay projection should be one narrow Android-to-runtime status contract that distinguishes at least `wifi`, `cellular`, `other`, and `offline`. It must not change the rule that management address advertising remains Wi-Fi-only.

### 5. The existing management site is the correct setup surface

The product management site is served from:

- canonical web source: `web/management/`;
- packaged mirror: `android/runtime-host/src/main/assets/management/`;
- HTTPS host: `android/runtime-host/.../ManagementHttpsServer.java`;
- explicit proxy allowlist: `android/runtime-host/.../ManagementRuntimeProxy.java`;
- paired/CSRF-guarded routes: `runtime/resono_runtime/api/routes.py` and `security/pairing.py`.

Tailscale enrollment and status belong on this real paired management surface. They must not call Tailscale directly from JavaScript, expose the local Tailscale control socket, accept raw auth keys into browser storage, or create a disconnected native settings page.

### 6. Tailscale's own device web interface is not the Android answer

Current official Tailscale documentation describes its device web interface for desktop-platform clients: Linux, macOS, and Windows. It does not establish that the Android client exposes that interface.

Official Android documentation instead supports interactive SSO, QR-code login, and an Android TV generated-code flow completed in the Tailscale admin console. A ReSono web-assisted enrollment is therefore plausible, but must be a ReSono management flow around a real Tailscale authorization URL/code—not an assumption that `100.100.100.100` or port 5252 is available on the R1.

### 7. Select the upstream Android engine/VPN topology

A focused implementation review selects the open-source Tailscale Android engine and Android `VpnService` lifecycle as the planning default:

- Tailscale officially supports Android 8 and later and publishes the Android client source under BSD-3-Clause.
- The upstream Android client already binds its Go networking engine through `libtailscale` and implements the required Android `VpnService` behavior.
- The Tailscale backend emits a short-lived `BrowseToURL` authorization URL and explicit backend states such as `NeedsLogin`, `NeedsMachineAuth`, and `Running`. Those are sufficient to drive the paired ReSono web flow without using Tailscale's Android UI.
- Android officially requires `VpnService.prepare()` and first-use user consent. A remote browser cannot approve that system security dialog for the user.
- Tailscale supports Android app-based split tunneling, but the R1 does not need an exit node or general Internet routing. The imported provider must advertise only the tailnet routes required by approved peers and must not configure an exit node.

Do not install the stock Tailscale APK as an independently configured product surface. It would split ownership between Tailscale UI and ReSono UI and does not provide the narrow versioned application contract the runtime requires. Instead, import the minimum reviewed upstream Android engine/VPN behavior into an isolated ReSono Android transport module, retaining source provenance, license, notices, and upstream-update tests.

Do not select `tsnet` or a standalone userspace `tailscaled` proxy for the first implementation. `tsnet` is designed to embed a node in a Go program and is attractive for scoped dialing, but Tailscale has a documented Android failure history for that path and does not present it as the supported Android client architecture. It remains only a reopen alternative if a pinned current revision is later physically proved superior on this R1.

The later build contract still requires a short physical import spike, but the spike now validates the selected Android path; it does not build and retain two competing transports.

### 8. MCP connections and agent connections are different records

`runtime/resono_runtime/storage/mcp_connections.py` and migrations `v010`–`v012` own MCP connection configuration and discovered MCP tools. An A2A/OpenClaw connection must not be stored as an MCP connection merely because both become Tool Catalog capabilities.

Use a distinct agent-connection repository and migration. Share credential and permission principles, not tables or protocol fields.

### 9. Credentials already have one Android Keystore owner

`android/runtime-host/.../RuntimeCredentialStore.java` is the Keystore-sealed credential owner, exposed to Python through `RuntimeCredentialBridge.java`. It currently has OpenAI-specific methods.

Future integration secrets require a versioned, namespaced credential-reference extension or a deliberately separate narrow store. SQLite stores only an opaque `auth_ref`. Tailscale engine state remains owned by the selected Tailscale host implementation and must be device-protected; raw auth keys and reusable control credentials must not be persisted as ordinary configuration.

### 10. Tool availability already has one product path

`runtime/resono_runtime/tools/catalog.py`, `agents/routing.py`, Skill activation, and the current MCP projections are the existing capability path. `hermes.delegate`, `hermes.status`, `hermes.cancel`, and later OpenClaw operations must register there with health-aware availability and existing audience/permission filtering.

Do not add a parallel `capabilities/registry.py` tree while Build Contract 07 is establishing the canonical Tool Catalog, Skill, Plugin, and MCP ownership.

## Target dependency rule

```text
Primary Voice or delegated worker
        ↓
existing Tool Catalog / capability policy
        ↓
named first-party integration
        ↓
protocol client
        ↓
Agent Network
        ↓
connection repository + network policy
        ↓
selected transport
        ↓
Android/OS underlay
```

Forbidden dependencies:

```text
Voice / Skill / Plugin / Hermes / OpenClaw → Tailscale
Voice / Skill / Plugin → arbitrary HTTPS or sockets
A2A client → SQLite or Android process APIs
Tailscale transport → A2A Task or Hermes types
management JavaScript → Tailscale daemon/control socket
```

## Exact future ownership

Names below are planning targets. A later build contract must reconcile them with the accepted end state of Build Contract 07 and use the next available migration number.

### Agent Network foundation slice

```text
runtime/resono_runtime/networking/
├── contracts.py
├── agent_network.py
├── policy.py
├── underlay.py
└── tailscale_transport.py

runtime/resono_runtime/storage/
├── agent_connections.py
└── agent_network_events.py

runtime/resono_runtime/api/
└── agent_network_routes.py

android/transport/tailscale/src/main/java/com/resonolabs/transport/tailscale/
├── TailscaleVpnService.kt
├── TailscaleEngine.kt
├── TailscaleEnrollment.kt
├── TailscaleStatusSource.kt
└── TailscaleRuntimeBridge.kt

android/runtime-host/src/main/java/com/resonolabs/runtime/host/
└── AgentUnderlaySource.java
```

- `networking/contracts.py`: immutable versioned request, response, stream, route, health, and transport protocols. No concrete provider checks.
- `networking/agent_network.py`: the single request/stream/health/disconnect choke point and transport lookup. It knows connection records and transport contracts, not A2A or integration types.
- `networking/policy.py`: caller, operation, connection, destination, and grant intersection. It returns allow/deny only; it does not perform I/O.
- `networking/underlay.py`: normalized read-only underlay state received from Android.
- `networking/tailscale_transport.py`: Tailscale-specific resolve/request/stream/health mapping through the selected Android host boundary. Tailscale names, addresses, route diagnostics, and errors stop here.
- `storage/agent_connections.py`: canonical logical connection configuration and enabled state. It stores `auth_ref`, never secret material.
- `storage/agent_network_events.py`: bounded diagnostic/audit persistence with redaction and retention. It is not the canonical task result store.
- `api/agent_network_routes.py`: paired management status, enrollment start/poll/cancel, connection CRUD, test, disconnect, and event projection. It follows the existing narrow route-owner pattern rather than growing `api/routes.py` indefinitely.
- `android/transport/tailscale`: one isolated Android library module containing the pinned upstream `libtailscale` artifact/source adaptation, VPN service, enrollment state, peer/status projection, and narrow bridge. No product UI, Hermes, OpenClaw, A2A, SQLite, or Python policy belongs here.
- `TailscaleVpnService.kt`: Android VPN interface and socket-protection lifecycle adapted from the exact pinned upstream source. It declares `BIND_VPN_SERVICE`, handles revoke/stop, and never owns product connection permissions.
- `TailscaleEngine.kt`: starts/stops the one embedded Tailscale backend, owns its device-protected provider state, and maps only reviewed stable events into local records.
- `TailscaleEnrollment.kt`: one-at-a-time login state machine. It validates and exposes the backend-produced authorization URL, expiry, machine-approval state, and terminal result; it never handles Tailscale passwords.
- `TailscaleStatusSource.kt`: converts backend self/peer/route state into a minimal immutable projection. Raw LocalAPI access remains inside this module.
- `TailscaleRuntimeBridge.kt`: the narrow Java/Python-facing transport surface used by `RuntimePythonHost`/`RuntimeApplication`; no raw backend object, control socket, node key, or unrestricted dialer crosses it.
- `AgentUnderlaySource.java`: one `ConnectivityManager` projection; no routing decisions.
- `RuntimeService.java`: composes and stops `TailscaleRuntimeBridge` with the existing runtime and passes the narrow bridge through `RuntimePythonHost`. It remains the Android process lifecycle owner; the VPN service owns only Android VPN lifecycle.
- `MainActivity`: launches the `VpnService.prepare()` result when a live web enrollment reports `vpn_permission_required`. The user must approve the real Android system dialog on the R1 once; no simulated confirmation is permitted.
- `RuntimeApplication`: receives the bridge as a composition dependency and composes the repository, policy, transport adapter, Agent Network, routes, health, events, and Tool Catalog availability.

Do not create generic `manager.py`, `service.py`, `connections.py`, `health.py`, or `utils.py` catch-alls. The codebase's clean-structure rule requires responsibility to be visible from the filename.

### Hermes/A2A slice

```text
runtime/resono_runtime/a2a/
├── contracts.py
├── client.py
├── agent_card.py
├── task_state.py
├── streaming.py
└── security.py

runtime/resono_runtime/integrations/hermes/
├── adapter.py
├── capabilities.py
└── normalization.py

runtime/resono_runtime/storage/
├── agent_peers.py
└── agent_tasks.py

runtime/resono_runtime/api/
└── hermes_routes.py
```

- A2A owns Agent Card validation, Messages, Tasks, streaming, cancellation, protocol bindings, errors, and protocol security.
- A2A receives an Agent Network port; it never resolves Tailscale names or creates unrestricted clients.
- Hermes selects a configured Hermes connection, maps ReSono operations to A2A, and normalizes real task state for Voice/web/native surfaces.
- `agent_tasks.py` owns durable remote task identity/state. It must be reconciled with the candidate internal job repository so internal Agents SDK jobs and remote A2A tasks share only a small normalized presentation contract, not one storage table or protocol.

### OpenClaw slice

```text
runtime/resono_runtime/integrations/openclaw/
├── adapter.py
├── capabilities.py
└── normalization.py
```

Freeze the actual OpenClaw application protocol only after reviewing the configured OpenClaw instance and named donor revision. If OpenClaw supports the accepted A2A contract, reuse `a2a/client.py`; otherwise add the smallest protocol-specific client under `integrations/openclaw/`. Do not invent a generic second protocol framework in advance.

OpenClaw receives the same Agent Network port and logical connection model as Hermes. It cannot import `tailscale_transport.py`.

## Connection and state contracts

The initial persisted logical connection should be smaller than the supplied speculative schema:

```text
agent_connections
    connection_id
    display_name
    integration_kind
    protocol_kind
    transport_kind
    destination
    port
    auth_ref
    enabled
    created_at
    updated_at
```

Observed values such as `last_seen`, `last_error`, provider route, and reachability should not be duplicated into that canonical configuration row unless a later contract proves they require durable snapshots. Current state belongs in the Agent Network health projection; bounded history belongs in `agent_network_events`.

Provider-specific metadata is one validated opaque object owned by the matching transport. No other module may read its fields.

The initial public operations are versioned and transport-neutral:

```text
resolve(connection_id, caller_context)
request(connection_id, operation, payload, caller_context)
stream(connection_id, operation, payload, caller_context)
health(connection_id)
disconnect(connection_id, caller_context)
```

Do not expose `tailscale_ip`, `tailscale_hostname`, `tailscale_status`, or `tailscale_connect` outside the transport/diagnostic projection.

## Web-assisted Tailscale enrollment contract

The target user flow is:

```text
paired ReSono management browser
        ↓
Agent Network → Connect
        ↓
POST /v1/management/agent-network/enrollment
        ↓
selected Tailscale host starts one enrollment attempt
        ↓
Android reports whether VPN consent is already present
        ↓
if required: paired web says "Confirm on your R1"
and the foreground R1 launches the real Android VPN consent dialog
        ↓
Tailscale engine returns a short-lived authorization URL
        ↓
browser opens Tailscale authorization in a new trusted tab
        ↓
runtime polls local Tailscale state
        ↓
connected identity and transport health become real
```

Required controls:

- Pairing session and CSRF protection are mandatory for start, cancel, disconnect, and connection mutation.
- Return only an HTTPS URL on an exact Tailscale-approved host or a documented generated code. Reject arbitrary redirect origins.
- The page never asks for or stores the user's Tailscale password.
- Prefer interactive authorization URL/QR or one-off pre-authentication. Do not ask an ordinary user to paste a reusable auth key into the R1 web page.
- If an operator provisioning mode later accepts a one-off auth key, transmit it once over paired HTTPS, redact it from logs/events, pass it directly to the Tailscale host, and never store it in SQLite, JavaScript storage, or a diagnostic record.
- Enrollment has one owner, one active attempt, expiry, cancellation, restart recovery, and explicit `needs_approval`, `connected`, `expired`, `denied`, and `error` states.
- Add explicit `vpn_permission_required`, `authorizing`, and `machine_approval_required` states. The web page must state that one physical confirmation is required on the R1. It cannot report success before Android and Tailscale both report ready.
- The official Tailscale device web UI must not be exposed on same-LAN management as a shortcut.
- No Agent Network UI lands before this real flow and a real private peer are connected.

Do not make Tailscale's alpha OAuth-app device-provisioning flow the R1 default. It requires a tailnet administrator to pre-create an OAuth app and securely distribute a client secret, which is inappropriate for ordinary personal setup. The normal backend-produced authorization URL creates the familiar Tailscale browser login without storing a reusable provisioning credential. OAuth-app provisioning can be reconsidered later for managed fleets.

### Web-owned connection configuration

After the Agent Network reports `connected`, the same paired ReSono management page owns logical connection setup:

```text
Agent Network
    status / underlay / Tailscale identity / disconnect

Add agent connection
    integration: Hermes or OpenClaw
    display name
    peer: selected from the live reachable tailnet peer list
    protocol-specific port/base path
    protocol authentication credential
    enabled
    Test and save
```

The browser obtains a sanitized peer list from `TailscaleStatusSource` through the runtime. The user selects a real peer instead of copying a `100.x` address. The Tailscale transport stores a provider-owned destination record containing the peer's stable observed identity and full MagicDNS name; upper layers retain only `connection_id`. If the peer is replaced or its identity no longer matches, the connection becomes `verification_required` instead of silently following a reused name.

Recommended paired routes:

```text
GET    /v1/management/agent-network
POST   /v1/management/agent-network/enrollment
DELETE /v1/management/agent-network/enrollment
POST   /v1/management/agent-network/disconnect
GET    /v1/management/agent-network/peers
GET    /v1/management/agent-connections
POST   /v1/management/agent-connections
POST   /v1/management/agent-connections/{id}/test
DELETE /v1/management/agent-connections/{id}
```

Every mutation uses the existing pairing session and CSRF boundary. The runtime, not JavaScript, validates integration kind, peer identity, scheme, port, protocol path, credential reference, and destination policy. Protocol credentials are submitted once to the Keystore owner; the browser receives only a boolean configured state. A connection is saved as configured but its capabilities remain unavailable until a real transport and protocol test passes.

The canonical editable web source remains `web/management/`, and the packaged `android/runtime-host/src/main/assets/management/` mirror changes in the same commit. `ManagementRuntimeProxy.java` receives only the exact routes above. No general `/network/*` proxy or arbitrary destination test endpoint is allowed.

## Link placeholder boundary

The owner authorized a placeholder because Link does not yet exist. Under the repository's no-mock rule, the placeholder is limited to:

- a stable transport contract designed without Tailscale fields;
- a reserved persisted provider identifier, `link`, only if forward-compatible storage requires it;
- validation that rejects selecting `link` with `provider_unavailable`;
- documentation and tests proving upper layers do not import Tailscale-specific types; and
- management wording such as `ReSono Link is not available in this release` only if the owner requires visibility.

Do **not** create `networking/link.py`, a fake connected state, placeholder routes, synthetic peers, a selectable working-looking Link option, Link credentials, or a mock Link control plane. The real `LinkTransport` file begins only when a Link protocol, identity, trust, discovery, routing, and acceptance environment exist.

## Availability and failure model

Availability is computed, not statically registered:

```text
capability declared
INTERSECT integration enabled
INTERSECT connection configured
INTERSECT caller/audience grant
INTERSECT transport ready
INTERSECT peer reachable
INTERSECT protocol compatible
= exposed capability
```

Preserve distinct machine-readable states:

| State | Meaning | Product effect |
|---|---|---|
| `underlay_offline` | No usable Wi-Fi/cellular/other Internet | Private peers offline; local R1 continues |
| `transport_unavailable` | Internet exists but Tailscale host is stopped, signed out, or unhealthy | Tailscale connections offline; public Internet/OpenAI unaffected |
| `peer_unreachable` | Tailscale ready but named destination unavailable | Only that connection's capabilities unavailable |
| `protocol_incompatible` | Host reachable but Agent Card/protocol negotiation fails | Only protocol-dependent operations unavailable |
| `permission_denied` | Route exists but policy rejects caller/operation | No transport request occurs |
| `timeout` | Authorized request exceeded the operation deadline | Task/request remains reconciled, not silently duplicated |

Direct, peer-relay, and DERP are diagnostics from Tailscale. They do not alter application semantics or security policy.

## Implementation sequence for the later foundation contract

1. Freeze the smallest observable scenario: enroll through paired management, connect one private test peer, survive Wi-Fi-to-cellular and cellular-to-Wi-Fi changes, issue one real HTTPS request, disconnect, and prove local Voice remains healthy through failures.
2. Perform a bounded physical import spike for the selected upstream Android engine/VPN path. Record exact source revision, license, ABI, artifact origin, APK packaging, VPN consent, direct boot, sleep/wake, network switching, streaming, DNS, and rollback behavior. Stop if the pinned upstream path cannot satisfy these requirements cleanly.
3. Record the selected Android path at a Material Decision Gate and delete spike-only alternatives. Do not retain a stock Tailscale UI or a second userspace implementation.
4. Define versioned network contracts and negative policy tests before transport I/O.
5. Add the next available SQLite migration for logical connections and bounded redacted events.
6. Add the Android host/underlay bridge and integrate it into the existing `RuntimeService` lifecycle.
7. Add the Tailscale adapter, interactive enrollment state machine, reconnect behavior, and health projection.
8. Add paired management routes, the proxy allowlist entries, then both management asset copies in the same change.
9. Connect one protocol-neutral private HTTPS test endpoint through `AgentNetwork.request()`; do not pull Hermes or OpenClaw into the foundation proof.
10. Physically test Wi-Fi, cellular, network transition, hard-NAT/relay where observable, reboot, key expiry, revocation, peer down, malformed destination, timeout, and transport crash.
11. Only after foundation acceptance, implement A2A and Hermes in their slice.
12. Only after Hermes acceptance, implement OpenClaw in its separate slice.

## Required tests and evidence

### Unit and boundary tests

- connection schema rejects unknown integration/protocol/transport values and credentials in destinations;
- transport-neutral modules cannot import Tailscale implementation types;
- policy denial occurs before resolve or network I/O;
- disabled, offline, unreachable, incompatible, and unauthorized capabilities are absent from Tool Catalog projections;
- Tailscale addresses and auth material are redacted from ordinary events/logs;
- Link selection returns explicit unavailable state and never fake success;
- A2A cannot construct its own HTTP client or read transport metadata;
- Hermes and OpenClaw cannot import Tailscale;
- browser enrollment rejects unpaired requests, missing/invalid CSRF, unsafe URLs, duplicate attempts, expired attempts, and oversized payloads;
- only backend-produced `https://login.tailscale.com/` authorization URLs pass the default enrollment allowlist;
- VPN consent state cannot be forged by the browser and enrollment cannot become connected before the Android VPN and Tailscale backend are both ready;
- peer selection persists no `100.x` address as an application identifier and detects peer identity replacement;
- management proxy exposes only exact Agent Network routes;
- Tailscale failure does not make overall runtime health `not_ready` when local required capabilities are healthy.

### Physical R1 evidence

- exact Tailscale source/binary/APK revision, SHA-256, license, destination, and build/import record;
- enrollment initiated on the paired ReSono web site and completed with real Tailscale authorization;
- any unavoidable on-device VPN consent documented honestly;
- one private peer reached on Wi-Fi and on cellular without changing the logical connection ID;
- Wi-Fi-to-cellular and cellular-to-Wi-Fi transition behavior;
- direct or relay route diagnostics where physically observable;
- transport crash/restart, R1 reboot, peer outage, key expiry/revocation, and protocol failure;
- OpenAI/public HTTPS remains on ordinary underlay and operational when Tailscale is down;
- no inbound LAN address or port-forward dependency;
- disconnect/revocation removes capability availability while local Voice continues;
- exact rollback artifact and persistent-state handling.

### Later integration evidence

- Hermes: real Agent Card, Message/Task ID, stream, clarification, cancellation, result, incompatible protocol, and loop defense through Agent Network;
- OpenClaw: real configured instance and protocol transcript through the same Agent Network, with independent disable/revoke behavior;
- no application-level behavior changes when the same logical connection is exercised with a future real Link transport.

## External standards and provider review

Reviewed current primary sources:

- [Tailscale connection types](https://tailscale.com/docs/reference/connection-types)
- [Tailscale Android installation](https://tailscale.com/docs/install/android)
- [Tailscale device web interface](https://tailscale.com/docs/features/client/device-web-interface)
- [Tailscale userspace networking](https://tailscale.com/docs/concepts/userspace-networking)
- [Tailscale Android app-based split tunneling](https://tailscale.com/docs/features/client/android-app-split-tunneling)
- [Tailscale `tsnet`](https://tailscale.com/docs/features/tsnet)
- [Tailscale auth keys](https://tailscale.com/docs/features/access-control/auth-keys)
- [Tailscale OAuth-app device provisioning](https://tailscale.com/docs/features/oauth-apps/device-provisioning)
- [Tailscale QR-code enrollment](https://tailscale.com/docs/features/access-control/device-management/how-to/set-up-qr-code)
- [Tailscale Android source](https://github.com/tailscale/tailscale-android)
- [Android `VpnService`](https://developer.android.com/reference/android/net/VpnService)
- [A2A protocol specification](https://a2a-protocol.org/latest/specification/)

These sources support the transport behavior, Android enrollment options, desktop-only documented device web UI, Android VPN consent, backend authorization URL/state approach, split-tunneling controls, and A2A protocol shapes. They support selecting the upstream Android client architecture over `tsnet` for planning, but do not replace physical proof on this R1.

## Material Decision Gate — placement and architecture boundary

**Decision:** where should the mobile private-agent network, Tailscale, Hermes, OpenClaw, and future Link seam enter the delivery plan?

**Authority and evidence:** owner request on 2026-08-20; accepted baseline OD-01–OD-03, OD-08–OD-11, OD-17–OD-18 and clean-structure rules; current Slice 8/9 boundaries; current runtime/Android ownership cited above; official Tailscale and A2A documentation.

**Alternatives considered:**

1. Add Tailscale/networking to active Build Contract 07.
2. Put network, Tailscale, A2A, Hermes, and OpenClaw into current Delivery Slice 8.
3. Add one transport foundation before Hermes, retain Hermes/A2A as its integration slice, then add OpenClaw as a separate post-Hermes slice.
4. Keep the accepted plan unchanged and make Hermes depend on LAN/public reachability.
5. Wait for Link and make it a first-release dependency.

**Selection and real-world function:** select alternative 3. The R1 first proves one small transport-neutral egress boundary and one real Tailscale provider. Hermes then proves standard A2A over it. OpenClaw later proves the second application integration. Link remains an explicitly unavailable future provider at the contract boundary.

**Why the others are not selected:**

- Alternative 1 changes an active owner-gated contract and couples transport work to the still-moving Skills/Plugins/MCP foundation.
- Alternative 2 combines OS networking, enrollment, security policy, persistence, A2A, two integrations, task state, Voice, and UI into one unreviewable contract.
- Alternative 4 fails the mobile/cellular/NAT use case and invites LAN/Tailscale details into Hermes.
- Alternative 5 contradicts the owner's statement that Link is unavailable and blocks current product progress on nonexistent infrastructure.

**Counterexample/reopen trigger:** reopen this selection if the physical R1 cannot safely host the pinned upstream Android Tailscale engine/VPN path; if the configured Hermes is already securely public and no private OpenClaw implementation remains in first-release scope; if Link publishes an implementable protocol before this slice freezes; or if current Android VPN/process constraints require a materially different product boundary.

**Affected dependents:** grounding success scenarios and explicit non-scope; master plan numbering; primary delegation candidate; Tool Catalog availability; Skill/Plugin/MCP boundaries; Android foreground runtime and final image; SQLite; Keystore; management web/proxy; Hermes/A2A; OpenClaw; External AI sequencing; final release tests and licensing.

**Result:** `CONDITIONAL`. Placement and ownership are selected for planning. Baseline amendment, physical topology proof, and a later owner-accepted build contract are required before implementation.

## Open decisions for the later build contract

1. Exact pinned Tailscale Android/libtailscale revision, import subset, BSD-3-Clause notice, reproducible build path, and update ownership.
2. Exact foreground R1 interaction that launches and explains the mandatory first-use Android VPN consent.
3. Whether the management page additionally renders a QR code for the backend-produced authorization URL.
4. User-owned R1 Tailscale identity, tailnet grants, device approval, key expiry, and revocation policy; tagged/fleet provisioning is later unless separately authorized.
5. Stable ReSono device and agent identity contract independent of Tailscale.
6. Exact first private protocol-neutral test peer and its TLS trust model.
7. Whether Direct HTTPS is required for a named first-release public agent or remains a later transport.
8. Configured Hermes A2A version/binding and authentication method at implementation time.
9. Actual OpenClaw protocol and donor behavior after Hermes acceptance.
10. Agent Network event retention and redaction limits.
11. Relationship between internal delegated jobs and remote A2A/OpenClaw task presentation.

## Next documentation action

After all owner-proposed additions have been reviewed:

1. present the combined proposed ordering and scope changes for owner acceptance;
2. amend `GROUNDING-BASELINE.md` once, including OD-11/MDG-08 and explicit non-scope;
3. update the master plan once and renumber slices consistently;
4. update scenario/dependency/risk traceability;
5. freeze separate later build contracts for Agent Network, Hermes/A2A, and OpenClaw only when their entry gates pass; and
6. leave active Build Contract 07 unchanged.
