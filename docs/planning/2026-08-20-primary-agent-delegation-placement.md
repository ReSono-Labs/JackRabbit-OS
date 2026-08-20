# Primary ReSono Agent and Conditional Delegation — Placement Review

**Candidate:** `R1-PRIMARY-AGENT-DELEGATION-PLACEMENT-v0.1`  
**Date:** 2026-08-20  
**Status:** Owner-proposed planning addition; codebase-grounded placement review; not an active build contract  
**Grounding:** `GROUNDING-BASELINE-v0.5` and `R1-STANDALONE-DELIVERY-PLAN-v0.3`  
**Repository state reviewed:** current working tree during active Build Contract 07 Skills/Plugins/MCP work  
**Implementation authority:** none. This document does not authorize code, APK, device, or active-contract changes.

> Build Contract 07 is read-only for this review. This candidate records a possible later insertion and does not alter, append to, or reopen the active contract.

## Placement outcome

Place this capability in a new delivery slice:

```text
current Delivery Slice 7
Calendar + Contacts + Reminders
        ↓
NEW SLICE
Primary ReSono identity + delegated Agents SDK work
+ conditional multi-agent orchestration
        ↓
current Delivery Slice 8
Hermes A2A + unified product experience
```

The insertion point is **after current Delivery Slice 7 and before current Delivery Slice 8**. Do not add it to Build Contract 07.

This is the narrowest logical placement because:

1. Build Contract 07 is actively establishing the shared Tool Catalog, Agent Audience Router, Agent Skills activation, Agent Plugin lifecycle, and later outbound MCP connections. Delegated workers must consume those accepted owners; they must not design parallel capability or permission systems while those boundaries are still changing.
2. Current Delivery Slice 7 must complete the already accepted Calendar, Contacts, and Reminders work through the Mail-proven domain/plugin boundary. The new feature does not justify delaying or redesigning those required domains.
3. The first later slice with an unavoidable delegation concern is current Delivery Slice 8, where Hermes A2A enters. Establishing the R1-owned internal delegation/job contract immediately before Hermes prevents Hermes from becoming the de facto owner of delegation semantics.
4. The new slice can prove internal OpenAI worker delegation independently. Hermes remains one external A2A target in its own accepted slice and does not become an OpenAI worker implementation.

Final slice numbering should wait until the owner has supplied and placed the remaining proposed additions. Renumbering the accepted plan repeatedly would create avoidable cross-document churn.

## Authority and scope state

The owner supplied the architecture in this review request and explicitly asked for its logical build placement. That authorizes this planning candidate. It does not by itself make the capability part of the accepted baseline or active implementation.

Before this item enters the authoritative master delivery plan:

- `GROUNDING-BASELINE.md` must be amended and owner accepted because OD-17 closed first-release capability discovery and the current clean-code rules prohibit premature orchestration infrastructure;
- the new observable success behavior, scope boundary, controlled terms, dependency order, and acceptance evidence must be recorded once in the baseline and delivery plan;
- current Build Contract 07 remains unchanged; and
- a later build contract must freeze the implementation only after its entry dependencies pass.

This candidate therefore has status `CONDITIONAL`, not accepted or implementation-ready.

## Owner-supplied architecture retained

The following product rules are retained from the supplied external architecture input:

1. The user experiences one ReSono assistant and one conversational identity.
2. The native Realtime Voice model remains the live conversational owner; it is not reduced to speech-to-text in front of an unrelated text agent.
3. Ordinary conversation stays with the primary ReSono agent.
4. A capability change does not imply a new agent. Calendar, Mail, memory, device, and MCP actions normally remain direct primary-agent tool or Skill use.
5. The primary agent may request deeper work through one bounded delegation capability.
6. Runtime code, not the Realtime model, selects the execution topology, worker count, model, parallelism, timeouts, permissions, and stopping rules.
7. One temporary Agents SDK worker handles substantial but coherent delegated work.
8. Multiple temporary workers are used only when decomposition, parallelism, distinct reasoning objectives, or independent verification materially improves the result.
9. Workers are job instances, not permanent user-facing specialist personalities.
10. Manager-style orchestration is preferred over conversational handoffs because ReSono must retain final-answer ownership.
11. Skills are injected only when relevant to the delegated objective.
12. Workers receive only the intersection of requested, installed, granted, healthy, task-relevant, and worker-policy-approved capabilities.
13. Background lifecycle agents such as the memory reviewer remain separate from current-conversation delegation.
14. Multi-agent execution has bounded total workers, bounded parallelism, timeouts, cancellation, and cost/resource controls.
15. No AutoGen or second orchestration framework is added.

The supplied four execution levels remain useful controlled vocabulary:

| Level | Meaning | R1 behavior |
|---:|---|---|
| 0 | Primary only | Conversation or reasoning in the live ReSono agent |
| 1 | Primary plus capability | Direct Skill, built-in Tool, memory, or MCP invocation |
| 2 | One delegated worker | One bounded Agents SDK job with its own context and lifecycle |
| 3 | Conditional multi-agent job | Multiple bounded workers only when the task-shape and policy gates pass |

Examples such as research branches, specialist reviews, executor/reviewer loops, and planner/executor/reviewer coding work are retained as **task-shape examples**, not as permanent agent types or guaranteed initial topologies.

## Corrections from the actual codebase

The supplied architecture was explicitly described as external understanding. The current repository changes several of its assumed file and runtime boundaries.

### 1. The primary Voice agent already exists as a runtime composition, not a `primary/` package

The permanent Voice owner is currently distributed across real accepted seams:

- `runtime/resono_runtime/providers/controller.py` builds the Realtime session from the active provider/access/model selection, session memory context, Skill disclosure, and Voice Tool Catalog projection.
- `runtime/resono_runtime/providers/openai/platform.py::_realtime_session()` currently owns the base identity string, `"You are ReSono Voice"`, and serializes the provider-specific Realtime session.
- `runtime/resono_runtime/tools/catalog.py` is the single in-process owner of executable tool definitions and agent-audience projection.
- `runtime/resono_runtime/skills/activation.py` supplies progressive Skill disclosure and just-in-time instruction loading.
- `runtime/resono_runtime/memory/session_context.py` supplies session-start recalled context.
- `android/feature/voice/src/main/java/com/resonolabs/feature/voice/VoicePageView.java` owns the native live interaction, transcript, Realtime function-call, and result-continuation behavior.

Therefore a future `runtime/resono_runtime/agents/primary/agent.py` must not instantiate a second Voice agent or duplicate session composition. The later build should extract only the provider-neutral ReSono identity/instruction and delegation contract from the current seams where that creates one clear owner.

### 2. `AgentAudienceRouter` is not a delegation router

Current files:

- `runtime/resono_runtime/agents/audience.py`
- `runtime/resono_runtime/agents/routing.py`
- `runtime/resono_runtime/storage/agent_audiences.py`

These own whether an imported capability is exposed to `voice`, `text`, or `both`. They do not classify tasks, start agents, grant permissions, select models, or route work.

Temporary workers must not be added as a fourth user-selectable audience. A worker inherits a strictly reduced capability view from the invoking `voice` or `text` surface and the current task. This keeps user-facing audience selection separate from internal execution topology.

### 3. One Agents SDK construction path already exists

`runtime/resono_runtime/agents/sdk_runner.py` is the canonical `Agent`/`Runner` construction and execution path. It is consumed by:

- `runtime/resono_runtime/agents/runner.py` for the current text turn; and
- `runtime/resono_runtime/agents/memory_reviewer.py` for the post-session review agent.

The new worker path must extend this owner or a narrowly versioned successor. It must not create a second direct `Agent`/`Runner` factory elsewhere.

The existing `AgentsSdkTextRunner` is not a Worker Manager. It is a synchronous, memory-free management text-turn adapter with a hard-coded `get_device_status` MCP filter. It must not be renamed into a general worker service without separating its accepted existing responsibility.

### 4. The current native Voice tool call is too short-lived for substantial delegation

The current path is:

```text
Realtime function call
  -> VoicePageView.callTool()
  -> RuntimeVoiceClient.callTool()
  -> local MCP tools/call
  -> ToolCatalog.invoke()
  -> function_call_output
  -> response.create
```

`android/runtime-host/src/main/java/com/resonolabs/runtime/host/RuntimeVoiceClient.java` uses a single-thread executor and a 10-second MCP read timeout. That is correct for the current bounded device/memory/Skill tools but cannot carry the supplied multi-minute research, coding, comparison, or evaluator examples as one synchronous `delegate_task()` response.

The later slice therefore needs a durable asynchronous job contract. The Realtime tool should start or attach to a job and return bounded truthful state promptly. Runtime-owned job completion must later be presented back through the primary ReSono agent. It must never let a worker speak directly as a replacement conversational identity.

### 5. The runtime has threads but no durable agent-job owner

`runtime/resono_runtime/api/http_server.py` uses `ThreadingHTTPServer`, and `runtime/resono_runtime/api/events.py` has an in-process event stream. Neither is a persistent worker queue or restart-safe job lifecycle. `RuntimeApplication.stop()` currently stops the HTTP server but has no delegated-job shutdown/cancellation owner.

The new slice requires explicit job persistence, restart recovery, bounded concurrency, cancellation, terminal status, and result ownership. An HTTP request thread, SSE queue, or `asyncio.gather()` call alone does not satisfy that requirement.

### 6. Worker permissions cannot reuse the current broad local bearer unchanged

`runtime/resono_runtime/mcp/server.py` currently owns one local MCP server instance composed for `AgentKind.VOICE`. The Agents SDK text adapter connects with the runtime bearer and locally filters to `get_device_status`.

A worker-specific capability intersection cannot be enforced only by changing an SDK-side tool filter. The runtime must mint or carry a job-scoped execution context so `ToolCatalog` and invocation checks enforce the reduced view server-side. All workers still use the one Tool Catalog and local MCP implementation; there is no separate Worker MCP registry.

### 7. Model routing examples are hypotheses, not frozen product policy

The supplied Luna/Terra/Sol examples are useful policy candidates but are not currently grounded as worker routing rules.

- `runtime/resono_runtime/storage/provider_settings.py` stores one selected text model and reasoning effort for the current product.
- `runtime/resono_runtime/storage/provider_catalog.py` and `ProviderController` own currently available/reported models.
- `runtime/resono_runtime/providers/openai/access.py` is the one selected Platform-versus-subscription credential/base-URL resolver for every OpenAI consumer.

Workers must use runtime-reported available models and the selected access path without hidden fallback. Exact worker routing, reasoning effort, and concurrency defaults require representative quality, latency, cost, Android packaging, and physical R1 resource evidence in the later contract.

### 8. Background system agents remain separate

`runtime/resono_runtime/agents/memory_reviewer.py` is already a lifecycle-triggered background agent with its own instructions and structured result gates. It remains outside current-conversation delegation and should continue to use the single SDK execution path.

## Code-grounded target ownership

The later build should start from the smallest set of precise owners below. Names are planning targets and are frozen only by that later build contract.

```text
runtime/resono_runtime/agents/
  primary.py                 # provider-neutral ReSono identity/context contract only
  delegation.py              # delegation request/result and primary-facing tool behavior
  delegation_policy.py       # direct vs one-worker vs multi-worker decision and hard limits
  workers.py                 # temporary Agents SDK worker construction through sdk_runner.py
  orchestration.py           # created only when Level 3 is actually proved
  jobs.py                    # durable lifecycle, cancellation, restart, and result ownership

runtime/resono_runtime/storage/
  agent_jobs.py              # canonical delegated-job repository
  migrations/vNNN_agent_jobs.py

runtime/resono_runtime/api/
  agent_job_routes.py        # support-safe inspect/cancel transport; never an agent bypass
```

Existing owners that must be extended rather than copied:

| Existing owner | Later responsibility |
|---|---|
| `application.py` | Construct exactly one delegation policy, job owner, worker executor, and primary contract; start and stop them in process order. |
| `agents/sdk_runner.py` | Remain the single OpenAI Agents SDK construction/run path for text, memory review, and temporary workers. |
| `providers/openai/access.py` | Resolve the one selected credential/base URL for every worker. |
| `providers/controller.py` | Add the primary delegation disclosure/tool to the existing Realtime session composition. |
| `providers/openai/platform.py` | Serialize the already-composed primary instructions and tools; stop owning provider-neutral product identity. |
| `skills/activation.py` | Supply only selected, audience-compatible Skill metadata/instructions to a worker job. |
| `tools/catalog.py` | Produce a job-scoped, permission-filtered capability projection and enforce it again at invocation. |
| `mcp/server.py` | Carry the trusted caller/job context through the same local MCP boundary. |
| `api/events.py` | Publish support-safe delegated-job state after durable state changes; it is not the canonical job store. |
| `VoicePageView.java` / `RuntimeVoiceClient.java` | Start/observe/cancel delegated work and return completion to Realtime without adding worker identities or business rules to Android. |

Do not create generic `manager.py`, `factory.py`, `policies.py`, `utils`, `helpers`, or `common` files. The current repository boundary check rejects catch-all ownership, and the target names above describe one responsibility each.

## Execution contract

### Primary decision and runtime decision

The primary model decides only whether deeper work is needed and supplies a bounded intent:

```text
objective
relevant context reference(s)
requested Skills
requested capabilities
complexity/parallelism/verification hints
expected result shape
```

It does not name workers, choose a worker count, select a model, select a provider credential, or construct a topology.

Runtime policy then decides:

```text
Level 0: no delegation
Level 1: direct approved capability
Level 2: one temporary Agents SDK worker
Level 3: bounded multi-worker job
```

If multi-agent execution provides no measured advantage, policy selects Level 2 or rejects the delegation hint. A model hint never overrides resource, permission, approval, or active-slice policy.

### Durable job lifecycle

The minimum truthful lifecycle is:

```text
accepted -> queued -> running -> completed
                           \-> failed
              \-> cancelled
```

If a worker needs clarification or approval, the later contract must add an explicit bounded waiting state instead of leaving a thread or Realtime tool call open indefinitely.

Each job needs:

- a runtime-minted job ID;
- invoking user/session/turn and primary surface;
- immutable objective and expected result contract;
- selected execution level and topology record;
- selected access path/model/reasoning and why they were allowed;
- exact effective Skill and Tool capability set;
- worker/step state, deadlines, retry count, and cancellation state;
- support-safe usage/cost metadata where the provider reports it;
- result, reviewer outcome, and failure reason; and
- restart/recovery disposition.

The worker result is data for the primary ReSono agent. It is not a direct user-facing specialist reply.

### Capability intersection

The effective worker view is:

```text
primary requested capabilities
  INTERSECT installed and enabled capabilities
  INTERSECT invoking agent audience
  INTERSECT user and tool grants
  INTERSECT connection/domain health
  INTERSECT task relevance
  INTERSECT worker policy
  INTERSECT approval state
  = worker-visible Skills and Tools
```

Workers never receive all R1 tools. Side-effecting tools retain their existing approval and domain constraints. Delegation cannot turn a read request into Mail send, calendar deletion, connection configuration, Skill installation, Plugin installation, or another management action.

## Initial delivery shape

The new slice should prove the architecture in dependency order:

1. Extract one provider-neutral ReSono primary identity/context owner without changing accepted Voice behavior.
2. Add durable delegated-job storage, status, cancellation, restart recovery, and bounded result ownership.
3. Add one `delegate_task`-equivalent primary Tool Catalog definition that starts a job; freeze its exact public name and schema in the later contract.
4. Run one coherent temporary worker through `agents/sdk_runner.py` with one reduced Skill/Tool view.
5. Return the result through the same primary ReSono identity.
6. Add code-controlled Level 3 orchestration only after a representative decomposable task proves a material advantage over the one-worker baseline.
7. Prove one bounded parallel job and one executor/reviewer or independent-verification job.
8. Prove that ordinary direct Tool/Skill requests do not delegate.

The first worker proof should use already accepted local capabilities and a bounded read-only task. It must not depend on Mail send, calendar mutation, coding sandbox execution, arbitrary shell, hosted spawning, or Hermes.

## Required tests and evidence for the later slice

Positive evidence:

- one real Voice request handled directly with no worker;
- one real Voice request handled by a direct Skill/Tool with no worker;
- one real substantial request completed by one Agents SDK worker;
- one real decomposable request completed through bounded parallel workers with a measured benefit or quality rationale;
- one real worker result summarized by the primary ReSono agent without a specialist identity taking over;
- worker Skill activation through the existing Skill Catalog;
- worker MCP invocation through the existing Tool Catalog/local MCP path; and
- restart-safe retrieval of a completed or interrupted job.

Negative and recovery evidence:

- delegation hint rejected or reduced when one direct capability is sufficient;
- requested capability removed by user grant, audience, health, task, or worker policy;
- worker cannot use an ungranted side-effect tool;
- worker cannot install/configure a Skill, Plugin, MCP connection, or credential;
- model and access-path unavailability fail truthfully without Platform/subscription substitution;
- worker timeout, cancellation, provider failure, malformed output, and primary-session closure;
- R1 runtime restart while queued, running, and completed;
- stale/replayed job ID and cross-session/user denial;
- parallel-worker cap and total-worker cap enforcement;
- evaluator loop iteration cap and failed-review terminal behavior;
- no worker writes directly to Android UI, canonical domain storage, or another worker's mutable state; and
- no handoff changes the user-facing conversational owner.

Acceptance requires physical R1 evidence for memory pressure, foreground-runtime continuity, Voice responsiveness, cancellation, and concurrent job limits. Host-only concurrency tests cannot establish safe device defaults.

## External OpenAI documentation review

The supplied manager-versus-handoff distinction is consistent with current official OpenAI documentation: Agents SDK manager-style workflows use an agent as a bounded tool when the outer agent must retain final-answer ownership, while handoffs transfer conversational control. Official guidance also says to start with one agent and add specialists only when they materially improve isolation, prompt clarity, or trace legibility.

Current official documentation additionally exposes Responses API Multi-agent as a GPT-5.6 beta. That is a materially different execution option from the supplied code-controlled Agents SDK Worker Manager. It can create parallel subagents inside a Responses request, but its beta schemas may change, its subagents share the request model and available tools, and it may not satisfy the R1's subscription transport, job persistence, per-worker capability intersection, or one canonical Agents SDK path.

Therefore this candidate does **not** select Responses Multi-agent beta for the R1. The later build contract must compare only:

1. code-controlled temporary workers using the existing Agents SDK execution path; and
2. the provider beta only if it is supported by both required access paths and can obey the same R1 job, permission, persistence, and acceptance boundaries.

No second orchestration authority is permitted.

Official references reviewed 2026-08-20:

- [OpenAI Agents SDK — orchestration and handoffs](https://developers.openai.com/api/docs/guides/agents/orchestration)
- [OpenAI voice-agent architecture](https://developers.openai.com/api/docs/guides/voice-agents)
- [OpenAI Responses API Multi-agent beta](https://developers.openai.com/api/docs/guides/responses-multi-agent)

## Material Decision Gate — placement and architecture boundary

**Question:** Where should the owner-proposed primary-agent/delegated-worker/multi-agent capability enter the accepted build, and which existing owners must it extend?

**Authority and evidence:** owner request on 2026-08-20; `GROUNDING-BASELINE-v0.5` OD-01, OD-02, OD-08–OD-11, OD-17 and clean-structure rules; accepted delivery plan dependency order; active Build Contract 07 boundaries; current code paths cited above; current official OpenAI documentation.

**Material alternatives:**

1. Add it to active Build Contract 07.
2. Insert it immediately after Build Contract 07 but before Calendar/Contacts/Reminders.
3. Insert it after current Delivery Slice 7 and before current Delivery Slice 8.
4. Add it to Hermes/current Delivery Slice 8.
5. Defer it until after Hermes or first release.

**Selection and real-world function:** select alternative 3. Complete the shared capability and required personal-domain foundations first, then add one R1-owned internal delegation/job layer before the external Hermes delegation slice. The primary ReSono Voice identity remains the only user-facing conversational owner.

**Why the alternatives fail now:**

- Alternative 1 changes an active owner-gated contract, mixes an unaccepted job/orchestration system into current Skills/Plugins/MCP work, and violates the owner's explicit instruction not to touch Build Contract 07.
- Alternative 2 delays accepted personal-data domains even though their domain/tool boundaries do not depend on worker orchestration.
- Alternative 4 makes one slice own internal OpenAI workers, external A2A interoperability, and the unified UI, producing an oversized contract and risking two delegation authorities.
- Alternative 5 lets Hermes arrive before the R1 owns its internal delegation semantics and postpones an owner-selected capability beyond its useful dependency point.

**Counterexample/reopen trigger:** reopen placement if Build Contract 07 does not complete one shared permission-filtered Tool Catalog/MCP path, if the later Calendar/Contacts/Reminders contracts prove they require delegated jobs to satisfy their accepted behavior, or if physical R1 evidence shows safe delegated execution cannot coexist with live Voice in the single supervised runtime.

**Affected dependents:** baseline success/scope, master delivery plan numbering and traceability, later build contract, Agents SDK execution, primary Voice instructions, Tool Catalog/MCP caller context, Skills activation, provider/model policy, SQLite migrations, native Voice tool continuation, Hermes sequencing, final release tests.

**Result:** `CONDITIONAL`. Planning placement is selected. Authoritative scope and implementation remain blocked on owner acceptance of the eventual baseline/master-plan amendment and the new slice's entry gates.

## Open decisions for the later build contract

These are deliberately not guessed in this placement review:

1. Exact owner-facing wording and whether `delegate_task` is the final model-facing tool name.
2. How a completed job is returned when its originating Realtime session has ended, while preserving one ReSono identity and avoiding a new disconnected UI.
3. Whether an initial job may pause for clarification/approval and the exact resumable state contract.
4. Initial physical R1 parallel-worker and total-worker limits.
5. Worker model/reasoning selection policy and whether the user may configure it.
6. Whether both Platform and subscription access must prove delegated work in the initial slice or one path may remain conditional.
7. Whether current Agents SDK `as_tool` composition or explicit runtime-controlled nested runs best preserves the R1 job and permission boundary with the pinned Android SDK version.
8. Whether the Responses Multi-agent beta is compatible enough to evaluate or remains deferred.
9. Exact relationship between the internal delegated-job envelope and later Hermes A2A task state without collapsing the two protocols.

Each choice must be resolved in the later contract from current code, the then-pinned SDK/provider behavior, physical device evidence, and owner authority.

## Next documentation action

Hold this file as the first proposed insertion while the owner supplies the remaining additions. After all additions are reviewed:

1. compare their dependencies and consolidate placement;
2. amend `GROUNDING-BASELINE.md` once with the owner-approved new decisions and success behavior;
3. revise the master delivery plan once, inserting and renumbering slices as necessary;
4. update requirement traceability and open gates;
5. run a separated Phase 02 plan review; and
6. leave Build Contract 07 unchanged.
