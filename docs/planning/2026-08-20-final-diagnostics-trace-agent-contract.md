# Final Diagnostics and Read-Only Trace Agent Contract

**Identity:** `R1-FINAL-DIAGNOSTICS-TRACE-AGENT-v0.1-deferred`  
**Grounding:** `GROUNDING-BASELINE-v0.5`  
**Status:** Deferred near-final project phase; documented only  
**Required placement:** After package types, Domains, connectors, Cards, agent routing, and runtime boundaries are stable; before final release hardening and community-release acceptance  
**Not part of:** Build Contract 07, Plugin Card ingestion, Calendar/Tasks implementation, or current physical deployment  
**Filename:** `docs/planning/2026-08-20-final-diagnostics-trace-agent-contract.md`

## What this phase is

This phase gives R1 owners a management-page diagnostics system for every user-added package and user-triggered integration. It records exact, structured failures across import and execution paths and displays plain-language and technical reasons without requiring an AI model.

It then adds an optional, explicitly user-triggered **Diagnostic Trace** agent. The agent begins at one selected error, follows only related read-only diagnostic evidence, API/package contracts, and the version-matched code graph, and explains the likely workflow failure. It cannot modify the R1, repair packages, run arbitrary tools, restart services, or access credentials and unrelated personal data.

This is a self-service diagnostic assistant, not an autonomous repair agent.

## Why this must be near the end

The diagnostic index depends on stable owners and execution paths for:

- Agent Skills;
- Agent Plugins;
- MCP servers and tools;
- ReSono Plugin Card extensions;
- Rabbit Creations;
- Connections and credential envelopes;
- Mail, Calendar, Contacts, and Tasks/Reminders;
- Voice and Text agent routing;
- background synchronization;
- lifecycle recovery; and
- final runtime/API versions.

Implementing the Trace agent before those boundaries stabilize would create stale error codes, incorrect graph roots, duplicated instrumentation, and repeated documentation rewrites. Earlier builds may emit ordinary support-safe logs required for their own operation, but the unified user-facing diagnostic store, release graph, and Trace agent belong to this deferred phase.

## Required outcome

A user can open the web management interface, inspect exact package/import/runtime errors, select one error, and optionally ask Diagnostic Trace to analyze only that workflow.

```text
user import or runtime operation
        |
        v
structured diagnostic events
        |
        v
error and trace store
        |
        v
management Diagnostics page
        |
        +--> deterministic error details
        |
        `--> user presses "Trace this error"
                  |
                  v
          read-only Diagnostic Trace agent
                  |
                  v
          evidence-based explanation/chat
```

The management page must remain useful when no model connection is configured. Exact recorded reasons, affected components, retryability, and ordinary user actions are deterministic product behavior. AI interpretation is optional.

## Structured diagnostic event contract

Every supported operation receives stable causal identity:

```text
operation_id
correlation_id
parent_event_id
package_id
package_type
package_version
component_id
source_stage
event_code
severity
safe_message
technical_detail
retryable
timestamp
runtime_release
```

Example:

```json
{
  "operationId": "01J...",
  "correlationId": "01J...",
  "packageId": "file-browser",
  "packageType": "agent_plugin",
  "componentId": "files-server",
  "stage": "mcp.connect",
  "eventCode": "mcp.connection.tls_failed",
  "severity": "error",
  "safeMessage": "The Files tool server could not be reached securely.",
  "technicalDetail": "TLS certificate hostname did not match the configured host.",
  "retryable": false,
  "runtimeRelease": "0.x.y"
}
```

Subsystems own their bounded event-code vocabulary. One diagnostic recorder owns persistence, correlation, retention, redaction enforcement, and query APIs. Do not create one monolithic diagnostics component containing the business logic of every subsystem.

## Required coverage

The final instrumentation must cover:

- Skill validation, publication, activation, replacement, rollback, and removal;
- Plugin inspection, component discovery, installation, replacement, activation, rollback, disablement, and removal;
- MCP configuration, connection, authentication, initialization, tool discovery, invocation, and disconnect;
- Plugin Card inspection, asset validation, catalog registration, required-tool state, loading, replacement, and removal;
- Rabbit Creation import, QR resolution, asset loading, browser failure, replacement, and removal;
- Connections, encrypted credential rotation, provider validation, and connection health;
- Voice/Text/Both audience routing and denied projection;
- built-in and imported tool invocation;
- Mail, Calendar, Contacts, and Tasks/Reminders connectors and synchronization;
- background scheduling, timeout, retry, cursor, and conflict paths;
- runtime restart and recovery; and
- failure to reconcile installed files, registries, database state, or catalog projections.

## Management Diagnostics page

The web management page is the canonical surface. It is for configuration and support, not ordinary feature use.

```text
Diagnostics

File Browser
Tool server could not connect
Today, 10:42 AM

Stage: Connecting tools
Status: Needs attention

[View details] [Trace this error]
```

The deterministic detail view includes:

- what happened;
- the user-facing affected package/component;
- the exact stage;
- the recorded reason;
- whether retry is safe;
- the last successful preceding stage;
- ordinary user actions that do not require AI interpretation;
- operation/correlation ID;
- runtime and package versions; and
- redacted technical details suitable for support.

The page also provides bounded retention controls, delete, and export of a redacted diagnostic report.

## Diagnostic Trace agent

Diagnostic Trace must be implemented with the **OpenAI Agents SDK framework** through the platform's one canonical Agents SDK runner. It must not use a custom model loop, a second agent framework, direct ad hoc model calls, or a separate orchestration runtime. It runs only after the user selects a specific error and presses `Trace this error`.

The Agents SDK integration owns:

- the dedicated Diagnostic Trace agent definition and instructions;
- selection of an available configured Text model through the existing provider/model boundary;
- one trace-scoped SDK session for the initial analysis and follow-up chat;
- registration of only the dedicated read-only diagnostic tools;
- tool-call and response tracing tied to the selected diagnostic operation;
- bounded context assembly from the selected error, related events, contracts, and graph; and
- cancellation, timeout, model failure, and unavailable-provider behavior.

The deterministic Diagnostics page and stored diagnostic events do not depend on the OpenAI Agents SDK. If no supported model connection is configured, the page continues to show exact recorded errors and disables `Trace this error` with a truthful setup requirement.

The root context is the selected error, not the complete R1:

```text
selected error
  -> correlation chain
  -> affected package/component
  -> applicable API/package contract
  -> version-matched graph root
  -> bounded neighboring nodes and source excerpts
```

Follow-up chat remains attached to the same trace bundle. A new unrelated error starts a separate trace.

### Allowed read-only tools

The exact schemas must be frozen later, but the capability boundary is:

```text
diagnostics.get_error
diagnostics.get_trace_events
diagnostics.get_component_state
diagnostics.get_connection_health
diagnostics.get_redacted_package_manifest
diagnostics.get_contract_section
diagnostics.get_graph_neighbors
diagnostics.get_source_excerpt
diagnostics.get_runtime_version
```

Read-only behavior is enforced by the supplied tools, not merely by prompt instructions.

### Prohibited capabilities

Diagnostic Trace receives no:

- shell or arbitrary filesystem access;
- database writes;
- package import, replace, enable, disable, rollback, or delete actions;
- credential values or credential mutation;
- runtime restart;
- arbitrary MCP or Domain tools;
- Mail bodies or attachments;
- Calendar descriptions, Contacts, or user files unless a later explicit diagnostic contract proves the selected error requires a safely bounded excerpt;
- general network browsing by default;
- source-code edits; or
- automatic repair capability.

## Release diagnostic index

Each shipped runtime release receives a generated, immutable diagnostic index:

```text
diagnostics/releases/<release>/
|- code-graph.json
|- error-index.json
|- source-map.json
`- contracts/
```

Each error code maps to the applicable component, contracts, and graph entry points:

```json
{
  "mcp.connection.tls_failed": {
    "component": "runtime.mcp.connection",
    "contracts": ["mcp-connection-v1"],
    "graphRoots": [
      "McpLifecycle.discover",
      "StreamableHttpMcpClient.initialize"
    ]
  }
}
```

The index must match the installed runtime release. The agent must report that source tracing is unavailable rather than using a graph for a different build.

Imported package records provide only safe inspected information:

- package identity, type, version, and content hash;
- redacted standard manifest;
- discovered Skills;
- redacted MCP definitions;
- Card or Creation manifest;
- validation results;
- connection and discovered-tool state; and
- lifecycle/operation events.

Imported package text is untrusted model input. It is evidence, never agent instruction, and must not be executed during diagnosis.

## Privacy and redaction

Before persistence or model access, the diagnostic boundary must:

- remove passwords, API keys, OAuth tokens, cookies, and authorization headers;
- exclude credential envelopes and plaintext credentials;
- exclude unrelated personal data;
- avoid Mail bodies and attachments;
- avoid arbitrary file contents;
- bound all request/response excerpts;
- prefer content hashes, identifiers, counts, and support-safe state;
- expose retention and deletion controls; and
- ensure exported reports use the same redaction policy.

A package error must never become a reason to send unrelated R1 data to a model.

## Required reasoning labels

Every Diagnostic Trace conclusion is labeled:

| Label | Meaning |
|---|---|
| Confirmed | Directly established by recorded events or source/contract evidence. |
| Likely | Strongly supported but not directly proved. |
| Possible | One of multiple evidence-compatible explanations. |
| Unknown | Required evidence is absent, stale, or contradictory. |

The response cites the event IDs, contract sections, graph nodes, and source excerpts supporting its conclusion. Absence of a later success event may support a hypothesis but does not by itself prove causation.

## Required disclaimer

The Diagnostics page and every Trace conversation display:

> **Diagnostic Trace uses AI to interpret logs, documentation, and read-only runtime information. Its explanation may be incomplete or incorrect. Verify recommendations before changing configuration or reporting a defect. Sensitive credentials and unrelated personal data are excluded from the trace.**

When evidence is insufficient, display:

> **This is a possible explanation, not a confirmed diagnosis. The available evidence was insufficient to determine the exact cause.**

## Delivery subphases

### DT-1 - Diagnostic event contract

Freeze event identity, correlation, error-code ownership, severity, redaction, retention, export, and deletion.

### DT-2 - Complete instrumentation

Instrument all accepted import and runtime paths without changing their behavior. Prove causal chains, redaction, failure isolation, and bounded storage.

### DT-3 - Management Diagnostics page

Display deterministic user-facing errors and technical details. This must work without an AI connection.

### DT-4 - Release diagnostic index

Generate and package the version-matched code graph, contracts, error index, and source map.

### DT-5 - Read-only Diagnostic Trace agent

Add the user-triggered OpenAI Agents SDK workflow through the existing canonical SDK runner and only the dedicated diagnostic tools. Prove that no parallel or direct model-execution path exists.

### DT-6 - Scoped trace chat and issue export

Add trace-bound follow-up chat and generate a redacted diagnostic report suitable for a GitHub issue.

## Acceptance requirements

- Every supported user package path emits a coherent operation chain.
- Exact deterministic reasons are visible without AI.
- Secrets and unrelated personal data are absent from storage, API responses, exports, and model requests.
- Trace begins only on explicit user action and at the selected error.
- Trace execution uses the OpenAI Agents SDK framework and the existing configured Text-model/provider boundary.
- No custom agent loop, second agent framework, or direct ad hoc model call exists for diagnostics.
- Trace cannot mutate device or package state.
- Graph and source evidence match the installed release.
- Imported package content cannot change agent instructions or gain tool access.
- Confirmed, likely, possible, and unknown conclusions remain distinct.
- The required fallibility disclaimer is continuously visible.
- Disabling or disconnecting the model leaves deterministic diagnostics functional.
- Real negative tests prove denied writes, denied unrelated reads, prompt-injection resistance, stale-graph rejection, missing evidence, retention, deletion, and export redaction.

## Explicit non-scope

- Autonomous repair.
- Automatic configuration edits.
- Agent-triggered reinstall, rollback, deletion, restart, or credential rotation.
- General-purpose device administration.
- Unrestricted source, shell, database, filesystem, network, or personal-data access.
- Treating an AI hypothesis as authoritative support evidence.

## Status and next action

This phase is intentionally deferred. Earlier build documents may reference this filename as the future owner of unified diagnostics, but must not pull its agent, graph, management page, or cross-system instrumentation into their implementation scope.

The next action occurs only after the project’s package, Card, Domain, connector, Voice/Text, and runtime contracts are stable: open DT-1 as a new controlled build contract and revalidate this candidate against the installed release architecture.
