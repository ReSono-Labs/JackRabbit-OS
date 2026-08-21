# First-Party Tasks Package Contract

**Status:** Owner-authorized implementation contract

## Scope correction

Contacts and Reminders are suspended from the final integrated build. They may return later as separately installed packages. Their names, stores, Cards, tools, and management surfaces must not be created as placeholders.

Tasks is the only new first-party capability in this subphase. It is not a renamed Reminders domain and does not schedule notifications, alarms, recurring reminders, or external synchronization.

## Ownership

“First-party package” means a cohesive built-in product capability, not an imported Agent Plugin archive.

```text
Tasks database/repository
        -> Tasks service
        -> Tasks device API -> native Tasks Card
        -> Tasks tool package -> Voice Tool Catalog
```

- Canonical data: `runtime/resono_runtime/domains/tasks/`.
- Uniform Voice tools: `runtime/resono_runtime/tools/tasks/`.
- Device-only projection: `runtime/resono_runtime/api/task_routes.py`.
- Native Card: `android/feature/tasks/`.
- Cards owns navigation only and does not interpret task records.
- No management page is required because Tasks has no account or connection setup.
- No Plugin, Creation, or Card catalog record owns built-in Tasks data.

## Canonical task

```text
task_id
text
status: open | completed
created_at
updated_at
completed_at (optional)
```

The active Card projection returns open tasks ordered by creation time and stable ID. Completed tasks are not shown in the active list but remain readable through Voice until explicitly removed.

## Version 1 Voice tool package

- `tasks_list`
- `tasks_read`
- `tasks_add`
- `tasks_edit`
- `tasks_mark_completed`
- `tasks_remove`
- `tasks_confirm_action`

The full set is registered through one `TasksToolPackage.register(ToolCatalog)` call and one stable `domain_tool_set:tasks` audience resource. There is no user-facing text-agent projection.

Reads execute immediately. Add, edit, mark completed, and remove prepare an immutable action. Voice reads the exact change to the user and asks for approval. `tasks_confirm_action` executes the unchanged action only after a later explicit approval in the same trusted Voice session, within ten minutes, and only once.

Tasks never interpret date or future wording as a schedule. If the user says a
phrase such as "tomorrow," Voice preserves that wording in the plain task text,
explains that Tasks cannot schedule the item or send a reminder, reads the exact
prepared text back, and requests confirmation normally. Voice must not silently
drop the date wording or claim that a timed reminder was created.

Task removal permanently deletes the local task after confirmation. Marking completed is not deletion.

## Native Card

The Card uses the established 480x640 R1 list/detail language:

- five task rows per page;
- 31 px task text and a restrained 21 px `OPEN` status line;
- selected long task text scrolls right-to-left with the donor-proven pause/travel/pause behavior;
- direct horizontal finger pan for overflow;
- wheel/touch selection;
- tap/activate opens detail;
- detail shows the complete task text and state;
- writable actions return to persistent Voice with clear wording rather than opening a CipherOS dialog;
- local projection refreshes dynamically without reboot.

## Explicit non-scope

- Contacts.
- Reminders, alarms, notifications, recurrence, or background delivery.
- Due dates, due times, schedules, notes, priorities, tags, lists, subtasks, or attachments.
- External task providers or connections.
- Web task list or task editing.
- Imported Plugin ownership of the built-in task table.
- Arbitrary package storage.
- A user-facing text agent.

## Implementation order

1. Migration and canonical repository.
2. Service with immutable ten-minute actions.
3. Uniform Voice tool package and runtime composition.
4. Device-only task routes.
5. Dedicated Android module and built-in Cards entry.
6. Focused host contract and physical 480x640 acceptance.

## Acceptance

- One canonical task table and repository.
- Voice can list/read and, after exact review and approval, add/edit/complete/remove.
- Pending actions expire after ten minutes and are single-use.
- The Card shows real active tasks only and refreshes without restart.
- Completed tasks leave the active Card immediately but remain queryable.
- Removed tasks are permanently absent.
- Contacts and Reminders have no built-in implementation or implied placeholder.

## Implemented source map

- Task migration: `runtime/resono_runtime/storage/migrations/v029_tasks.py`.
- Canonical model/repository/service: `runtime/resono_runtime/domains/tasks/`.
- Versioned Voice package: `runtime/resono_runtime/tools/tasks/`.
- Device projection: `runtime/resono_runtime/api/task_routes.py`.
- Android runtime client: `android/runtime-host/src/main/java/com/resonolabs/runtime/host/TaskClient.java`.
- Native Card: `android/feature/tasks/src/main/java/com/resonolabs/feature/tasks/TaskPageView.java`.
- Cards routing: `android/feature/cards/src/main/java/com/resonolabs/feature/cards/`.
- Focused host contract: `tests/runtime/test_tasks_contract.py`.

No reboot is required for task data changes. The Card polls the authenticated
loopback projection every two seconds, so a confirmed Voice mutation appears
without rebuilding or restarting the runtime.

## 2026-08-20 build and deployment evidence

- Focused host contracts: Tasks and Calendar, five tests passed.
- Android build: `BUILD SUCCESSFUL`, 299 tasks.
- Structural gates: `standalone Android boundaries: OK` and
  `embedded runtime package: OK`.
- Preserved candidate:
  `artifacts/local-builds/ReSonoR1-build07-tasks-20260820T211345Z.apk`.
- SHA-256:
  `86f38aa4c0fefbbd848cb7729b50ac2954e43b42355a1f2d28bdb2414e5fe02b`.
- Installed through the existing ADB transport on R1 serial
  `919109A5P1600502814D`; streamed install returned `Success`.
- Installed HOME package: `com.resonolabs.voice.engineering`, version code 29,
  version name `0.4.24-openai-settings-controls-debug`.
- `MainActivity` was explicitly brought to the foreground after installation.

This is implementation/build/deployment evidence, not owner interaction or
visual acceptance. Voice mutation behavior and the 480x640 Tasks Card remain
subject to the planned physical acceptance pass.

## Native-card startup correction

Physical review found that the Cards deck initially showed an empty imported
Creations state when the catalog request had not completed. Built-in Calendar
and Tasks were incorrectly populated only from the catalog-success callback.
`CardsDeckView` now initializes its native built-in entries immediately; later
catalog responses append imported Cards without owning or gating first-party
Cards. This keeps built-in navigation available even when the import catalog is
empty or temporarily unavailable.

The shared rolodex card face uses slightly enlarged typography for the 480x640
display: 15 px category/status labels, 32 px titles, and 19 px descriptions
with 28 px line spacing. This applies uniformly to built-in, Plugin, and
Creation card faces without changing the persistent header, card dimensions,
or activated content views.

Rolodex cards do not repeat a separate centered title. The colored top-left
category is the card heading and the top-right readiness value is its state;
both use 22 px text. The description begins directly below that row. This rule
applies uniformly to built-in, Plugin, and Creation card faces.

## Deployed migration recovery

Physical version-29 review exposed a deployed-database-only failure in migration
30. The migration runner had an active transaction from earlier migration
version records, causing SQLite to ignore `PRAGMA foreign_keys = OFF` before the
shared `connections` table rebuild. Existing Mail rows then prevented the drop,
the runtime supervisor recorded three startup failures, and Voice correctly
reported the loopback runtime unavailable. Migration 30 now commits the prior
transaction first, disables foreign keys before rebuilding, removes a shadow
table left by an interrupted attempt, checks foreign-key integrity, and then
restores enforcement. No app data or credentials are cleared by this recovery.

The same physical retry then exposed an import-contract regression in the
shared outbound-security module before migrations ran. Its rewrite retained
new URL/redirect checks but removed `UnsafeOutboundHost` and
`resolve_public_host`, and changed `validate_public_host` incompatibly. MCP,
Creation QR, and Mail still use those public contracts. The module now retains
one SSRF-safe resolver while restoring all three APIs; MCP can pin the validated
address, and Creation/Mail keep their existing exception and port contracts.

## Global Voice approval correction

Physical transcripts proved that valid approvals including `Yeah, go ahead and
save that`, `Yes, approved`, `Yeah, it's, yes`, `OK, good`, and `Approved` were
rejected. Tasks compared the complete normalized utterance with a small English
phrase allowlist. Calendar and Mail duplicated the same defect.

Approval is now language-independent at the domain boundary. The Voice agent
may call the confirm tool after interpreting explicit approval intent; the
runtime does not second-guess that intent with keywords. Runtime authorization
still requires the immutable pending action, exact content hash, same trusted
Voice session, a strictly newer native utterance sequence, validity window, and
single-use claim. The model has no `approved` argument and cannot bypass those
structural controls. The focused Tasks contract includes the physically
rejected phrases and proves that a preparation utterance cannot confirm its own
action.
