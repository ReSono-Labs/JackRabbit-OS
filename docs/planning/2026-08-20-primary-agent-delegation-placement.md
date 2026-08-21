# Build Contract 08 - Primary Voice and Delegated Background Work

**Identity:** `R1-BUILD-CONTRACT-08-DECISIONS-v1.2`  
**Date:** 2026-08-20; consolidated 2026-08-21  
**Status:** Owner-authorized decision record  
**Implementation authority:** `2026-08-21-build-contract-08-execution-plan.md`

## Purpose

This file retains the owner decisions that place Build Contract 08. It is not a
second execution plan. Exact implementation state, source ownership, workspace
contracts, ordered subphases, exit gates, and deferrals live only in the
authoritative execution plan.

## Frozen product decisions

1. Primary Voice is the user's normal conversational agent.
2. The background text agent is a powerful delegated worker, not a user-facing
   text-chat product and not a read-only helper.
3. A clear request for delegated background work must cause Primary Voice to
   enter a dedicated Goal Intake mode on the same live Realtime session.
4. Goal Intake receives a distinct trusted instruction profile and restricted
   tool catalog, performs the adaptive interview, submits one typed goal, and
   switches the same session back to Primary Voice.
5. Mode switching must replace both provider-visible instructions and tools
   through an acknowledged `session.update`. A label, prompt-only convention,
   unchanged tool catalog, simulated specialist, ordinary intake tool, or
   disconnected second session is noncompliant.
6. The background run does not depend on the Voice session remaining live.
7. A terminal result is committed once. It returns to the exact originating
   Primary Voice session when that session is still live and is also retained
   for the future notification system. Delivery failure never changes a
   completed run into a failed run.
8. The complete durable user workspace and artifact-publication boundary are
   required Build 08 work, separate from temporary per-run scratch storage.
9. Primary Voice must have bounded read-only access to background run files and
   durable published artifacts. It receives no workspace write, overwrite,
   move, delete, publish, or cleanup capability.
10. One canonical Tool Catalog, audience router, Agents SDK runner, Skill owner,
    memory owner, MCP lifecycle, provider-access owner, run owner, and workspace
    owner must be preserved.
11. No hidden chain-of-thought is requested, stored, reconstructed, or shown.
    Provider reasoning summaries, tool events, usage, explicit review findings,
    and state transitions remain observable.
12. Hermes, OpenClaw, A2A networking, Agent Network, Tailscale, Link, remote
    artifacts, notification UI, user-facing text chat, unrestricted execution,
    and multi-worker orchestration are deferred until the local Build 08 system
    is completed and accepted.

## Proven donor principles retained

The Presentation donor demonstrated useful ownership patterns: structured
goal/result models, explicit tool manifests, bounded tool and turn budgets,
Agents SDK execution with provider-returned reasoning summaries, per-run
workspaces, host-owned file tools, validation, review/repair, and fail-closed
command isolation. Build 08 reuses those principles without copying the donor's
website-specific builder/reviewer product or assuming Bubblewrap works on the
R1.

The current device has not proved a Bubblewrap backend. Build 08 therefore
permits only capability-sandboxed host tools and confined workspace operations.
Shell, arbitrary Python, unrestricted filesystem access, APK/system mutation,
and unsandboxed command execution remain absent.

## Canonical execution flow

```text
User
  -> Primary Voice
  -> same-session Goal Intake mode
  -> restricted Goal Intake instructions and tools
  -> adaptive interview and typed goal submission
  -> acknowledged same-session switch back to Primary Voice

Background text agent
  -> authorized tools + relevant Skills/memory + confined workspace
  -> bounded Agents SDK work/review
  -> canonical result + controlled artifact publication
       -> exact live originating Primary Voice session, when available
       -> durable notification-ready completion context, always
```

## Authoritative implementation reference

Continue only from
`docs/planning/2026-08-21-build-contract-08-execution-plan.md`. Do not restore
the former proposed source map, A2A adapter, duplicate subphase sequence, or
“implementation not started” status that previously lived in this file.

The verified donor mechanism and R1 adaptation contract are normative at
`docs/references/VOICE_RUNTIME_MODE_SWITCHING_DONOR.md`.
