# Build Contract 07 - Standard Extensions, Voice Mail, and Web Search

**Identity:** `R1-BUILD-CONTRACT-07-v0.7-audited-implementation`  
**Grounding:** `GROUNDING-BASELINE-v0.5`  
**Delivery slice:** 6  
**Status:** Code implementation and host/build evidence complete. Physical acceptance is partial; only the explicitly recorded device results below are accepted. Remaining provider, import-lifecycle, and on-device Creation evidence must not be inferred from build results.  
**Opened:** 2026-08-20  
**Authority added by owner on 2026-08-20:** the Mail and tool-surface decisions recorded in this contract.

**Reading rule:** Owner-fixed decisions, the final implementation closure record, and later owner corrections control. Sections explicitly labelled historical, prototype, finding, review, or earlier checkpoint are retained as audit history only; they do not describe current behavior and cannot override the final closure record.

**2026-08-21 Plugin import correction:** Browser Plugin uploads send the required `X-ReSono-Plugin-Filename` header. A confirmed valid Plugin import is atomically installed and immediately enters `enabled`; its audience, valid MCP definitions, and optional Card projection become active in the same lifecycle operation. The management surface therefore reports `Enabled` rather than leaving a newly imported Plugin in an inert `installed` state. Delete remains paired-session and CSRF protected, disables first, then removes owned MCP definitions, Cards, audience bindings, component/catalog records, installed files, and rollback files without requiring a restart.

## Outcome

The R1 runs a real local Mail service for up to three independently configured mailboxes. The service synchronizes every server folder and all mail with each account at least every five minutes, persists the synchronized mailbox locally, and exposes a deliberately bounded Mail tool set to the real Voice agent. This contract builds the authenticated management APIs needed to configure accounts and report truthful connection/synchronization state, but it does not implement those controls in the current website. The management interface requires a separate full overhaul before these APIs receive their Browser Voice surfaces. It will never become a webmail client or display a mailbox/message list.

The same runtime-owned agent tool catalog also exposes `web_search`. Contract 07 builds the API projection through which the future overhauled web Agents surface will show Mail and web search; it does not add that surface to the present website. The website will not own or duplicate executable definitions. The Voice agent receives only the tools the runtime reports as available and granted.

This contract also establishes the smallest standards-conforming Agent Skill and Agent Plugin lifecycle required by Delivery Slice 6. It does not import the donor's hosted catalog, billing, entitlement, multi-party review, sandbox, evaluation, or release-pipeline machinery.

## Owner-fixed decisions

The following are requirements, not hypotheses:

1. Mail is an on-device Voice-agent capability. It is not a webmail product.
2. The management interface will eventually be used only to add, edit, validate, disconnect, remove, and inspect the synchronization status of Mail accounts. Contract 07 implements the authenticated APIs first and makes no current web-interface changes.
3. A single R1 supports zero to three active Mail accounts. A fourth account is rejected before credentials are stored.
4. Mail credentials are encrypted and persisted in the on-device database. Plaintext credentials must never be stored in SQLite, logs, status payloads, tool results, crash evidence, or web responses.
5. Every configured account synchronizes automatically every five minutes while the runtime is operating.
6. "All mail" means every discoverable server folder and the complete message history available to the configured account, not only Inbox, unread messages, recent messages, or a bounded latest-message cache.
7. The synchronized local store is the canonical on-device read source for the Voice agent. Ordinary Voice reads do not fetch an ad hoc answer directly from IMAP.
8. Provider state remains real and bidirectional. At minimum, read/unread changes made through ReSono are written to IMAP and remote read/unread changes are reflected locally on the next synchronization.
9. Sending uses SMTP and appends the exact sent message to the server's Sent folder over IMAP so other clients see it.
10. The Voice agent cannot delete mail. No Mail delete, trash, expunge, purge, or equivalent tool, dispatcher branch, service method, or provider mutation may be implemented for the agent.
11. Mail tools and `web_search` appear in the web-managed Agents tool list.
12. The runtime is the single authority for tool names, schemas, targets, grants, and availability. The website renders the runtime projection and never maintains a second hard-coded executable catalog.
13. Donor behavior must be reused and narrowed before replacement is considered. Donor repositories remain read-only.
14. Voice may mark messages read/unread, archive messages, move messages, create folders, and rename folders.
15. Voice may compose and send mail only after exact explicit user confirmation bound to the exact pending content.
16. Initial synchronization stores all message records and attachment metadata, but attachment bytes are fetched only when explicitly requested and are subject to bounded size/type controls.
17. `web_search` must work through both configured OpenAI access paths: ChatGPT/Codex subscription and OpenAI Platform.
18. One synchronization work run has a hard ten-minute execution limit. It must checkpoint before yielding and resume without losing or duplicating work until the complete mailbox is synchronized.
19. Explicit management removal of a Mail account immediately deletes its local synchronized Mail data and encrypted credential envelope after scheduling/provider activity is stopped. It never deletes remote mail.
20. Code, storage, runtime behavior, and authenticated management APIs are implemented before any new management UI. The current website is not extended piecemeal because its full overhaul must occur first.
21. Users will be able to create/edit/publish standard Agent Skills to the R1 and upload/install their own standard Agent Skills and Agent Plugins. Contract 07 implements the runtime and API behavior, not the new web surfaces.

## Entry gates

| Gate | State | Effect |
|---|---|---|
| Slice 4 accepted | Met | Provider, Voice, MCP, and management foundations may be reused. |
| Slice 5 / Build Contract 06 physical evidence | Open | Owner explicitly directed focus onto Contract 07 on 2026-08-20. Contract 07 implementation may proceed, but unresolved older physical acceptance remains visible and cannot be relabeled complete. |
| Agent Skills specification selected | Ready for freeze | Use the official Agent Skills specification at `https://agentskills.io/specification`; record the retrieved revision/date in implementation evidence. |
| Agent Plugins specification selected | Ready for freeze | Target Agent Plugins `1.0.0` and its canonical `plugin.json` and `mcp.json` schemas unless the owner changes this before implementation. |
| Exact donor intake record | Drafted below | Before copying, add exact revision, content hashes, destinations, retained/omitted behavior, license disposition, and proving tests to `docs/DONOR_CODE_REFERENCE_MAP.md`. |
| Mail test account access | Open | Physical acceptance requires at least two independent clients observing the same account state and Sent folder. |
| Web-search access-path decision | Resolved | Owner requires both ChatGPT/Codex subscription and OpenAI Platform paths. |

## Included

- SQLite schema and repositories for as many as three Mail accounts, folders, messages, message flags, attachment metadata, drafts/send requests, sync cursors, sync runs, and encrypted credential envelopes.
- Android Keystore-backed encryption key ownership with encrypted credential ciphertext stored in SQLite.
- Authenticated management APIs for Mail account setup, validation, edit/rotation, disconnect/removal, and sync status; no new web UI in this contract.
- IMAP folder discovery and complete initial synchronization of every discoverable mail folder.
- Incremental five-minute synchronization after the initial complete synchronization.
- Remote-to-local and local-to-remote read/unread flag synchronization.
- SMTP send plus IMAP Sent-folder append.
- A runtime-owned Voice Mail tool allowlist with local-store reads, read/unread, archive/move/folder mutations, and tightly controlled compose/send.
- A runtime-owned `web_search` tool following the donor's OpenAI Responses web-search adapter pattern.
- A runtime tool-catalog projection API for the future overhauled web Agents tool list.
- Standard Agent Skill create/edit/validate/publish/import/discovery and Agent Plugin `1.0.0` upload/validate/install/discovery.
- Install, configure, grant, enable, disable, remove, quarantine, and last-known-good rollback for user-installed extensions.
- One bundled first-party Mail plugin/capability that binds the approved Mail tools without creating a ReSono-specific package format.
- Offline, integration, restart/recovery, normal-browser, and physical R1 evidence described below.

## Explicitly excluded

- All new management UI, including Mail setup/status, Skills, Plugins, Connections, Personal Data/Apps, and Agents tool-list screens. Contract 07 supplies their authenticated APIs only; UI waits for the full web overhaul.
- Webmail UI, native R1 mailbox/message screens, inbox cards, fake message data, or disconnected Mail controls.
- Mail deletion in every form: delete, trash, expunge, purge, empty-trash, retention cleanup presented as user deletion, or a generic provider-action escape hatch capable of performing deletion.
- `agent_mail`, per-agent mailboxes, autonomous inbox review, auto-reply, LangGraph communications agents, background model review, and donor autonomy extras.
- Donor billing, entitlements, marketplace, hosted catalog, multi-party developer review, evaluation farm, cgroups/sandbox platform, release pipeline, and admin console.
- Calendar, Contacts, Reminders, Hermes, External AI, ChatGPT outbox/capture, camera, and final-image work.
- A proprietary combined ReSono manifest. Skills remain Agent Skills; Plugins remain Agent Plugins.
- Browser-side execution of Mail or web-search tools.
- A second agent loop. Applicable text/background agents continue through the one OpenAI Agents SDK runner.

## Frozen architecture vocabulary and ownership

These nouns are separate controlled entities. Code, APIs, database records, and management projections must use them consistently.

| Entity | Controlled meaning | Runtime owner |
|---|---|---|
| **Skill** | Standard instructions that teach an agent how to handle a kind of task. A Skill is a standard directory centered on `SKILL.md`; it is not infrastructure or a provider connection. | `runtime/resono_runtime/skills/` plus installed content under top-level `skills/` |
| **Tool** | A real callable operation the agent can perform. Local domain tools and normalized MCP tools enter one permission-filtered Tool Registry. | `runtime/resono_runtime/tools/` |
| **MCP** | The standard protocol/lifecycle through which tools, resources, prompts, and context are exposed. It is not the provider media transport and not a synonym for Plugin. | `runtime/resono_runtime/mcp/` |
| **Plugin** | A portable Agent Plugins package with required `plugin.json` and optional standard `skills/` and/or `mcp.json`. It is a shipping container, not an executing capability or canonical-data owner. | `runtime/resono_runtime/plugins/` plus immutable installed packages under top-level `plugins/` |
| **Connector** | Code that communicates or synchronizes with an external service or file format, such as IMAP, SMTP, ICS, or CalDAV. | Domain-specific `runtime/resono_runtime/connectors/` modules as their slices land |
| **Connection** | A configured external account or endpoint plus authentication, authorization, health, and status. Credentials never live in plugin directories. | `runtime/resono_runtime/connections/` and the credential-envelope boundary |
| **Domain** | The R1-owned canonical application/data system, such as Mail, Calendar, Contacts, or Reminders. | `runtime/resono_runtime/domains/` |

Normative dependency rules:

```text
Skills may refer to permitted Tools.

Plugins may install standard Skills and MCP server definitions.
Plugin installation decomposes package components into the Skill Registry and MCP Manager.
The agent never executes or depends on a Plugin object.

The MCP Manager owns MCP clients, server definitions, connections, discovery,
health, and normalization of discovered tools into the Tool Registry.

The Agent depends only on the Skill Registry and permission-filtered Tool Registry.

Domain Services do not depend on Plugins.
Connectors do not depend on Agents.
Connections own credentials, authorization, endpoints, and connection health.
Plugins never own canonical user data.
```

Actual tool availability is the intersection:

```text
plugin/component request
  INTERSECT user grant
  INTERSECT agent grant
  INTERSECT connection/domain health
  = tool definitions actually supplied to the model
```

Tools denied by any layer are removed before the model receives its catalog. Denial only at call time is defense in depth, not the primary permission mechanism.

### Plugin installation decomposition

```text
uploaded Plugin package
  -> Plugin Manager quarantine/validation/permission/lifecycle
     -> skills/*/SKILL.md -> Skill Registry
     -> mcp.json          -> MCP Manager
                              -> local/remote MCP connection
                              -> tools/list
                              -> normalized Tool Registry
  -> Agent sees only activated Skills and granted Tools
```

Disabling or removing a Plugin deactivates the Skills and MCP definitions installed by that package. It does not delete canonical Domain data or unrelated Connection credentials. A connection created for a plugin MCP endpoint is managed by the Connection boundary and becomes disconnected/unused when its last owning definition is removed, subject to an explicit lifecycle policy.

### Domain, connector, tool, and first-party plugin separation

Mail is a Domain. IMAP and SMTP are Connectors. A configured mailbox plus encrypted authentication is a Connection. `email_search` and `email_send_pending` are Tools. The built-in Mail domain owns those tool definitions and handlers. A first-party standard Mail Plugin may ship a Mail Skill, but it does not register, own, or grant Mail tools and never owns the Mail tables, synchronized messages, credential envelopes, scheduler, or provider connectors.

The same rule controls later Calendar work: Calendar is the Domain; ICS and CalDAV are Connectors; a calendar account is a Connection; calendar operations are Tools; and a distributable Calendar Plugin may teach/use those tools without owning calendar data.

ChatGPT connecting into the R1 through the later External AI HTTPS MCP gateway is not an internal Agent Plugin. ChatGPT is an external MCP client and the gateway is the MCP server. Conversely, an R1-installed Home Assistant package containing a Skill plus `mcp.json` is a Plugin because it extends the internal R1 agent by installing a Skill and an outward MCP server definition.

### API-first management contract

Contract 07 creates authenticated, versioned APIs for the future overhauled management site:

- `/v1/management/skills`: list, inspect, create draft, edit draft, validate, publish to R1, upload/import, enable, disable, and remove;
- `/v1/management/plugins`: upload, inspect components, validate, request/grant permissions, install, enable, disable, rollback, remove, and report health;
- `/v1/management/mcp`: list installed server definitions, connection/handshake health, discovered tools, and support-safe failures;
- `/v1/management/tools`: return the canonical permission-filtered tool projection, including Mail and `web_search` availability;
- `/v1/management/connections`: support-safe connection metadata/health with connection-specific setup routed through bounded subresources;
- `/v1/management/mail/accounts`: create, validate, list status, rotate credentials, enable/disable, request sync, and remove for zero to three accounts.

Route names may be corrected during API contract freeze to match the existing router's versioning conventions, but the entity separation and behavior cannot be collapsed. No HTML, CSS, JavaScript, React, or native UI implementation is part of these checkpoints. API fixtures and direct authenticated calls are the acceptance surface until the web overhaul contract consumes them.

## Mail product contract

### Account model

Each account has a stable random `mail_account_id` and the following support-safe database state:

- user-provided display label;
- email address;
- provider kind `imap_smtp`;
- IMAP host, port, TLS mode, and username;
- SMTP host, port, TLS mode, and username;
- encrypted credential envelope reference and encryption version;
- enabled/disabled state;
- connection validation state and last support-safe error code;
- initial-sync state: `not_started`, `running`, `complete`, or `failed`;
- last attempt, last success, next scheduled attempt, and current sync owner/lease;
- folder count, message count, and pending local mutation count;
- no secret or message content in management status payloads.

The repository enforces the three-account limit transactionally. Concurrent fourth-account attempts cannot both pass a preflight count. Account removal revokes its scheduled work, removes its encrypted credential envelope, and then removes its local synchronized Mail data through an explicit management action. This management-only account removal is not an agent Mail-delete capability.

### Credential boundary

The existing OpenAI credential bridge proves Android Keystore ownership but only exposes fixed OpenAI methods. Contract 07 must add a narrow generic secret-envelope bridge rather than add three sets of mailbox fields to the bridge.

Required flow:

```text
paired HTTPS account form
  -> CSRF/origin/body validation
  -> runtime validates support-safe fields
  -> Android Keystore bridge encrypts the secret payload with authenticated encryption
  -> SQLite transaction stores account metadata + ciphertext envelope
  -> plaintext request buffers and temporary objects are discarded
  -> provider validation decrypts only inside the trusted runtime call
```

The SQLite record stores ciphertext, nonce/IV, algorithm/envelope version, Keystore alias/key version, and timestamps. The Keystore key is non-exportable. Passwords are write-only: status and edit routes return `configured: true`, never the saved value. Rotation writes and validates a new envelope before atomically selecting it. Failed validation does not destroy the last working credential. Logs may contain only account id, provider, stage, duration, and a bounded support-safe error code.

Database-file encryption alone is not accepted as credential encryption. Base64, hashing, redaction on read, or relying only on Android application sandbox permissions also fails this requirement.

### Synchronization semantics

The donor's `email_sync_interval_seconds = 300` is retained. Its `max_email_sync_messages_per_credential = 25` is a work-page size, not an acceptance limit. The standalone implementation must keep scheduling pages until the initial complete synchronization reaches a durable completion cursor for every folder.

For each enabled account:

1. Acquire a database-backed per-account sync lease so scheduler ticks and manual validation cannot run overlapping syncs.
2. Decrypt credentials only for the bounded provider operation.
3. Connect over TLS after public-host validation.
4. Discover all selectable folders and their provider attributes.
5. Resolve stable folder identity, delimiter, special-use role, and current UID validity.
6. For an unsynchronized or invalidated folder, page through every available message UID until complete.
7. For a synchronized folder, fetch changes since the durable cursor and reconcile remote flags.
8. Parse and normalize RFC-822/MIME content, preserving provider message id, folder/UID identity, dates, addresses, subject, text body, HTML-derived text, and attachment metadata.
9. Apply pending local read/unread changes to the provider with an idempotent mutation record, then confirm them through provider state.
10. Commit each bounded page and its cursor atomically so power loss resumes rather than restarts or falsely completes the folder.
11. Mark the account complete only after every discovered folder has a complete durable cursor.
12. Stop a work run before its hard ten-minute deadline, atomically checkpoint incomplete folder/page state, release the lease, and resume the incomplete account on the next eligible worker pass until initial synchronization is complete.
13. After complete synchronization, maintain the five-minute due cadence and release the lease after every bounded run.

The scheduler starts after runtime/database readiness and continues under the existing supervised runtime. Restart reads durable `next_sync_at`, incomplete runs, leases, cursors, and pending mutations from SQLite. Expired leases are reclaimable. Offline/provider failure preserves the last synchronized mailbox, reports stale state truthfully, applies bounded retry/backoff, and never reports a successful current sync.

"Every five minutes" means each enabled account becomes due on a 300-second cadence. One synchronization work run may execute for no more than ten minutes. It must checkpoint and yield rather than overlap or run indefinitely. An incomplete initial synchronization remains `running`/`incomplete`, resumes from its durable cursor, and never truncates the mailbox or reports completion early. The scheduler must fairly service all enabled accounts; one large account cannot starve the other two.

### Sent-mail transaction

Sending is a two-provider-operation workflow:

1. `email_compose` creates or updates a local pending draft/send request; it does not transmit.
2. The Voice agent summarizes recipients, subject, and the intended action and obtains explicit user confirmation.
3. The runtime creates a single-use, caller-owned approval/action id bound to the exact sender account, recipients, subject, body hash, and attachment set.
4. `email_send_pending` accepts only the pending draft ID and exact content hash as model arguments. Approval comes separately from the trusted native Voice transcription context, never from a model-created boolean or phrase.
5. SMTP transmits the message with a stable generated Message-ID.
6. The exact MIME message is appended to the resolved IMAP Sent folder.
7. Local state records SMTP and Sent-append outcomes independently so a successful send with failed append is never resent automatically.
8. A failed append is retried idempotently by Message-ID and appears as degraded Sent parity, not as a failed SMTP send.

### Attachment boundary

Attachment metadata is synchronized for every message. Attachment bytes are not downloaded eagerly. `email_read_attachment` explicitly fetches the selected attachment through the bounded provider path, enforces configured size/type limits before materialization, stores no secret-bearing provider URL, and returns a truthful unavailable/too-large/unsupported result. The contract does not claim offline attachment availability.

## Voice Mail tool contract

The first-party Mail plugin registers only the following candidate tools. Final schemas are frozen from the donor definitions after removing hosted scope fields and adding an explicit `mailAccountId` where ambiguity exists.

### Read-only tools

| Tool | Runtime target | Function |
|---|---|---|
| `email_account_status` | `email.account_status` | List configured accounts and truthful sync freshness without secrets. |
| `email_list_folders` | `email.list_folders` | List locally synchronized folders for one account. |
| `email_check` | `email.check` | Return a bounded recent local-mail summary. |
| `email_get_unread` | `email.get_unread` | Return bounded unread messages from the local synchronized store. |
| `email_search` | `email.search` | Search synchronized local messages by sender, recipient, subject, body text, date, account, and folder. |
| `email_read` | `email.read` | Read one synchronized message by stable local id. |
| `email_read_attachment` | `email.read_attachment` | Read one approved attachment subject to the attachment decision and size/type limits. |
| `email_contact_lookup` | `email.contact_lookup` | Derive bounded address suggestions from synchronized mail without creating the Contacts domain. |

### Allowed side-effect tools

| Tool | Runtime target | Function and guard |
|---|---|---|
| `email_mark_read` | `email.mark_read` | Queue and confirm a real IMAP Seen flag. |
| `email_mark_unread` | `email.mark_unread` | Queue and confirm removal of the IMAP Seen flag. |
| `email_compose` | `email.compose` | Create/update a local pending draft only. |
| `email_send_pending` | `email.send_pending` | Send only an exact pending request after a strictly later, explicit affirmative user utterance in the same Voice session. |
| `email_archive` | `email.archive` | Move a selected message to the resolved archive folder; never resolves Archive to Trash. |
| `email_move_message` | `email.move_message` | Move a selected message to an explicit non-trash destination folder. |
| `email_create_folder` | `email.create_folder` | Create an explicitly named folder under the normal Voice action policy. |
| `email_rename_folder` | `email.rename_folder` | Rename an explicit non-special folder under the normal Voice action policy. |

### Tools that must not exist

The runtime registry, MCP list, Realtime session payload, web Agents list, dispatcher, Mail service, and provider adapter must contain none of the following or an equivalent generic escape hatch:

- `mail_delete`, `mail_trash`, `mail_expunge`, `mail_purge`, or `mail_empty_trash`;
- a generic raw IMAP command tool;
- a generic provider-action tool capable of selecting delete/trash/expunge;
- any tool that accepts an arbitrary provider target or mutation name.

Archive, move, create-folder, and rename-folder schemas must exclude Trash/Junk deletion semantics. Only send has the Build 7 mandatory exact-draft confirmation protocol. A provider that cannot perform an allowed archive or move without a delete or expunge operation is unsupported for that action; it must fail closed. Copy-plus-delete fallback is prohibited.

The implementation must include a source-level boundary check that searches the registered Mail tool definitions and dispatcher targets for forbidden deletion semantics. A denial test is necessary but insufficient: the capability must be absent, not merely rejected after exposure.

## Web-search tool contract

The donor path is retained conceptually:

```text
canonical tool definition (`web_search`, target `web.search`, closed query schema)
  -> runtime tool catalog and grant filter
  -> Voice Realtime function-tool call
  -> local MCP/session dispatcher
  -> OpenAI Responses web-search adapter
  -> bounded answer, sources/citations, provider metadata
  -> Voice follow-up response
```

The tool schema contains one required non-empty `query` and rejects additional properties. Guidance tells Voice to use it for current, uncertain, or time-sensitive public information and to announce the research action naturally. Results must retain source title/URL information sufficient for the Voice response to cite or identify sources. Provider errors, unavailable credentials, timeouts, malformed results, and unsupported access paths fail truthfully.

The donor also has `web_fetch_url`; this contract does not add it unless the owner explicitly expands the requested web-search scope. `web_search` is not implemented as arbitrary browser automation, direct unrestricted URL fetching, or a new search-provider abstraction.

The donor implementation uses an OpenAI Responses request with a provider-native `web_search` tool. The owner requires the R1 tool to work through both existing OpenAI access paths. Platform execution uses the configured Platform credential and standard Responses endpoint. Subscription execution must reuse the donor-proven ChatGPT/Codex Responses transport and authorization behavior through the existing provider adapter; it must not silently substitute a Platform credential. Each path requires its own positive, revoked-credential, unsupported-model, timeout, and provider-denial proof.

## Runtime-owned Agents tool-list API

The future overhauled management Agents page will consume a support-safe projection such as:

```json
{
  "name": "email_search",
  "displayName": "Search mail",
  "description": "Search synchronized mail on this R1.",
  "capability": "mail",
  "effect": "read",
  "available": true,
  "enabled": true,
  "stateReason": null
}
```

The projection is derived from the same canonical runtime registry used to build the Realtime/MCP tool definitions. It may add display metadata but cannot change the executable name, target, input schema, effect classification, grant, or availability. Mail tools report unavailable until at least one enabled account has usable encrypted credentials and a valid local store. `web_search` reports unavailable when its selected access path lacks usable authorization.

Contract 07 implements the projection and mutation APIs but no page or controls. The future website may enable/disable a capability or approved per-tool grant only through authenticated, CSRF-protected management routes. A hidden or unchecked row is not sufficient enforcement; the runtime grant filter controls the actual session payload and MCP dispatcher.

## Standards-based extension boundary

### Agent Skills

- A Skill is a directory whose required `SKILL.md` has valid YAML frontmatter and Markdown instructions.
- Required `name` and `description` constraints follow the official Agent Skills specification.
- Optional `scripts/`, `references/`, and `assets/` remain optional and are contained beneath the Skill root.
- Skill metadata is discovered first; full instructions and referenced resources load progressively only when activated.
- Experimental `allowed-tools` is not treated as a runtime permission grant. Runtime grants remain an explicit ReSono security decision.

### Agent Plugins 1.0.0

- A Plugin is a directory with required root `plugin.json`.
- Optional Skills are discovered only from `skills/*/SKILL.md`.
- Optional MCP configuration is discovered only from root `mcp.json`.
- Missing optional component locations are accepted.
- An invalid component disables/skips that component without silently validating it or necessarily invalidating independent valid components, as required by the specification.
- `plugin.json` and `mcp.json` must target the same supported canonical schema version.
- Resolved paths, executable paths, working directories, and referenced files must remain contained under the plugin root; writable state uses a separate install-owned data directory.
- Only supported MCP transports are activated. Failed start, connect, authentication, or handshake remains an explicit component failure.

### Local lifecycle

```text
receive package
  -> immutable quarantine
  -> bounded safe extraction
  -> standard schema/structure validation
  -> containment and secret scanning
  -> requested-permission evaluation
  -> owner grant
  -> immutable installed revision
  -> atomic active pointer
  -> enable/disable/use
  -> rollback pointer or remove
```

Configuration edits create immutable revisions. Activation atomically moves an active pointer only after validation. A failed activation preserves or restores the last-known-good revision. Disabling/removing the Mail plugin revokes agent access but preserves configured Mail accounts and synchronized Mail data unless the owner separately performs the explicit management account-removal action.

## Donor research: exact start-to-finish behavior

All paths below are relative to the read-only donor root:

`/home/christian/Documents/Projects/ReSono-Labs-Voice/project-3d3354dadcad/workspace`

The observed repository revision recorded by the project donor map is `0f3b34223f745920e79d1d9db301f3b639d08393`, with owner changes present. Exact content hashes must be captured immediately before any copy; the revision alone does not identify dirty donor content.

### Mail setup and credential intake

1. `app/vault_runtime/provider_credentials.py` validates scoped provider credential payloads. Its Mail validation requires email address plus IMAP/SMTP host, username, and password fields.
2. `app/vault_runtime/email_service.py::connect_mailbox` parses credentials, validates the provider connection, establishes the mailbox record, derives a provider credential id from provider kind and mailbox id, and stores a scoped credential payload.
3. The donor store is account/workspace scoped and designed around a Vault private-data boundary. That ownership model is useful, but the standalone R1 cannot copy its storage assumption: Contract 07 uses one-device account ids, SQLite ciphertext envelopes, and Android Keystore key ownership.
4. The donor status result says credentials are stored locally and never returns the secret payload. Contract 07 retains write-only secrets and support-safe status.

### Scheduled synchronization

1. `app/vault_runtime/config.py` sets `email_sync_interval_seconds=300`, a credential work limit, and `max_email_sync_messages_per_credential=25`.
2. `app/vault_runtime/worker.py::_process_email_sync` runs from the worker loop, obtains the Mail sync store, and calls `VaultEmailService.sync_due_mailboxes` with the configured interval and page size.
3. `email_service.py::sync_due_mailboxes` calculates the due threshold, asks the canonical store for candidates, and invokes `sync_mailbox` for each.
4. `sync_mailbox` claims the mailbox to prevent overlapping work and records an explicit sync run.
5. `_sync_claimed_mailbox` decrypts/loads the scoped credential, opens one provider sync session, lists remote folders, upserts folder state, and calls `_sync_folder` for each folder.
6. `_sync_folder` pages provider messages, normalizes messages/attachments, stores them, and advances folder progress. Completion and failure are recorded separately.
7. Contract 07 retains the interval, claim, run, folder loop, bounded page processing, and durable status pattern. It strengthens completion: the 25-message donor page size cannot become a latest-25 product limit, and every folder must reach a durable complete cursor.

### IMAP/SMTP provider behavior

1. `app/vault_runtime/email_provider.py` uses Python stdlib `imaplib`, `smtplib`, and `email` MIME parsing/composition.
2. Provider connection runs host validation before IMAP or SMTP access and uses configured TLS modes and timeouts.
3. `sync_session` reuses a bounded IMAP connection for the synchronization pass.
4. Folder listing, UID-based listing/fetch, RFC-822 parsing, HTML-to-text conversion, attachment metadata/content handling, read/unread flag mutation, search, folder operations, message movement, and MIME send are implemented in separate provider methods.
5. Send transmits through SMTP and `_append_sent_copy` appends the sent MIME message to IMAP Sent. Contract 07 retains this behavior and adds durable partial-outcome/idempotency requirements.
6. The provider contains archive, move, create-folder, and rename-folder operations. They are reviewed but excluded from this contract's Voice tools.

### Canonical Mail storage

1. `app/vault_runtime/email_store.py` owns scope-bound mailbox, folder, message, attachment, send-request, sync-candidate, claim, run, and search/read operations.
2. Stable deterministic identifiers prevent duplicate local records when the same provider object is observed again.
3. The service reads from this canonical local store for ordinary Voice queries rather than treating each question as a new provider fetch.
4. Contract 07 ports the ownership pattern to focused SQLite repositories under `runtime/resono_runtime/mail/` and `runtime/resono_runtime/storage/`; it does not copy Vault account/workspace or PostgreSQL infrastructure.

### Mail tools and dispatch

1. `app/vault_runtime/signals/email/session_tools.py` defines separate read and side-effect tool-name sets.
2. The handler routes account status, folder listing, search/unread/check/read, attachments, and contact lookup to the canonical Mail service/store.
3. Side effects route through a distinct adapter path. Sending requires a caller-owned provider action id rather than allowing the model to transmit arbitrary content directly.
4. `app/vault_runtime/session_tools/email_adapters.py` binds tool targets to cache/read or side-effect handlers with canonical metadata.
5. `app/vault_runtime/session_tools/runtime.py` holds registry ownership and dispatch selection. Tool exposure and execution therefore share authoritative names/targets rather than relying on UI strings.
6. The donor exposes 25 approved email targets and includes archive/folder/move behavior. Contract 07 deliberately ports only the 16 tools listed above and implements no delete-equivalent target.

### Realtime tool-list construction

1. `app/contracts/internal/browser_voice_tools.py` owns shared `ToolDefinition` builders with tool name, description, function transport, dotted runtime target, and closed JSON input schema.
2. `app/modules/inference_runtime/realtime_session_builder.py` collects base tools and active capability tools, filters tools by real mode/capability state, removes duplicate global tools, and appends canonical global definitions.
3. The resulting tool definitions enter the provider Realtime session request. The web UI is not the execution authority.
4. The standalone R1 already follows a smaller equivalent structure in `runtime/resono_runtime/providers/openai/platform.py`, `runtime/resono_runtime/mcp/server.py`, and the Android Voice MCP bridge. Contract 07 extends those owners rather than adding a parallel tool system.

### Web search

1. `app/contracts/internal/browser_voice_tools.py::web_search_tool_definition` defines `web_search`, target `web.search`, a required `query`, and `additionalProperties: false`.
2. `app/modules/inference_runtime/realtime_session_builder.py` treats `web_search` as a global foundation tool, filters duplicates, and appends the canonical definition outside build mode.
3. `app/vault_runtime/session_tools/runtime.py` maps `web_search` into the web adapter family and dispatches it independently from Mail.
4. `app/vault_runtime/session_tools/brokers/web.py` validates/runs the call, records support-safe metadata/audit information, and normalizes the tool result.
5. `app/vault_runtime/web_search_provider.py` uses an OpenAI Responses request with `tools: [{"type": "web_search", ...}]`, requests current authoritative sources, extracts the answer and citations, bounds provider responses, and returns explicit provider/failure metadata.
6. Contract 07 ports this narrow path. It does not import recipe, local-events, research-signal, browser-rendering, or general web-fetch machinery.

### Web management projection

1. The donor's `frontend/src/browser-voice/BrowserVoiceAgentsPanel.tsx` obtains catalog, installed-agent, detail, configuration, and lifecycle state from APIs; it does not define runtime-executable tools in the React component.
2. Capability detail responses carry tool counts/details, configuration fields distinguish public values from secret/write-only values, and enable/disable/install/remove operations call lifecycle APIs.
3. Dynamic private tool descriptors are returned in Browser Voice runtime route hints and the bridge fails closed when descriptor metadata is absent.
4. Contract 07 retains the server-projection rule but adapts it to the existing small static management site. Mail account forms and the Agents tool list render real runtime state only.

## Donor freeze and intended destinations

| Concern | Read-only donor source | Intended standalone owner | Retained / omitted |
|---|---|---|---|
| IMAP/SMTP transport | `app/vault_runtime/email_provider.py` | `runtime/resono_runtime/connectors/mail/{imap,smtp,mime,endpoint_policy}.py` | Retain stdlib transport, UID/MIME/TLS/host validation, flags, send + Sent append; omit delete and unselected folder mutations. |
| Mail orchestration | `app/vault_runtime/email_service.py` | `runtime/resono_runtime/mail/{accounts,messages,synchronization,actions,scheduler}.py` | Retain connect/validate/sync/send flow; adapt to three accounts, full durable sync, SQLite, Keystore envelopes. |
| Canonical store | `app/vault_runtime/email_store.py`; relevant `datastore/schema.py` | `runtime/resono_runtime/storage/mail/{accounts,messages,sync_state,actions}.py`; migrations | Retain stable ids/state/run patterns; omit Vault/PostgreSQL/account-workspace infrastructure. |
| Scheduler | `app/vault_runtime/config.py`; `worker.py::_process_email_sync` | `runtime/resono_runtime/mail/scheduler.py` | Retain 300-second cadence and bounded work; add durable resume/full-completion semantics. |
| Credential validation | `app/vault_runtime/provider_credentials.py`; scoped private-data store | `runtime/resono_runtime/mail/credentials.py`; Android credential bridge | Retain field/scope validation; replace Vault storage with Keystore-authenticated ciphertext envelope in SQLite. |
| Mail tool sets | `app/vault_runtime/signals/email/session_tools.py` | `runtime/resono_runtime/mail/tools.py` | Retain the donor's exact eight read and eight allowed-effect `email_*` definitions; omit delete and agent mail. |
| Tool adapters/registry | `app/vault_runtime/session_tools/email_adapters.py`; `session_tools/runtime.py` | `runtime/resono_runtime/tools/catalog.py`; `mcp/server.py` | Retain canonical definition/dispatch split and fail-closed grants; omit broad donor registry. |
| Web search definition | `app/contracts/internal/browser_voice_tools.py` | `runtime/resono_runtime/tools/catalog.py` | Retain exact closed query schema and target separation. |
| Web search adapter | `app/vault_runtime/web_search_provider.py`; `session_tools/brokers/web.py` | `runtime/resono_runtime/search/openai_web_search.py` | Retain Responses provider tool, citations, bounds, failures; omit general browser/web-fetch paths. |
| Realtime assembly | `app/modules/inference_runtime/realtime_session_builder.py` | `runtime/resono_runtime/providers/openai/platform.py`; provider controller | Retain canonical dedupe/filter/availability pattern; avoid donor mode/platform breadth. |
| Agent/tool management contract | `frontend/src/browser-voice/BrowserVoiceAgentsPanel.tsx`; capability detail types | management routes and runtime projection serializers only | Retain the API-projected list/config/lifecycle contract; do not change current web files in Contract 07. |
| Quarantine/extraction | `app/modules/developer_publishing/quarantine_storage.py`; `extraction.py`; `archive_detection.py`; `extraction_limits.py` | `runtime/resono_runtime/extensions/quarantine.py`; `packages.py` | Retain immutable staging, containment, bounded extraction; omit hosted review console. |
| Permission/config lifecycle | selected `skill_catalog/service.py::_evaluate_install`; `configuration.py`; agent-package config revision/pointer pattern | `runtime/resono_runtime/extensions/registry.py`; `permissions.py`; `configuration.py` | Retain permission intersection and immutable revision rollback; omit billing/entitlements/release machinery. |

## Clean ownership and dependency direction

```text
future web management
  -> authenticated management routes for setup, import, lifecycle, grants, status, and deletion
    -> mail/application services or extension lifecycle
      -> repositories / credential-envelope boundary / tool catalog
        -> SQLite, Android Keystore bridge, IMAP/SMTP, OpenAI Responses

Voice provider session
  -> runtime-owned Voice-granted tool definitions
    -> local MCP/session dispatcher
      -> Mail tools -> synchronized local Mail service/store
      -> web_search -> OpenAI Responses search adapter
```

No UI calls SQLite, IMAP, SMTP, or OpenAI directly. No provider module imports web code. No Mail repository owns scheduling, credentials, or tool schemas. Avoid `utils`, `helpers`, `common`, `manager`, or a catch-all service.

## Dependency checkpoints

1. **Freeze owner decisions and standards.** Resolve the open questions below, record exact Agent Skills and Plugins schema identifiers, and freeze this corrected `v0.2` candidate.
2. **Donor intake.** Hash exact donor files, record destinations/retained/omitted behavior/license/tests in the donor map, and prove donors unchanged.
3. **Schema and credential envelope.** Add the account/folder/message/attachment/send/sync tables and generic Keystore envelope bridge. Prove migration, three-account atomic limit, ciphertext-at-rest, rotation rollback, redaction, and removal.
4. **Provider port.** Port the narrow IMAP/SMTP behavior with host validation, TLS, folder discovery, UID fetch, MIME parsing, flags, send, and Sent append. No delete or generic raw operation.
5. **Complete synchronization.** Implement durable per-folder cursors, full initial paging, five-minute due scheduling, non-overlap leases, restart resume, incremental reconciliation, and truthful stale/error state.
6. **Canonical Mail reads.** Prove status/folder/unread/search/read/attachment/contact lookup read the SQLite synchronized store without ad hoc IMAP queries.
7. **Controlled Mail mutations.** Prove read/unread provider parity and compose/explicitly confirmed send/Sent parity. Prove forbidden mutation code and tools are absent.
8. **Runtime tool catalog.** Introduce one canonical catalog/projection and extend MCP/Realtime assembly with availability/grant filtering. Existing device and memory tools remain intact.
9. **Web search.** Port the donor Responses search adapter and citation result, then prove the owner-selected OpenAI access path physically.
10. **Management APIs, no UI.** Add authenticated Mail account setup/status APIs, Skills create/edit/validate/publish/import APIs, Plugin upload/lifecycle APIs, MCP/Connection health APIs, and the runtime-projected Agents tool-list API. Do not modify the present web interface.
11. **Standards lifecycle.** Add standard Skills/Plugins validation, quarantine, permission intersection, immutable install/config revisions, create/edit/publish/upload/install/enable/disable/remove, and rollback.
12. **First-party Mail instructional artifact.** Package and validate the bundled standards-conformant Mail Skill through the standard extension boundary without making Mail definitions, grants, accounts, or data plugin-owned.
13. **Offline attack pass.** Run the positive/negative matrix below plus Android build/boundary/package checks and donor-isolation checks.
14. **Physical acceptance.** Install one exact candidate; prove three-account behavior, complete sync with ten-minute work limits, five-minute refresh, cross-client flags, confirmed send/Sent parity, archive/move/folder operations, Voice Mail tools, absent delete, both-path Voice web search, management APIs, restart recovery, and rollback.

## Required positive tests

- Add and validate one, two, and three distinct Mail accounts; persist across runtime and device restart.
- Reject a fourth account transactionally without storing its credential.
- Inspect SQLite and exported diagnostic state to prove only authenticated ciphertext, never plaintext passwords.
- Rotate a password successfully; failed rotation retains the last working envelope.
- Discover and synchronize every selectable folder and every message from a seeded multi-folder account whose history exceeds one work page.
- Resume an interrupted initial sync from the last committed page without duplicates or false completion.
- Force a mailbox to exceed one ten-minute work window; prove the run checkpoints before the deadline, yields fairly, and resumes to eventual complete synchronization.
- Run automatic sync after 300 seconds and reflect a remotely arrived message locally.
- Reflect remote read/unread changes locally and local Voice read/unread actions in a second independent mail client.
- Search/read across accounts and disambiguate identical folders/messages using `mailAccountId`.
- Compose a draft without sending; require exact explicit approval for send.
- Archive and move messages to explicit non-trash destinations and observe the new folder state in another client.
- Create and rename an allowed folder through the normal Voice action policy and observe it in another client.
- Send once over SMTP and observe the same Message-ID in the other client's Sent folder.
- Recover a successful SMTP/failed Sent-append partial outcome without sending a duplicate.
- List the exact approved Mail tools and `web_search` through the management Agents tool-list API without adding a current web screen.
- Prove the exact same canonical names/schemas/grants drive Realtime/MCP exposure.
- Complete a physical Voice query that reads synchronized local Mail.
- Complete a physical Voice read/unread mutation and confirmed send.
- Complete physical `web_search` calls through both Platform and ChatGPT/Codex subscription access, each returning current information with source metadata and no fallback to the other credential.
- Create/edit/validate/publish a standard Skill through the API and upload/import another standard Skill.
- Upload a standard Plugin package through the API and inspect its independently discovered Skill and MCP components.
- Install a valid Skill-only plugin, MCP-only plugin, and combined plugin; activate, configure, disable, re-enable, and remove them.
- Roll back a deliberately failed configuration activation to the last-known-good revision.

## Required negative and recovery tests

- Wrong IMAP/SMTP password, revoked credential, TLS failure, invalid certificate, private/loopback/link-local host, DNS rebinding, timeout, malformed greeting, and unsupported auth.
- Fourth-account race, duplicate address with different account id, concurrent sync tick, expired lease, process kill mid-page, SQLite busy/unavailable, power loss after data commit but before cursor update, and malformed durable cursor.
- UID validity change, folder rename/removal, UID reuse, expunge observed remotely, duplicate Message-ID, malformed MIME, oversized header/body, decompression/archive bomb, attachment path traversal, and unsupported encoding.
- Attempt archive/move to Trash, Junk, a deletion alias, or a provider-resolved destructive special folder; deny before provider mutation.
- Provider unavailable for longer than one cadence; stale local data remains readable but freshness is truthful.
- SMTP rejection, ambiguous timeout, successful SMTP plus failed Sent append, duplicate retry, expired/wrong/replayed approval id, and content changed after approval.
- Cross-account message-id access, cross-account folder access, unknown local id, disabled account, removed account, and secret-field reflection.
- Confirm `tools/list`, Realtime session JSON, web Agents projection, dispatcher registry, and source boundary contain no Mail delete/trash/expunge/purge capability.
- Attempt invented tool names, arbitrary dotted targets, extra JSON properties, raw IMAP commands, and generic provider mutations; fail closed before provider access.
- Disable the bundled Mail instructional artifact while a session is live; its Skill is withdrawn while the independently granted built-in Mail tools and account data retain their truthful state.
- Web-search missing credential, unsupported access path, provider denial, timeout, malformed/citation-free result, oversized result, prompt-like page content, and query with extra fields.
- Invalid plugin manifest, mismatched schema versions, malformed optional component, traversal/symlink escape, absolute command/cwd, unsupported transport, hard-coded secret, excessive permission, failed MCP handshake, and failed activation.

## Required evidence

- Frozen contract identity and owner resolution of every open material decision.
- Exact donor revision plus per-file SHA-256 values before copying; donor-isolation proof afterward.
- Migration version and schema inventory.
- Redacted SQLite evidence showing ciphertext envelopes and no plaintext credential material.
- Offline test transcript with exact counts and named test files.
- Sync evidence from a controlled account containing more than one page, multiple folders, remote flag mutation, and restart interruption.
- Redacted provider logs proving scheduled times, pages, folder completion, partial send outcomes, and no secrets.
- Runtime tool-catalog response, MCP `tools/list`, and Realtime session tool names from the same candidate.
- Authenticated management API captures for Mail setup/status, Skills publishing/import, Plugin upload/lifecycle, MCP/Connection health, and Agents tool projection. No new web-interface capture is required or permitted in this contract.
- Physical R1 Voice transcript/tool events for local Mail read, permitted mutation, confirmed send, and web search.
- Independent-client evidence for read/unread and Sent parity.
- Exact APK path, version code, size, SHA-256, installed hash, rollback artifact, and rollback command.
- Owner acceptance. Structural/offline evidence alone cannot close this contract.

## Internal attacks and stop rules

- A latest-N cache, Inbox-only sync, or on-demand IMAP query presented as "all mail" fails.
- A scheduler configured to 300 seconds without physical repeated-sync evidence fails.
- Plaintext or reversibly encoded credentials in SQLite fail.
- A Mail delete-equivalent function anywhere in the agent execution path stops the build.
- Any current web-interface implementation is out of sequence and stops the affected work until the full web-overhaul contract.
- A webmail/message-list UI remains prohibited after that overhaul.
- A web list that hard-codes tools independently of the runtime registry fails.
- A tool displayed as available but absent from the actual Realtime/MCP grant fails.
- A send without an exact single-use approval binding fails.
- SMTP success reported as complete Sent parity before IMAP append succeeds fails.
- A valid standard Skill/Plugin that must be rewritten into a ReSono format fails.
- Donor bulk import, donor mutation, or replacement without a documented blocker fails.
- Hiding the unresolved Slice 5 physical evidence or claiming it complete because Contract 07 proceeds stops the affected acceptance claim.

## Rollback and data preservation

The accepted version-26 APK remains the product base and the accepted runtime rollback chain remains intact. Contract 07 migrations are additive. A failed candidate is replaced by the prior accepted APK/runtime release without modifying donor or image baselines.

Extension activation uses an atomic active pointer; failed revisions roll back without deleting prior packages or configuration revisions. Disabling or removing the bundled Mail instructional artifact withdraws its Skill but does not revoke independently granted built-in Mail tools, account configuration, or synchronized Mail. Removing a Mail account is a separate explicit management operation that first stops scheduling and removes the credential envelope, then removes that account's local synchronized data. No rollback operation mutates the remote mailbox.

## Exit condition

Build Contract 07 exits only when:

- its entry gates and owner decisions are closed;
- the standard Skill/Plugin lifecycle passes real install/use/disable/remove/rollback flows;
- up to three Mail accounts are securely configured with encrypted SQLite credential envelopes;
- complete every-folder synchronization and subsequent five-minute synchronization are physically proven;
- local and remote read/unread state and Sent-folder parity are physically proven with another client;
- the Voice agent uses the exact approved Mail tool set and has no delete-equivalent capability;
- `web_search` is visible in the runtime-projected Agents tool-list API and completes real Voice calls through both Platform and subscription access paths;
- the management APIs are complete while the current web interface remains unchanged pending its full-overhaul contract;
- the exact installed artifact and rollback are preserved; and
- the owner accepts the physical behavior.

Passing unit tests, rendering tool rows, or synchronizing a small recent subset cannot close the contract.

## Material Decision Gates

### BC07-MDG-01 - Mail product surface

- **Question:** Webmail/native Mail UI, or Voice-only Mail with management setup/status?
- **Authority/evidence:** Owner decision 2026-08-20; baseline no-mockup rule; Slice 6 requires a real local Mail client and agent flow.
- **Alternatives:** Webmail; native mailbox UI; Voice-only Mail plus web account setup/status; blocked.
- **Selection/function:** Voice-only Mail capability with authenticated setup/status APIs now and a future overhauled web management surface limited to account setup and truthful sync status. The local service remains a real synchronized client even though messages are consumed through Voice tools.
- **Counterexample:** The browser displays message lists, or Voice answers through ad hoc IMAP without a synchronized local mailbox.
- **Dependents:** Web routes/UI, Mail repositories, Voice tools, acceptance evidence.
- **Result:** `CONTINUE`.

### BC07-MDG-02 - Account count and credential custody

- **Question:** One mailbox, unbounded accounts, or a hard maximum of three with Keystore-backed encrypted database records?
- **Authority/evidence:** Owner decision 2026-08-20; existing R1 Keystore bridge; baseline protected-credential requirement.
- **Alternatives:** One; three; unbounded; plaintext SQLite; Keystore-only fixed fields; ciphertext envelope in SQLite with Keystore key.
- **Selection/function:** Maximum three; account metadata and authenticated ciphertext envelopes in SQLite; non-exportable encryption key in Android Keystore.
- **Counterexample:** A fourth concurrent create succeeds, a database inspection reveals a password, or losing the Keystore key silently yields usable secrets.
- **Dependents:** Schema, bridge, setup routes, sync, backup/recovery, tests.
- **Result:** `CONTINUE`.

### BC07-MDG-03 - Synchronization meaning

- **Question:** Recent cache, query-time IMAP, or complete durable synchronization every five minutes?
- **Authority/evidence:** Owner decision 2026-08-20; donor proves 300-second scheduling and paged sync but not this standalone acceptance outcome.
- **Alternatives:** Latest-N cache; Inbox only; live query; every folder/history with incremental durable sync; blocked for storage limits.
- **Selection/function:** Every discoverable folder and complete available history, paged durably; each enabled account becomes due every 300 seconds.
- **Counterexample:** Message 26 is absent because page size was treated as retention, or a remote change remains unseen after a successful due sync.
- **Dependents:** Provider, store, scheduler, status, Voice reads, physical evidence.
- **Result:** `CONTINUE`; attachment metadata sync plus explicit bounded byte fetch is owner-fixed.

### BC07-MDG-04 - Mail tool authority and deletion

- **Question:** Copy all donor tools, expose generic Mail operations, or use a narrow explicit allowlist with deletion absent?
- **Authority/evidence:** Owner prohibition on deletion; baseline least-capability and no-reinvention controls; donor split tool registry.
- **Alternatives:** Full donor set; generic raw provider tool; narrow allowlist; read-only only.
- **Selection/function:** The listed read tools plus mark-read/unread, archive, move, create-folder, rename-folder, compose, and confirmed send. Deletion has no code or tool definition, and allowed move/folder operations cannot target destructive special folders.
- **Counterexample:** A generic operation parameter can select `STORE +\\Deleted`, MOVE to Trash, or EXPUNGE even though no tool is named delete.
- **Dependents:** Catalog, MCP, Realtime, dispatcher, provider, UI, boundary tests.
- **Result:** `CONTINUE`; owner confirmed all listed non-delete mutations.

### BC07-MDG-05 - Tool-list ownership

- **Question:** Hard-code the web list, derive it from package manifests, or project the canonical runtime registry?
- **Authority/evidence:** OD-02 clean ownership; OD-06 runtime-reported availability pattern; donor Realtime builder and Browser Voice API projection.
- **Alternatives:** UI registry; manifest registry; runtime registry plus support-safe projection.
- **Selection/function:** One runtime catalog owns definitions and grants; web, MCP, and Realtime consume projections/definitions from it.
- **Counterexample:** Renaming a UI row leaves the actual tool unchanged, or a disabled UI row remains callable.
- **Dependents:** Agents page, MCP, Realtime, plugins, tests.
- **Result:** `CONTINUE`.

### BC07-MDG-06 - Web-search implementation

- **Question:** Donor Responses web search, arbitrary web fetching/browser automation, or a new provider abstraction?
- **Authority/evidence:** Owner decision to add `web_search`; donor canonical tool/adapter; smallest-scope controls.
- **Alternatives:** Donor Responses tool; raw HTTP/browser; multiple search providers; defer.
- **Selection/function:** Port the narrow OpenAI Responses `web_search` tool path with source metadata and truthful failures through both Platform and ChatGPT/Codex subscription authorization, with no cross-path fallback.
- **Counterexample:** The tool returns uncited model knowledge without executing search, or the website performs the search itself.
- **Dependents:** Access credentials, tool catalog, dispatcher, Realtime, UI, physical evidence.
- **Result:** `CONTINUE`; owner requires both access paths.

### BC07-MDG-07 - Extension format

- **Question:** One proprietary combined manifest, separate unrelated systems, or Agent Plugins containing optional standard Agent Skills and MCP configuration?
- **Authority/evidence:** OD-10; Agent Skills specification; Agent Plugins 1.0.0 specification and schemas.
- **Alternatives:** ReSono format; Skills only; Plugins only; standards-compliant composable support.
- **Selection/function:** Validate Skills directly and Plugins through required `plugin.json` plus optional fixed-location `skills/` and `mcp.json` components.
- **Counterexample:** A valid Skill-only or MCP-only plugin is rejected because an absent optional component is required.
- **Dependents:** Validator, quarantine, lifecycle, Mail plugin, web controls, tests.
- **Result:** `CONTINUE` subject to freezing exact schema identifiers in Checkpoint 1.

## Owner resolutions recorded 2026-08-20

1. Voice may mark messages read and unread.
2. Voice may archive/move messages and create/rename folders through the normal Voice action policy and the absolute no-delete/no-trash/no-expunge boundary. Only send requires the Build 7 exact-draft confirmation protocol.
3. Voice may compose and send after donor-style exact explicit confirmation.
4. Synchronize all messages and attachment metadata; fetch attachment bytes only on explicit request.
5. `web_search` must work through both ChatGPT/Codex subscription and OpenAI Platform access.
6. Each synchronization work run has a hard ten-minute limit, durable checkpoint, fair yield, and later resume until complete.
7. Explicit management account removal immediately removes its local synchronized data and encrypted credentials after stopping account work; remote Mail is untouched.
8. Contract 07 implements code and authenticated APIs first. It does not implement web UI before the required full overhaul.
9. Standard Agent Skills and Agent Plugins are mandatory. Users may create/edit/validate/publish Skills and upload/import Skills and Plugins through the eventual management experience; Contract 07 supplies the runtime and APIs.

## Voice-first drift review - 2026-08-20

**Review status:** Internal contract correction based on owner direction and read-only donor evidence. It does not accept this draft, advance an active gate, or add Calendar, Contacts, or Reminders implementation to Build 7.

### Frozen user-facing execution boundary

The platform is Voice-first. A user asks, reviews information, approves an action, and receives the result through the native Realtime Voice session. The web management API is an authenticated administrative control plane only: it configures accounts/connections, imports and publishes standards artifacts, manages grants/lifecycle, exposes truthful status, and performs explicit local removal. It never invokes an agent tool, reads Mail content, composes Mail, or confirms a send.

The existing Agents SDK text runner remains part of the accepted earlier platform implementation. Build 7 does not turn it into a second personal-data or extension-execution product surface. It receives no newly introduced Mail, imported-MCP, Skill activation, or `web_search` grants. This preserves the accepted text capability without competing with the Voice product.

### Material findings and corrections

| Finding | Authority/evidence | Classification | Contract correction |
|---|---|---|---|
| User-facing execution was described in several places as shared between text and Voice. | Owner clarification that the whole platform is Voice-first; donor Browser Voice bridge forwards Realtime function calls to the runtime. | Correction | New Build 7 tools execute only from trusted Voice session context. The management projection is non-executing; existing text behavior is not expanded. |
| Early tables used new `mail_*` names even though the required donor sets are `email_*`. | `app/vault_runtime/signals/email/session_tools.py`; `session_tools/email_adapters.py`. | Correction | The canonical Build 7 names and dotted targets are the donor's exact `email_*` names. No alias layer is introduced. |
| One early move rule allowed copy-plus-delete. | Owner prohibition on any Mail delete code; donor adaptation must not weaken it. | Correction | A server that needs delete/expunge to archive or move is unsupported for that action. No copy-plus-delete fallback is written. |
| Earlier wording made Mail tool ownership sound plugin-owned. | Owner taxonomy: Domain owns data and built-in tools; Plugin is a distribution container. | Correction | The built-in Mail domain registers Mail definitions and handlers. A bundled Mail Plugin may supply a standard Skill only and never owns or grants Mail tools/data. |
| Backend Calendar/Contacts capabilities could be mistaken for approved Voice scope. | Donor session adapters and brokers, summarized below; Slice 7 remains the governing implementation slice. | Scope control | Build 7 defines the shared Voice/catalog/approval boundary only. It does not implement Calendar, Contacts, or Reminders. |

### Donor Voice behavior informing the next personal-data slice

These are read-only findings from `/home/christian/Documents/Projects/ReSono-Labs-Voice/project-3d3354dadcad/workspace/`. They are not Build 7 authorization and must be revalidated against the active contract before any later implementation.

| Domain | Donor Voice path | Proven Voice behavior | Boundary to preserve later |
|---|---|---|---|
| Contacts | `app/vault_runtime/session_tools/brokers/contacts.py`; builtin definitions in `app/modules/skill_runtime/builtins.py` | `contacts_search`; `contacts_prepare_save` then `contacts_confirm_pending` for create/update/delete; private contact-field use is separately prepared/confirmed. | Mutations are staged and tied to a Voice session. Do not let an untrusted model boolean be the approval authority. Contact deletion is a later Slice 7 decision, not a Mail exception. |
| Calendar | `app/vault_runtime/session_tools/calendar_adapters.py`; `calendar_provider.py`; `calendar_sync.py` | Voice exposes `calendar.check`, `calendar.read_day`, `calendar.search`, `calendar.read_event`, and confirmed `calendar.create`. The provider also has update/delete internals that are not exposed by that Voice adapter. | A domain backend capability does not automatically become a Voice tool. ICS/CalDAV are connectors to a Calendar domain, not Plugins. |
| Reminders | `app/vault_runtime/session_tools/reminders_adapters.py`; `handlers/reminders.py`; `reminder_delivery.py` | Voice exposes create/list/cancel through route grants. | Future Reminder tools enter the same Voice catalog and grant boundary; management remains setup/status only. |

**MDG-08 - Voice execution surface:** Owner direction selects native Voice as the only new Build 7 execution surface. The rejected alternatives are web invocation and a new text-agent extension surface. Counterexample: a management route can call `tools/call`, a web page can approve a pending send, or a new Mail/imported tool appears in the text runner. Dependents: Tool Catalog, MCP server, Realtime assembly, Android invocation context, management route groups, acceptance evidence. **Result:** `CONTINUE` as an owner-directed correction; full contract acceptance remains open.

## Repository integration blueprint and implementation handoff

This section is authoritative over earlier conceptual examples in this contract. It records the result of reviewing the current R1 source tree, the accepted repository boundary checks, the donor implementation, and the published Agent Skills, Agent Plugins, and MCP specifications. If an earlier example uses a generic `manager.py`, implies a web Mail client, lets a plugin own domain data, or suggests a second tool path, this section controls instead.

This is still a draft future contract. It does not change the active gate recorded in `GROUNDING-BASELINE.md`, does not declare Build Contract 05 or any intervening contract complete, and does not authorize implementation before its dependencies are accepted.

### Product intent for an open-source, owner-customizable R1

Build 7 must leave a clear home and a public lifecycle for every customizable concern. A contributor must be able to locate a capability by noun, and a future management UI must be able to use the same APIs as any other client. Customization is not permission bypass and is not arbitrary code injection.

The supported import model is:

| User intent | Accepted artifact or configuration | Runtime owner | Deletion action |
|---|---|---|---|
| Create or import agent instructions | Standards-conformant Agent Skill directory/archive with `SKILL.md` | Skill Catalog | Delete the standalone skill and all inactive revisions |
| Import a distributable extension | Agent Plugins 1.0.0 package with root `plugin.json`, optional `skills/`, and optional `mcp.json` | Plugin Lifecycle | Uninstall the plugin and withdraw all contributed components |
| Connect an external tool server | Explicit MCP endpoint configuration, or an MCP definition contributed by a standard plugin | MCP Connections | Delete the connection and withdraw all of its discovered tools |
| Inspect or grant a tool | Tool Catalog projection discovered from built-in code or MCP | Tool Catalog and Tool Grants | Disable a binding, or remove its owning import/connection; never mutate an installed package silently |
| Connect a Mail account | Mail connection configuration plus a Keystore-sealed credential envelope | Connections and Mail | Delete local Mail data and the encrypted credential immediately; never change remote mail |
| Import an R1 Creation | Static Creation ZIP/TAR with root `index.html`, plus R1 compatibility declaration | Creation Catalog | Delete the immutable artifact, its scoped storage/envelope, and its Card entry; never delete other domains |

The later web interface may present simple `Import`, `Publish`, `Enable`, `Disable`, `Rollback`, and `Delete` actions. Build 7 implements authenticated management APIs first. The sole owner-authorized UI exception is the final-subphase Creation Catalog: it is added only when wired to the real Creation lifecycle and Cards host, never as a disconnected control.

An individual MCP tool is normally discovered, not uploaded as executable source. A future web action labelled `Import tools` must route either to the Agent Plugin importer or to MCP connection setup. Build 7 must not invent a ReSono tool-package format and must not accept arbitrary Python, shell, JavaScript, APK, or native executable uploads as tools.

### Current repository findings that constrain the design

The current product already has a coherent physical spine. Build 7 extends it rather than constructing a parallel platform:

1. `runtime/resono_runtime/application.py` is the only Python composition root. It constructs storage, provider, agent, MCP, memory, event, and HTTP owners. Every Build 7 repository, catalog, lifecycle, connector, scheduler, and route group must be constructed there and passed explicitly to its consumers.
2. `runtime/resono_runtime/entrypoint.py` owns the singleton runtime and process lock. Build 7 adds no process and no second entrypoint.
3. `android/runtime-host/.../RuntimeService.java` remains the one sticky foreground supervisor. It starts the local management HTTPS server and embedded Python through `RuntimePythonHost`. Build 7 adds no Android service, worker process, or independent daemon.
4. `android/runtime-host/build.gradle.kts` packages `runtime/` directly as the Chaquopy source tree. First-party Python and bundled extension artifacts therefore live under `runtime/`; installed and user-authored artifacts live under the configured runtime workspace, not in the APK source tree and not in `web/`.
5. `runtime/resono_runtime/api/http_server.py` owns loopback HTTP mechanics and bearer authentication only. `runtime/resono_runtime/api/routes.py` is already a large dispatcher. Build 7 must extract responsibility-specific route groups and make `RuntimeRoutes` delegate to them rather than adding hundreds of conditionals to one file.
6. `android/runtime-host/.../ManagementRuntimeProxy.java` uses an explicit route allowlist and route-specific timeouts. Every new browser-facing management endpoint and upload limit must be deliberately proxied. A wildcard `/v1/management/*` pass-through is prohibited.
7. `android/runtime-host/.../ManagementHttpsServer.java` remains the TLS/static-asset host. Because this contract adds APIs only, it receives no Build 7 product UI and no Mail browsing route.
8. `runtime/resono_runtime/mcp/server.py` is the existing local MCP Streamable HTTP server. It currently hard-codes `get_device_status` and optionally `memory_lookup`. This is the one model-facing boundary to generalize; it must not be replaced with another local tool protocol.
9. `runtime/resono_runtime/agents/runner.py` currently constructs the Agents SDK MCP client with a hard-coded `get_device_status` allowlist. `runtime/resono_runtime/providers/openai/platform.py` separately constructs Realtime function definitions. Those two lists are duplicated authority today and must both become projections of one Tool Catalog.
10. Native Voice is already name-agnostic. `VoicePageView` forwards the Realtime function name and arguments, and `RuntimeVoiceClient` invokes local MCP `tools/call`. Mail-specific dispatch does not belong in Android. Android changes are limited to trusted invocation/approval context and existing generic transport behavior.
11. `runtime/resono_runtime/providers/openai/access.py` is the platform-wide authority for Platform API key versus ChatGPT/Codex subscription access and base URL. `web_search` must call this resolver on every invocation. It must not read credentials, environment variables, or selection state independently.
12. `runtime/resono_runtime/agents/sdk_runner.py` is the one OpenAI Agents SDK execution path. Skills, imported tools, Mail, and web search must enter the existing agent through instructions and the local MCP server; no second agent loop is allowed.
13. `RuntimeCredentialStore.java` already uses Android Keystore AES-GCM, record-name AAD, and a versioned ciphertext envelope, but it persists fixed OpenAI records in device-protected SharedPreferences. Mail and MCP credentials must reuse the cryptographic implementation while returning a sealed envelope to Python for SQLite persistence. Raw Mail or MCP secrets must not be copied into SharedPreferences.
14. `runtime/resono_runtime/storage/database.py` currently owns migrations through schema version 5. Build 7 is too large to continue placing every DDL statement inline. Versioned immutable migration modules are required.
15. `android/scripts/check_boundaries.sh` rejects `utils`, `helpers`, `common`, `manager`, and `managers` paths. Conceptual phrases such as “Plugin Manager” and “MCP Manager” are allowed in architecture discussion, but source owners must use precise names such as `plugins/lifecycle.py`, `mcp/connections.py`, and `tools/catalog.py`.
16. The same boundary script rejects future Hermes, A2A, External AI, and hosted-platform work. None enters Build 7.
17. `android/scripts/check_runtime_package.sh` verifies the embedded runtime and required native dependencies. It must be extended to prove that pinned extension schemas and any new pure-Python parser dependency are present in the APK.
18. The current management route request helper defaults to small JSON bodies. Archive import requires a bounded raw-body upload path; base64 archives inside JSON are not the canonical API.
19. Current tests mirror runtime concerns under `tests/runtime/`. Build 7 follows that convention and adds focused files rather than one contract-wide test file.
20. There is no existing Skill Catalog, Plugin Lifecycle, outbound MCP connection owner, generic Tool Catalog, Connections domain, Mail domain, or Mail scheduler in this repository. They are new explicit owners, not aliases around hidden existing behavior.

### Frozen dependency direction

The implementation must preserve this one-way flow:

```text
entrypoint
  -> application composition
      -> management route groups
      -> agent runners / OpenAI provider
      -> local MCP server
      -> Skill Catalog
      -> Plugin Lifecycle
      -> MCP Connections
      -> Tool Catalog + Tool Grants + Invocation Policy
      -> Connections
      -> Mail domain + Mail scheduler
      -> storage repositories
          -> SQLite

Plugin Lifecycle
  -> Skill Catalog for discovered skills
  -> MCP Connections for mcp.json entries

Native Realtime Voice
  -> the permission-filtered local MCP tool projection for all Build 7 personal-data, imported-tool, Skill, and web-search execution

Existing Agents SDK text runner
  -> remains unchanged for its accepted Build 5 responsibilities; Build 7 does not grant it Mail, imported MCP, Skill activation, or web-search execution

Mail domain
  -> IMAP/SMTP connectors
  -> Mail storage repositories

Connections
  -> generic Keystore envelope bridge
  -> encrypted envelopes stored in SQLite
```

Forbidden dependency directions are:

- domains depending on plugins;
- connectors depending on agents;
- plugins owning canonical Mail or other personal data;
- Android presentation owning tool definitions or Mail rules;
- route modules containing domain behavior;
- imported packages reading the credential database;
- provider adapters deciding permissions;
- a Skill or `allowed-tools` value granting a tool;
- direct remote MCP registration into only one agent surface; and
- direct invocation of user-supplied scripts or subprocesses.

### Exact persistent filesystem layout

`RuntimeConfig.workspace_path` remains the trusted root for mutable artifact files. Build 7 adds explicit derived paths and creates them in `RuntimeConfig.prepare_directories()`:

```text
<runtime-root>/workspace/
  creations/<creation-id>/<revision>/
  creation-data/<creation-id>/
  skill-drafts/<skill-id>/<revision>/
  skills/<skill-id>/<revision>/
  plugins/<plugin-id>/<revision>/
  plugin-data/<plugin-id>/
  extension-staging/<operation-id>/
  extension-quarantine/<operation-id>/
```

Rules:

- SQLite is the canonical registry and active-revision authority; directory names are opaque stable IDs, not trusted manifest names.
- Published skill and installed plugin revisions are immutable. Editing creates a new revision and atomically switches the database active pointer only after validation.
- Staging and quarantine are outside active roots. A failed edit or update cannot overwrite the active revision.
- Quarantine records retain an inventory, content hashes, validation findings, provenance, and failure reason. They contain no decrypted credential.
- Package paths, symlinks, hardlinks, junction-like entries, duplicate paths, absolute paths, `..`, backslashes, excessive depth, nested archives, and extraction-size violations are rejected before activation.
- Plugin-owned cache/configuration may live only under `plugin-data/<plugin-id>/`. Plugins never place data in Mail tables or another domain root.
- Creation artifacts are immutable under `creations/<creation-id>/<revision>/`; Creation-scoped plain data lives only under `creation-data/<creation-id>/`. Secrets use a Creation-scoped Keystore envelope record and never enter the artifact directory.
- Account removal has no attachment-blob cleanup problem because background Mail synchronization stores attachment metadata only and explicit attachment reads do not persist bytes by default.

First-party standards-conformant artifacts that must ship in the APK live under:

```text
runtime/resono_runtime/plugins/bundled/<plugin-name>/plugin.json
runtime/resono_runtime/plugins/bundled/<plugin-name>/skills/<skill-name>/SKILL.md
```

The first-party Mail plugin may teach Mail use, but the Mail database, connectors, scheduler, credentials, and tools remain built-in domain capabilities. Disabling or removing its instructional component must not remove Mail accounts or messages.

### Database migrations and canonical records

Add `runtime/resono_runtime/storage/migrations/` with an ordered runner called by `RuntimeDatabase.migrate()`. Existing schema versions remain unchanged. Build 7 uses two reviewable migrations:

- `v006_extensions.py`: skills, skill revisions, plugins, plugin revisions/components, MCP server records, tool projections, tool grants, connections, credential envelopes, import operations, quarantine findings, and invocation/approval records.
- `v007_mail.py`: Mail accounts, folders, messages, addresses/recipients, attachment metadata, synchronization cursors/checkpoints, pending sends, and send receipts.
- `v008_creations.py`: Creation records/revisions, compatibility declarations/findings, active pointers, scoped storage metadata, and Cards catalog generation.

The minimum stable identities are:

- skill ID plus immutable revision ID and content hash;
- plugin ID plus immutable revision ID and artifact hash;
- component ID linked to its owning plugin revision;
- MCP server ID linked to a plugin component or explicit connection;
- tool ID linked to source kind/source ID and a stable model-facing name;
- connection ID, kind, public configuration JSON, encrypted credential envelope, status, and last error;
- Mail account ID linked one-to-one to a Mail connection;
- Mail folder identity including server name, delimiter, special-use flags, UIDVALIDITY, and synchronization cursor;
- Mail message identity by account, folder, UIDVALIDITY, and UID, with RFC Message-ID retained as metadata rather than trusted uniqueness;
- pending action ID linked to exact immutable draft hash, caller session/turn, state, and idempotency result.

Credential plaintext is never a database column. Portable skill/plugin artifacts never contain connection secrets or grants. Tool grants and connection configuration remain runtime-owned records and are never written back into `SKILL.md`, `plugin.json`, or `mcp.json`.

Account removal is a local destructive transaction owned by the Mail account lifecycle. It first makes the connection unusable, then deletes the encrypted envelope and cascades local Mail rows. It never logs in to IMAP/SMTP and never alters remote messages, folders, or account state. Restart recovery must finish any interrupted local purge before the account can reappear.

### Concern 1: canonical Tool Catalog and invocation boundary

New code home:

```text
runtime/resono_runtime/tools/
  definitions.py
  catalog.py
  grants.py
  invocation.py
  approvals.py
```

Responsibilities:

- `definitions.py` owns one immutable `ToolDefinition` shape: stable tool ID, model-facing name, description, JSON input schema, output limit, source identity, effect class, supported agent surfaces, and handler target.
- `catalog.py` registers built-in handlers and source-owned MCP projections, rejects duplicate IDs/names, produces MCP and Realtime schemas, and withdraws every projection when its source is disabled or removed.
- `grants.py` computes effective availability as source enabled AND tool enabled AND user grant AND agent grant AND surface compatibility AND live policy/approval requirements.
- `invocation.py` validates names, JSON schema, input/output bounds, source health, trusted caller context, idempotency, and audit state before calling a registered handler.
- `approvals.py` owns short-lived, single-use approval evidence for confirmation-required effects. It never accepts a model-created boolean as proof of user approval.

Built-in tool names remain stable (`get_device_status`, `memory_lookup`, `web_search`, and the frozen Mail names). Imported MCP tools receive a deterministic model-safe namespace:

```text
mcp__<source-slug>__<remote-tool-name>
```

The catalog preserves the remote name and source metadata for display and forwarding. Namespace collisions are an install/discovery error; install order must never silently rename an existing tool.

`runtime/resono_runtime/mcp/server.py` must delegate `tools/list` and `tools/call` to the catalog/invocation owners. `tools/list` is caller-filtered; unauthorized tools are absent rather than advertised and rejected later. The MCP server continues to return standards-shaped content, structured content, and `isError`.

`runtime/resono_runtime/agents/runner.py` consumes the same catalog projection for its agent identity. Imported Skills, Plugin components, MCP tools, and Creations are filtered by the selected `voice`, `text`, or `both` audience. Built-in Mail and web search remain Voice capabilities in Build 7 unless a later contract explicitly grants them to Text. `runtime/resono_runtime/providers/openai/platform.py` serializes the effective Voice definitions from the same catalog. Native `VoicePageView` remains generic.

Imported MCP annotations are hints, not authority. Unknown imported tools begin disabled and ungranted. A management grant must record an effect class (`read`, `local_write`, `external_write`, or `destructive`) and permitted surfaces. A destructive imported tool cannot become available merely because a remote server labels it read-only.

Delete behavior:

- built-in tools are not deletable; applicable grants may be disabled;
- a tool contributed by a plugin is source-owned, so individual `DELETE` returns `409 source_owned` with the owning plugin ID; uninstalling the plugin removes it;
- a tool discovered from an explicit MCP connection is withdrawn by deleting that connection;
- disabling a single discovered binding records a local suppression without mutating the remote server or package; and
- reconnect/discovery must respect suppressions instead of silently re-enabling a removed binding.

### Concern 2: Agent Skills client and authoring lifecycle

Normative source: `https://agentskills.io/specification`, retrieved for this contract on `2026-08-20`. Implementation must pin the exact normative snapshot and record its hash/license before copying any schema/reference artifact.

New code home:

```text
runtime/resono_runtime/skills/
  specification.py
  catalog.py
  lifecycle.py
  activation.py
  resources.py
```

Responsibilities:

- `specification.py` parses YAML frontmatter and enforces the published name, description, directory-name, optional-field, and layout rules. It records but does not authorize experimental `allowed-tools`.
- `catalog.py` owns installed identity, immutable revisions, source/provenance, enablement, ownership, and compact discovery metadata.
- `lifecycle.py` owns draft creation, archive import, validation, publish, enable, disable, rollback, and delete. It uses the shared staging/quarantine behavior and never edits an active revision in place.
- `activation.py` exposes only enabled/granted name and description metadata at agent startup and loads the exact active `SKILL.md` body only when selected.
- `resources.py` reads bounded files relative to the immutable skill root, prevents path escape, and records resource provenance.

Progressive disclosure is mandatory:

1. Voice session instructions receive only enabled skill names, descriptions, and stable activation identifiers.
2. A built-in `skill_activate` local tool returns one selected revision’s instructions and resource inventory.
3. A built-in `skill_read_resource` local tool returns one bounded referenced file after root-containment and policy checks.
4. The invocation record stores the skill ID/revision and resources used.

The standard permits optional `scripts/`, but script runtime support is client-defined. Build 7 inventories, scans, preserves, and displays scripts as compatibility information; it does not execute them and does not expose Bash, Python execution, filesystem write, dependency installation, or subprocess tools. This is required because the current R1 has no accepted untrusted-code sandbox. A skill that requires script execution is installable only as `incompatible`/disabled or is quarantined according to the validation result; it is never partially executed.

The YAML dependency must be an explicit pinned runtime dependency, not a hand-written partial YAML parser presented as standards conformance. The first checkpoint must prove that the chosen pure-Python parser packages into arm64 Chaquopy; if it does not, implementation stops at a material dependency gate.

Management API contract:

```text
GET    /v1/management/skills
GET    /v1/management/skills/<skill-id>
POST   /v1/management/skills/drafts
POST   /v1/management/skills/<skill-id>/draft-revisions
POST   /v1/management/skills/<skill-id>/validate
POST   /v1/management/skills/<skill-id>/publish
POST   /v1/management/skills/<skill-id>/enable
POST   /v1/management/skills/<skill-id>/disable
POST   /v1/management/skills/<skill-id>/rollback
POST   /v1/management/skills/import
DELETE /v1/management/skills/<skill-id>
```

`Publish to R1` means validate the candidate, write an immutable revision, atomically update the active pointer, update the Skill Catalog, and emit a lifecycle event. A failed editable change is quarantined and leaves the prior active revision byte-identical and usable. A plugin-contained skill cannot be edited or deleted independently; the API reports its owning plugin.

#### Import contract 1 - standalone Agent Skills

**Normative format:** Agent Skills specification, retrieved from `https://agentskills.io/specification` on `2026-08-20`. A valid import is one Skill root directory containing exactly one required `SKILL.md`; `SKILL.md` has YAML frontmatter followed by Markdown instructions. `name` and `description` are required. `name` is 1-64 lowercase letters, digits, or hyphens, has no leading/trailing/consecutive hyphen, and equals the root directory name. `description` is non-empty and at most 1024 characters. Optional `license`, `compatibility`, string-to-string `metadata`, and experimental `allowed-tools` are parsed according to the standard but never grant ReSono permissions.

**Supported input forms:**

| Operation | Request | Accepted body | Result |
|---|---|---|---|
| Create editable Skill | `POST /v1/management/skills/drafts` | bounded JSON metadata and Markdown instruction text | Creates a private draft revision; no agent activation. |
| Add draft revision | `POST /v1/management/skills/<skill-id>/draft-revisions` | bounded JSON replacement metadata/instructions | Creates a new immutable draft revision; never edits the active revision. |
| Import Skill | `POST /v1/management/skills/import` | raw `application/zip` or `application/x-tar` containing one Skill root | Stages, extracts, validates, scans, and returns an import operation. It never activates directly. |
| Validate staged/draft Skill | `POST /v1/management/skills/<skill-id>/validate` | no arbitrary file path or command fields | Returns structured standard-validation and ReSono compatibility findings. |
| Publish Skill | `POST /v1/management/skills/<skill-id>/publish` | validated revision ID only | Atomically publishes and activates a new immutable revision. |

An archive has one top-level directory only. Its directory name must equal the standardized `name`; archives containing multiple roots, a root-level `SKILL.md`, path escapes, links, duplicate names, nested archives, encrypted archives, or size-limit violations are rejected before activation. The importer preserves allowed non-executable resources under the immutable Skill root. It inventories `scripts/` because the standard permits it, but Build 7 does not execute scripts, install dependencies, expose a shell, or make scripts available as MCP tools. A script-required Skill is reported as incompatible and remains disabled; standards conformance is not a sandbox claim.

**Stable API response shape:** every draft/import/installed revision returns `skillId`, `revisionId`, `source` (`draft` or `import`), `state` (`draft`, `validated`, `published`, `disabled`, `incompatible`, or `quarantined`), `standardName`, `contentSha256`, `findings`, `ownership`, and `allowedActions`. Read responses disclose only support-safe metadata and resource inventory, never credentials, grants, or an active Skill body unless the authenticated owner asks for that exact revision.

**Permission rule:** Skill instructions may request tools and `allowed-tools` may be displayed as compatibility metadata, but neither can create a Tool Catalog entry or elevate a grant. The Voice session sees only enabled Skill metadata; it can load an active Skill body only through the catalog-controlled `skill_activate` behavior introduced in the approved lifecycle subphase.

**Delete rule:** `DELETE /v1/management/skills/<skill-id>` deletes a standalone Skill's mutable draft and published revisions only after it is no longer the active revision or after an explicit disable transition. It returns `409 source_owned` for a plugin-contained Skill and identifies the owning Plugin. Deletion never deletes a Plugin, connection, Mail account, or canonical personal data.

### Concern 3: Agent Plugins 1.0.0 lifecycle

Normative source: `https://agent-plugins.org/specification`, published version `1.0.0`, retrieved for this contract on `2026-08-20`. The client bundles recognized schemas for offline validation and must not fetch a schema while installing.

New code home:

```text
runtime/resono_runtime/plugins/
  specification.py
  archives.py
  inspection.py
  lifecycle.py
  catalog.py
  schemas/1.0.0/plugin.schema.json
  schemas/1.0.0/mcp.schema.json
  bundled/
```

The standard package is preserved exactly: root `plugin.json`, immediate skills under `skills/`, and MCP configuration at root `mcp.json`. Unknown plugin top-level fields are reported and ignored exactly as the specification requires; ReSono does not assign them meaning. Invalid contained skills are skipped/reported at the standard’s component failure boundary. Invalid MCP entries do not silently invalidate unrelated valid components unless the normative failure rule requires full rejection.

`archives.py` adapts the donor safe-extraction behavior: ZIP and TAR support, streamed extraction, declared/actual size enforcement, duplicate rejection, no links, no encrypted ZIP, no nested archive, normalized contained paths, and exclusive file creation. Initial device limits are 16 MiB compressed input, 64 MiB total expanded data, 8 MiB per file, 512 files, path depth 16, and normalized path length 240. Any change requires a recorded device-resource decision.

`inspection.py` adapts the donor secret-pattern and dangerous-runtime scan, produces structured findings, inventories executables/scripts/licenses, and never treats scanning as a sandbox. A hard-coded credential, path escape, unrecognized schema, invalid manifest, executable MCP command, or unsupported runtime requirement prevents activation.

`lifecycle.py` implements stage, validate, inspect, install, enable, disable, rollback, and uninstall. Installation decomposes a plugin into component records:

```text
Plugin Lifecycle
  -> Skill Catalog: standards-conformant skill revisions
  -> MCP Connections: validated server definitions
  -> no direct Agent dependency
```

Agent Plugins 1.0.0 describes portable packages; it does not grant permissions, store OAuth credentials, sandbox subprocesses, or own ReSono lifecycle. Build 7 does not require a ReSono client extension in `plugin.json` for ordinary operation. If a later contract adopts `extensions.org.resono.r1`, that schema must be separately frozen and cannot replace standard fields.

Plugin `mcp.json` may contain stdio, Streamable HTTP, or legacy SSE definitions under the published schema. Build 7 supports remote Streamable HTTP as the primary active transport and legacy SSE only where the pinned MCP client dependency proves it. Arbitrary plugin-supplied stdio commands are validated and reported but remain disabled as `unsupported_untrusted_execution`; they are not launched on the R1 without a later accepted sandbox contract. This limitation is truthful client capability reporting, not a proprietary package rewrite.

Management API contract:

```text
GET    /v1/management/plugins
GET    /v1/management/plugins/<plugin-id>
POST   /v1/management/plugins/import
POST   /v1/management/plugins/<plugin-id>/validate
POST   /v1/management/plugins/<plugin-id>/install
POST   /v1/management/plugins/<plugin-id>/enable
POST   /v1/management/plugins/<plugin-id>/disable
POST   /v1/management/plugins/<plugin-id>/rollback
DELETE /v1/management/plugins/<plugin-id>
```

Disable preserves the immutable artifact, non-canonical plugin data, and connection records but withdraws all contributed skills/tools. Uninstall removes artifacts, contributed components, plugin-scoped cache/configuration, and plugin-scoped credential envelopes. It never deletes Mail or any other domain’s canonical data. Built-in plugins report `deletable: false`; they may be disabled only when doing so does not falsify a required product capability.

#### Import contract 2 - Agent Plugins 1.0.0

**Normative format:** Agent Plugins Specification `1.0.0`, with its published manifest schema `https://agent-plugins.org/schemas/1.0.0/plugin.schema.json` and MCP schema `https://agent-plugins.org/schemas/1.0.0/mcp.schema.json`, reviewed on `2026-08-20`. Build 7 recognizes only those exact schema identifiers. Schema artifacts are bundled and hash-recorded before implementation; installation never fetches a schema.

**Accepted package:** raw `application/zip` or `application/x-tar` submitted to `POST /v1/management/plugins/import`. It contains exactly one root directory with a required root `plugin.json`. The manifest is a JSON object containing required `$schema` and `name`; `name` is 1-64 lowercase letters/digits/hyphens/periods, starts/ends alphanumeric, and contains neither `--` nor `..`. Optional portable fields are `version`, `description`, `author`, `homepage`, `repository`, `license`, `keywords`, and `extensions`. Unknown top-level manifest fields are reported and ignored as the specification requires; they receive no ReSono meaning. Only an object under a reverse-domain `extensions` namespace may hold client-specific data, and Build 7 does not define one.

**Fixed component discovery:** `plugin.json` cannot redirect discovery or define inline components. A valid package may contain either or both of these optional components:

| Component | Exact fixed location | Import behavior |
|---|---|---|
| Agent Skills | immediate child directories of `skills/` that contain a regular `SKILL.md` | Each is evaluated under Import Contract 1. An invalid Skill is reported/skipped without discarding valid independent components. |
| MCP configuration | root `mcp.json` | Must have the exact MCP schema identifier and an `mcpServers` object. Each server entry is independently validated and recorded. |

Absent `skills/` or `mcp.json` is valid. A present component path with the wrong filesystem kind is invalid only for that component type. All resolved package paths must remain inside the resolved Plugin root; no absolute paths, `..`, links escaping the root, duplicate paths, encrypted/nested archives, or archive-limit violations are accepted.

**MCP component contract inside a Plugin:** `mcp.json` supports the standard closed entries `stdio` (`command`, optional `args`, `env`, `cwd`), `streamable-http` (`url`, optional string headers), and legacy `sse` (`url`, optional string headers). The package format is accepted and inspected for all three. Build 7 activates remote Streamable HTTP first; legacy SSE activates only if the pinned client proves support. Every `stdio` entry is retained as a truthful `unsupported_untrusted_execution` finding and disabled. It is never launched, given a shell, package root, credential database, `PLUGIN_ROOT`, or `PLUGIN_DATA` access beyond static validation. Secret-like headers or environment values are findings, not imported credentials; credentials are supplied later only through a separate Connection record.

**Lifecycle wire contract:**

| State transition | Endpoint | Preconditions | Result |
|---|---|---|---|
| Stage | `POST /v1/management/plugins/import` | bounded archive and authenticated caller | immutable staging record and inspection operation; no active component |
| Validate | `POST /v1/management/plugins/<plugin-id>/validate` | staged revision | structured manifest/component/containment findings |
| Install | `POST /v1/management/plugins/<plugin-id>/install` | validated revision with no activation-blocking findings | immutable installed revision plus independently recorded Skill/MCP components |
| Enable / disable | `POST /v1/management/plugins/<plugin-id>/enable` or `/disable` | installed revision | activates or withdraws only contributed components through their own catalogs |
| Roll back | `POST /v1/management/plugins/<plugin-id>/rollback` | prior validated revision | atomic active-pointer change; no in-place mutation |
| Uninstall | `DELETE /v1/management/plugins/<plugin-id>` | explicit authenticated deletion | removes package-owned artifacts/components/cache/envelopes only |

Every Plugin response includes `pluginId`, `revisionId`, `standardName`, `schemaId`, `artifactSha256`, `state`, `components`, `findings`, `ownership`, and `allowedActions`. `components` identifies each discovered Skill or MCP definition and its independent activation state. A plugin cannot create a Tool Catalog grant, read canonical Mail/Calendar/Contacts/Reminders data, or overwrite a user Connection. A source-owned tool returns `409 source_owned` on individual deletion; uninstalling the Plugin is the deletion action.

### Concern 4: outbound MCP connections and imported tools

The R1 currently acts as a local MCP server for its agents. Build 7 also makes it an MCP client for configured external servers without mixing those directions.

New code home:

```text
runtime/resono_runtime/mcp/
  server.py                 # existing local server, generalized
  client.py                 # one remote protocol client
  connections.py            # lifecycle, health, reconnect, shutdown
  discovery.py              # tools/list normalization
  forwarding.py             # validated tools/call forwarding
```

`connections.py` is deliberately not named `manager.py` because that path would fail the repository boundary check. It owns live remote sessions and deterministic shutdown. `discovery.py` converts remote MCP definitions to Tool Catalog entries but preserves source server, original name, schema, annotations, and discovery time. `forwarding.py` applies local grants and limits before any network call, then maps the result back to local MCP content.

All agent surfaces continue to connect only to `http://127.0.0.1:8765/v1/mcp`. The Agents SDK is not given remote MCP servers directly because doing so would create tools visible to text but not Voice and would bypass the canonical catalog. The local server forwards approved imported calls through the outbound client.

An explicit MCP connection record owns endpoint, transport, non-secret options, authentication reference, TLS policy, enablement, health, and source. Credentials are separate encrypted Connection data. Plugin files may use standard placeholders, but resolved values never get written back into the package.

Endpoint policy:

- HTTPS Streamable HTTP is the default.
- Redirects are bounded and each destination is revalidated.
- User-entered LAN endpoints are allowed because they are an explicit authenticated management action, not an agent-selected URL; link-local metadata destinations, multicast, unspecified addresses, and silent DNS rebinding remain denied.
- Plain HTTP is limited to loopback or an explicitly accepted same-LAN connection policy and is visibly reported as reduced transport security.
- Agents cannot add, edit, authenticate, enable, or delete an MCP connection.
- Discovery and calls have bounded connect/read deadlines and response sizes. A failed source becomes unhealthy and its tools are unavailable; there is no hidden fallback.

Management API contract:

```text
GET    /v1/management/mcp/connections
GET    /v1/management/mcp/connections/<connection-id>
POST   /v1/management/mcp/imports/preflight
POST   /v1/management/mcp/imports/confirm
POST   /v1/management/mcp/connections/<connection-id>/credentials
POST   /v1/management/mcp/connections/<connection-id>/discover
POST   /v1/management/mcp/connections/<connection-id>/enable
POST   /v1/management/mcp/connections/<connection-id>/disable
DELETE /v1/management/mcp/connections/<connection-id>

GET    /v1/management/tools
GET    /v1/management/tools/<tool-id>
POST   /v1/management/tools/<tool-id>/grant
POST   /v1/management/tools/<tool-id>/disable
POST   /v1/management/tools/<tool-id>/enable
DELETE /v1/management/tools/<tool-id>
```

The tool delete response must be truthful about whether it suppressed a standalone binding or requires removal of the owning source. It must never claim to delete a remote server capability.

#### Import contract 3 - direct MCP connections and discovered tools

**Normative protocol:** Model Context Protocol specification revision `2025-11-25`, reviewed at `https://modelcontextprotocol.io/specification/2025-11-25` on `2026-08-20`. R1 is the MCP host and client for outbound connections. It uses the MCP JSON-RPC lifecycle and capability negotiation, but Build 7 imports only server tools into the Voice Tool Catalog. It does not expose Roots, Sampling, Elicitation, remote Prompts, or remote Resources to the Voice agent in this contract.

**Accepted direct import:** `POST /v1/management/mcp/imports/preflight` accepts one bounded, industry-standard Agent Plugins 1.0 `mcp.json` document with the canonical `$schema` and `mcpServers` root. `POST /v1/management/mcp/imports/confirm` consumes its ten-minute preflight token. The R1 does not define a proprietary MCP connection import object.

```json
{
  "label": "Home Assistant",
  "transport": "streamable-http",
  "endpoint": "https://home.example.net/mcp",
  "enabled": false
}
```

`label` is support-safe display text. `transport` is `streamable-http` or, only after client proof, legacy `sse`. `endpoint` is an absolute URL. `enabled` defaults to `false`, so creating a connection cannot expose a tool. The route rejects arbitrary command, executable, shell, filesystem path, remote tool definition, unknown configuration key, inline secret, or a claim that a user-selected remote tool is already granted. A Plugin-provided `mcp.json` produces the same internal connection record with `source: plugin`; it does not get a second import path.

**Credential contract:** credentials are supplied only after a connection record exists, through `POST /v1/management/mcp/connections/<connection-id>/credentials`. The request may contain one supported credential kind and its write-only value, initially `bearer_token` or a named static header value. The runtime seals the value through the Android Keystore bridge and stores only the returned encrypted envelope in SQLite. `GET` responses return `credentialPresent` and a credential kind, never a value, ciphertext, header map, authorization URL, or provider error body. OAuth authorization is not claimed until a later accepted contract defines its redirect, PKCE, token-refresh, and revocation behavior.

**Discovery and normalization:** `POST /v1/management/mcp/connections/<connection-id>/discover` is the only action that runs `initialize`, capability negotiation, and `tools/list` against an enabled connection. It records the MCP protocol version, server identity, health, discovery timestamp, original tool name, original JSON schema, annotations, and bounded description. Remote names are normalized once to `mcp__<source-slug>__<remote-tool-name>`. A collision, malformed schema, unsupported protocol response, failed handshake, unhealthy endpoint, or output-limit violation leaves the affected remote tool unavailable; it never silently renames, falls back, or exposes the raw remote name to the model.

**Grant and invocation contract:** every discovered tool starts `disabled` and ungranted. A management grant must select an R1 effect classification (`read`, `local_write`, `external_write`, or `destructive`) and the permitted Voice surface. Remote annotations and descriptions are untrusted hints, never an effect classification or consent record. Only a granted, healthy tool appears in the Voice Realtime and local MCP projections. On a Voice call, the R1 validates the local normalized schema and limits before forwarding `tools/call`; it bounds the response, converts it into standard MCP content, and records source/tool/invocation audit metadata without secrets. The management API cannot invoke the tool.

**Lifecycle and deletion contract:**

| Action | Endpoint | Truthful result |
|---|---|---|
| Import / inspect | `POST /v1/management/mcp/imports/preflight`, `POST /v1/management/mcp/imports/confirm`, or `GET /v1/management/mcp/connections` | Imports standard `mcp.json` with exact overwrite confirmation, or returns configuration/status; no tool is granted automatically. |
| Add credential | `POST /v1/management/mcp/connections/<connection-id>/credentials` | Replaces the sealed envelope only after bounded validation. |
| Discover | `POST /v1/management/mcp/connections/<connection-id>/discover` | Records normalized candidate tools, all initially unavailable. |
| Enable / disable source | `POST /v1/management/mcp/connections/<connection-id>/enable` or `/disable` | Opens or closes the source; disable withdraws its catalog projections. |
| Grant / suppress tool | `POST /v1/management/tools/<tool-id>/grant`, `/disable`, or `/enable` | Changes only R1's local binding and never mutates the remote server. |
| Delete source | `DELETE /v1/management/mcp/connections/<connection-id>` | Closes the connection, removes its local discovered bindings and envelope, and never deletes a remote server/tool. |
| Delete tool binding | `DELETE /v1/management/tools/<tool-id>` | Returns local suppression or `409 source_owned` with the Plugin/connection deletion action. |

**Network and consent boundary:** HTTPS Streamable HTTP is the default; redirect destinations are revalidated. Same-LAN plain HTTP requires an explicit authenticated management choice and is reported as reduced security. Loopback, link-local metadata, multicast, unspecified addresses, private destinations reached through DNS rebinding, and unbounded redirects are denied. The user grants a connection and its selected tools before the Voice agent can invoke them; the Voice agent cannot add, authenticate, enable, modify, discover, or delete a connection.

### Concern 5: R1 Creations compatibility, catalog, and Cards host

**Companion design/implementation plan:** `docs/planning/2026-08-20-creations-cards-architecture.md` is authoritative for the Cards shell, Creation WebView separation, dynamic update path, SDK-global compatibility bridge, and visual/input acceptance criteria. This contract retains the lifecycle gate and repository ownership summary.

**Read-only SDK evidence:** `https://github.com/rabbit-hmi-oss/creations-sdk`, revision `62ef8b37de9c8ec74499987eeed1f07b9cfaaaf0`, reviewed on `2026-08-20`; license `MIT`. The repository is an example/static-web SDK, not an install/package specification. Its root README says only "Soon". The `plugin-demo` shows a static `index.html` with local CSS/JavaScript designed for a `240x282` viewport and expects browser globals injected by RabbitOS: `PluginMessageHandler`, `closeWebView`, `TouchEventHandler`, `window.creationStorage`, `window.creationSensors`, hardware events (`scrollUp`, `scrollDown`, `sideClick`, `longPressStart`, `longPressEnd`), and `window.onPluginMessage`. It provides no manifest, archive schema, signature model, import API, lifecycle model, or dynamic-update mechanism. No claim of an industry-standard Creation package format is therefore permitted.

The current R1 has no Cards host or Android `WebView`; `android/feature/voice/.../VoicePageView.java` only paints a non-interactive `Cards` label. A real imported Creation requires a new Cards feature, not an edit to Voice business logic.

New code home:

```text
runtime/resono_runtime/creations/
  catalog.py
  lifecycle.py
  archives.py
  compatibility.py
  assets.py
  storage.py

runtime/resono_runtime/storage/creations.py
runtime/resono_runtime/api/creation_routes.py

android/feature/cards/
  src/main/java/com/resonolabs/feature/cards/
    CardsPageView.java
    CreationWebViewHost.java
    CreationBridge.java
    CreationCatalogClient.java
    CreationInputRelay.java
```

`RuntimeApplication` composes the Creation Catalog and route group. `CardsPageView` owns Cards navigation/list state only. `CreationWebViewHost` owns a single selected Creation lifecycle and destroys it on switch/delete. `CreationBridge` is a narrow, capability-gated browser interface; it does not expose the Android context, arbitrary Java reflection, local filesystem, management bearer token, raw HTTP, or the runtime database. `CreationInputRelay` forwards only selected R1 input events to the active Creation after the Cards host, not Voice, owns that input focus. No Creation code enters `VoicePageView`.

Existing Android integration is equally specific: `android/app/.../ProductRootView.java` becomes the owner of the real two-page `Voice`/`Cards` navigation and routes `UiInputIntent` only to the visible page. `VoicePageView` stops painting a non-interactive Cards destination and retains no Creation import, rendering, input, or bridge code. `android/settings.gradle.kts` and `android/app/build.gradle.kts` add the new `:feature:cards` module; `android/feature/cards/build.gradle.kts` depends only on `:core:design`, `:core:input`, and `:runtime-host`. Android framework `WebView` is used, so no third-party browser engine dependency is added. A future implementation must use restricted WebView settings: JavaScript only for the selected local Creation origin, no file access, no content access, no mixed content, no external navigation, no service workers, no debugging in release, and a per-Creation origin/bridge lifecycle.

#### Import contract 4 - existing R1 Creations

**Accepted artifact:** raw `application/zip` or `application/x-tar` sent to `POST /v1/management/creations/import`. It is a static web artifact, not a Skill, Agent Plugin, MCP server, or executable upload. It must contain exactly one top-level Creation directory and a regular root `index.html`. Relative HTML assets may be present under that root. The import rejects missing `index.html`, multiple roots, path traversal, absolute paths, links, duplicate paths, nested/encrypted archives, archive-limit violations, service workers, native binaries, APKs, Python/shell/Node executables, and unsafe HTML asset references. The existing shared archive containment limits apply unless a dedicated device-resource decision changes them.

Because the public SDK has no manifest, R1 adds a **compatibility declaration outside the imported artifact**. The management import request supplies a support-safe `label` and one selected profile; it never rewrites the Creation or inserts a proprietary manifest into the archive:

| Profile | Browser globals/events available | Status |
|---|---|---|
| `static` | none beyond normal restricted WebView APIs | Required initial profile; static existing Creations render dynamically. |
| `local_storage` | namespaced `window.creationStorage.plain` | Requires explicit owner approval and size/quota evidence. |
| `secure_storage` | namespaced `window.creationStorage.secure` | Requires the Android Keystore envelope bridge and write-only management semantics. |
| `input_sensors` | selected wheel/PTT event dispatch and real accelerometer callbacks | Requires capability grant, foreground focus, rate limit, and physical hardware evidence. |
| `model_message` | `PluginMessageHandler` request/response bridge, response delivery through `window.onPluginMessage`, optional R1 speaker output, and explicit Creation journal record | Owner-directed compatibility profile. It must use the one existing Agents SDK execution path with a Creation-scoped no-personal-data tool projection, bounded request/response/quota policy, and Android-owned audio focus. |

All demonstrated SDK globals are required compatibility work: `PluginMessageHandler`, `window.onPluginMessage`, `closeWebView`, `TouchEventHandler`, namespaced plain/secure `creationStorage`, `creationSensors.accelerometer`, wheel/PTT events, `useLLM`, `wantsR1Response`, and `wantsJournalEntry`. Their exact R1 owners, containment rules, and no-second-agent-loop rule are defined in the companion plan. A global is not considered supported until its corresponding owner and physical evidence exist; imports report truthful per-profile compatibility state until then.

**Catalog and lifecycle wire contract:**

| Operation | Endpoint | Result |
|---|---|---|
| Import | `POST /v1/management/creations/import` | Immutable staged artifact, compatibility findings, and no active Card until validation/install. |
| List/inspect | `GET /v1/management/creations` and `GET /v1/management/creations/<creation-id>` | Support-safe Creation Catalog: label, revision, profile, state, dimensions/asset inventory, findings, and allowed actions. |
| Install/enable/disable | `POST /v1/management/creations/<creation-id>/install`, `/enable`, or `/disable` | Atomically changes the active revision/catalog generation. Enable makes one real Card entry available. |
| Delete | `DELETE /v1/management/creations/<creation-id>` | Disables it, invalidates its Card route, destroys an active host, removes immutable artifacts/scoped data/envelopes, and increments catalog generation. |
| Native Cards catalog | `GET /v1/cards/creations` | Loopback-native, authenticated runtime projection of enabled Creation cards only; it never exposes management actions or an archive. |

The final web Creation Catalog is an owner-authorized management UI exception: it renders the above real API state and invokes only real import/inspect/enable/disable/delete operations. It does not embed or run Creation content. The native Cards page is the only execution/rendering surface for a Creation.

#### Dynamic update and restart decision

No R1 reboot or runtime process restart is required for import, enable, disable, update, or delete. This is feasible because artifacts live under the mutable runtime workspace and the active revision is an SQLite pointer:

1. Import stages and validates a new immutable revision outside the active root.
2. Install/enable atomically changes the Creation Catalog active pointer and increments `cards_catalog_generation` only after the asset root is complete.
3. `CreationCatalogClient` observes generation changes while Cards is active. If the active Creation changed or was deleted, `CreationWebViewHost` stops event/sensor delivery, clears bridge state, destroys the old WebView, and creates a new restricted WebView at the newly active loopback Card asset route.
4. A Creation not currently open appears in the Cards list on the next catalog refresh. No device reboot is needed.
5. If the runtime is unavailable or a future Android WebView implementation cannot safely reload a changed local asset root, the catalog reports `restartRequired: true` before activation. It must never claim a hot update that was not applied.

The same dynamic rule applies to the other Build 7 artifact types: Skill/Plugin enablement and MCP connection/tool-grant changes update their runtime catalogs without reboot; a live Voice session keeps the tool snapshot it started with and sees changes only on its next Voice session. Mail account enablement/sync scheduling changes take effect in the running runtime. A code/Android-package update still requires installation of its APK and normal runtime restart; imported data/artifact lifecycle does not.

**MDG-09 - Creation compatibility and model bridge:** The selected scope is real static-Creation import, catalog, dynamic Cards rendering, deletion, and compatibility with every demonstrated Creations SDK global through named R1 owners. The rejected alternatives are treating SDK examples as a complete package standard, exposing raw Android/WebView bridges, and creating a second agent loop. `PluginMessageHandler` uses the one existing Agents SDK path under a Creation-scoped no-personal-data tool projection; speaker, journal, storage, sensor, touch, and input behavior remain capability-specific and contained. Dependents: archive validator, Creation Catalog, storage, management/UI routes, Android Cards feature, input ownership, OpenAI policy, and physical acceptance. **Result:** `CONTINUE` by owner direction; implementation/evidence remains final-subphase work.

### Concern 6: Connections and encrypted database credentials

New Python code home:

```text
runtime/resono_runtime/connections/
  records.py
  credentials.py
  lifecycle.py
```

`records.py` owns the cross-domain connection read model used by the later management page. Domain-specific mutation remains under Mail or MCP APIs so a generic route does not become a catch-all. `credentials.py` is the only Python caller of the generic Java envelope bridge. `lifecycle.py` owns common enable/disable/status transitions but delegates domain data deletion to the owning domain.

Android changes:

```text
android/runtime-host/src/main/java/com/resonolabs/runtime/host/
  RuntimeCredentialCipher.java       # new reusable AES-GCM envelope owner
  RuntimeCredentialStore.java        # existing fixed OpenAI storage delegates crypto
  RuntimeCredentialBridge.java       # adds narrow seal/open database-envelope methods
```

Refactor, do not duplicate, the current AES-GCM behavior. Preserve the accepted OpenAI ciphertext format, key alias, record-name AAD, and existing SharedPreferences behavior. Add bridge methods that seal/open a versioned envelope for a validated record name such as `connection:<uuid>:credential`. The bridge returns ciphertext to Python; Python stores that envelope in SQLite. The non-exportable key remains in Android Keystore. Plaintext exists only for the bounded connect/auth operation and must not enter logs, events, exception text, tool results, package files, quarantine reports, or management GET responses.

The cross-domain read API is:

```text
GET /v1/management/connections
GET /v1/management/connections/<connection-id>
```

It returns kind, label, enabled/connected/health state, credential presence, source ownership, timestamps, and permitted actions. It never returns a secret or encrypted envelope. Creation, credential replacement, testing, and deletion use the domain-specific Mail/MCP routes.

### Concern 7: OpenAI Responses web search

New code home:

```text
runtime/resono_runtime/search/
  openai_responses.py
  tool.py
```

The donor separates a stable `web_search` tool definition, a bounded adapter, an OpenAI Responses executor, and invocation/usage handling. Retain that separation but remove hosted Vault configuration, cloud fallback, billing, cache, workspace snapshot, and multi-tenant concerns.

`openai_responses.py`:

- calls `openai_provider_access()` for the currently selected Platform or subscription path;
- sends one Responses request with provider tool `{ "type": "web_search" }`;
- uses the runtime-selected text model unless the provider catalog explicitly declares a compatible search model;
- enforces a 45-second provider deadline, a 2,000-character query limit, and at most eight citations/results, following the donor’s proven bounds;
- extracts output text, URL citations/annotations, and usage without fetching cited pages locally;
- uses `store: false` where the access path supports it; and
- returns a typed unavailable/reconnect/unsupported error with no scraper, alternate provider, or silent access-path fallback.

`tool.py` owns the Tool Catalog definition and result shaping. `web_search` is a read/network Voice tool when the effective Voice grants allow it. It appears in the same management Tool Catalog projection as built-in Mail and imported MCP tools, but that projection is inspection and grant state, not an invocation surface.

The owner requires both Platform and ChatGPT/Codex subscription access. Each path needs its own real provider acceptance. Success on one path does not accept the other, and an unsupported subscription backend is a blocking finding rather than permission to fall back to Platform.

### Concern 8: Mail domain and connectors

New code home:

```text
runtime/resono_runtime/mail/
  accounts.py
  messages.py
  synchronization.py
  scheduler.py
  actions.py
  tools.py

runtime/resono_runtime/connectors/mail/
  imap.py
  smtp.py
  mime.py
  endpoint_policy.py

runtime/resono_runtime/storage/mail/
  accounts.py
  messages.py
  sync_state.py
  actions.py
```

The split is deliberate:

- `mail/` owns R1 behavior and policy;
- `connectors/mail/` owns protocol and RFC translation;
- `storage/mail/` owns SQL and transactions;
- `connections/` owns credential envelopes and common connection state;
- `tools/` owns catalog/invocation infrastructure, not Mail behavior; and
- plugins may teach or contribute MCP components but never own Mail.

Do not copy the donor’s single large provider/store files unchanged. Adapt retained behavior into these owners and record exact donor source revision/path/destination/retained/omitted/license/test evidence before any code is copied.

Mail account setup is API-only in Build 7. The management API accepts connection/account information, tests the real endpoint, stores public configuration plus an encrypted credential envelope, and reports sync health. It does not expose folders, message lists, bodies, compose screens, or a web Mail client.

Management API contract:

```text
GET    /v1/management/mail/accounts
GET    /v1/management/mail/accounts/<account-id>
POST   /v1/management/mail/accounts
POST   /v1/management/mail/accounts/<account-id>/credentials
POST   /v1/management/mail/accounts/<account-id>/test
POST   /v1/management/mail/accounts/<account-id>/sync
POST   /v1/management/mail/accounts/<account-id>/enable
POST   /v1/management/mail/accounts/<account-id>/disable
DELETE /v1/management/mail/accounts/<account-id>
```

There is no `/v1/management/mail/messages` endpoint in this contract. Mail content is available only through granted agent tools.

Account rules:

- zero to three configured Mail accounts per device;
- each account has independent IMAP and SMTP host/port/TLS/auth configuration and one encrypted credential envelope;
- TLS certificate verification is required; implicit TLS and STARTTLS are supported; plaintext credential transport is rejected;
- username/password or provider app-password authentication is the smallest required real path; generic provider OAuth is not claimed unless separately implemented and evidenced;
- agent tools select a mailbox explicitly or use a deterministic configured default; they never guess among accounts; and
- credentials and raw authentication errors never enter agent context.

Synchronization rules:

- every enabled account is scheduled continuously while the accepted foreground runtime is running;
- an incremental synchronization attempt begins no later than five minutes after the preceding attempt began, unless that account already has an active work unit;
- no overlapping work unit is allowed for one account;
- a work unit yields after ten minutes at the absolute latest, commits its cursor/checkpoint, and resumes from that checkpoint;
- up to three bounded account workers may run so one large historical mailbox cannot starve the other accounts;
- each work unit prioritizes current deltas, then advances full-history backfill across every discoverable folder fairly;
- `UIDVALIDITY`, UID cursors, flags, folder delimiter/special-use data, retries, and last success/error are persisted;
- restart recovery resumes committed work and does not restart a completed history range;
- all headers and message bodies are mirrored locally; attachment metadata is mirrored, but attachment bytes are fetched only by an explicit `email_read_attachment` call and are not persisted by default;
- MIME parsing is bounded and defensive; HTML is converted to safe text for the agent rather than rendered;
- remote deletions performed outside the R1 may be reflected as local tombstones/removals during reconciliation, but the R1 never sends a remote delete command; and
- sync errors are per account/folder and cannot stop the runtime, Voice, other accounts, or extension APIs.

The exact Mail tool sets retained from the donor and exposed through the Tool Catalog are:

```text
Read/cache:
  email_account_status
  email_list_folders
  email_check
  email_get_unread
  email_search
  email_read
  email_read_attachment
  email_contact_lookup

Allowed effects:
  email_mark_read
  email_mark_unread
  email_compose
  email_send_pending
  email_archive
  email_create_folder
  email_rename_folder
  email_move_message
```

Absolute prohibition:

- no `email_delete`, `email_trash`, bulk delete, empty-trash, purge, or equivalent definition;
- no delete/expunge handler is written and no hidden alias maps to one;
- the IMAP connector contains no operation that sets `\\Deleted` and no `EXPUNGE` call;
- archive and move require the server’s non-destructive move capability and a valid destination; there is no COPY-plus-delete fallback;
- the agent cannot move a message to a folder identified as Trash/Junk when that would be a deletion surrogate;
- plugin or imported MCP tools are not allowed to claim they are the built-in Mail domain or receive Mail credentials; and
- account deletion is local connection/data removal only and is not a Mail-message tool.

Send approval is a trusted two-step flow:

1. `email_compose` validates recipients/subject/body, creates an immutable pending draft keyed by a runtime-generated action ID and tool-call idempotency key, and returns the exact preview with `confirmationRequired: true`. It performs no SMTP action.
2. The agent presents the exact account, recipients, subject, and body and asks for explicit confirmation.
3. The trusted caller boundary records the next real spoken user confirmation against the same Voice session and pending draft hash. The Voice agent must first read/review the exact preview and ask whether it is okay to send. Model arguments cannot create this approval.
4. `email_send_pending` presents the pending ID and content hash. The native Voice client separately supplies the latest transcribed user utterance and its monotonic session-local utterance ID. The runtime requires an explicit affirmative and an utterance ID strictly later than the draft's compose utterance, then atomically claims and sends the immutable draft once. Model arguments cannot manufacture approval.
5. Any draft edit, account change, recipient/body change, expiration, denial, session mismatch, replay, or missing approval prevents send.
6. A successful SMTP result is stored as a receipt so retries return the prior result and never double-send.

To support this, `RuntimeVoiceClient.callTool` must carry trusted Voice session/tool-call context in private local headers; the model cannot set those headers. The local MCP route resolves that context to runtime-owned invocation and approval state before dispatch. The management API has no approval or tool-invocation route. This is a general Voice safety boundary, not Mail-specific Android dispatch.

### Donor findings and exact adaptation decisions

Donor root is read-only: `/home/christian/Documents/Projects/ReSono-Labs-Voice/project-3d3354dadcad/workspace/`.

| Donor source | Proven behavior to retain | Behavior to omit |
|---|---|---|
| `app/vault_runtime/email_provider.py` | IMAP/SMTP TLS connection, UID fetch, RFC-822/MIME parsing, compose, endpoint validation patterns | hosted account/workspace assumptions, agent-mail mailboxes, autonomy, any delete/expunge path, broad single-file ownership |
| `app/vault_runtime/email_store.py` | canonical message/folder/sync/pending-send identities and idempotency concepts | PostgreSQL/Vault coupling and multi-tenant schema |
| `app/vault_runtime/email_service.py` | synchronization orchestration, prepare-send then confirm-send separation, mailbox scoping | model-supplied approval as sufficient authority and hosted provider actions |
| `app/vault_runtime/signals/email/session_tools.py` | exact eight read/cache and eight allowed-effect tool names and argument/result behavior | agent-mail tool family, deletion, hosted fallback, cloud routing |
| `app/vault_runtime/signals/openai_search.py` | OpenAI Responses call with `{type: web_search}`, 45-second deadline, output/usage extraction | environment-owned credential/base URL selection |
| `app/vault_runtime/web_search_provider.py` | 2,000-character query bound, eight-result/citation bound, citation extraction, typed blocked/error results | Vault workspace snapshots, multi-purpose hosted profiles, billing/account metadata |
| `app/contracts/internal/browser_voice_tools.py` | one immutable definition shape separating model name, description, transport target, and JSON schema | the donor’s large unrelated tool inventory |
| `app/modules/skill_catalog/service.py::_evaluate_install` | requested/required/granted intersection, blockers, conflicts, immutable lifecycle events | billing, entitlement, marketplace, account/tenant, developer runtime, and hosted publication branches |
| `app/modules/developer_publishing/extraction.py` | streamed safe ZIP/TAR extraction, path containment, link/duplicate/nested/encrypted archive rejection, size limits | hosted review-storage orchestration |
| `app/modules/developer_publishing/quarantine_storage.py` | immutable quarantine commit pattern and atomic placement | hosted review-console identifiers |
| `app/modules/developer_publishing/scanner_rule_runtime.py` | secret-like pattern scan and dangerous Python/process/network behavior findings | claims that a scan makes code safe to execute |
| `app/vault_runtime/session_tools/invocation_journal.py` | caller-owned provider-action identity and replay/conflict validation pattern | PostgreSQL/session platform machinery not required on one device |

The donor’s tool structure confirms the target separation: definitions describe tools, session adapters validate arguments, brokers/connectors perform bounded external work, and the session runtime applies identity and policy. Build 7 retains this separation in smaller R1-specific packages rather than importing the donor’s hosted registries and approximately 140-file `agent_packages` subsystem.

No donor code is copied by this planning edit. Before implementation copies any code, the implementer must add the required provenance record with donor revision, exact source path, exact destination path, retained behavior, omitted behavior, license decision, and receiving tests.

### API route ownership and Android proxy wiring

New route groups:

```text
runtime/resono_runtime/api/
  skill_routes.py
  plugin_routes.py
  mcp_routes.py
  tool_routes.py
  connection_routes.py
  mail_routes.py
```

`RuntimeRoutes` retains top-level method dispatch and delegates after pairing/origin/CSRF authentication. Each group receives only its application-facing owner, not the database or Java bridge. Routes parse/bound input and serialize domain results; they do not perform extraction, SQL, network calls, encryption, or tool execution directly.

Add a bounded `request_bytes()` transport operation for archive endpoints. Raw ZIP/TAR upload is preferred over base64 JSON. Content type, compressed-byte limit, declared length, read deadline, and staging cleanup are enforced before extraction. Ordinary JSON endpoints retain small concern-specific limits.

`ManagementRuntimeProxy.java` must enumerate every management prefix above, preserve authorization/origin/CSRF headers, set explicit request-size and read-timeout policies, and continue rejecting unknown paths. Archive upload, Mail connection test, explicit Mail sync, MCP discovery, and plugin install have longer but bounded timeouts. The proxy does not inspect credentials and never logs request bodies.

No `/v1/host/*` duplicates are added for Build 7. The trusted native product consumes tools through local MCP; owner configuration uses paired management endpoints.

### Application startup and shutdown order

`RuntimeApplication.__init__` constructs repositories and pure owners without starting network/scheduler work. `start()` performs work in this order:

1. prepare runtime and extension directories;
2. run migrations 6 and 7;
3. seed/validate bundled first-party plugin revisions;
4. load active Skill and Plugin records;
5. construct Tool Catalog built-ins;
6. restore enabled MCP connection definitions and perform bounded discovery without blocking runtime readiness indefinitely;
7. register the effective Skill activation, web search, Mail, memory, and device tools;
8. start the existing HTTP server;
9. start the Mail scheduler; and
10. publish readiness plus per-subsystem degraded health.

`stop()` performs the reverse operational shutdown: stop accepting scheduler work, checkpoint Mail workers, close outbound MCP sessions, stop HTTP, and then publish stopped state. A broken plugin, MCP endpoint, or Mail account is degraded isolated state; it does not prevent base Voice/runtime readiness. A schema migration or Tool Catalog identity collision is a startup-blocking integrity failure.

### Exact implementation file impact

Existing files expected to change:

```text
runtime/resono_runtime/application.py
runtime/resono_runtime/config.py
runtime/resono_runtime/api/http_server.py
runtime/resono_runtime/api/routes.py
runtime/resono_runtime/agents/runner.py
runtime/resono_runtime/providers/openai/platform.py
runtime/resono_runtime/mcp/server.py
runtime/resono_runtime/storage/database.py
android/runtime-host/build.gradle.kts
android/runtime-host/src/main/java/com/resonolabs/runtime/host/RuntimeCredentialBridge.java
android/runtime-host/src/main/java/com/resonolabs/runtime/host/RuntimeCredentialStore.java
android/runtime-host/src/main/java/com/resonolabs/runtime/host/ManagementRuntimeProxy.java
android/runtime-host/src/main/java/com/resonolabs/runtime/host/RuntimeVoiceClient.java
android/scripts/check_boundaries.sh
android/scripts/check_runtime_package.sh
```

`VoicePageView.java` changes only if needed to attach trusted current user-turn evidence to the already-generic tool call; it must not gain Mail tool names or Mail business rules. No file under `web/` changes.

New tests mirror each owner:

```text
tests/runtime/test_tool_catalog.py
tests/runtime/test_tool_invocation.py
tests/runtime/test_skill_specification.py
tests/runtime/test_skill_lifecycle.py
tests/runtime/test_plugin_specification.py
tests/runtime/test_plugin_lifecycle.py
tests/runtime/test_mcp_connections.py
tests/runtime/test_web_search.py
tests/runtime/test_connection_credentials.py
tests/runtime/test_mail_accounts.py
tests/runtime/test_mail_synchronization.py
tests/runtime/test_mail_actions.py
tests/runtime/test_mail_tools.py
tests/runtime/test_extension_management_routes.py
tests/runtime/test_mail_management_routes.py
```

Existing `test_mcp_server.py`, `test_agents_sdk_runner.py`, `test_openai_realtime_session.py`, `test_management_pairing.py`, `test_runtime_lifecycle.py`, and boundary/package scripts must be extended where the shared path changes. Do not duplicate old tests into the new files.

### Sequential build checkpoints

## Subphase governance and approval gates

Build 7 is not one continuous implementation run. It is delivered as the following owner-gated subphases. Work may start only in the active subphase. At its end, update this contract with the exact files changed, tests/evidence run, unresolved findings, artifact identifiers where applicable, and a proposed next-subphase entry condition. Stop for owner approval before beginning the next subphase. Passing tests or completing a code review does not implicitly authorize the next subphase.

| Subphase | Scope | Completion package required for approval | Next subphase blocked until |
|---|---|---|---|
| **07A - Standards, storage, and catalog foundation** | Pin standards/dependencies; add migration framework and schema; introduce the Voice-only Tool Catalog, grants, and trusted invocation boundary; migrate only existing device/memory behavior without changing its accepted capability. | Proven dependency/package compatibility; migration evidence; catalog/Realtime/MCP consistency evidence; focused tests; exact changed-file list; no new user-facing capability claimed. | Owner approves the foundation and its public contracts. |
| **07B - Skills and Plugin lifecycle** | Standard Agent Skills authoring/import/publish/rollback/delete; Agent Plugins validation, quarantine, lifecycle, and bundled instructional Mail Skill. No remote MCP execution yet. | Real standards fixtures; validation/quarantine/rollback/deletion evidence; API contract captures; provenance/license record; focused tests. | Owner approves standards behavior and editable recovery. |
| **07C - Connections, outbound MCP, and Voice web search** | Keystore-backed SQLite credential-envelope bridge; management-only connection APIs; outbound MCP discovery/forwarding; Voice-only imported-tool projection; donor-adapted `web_search` through both selected OpenAI access paths. | Credential redaction/rotation/removal evidence; MCP lifecycle and fail-closed evidence; real cited Voice search through each access path; focused tests. | Owner approves connection custody and customizable Voice tools. |
| **07D - Mail client foundation and synchronization** | Mail account APIs, maximum-three account rule, IMAP/SMTP connectors, canonical store, full every-folder/history synchronization, five-minute scheduling, ten-minute checkpoint/yield, and account removal. No Voice Mail mutation tools yet. | Three-account and fourth-account rejection evidence; durable full-sync/restart/fairness/five-minute evidence; encrypted SQLite evidence; donor provenance record; focused tests. | Owner approves real-client semantics before agent access. |
| **07E - Voice Mail tools and confirmed send** | Register the exact `email_*` allowlist; Voice read/read-unread/archive/move/folder actions; Voice draft review and session-bound spoken confirmation; SMTP plus Sent-folder parity; static absence of deletion behavior. | Voice transcripts/tool events; independent-client parity evidence; single-send/replay/changed-draft denial evidence; source/runtime proof of no delete/trash/expunge/copy-delete fallback; focused tests. | Owner approves the actual Voice Mail behavior. |
| **07F - Creations Cards host and consolidated acceptance** | Add the Creation Catalog management UI exception, native Cards feature, restricted dynamic WebView host, static-Creation import/enable/delete/live-reload path, then run the single consolidated repository, Android, package, boundary, API, and physical acceptance pass. | Exact SDK provenance/license record; static Creation import/list/render/delete evidence; dynamic generation/reload evidence with no reboot; exact APK/install/rollback hashes; complete evidence inventory; known-issue list, including any blocked SDK profiles; final contract update; owner physical acceptance. | Contract closes only on explicit owner acceptance. |

Rules for every subphase:

1. Do not begin code from a later subphase to "prepare" it early.
2. Do not add web UI before 07F. In 07F, the only permitted web change is the real Creation Catalog wired to Creation lifecycle APIs; all other Build 7 web UI remains out of sequence.
3. Keep current accepted behavior intact. A regression stops the active subphase and is documented before any new scope begins.
4. Record every donor copy before it occurs: source revision, source path, destination, retained behavior, omitted behavior, license decision, and receiving tests.
5. An unresolved material ambiguity is a stop condition under the planning protocol, not an invitation to design ahead.

### 07A completion record - pending owner approval

**Scope completed:** versioned migration foundation plus the existing built-in Voice tool path only. No new user-facing tool, extension, connection, Mail, web-search, Cards, Creation, or web-management behavior was added.

**Implementation inventory:**

```text
runtime/resono_runtime/storage/migrations/__init__.py
runtime/resono_runtime/storage/migrations/v005_runtime_foundation.py
runtime/resono_runtime/storage/database.py
runtime/resono_runtime/tools/__init__.py
runtime/resono_runtime/tools/definitions.py
runtime/resono_runtime/tools/catalog.py
runtime/resono_runtime/tools/builtins.py
runtime/resono_runtime/mcp/server.py
runtime/resono_runtime/providers/controller.py
runtime/resono_runtime/providers/openai/platform.py
runtime/resono_runtime/application.py
tests/runtime/test_tool_catalog.py
```

`RuntimeDatabase` now applies ordered migration modules while retaining the existing schema version `5`, including the prior version-4 `memory_embeddings` upgrade behavior. `ToolCatalog` is the single owner of existing `get_device_status` and `memory_lookup` definition/schema/dispatch projection. The local MCP server and Realtime session consume that catalog. The existing Agents SDK text runner remains explicitly status-only and receives no Build 7 tool expansion.

**Focused validation:** `PYTHONPATH=runtime python3 -m unittest tests.runtime.test_tool_catalog tests.runtime.test_mcp_server tests.runtime.test_openai_realtime_session tests.runtime.test_runtime_lifecycle tests.runtime.test_agents_sdk_runner` passed on `2026-08-20`: **16 tests, 0 failures**. The workspace has neither `.venv/bin/pytest` nor a system `pytest` module; no dependency installation, full test suite, Android build, APK, or device test was run in this subphase.

**Standards freeze for subsequent subphases:** fetched directly from their normative sources on `2026-08-20` and recorded below. The retrieved files are reference evidence, not a scope authority or bundled implementation artifact.

| Input | Canonical source | SHA-256 |
|---|---|---|
| Agent Plugins manifest schema 1.0.0 | `https://agent-plugins.org/schemas/1.0.0/plugin.schema.json` | `0a4aad95ce337878ad38802ebf0daa3fde76abe3f65400c86bcbb1ec0b3ab883` |
| Agent Plugins MCP schema 1.0.0 | `https://agent-plugins.org/schemas/1.0.0/mcp.schema.json` | `6539175bfcdf43085855183e86da40ea94b166547a72b47ae9a0a390516d3acb` |
| Agent Skills specification | `https://agentskills.io/specification` | `88fbf9ea9c691cfb299ad324aa371568b50ef9231d2b8f322b01c69efa35ddab` |
| MCP specification 2025-11-25 | `https://modelcontextprotocol.io/specification/2025-11-25` | `4d11ccc3eae8f38155db6cf881d94c04aea1e289bfd96dd0b6422a0ca6811729` |

**Deferred dependency gate:** Agent Skills YAML parsing and APK packaging are intentionally not claimed in 07A. The current runtime has `jsonschema` but no pinned YAML parser; 07B must select, license-record, package, and validate the parser before any Skill implementation begins.

**Approval request:** approve `07A` foundation/evidence to begin `07B` standard Skills and Plugins lifecycle. No `07B` code starts before that approval.

### 07B entry-gate resolution - parser packaging proved

**Date:** 2026-08-20  
**Classification:** dependency gate passed; standalone Skills checkpoint may proceed.

The host Python provides compatible `yaml` version `6.0`. The first selected pin, `PyYAML==6.0.2`, was unavailable from Chaquopy's Python 3.13 arm64 index; it exposes `6.0.3` instead. `android/runtime-host/build.gradle.kts` therefore pins `PyYAML==6.0.3`.

The required packaging proof completed through the normal `./android/scripts/build_debug.sh` path after verifying the pinned Gradle/JDK launcher. Chaquopy installed:

```text
pyyaml-6.0.3-0-cp313-cp313-android_24_arm64_v8a.whl
chaquopy-libyaml-0.2.5-0-py3-none-android_24_arm64_v8a.whl
```

The resulting build completed with:

```text
BUILD SUCCESSFUL
standalone Android boundaries: OK
embedded runtime package: OK
```

The APK requirements archive was inspected and contains `yaml/_yaml.so` and
`chaquopy_libyaml-0.2.5`. `android/scripts/check_runtime_package.sh` now
enforces those exact packaged entries; the updated check passed.

The earlier `libnative-platform.so` launcher failure was resolved by verifying the pinned Gradle runtime under the same JDK and rerunning the normal build command. The recovery procedure is recorded in `SKILLS.md`. No Skill or Plugin lifecycle behavior is claimed by this dependency gate alone.

**Next rule:** use `yaml.safe_load`; do not replace the pinned parser with a partial YAML parser, a proprietary Skill format, or an unpinned environment dependency. Resume 07B at standalone Skills checkpoint 1.

### Sequential build checkpoints

Within an owner-approved subphase, work is strictly one checkpoint at a time. Focused tests are written/run for the owner being introduced; one consolidated repository/build/device run occurs only in Subphase 07F after the code verticals are complete, avoiding repeated full-device testing.

#### BC07-1: dependency and schema proof

- pin Agent Skills evidence, Agent Plugins 1.0.0 schemas, MCP protocol revision, YAML parser, license, and package provenance;
- prove required dependencies package in the arm64 APK;
- add versioned migration structure without changing behavior; and
- stop if the parser/client cannot run in the accepted Android/Chaquopy environment.

#### BC07-2: Tool Catalog and trusted invocation

- migrate device and memory tools into the catalog;
- feed the Realtime Voice surface from it while preserving, but not expanding, the existing Agents SDK text surface;
- preserve the accepted existing Voice/text behavior while exposing new Build 7 capabilities only to Voice;
- add caller identity, grant filtering, idempotency, and approval records; and
- prove unauthorized tools are absent from `tools/list`.

#### BC07-3: standalone Agent Skills

- implement standard validation, drafts/import, progressive disclosure, publish, rollback, disable, and delete;
- prove scripts never execute and paths never escape;
- activate one real standards-conformant skill through the Voice tool path; and
- prove a failed edit leaves the prior revision active.

#### BC07-4: Agent Plugins

- implement archive limits, extraction, scan, quarantine, schema/component validation, lifecycle, and deletion;
- install one skill-only plugin and one MCP-only or combined standard package;
- prove plugin disable withdraws components and preserves core domain data; and
- prove plugin uninstall deletes package-owned components/secrets/cache only.

#### BC07-5: outbound MCP and customizable tools

- configure/import a real MCP server, discover names/schemas, namespace projections, grant selected tools, and invoke through local MCP;
- prove the same imported tool is visible/callable through the Voice projection when granted;
- prove deletion/disable removes it from the Voice projection;
- prove stdio packages are reported but never launched; and
- prove an unhealthy server does not degrade base runtime readiness.

#### BC07-6: web search

- add the donor-adapted OpenAI Responses tool;
- prove real Platform search with citations;
- prove real subscription search with citations;
- prove no credential divergence and no hidden fallback; and
- add `web_search` to the same management tool projection as all other tools.

#### BC07-7: Mail accounts and continuous synchronization

- add generic database credential envelopes and Mail account APIs;
- connect one then three real accounts;
- synchronize every folder and historical range with persisted checkpoints;
- prove five-minute attempts, ten-minute yield, restart resume, account fairness, and attachment-metadata-only background behavior; and
- prove account deletion immediately removes local data/envelope without a remote mutation.

#### BC07-8: Mail agent actions

- register the exact sixteen allowed Mail tools;
- prove read/search/folder/account selection behavior;
- prove mark read/unread, archive, move, create folder, and rename folder against real servers without delete fallback;
- prove compose performs no send;
- prove send requires and consumes trusted exact-draft approval and is idempotent; and
- run negative source/static/runtime checks proving no Mail delete/trash/expunge capability exists.

#### BC07-9: API and physical acceptance consolidation

- exercise every management API through the real paired same-LAN HTTPS proxy, not loopback-only test calls;
- confirm no Build 7 web UI/assets were introduced;
- run the consolidated runtime, Android unit, boundary, package, build, and physical evidence suite once;
- preserve rollback artifacts and database migration/rollback evidence; and
- record residual unsupported plugin transports or provider limitations truthfully.

#### BC07-10: Creations Cards compatibility and final acceptance

- record the exact Creations SDK revision, paths, MIT license decision, retained browser-global evidence, and omitted RabbitOS assumptions before copying any reference material;
- implement the Creation Catalog, immutable archive lifecycle, scoped deletion, and loopback-native Cards projection;
- implement the new `android/feature/cards` host with one restricted WebView per selected active Creation, lifecycle-safe input ownership, dynamic catalog-generation reload, and no reboot/restart requirement for artifact changes;
- render one real static imported Creation on the native Cards page and prove import, enable, update, disable, and delete alter the Card list/host truthfully;
- prove unsupported `model_message`, synthesized touch, and ungranted storage/sensor globals return explicit unavailable behavior rather than gaining implicit authority;
- add the real web Creation Catalog only after the API/native behavior is complete; and
- include Creation evidence in the one final consolidated package/build/physical acceptance run.

### Required negative and lifecycle evidence

Acceptance must include failures, not only successful demonstrations:

- malformed Skill frontmatter and mismatched directory/name;
- invalid/unknown Plugin schema, partial component failure, and unsupported standard version;
- ZIP/TAR traversal, symlink, duplicate, nested archive, compression expansion, secret, and executable findings;
- active revision unchanged after validation/scan/install failure;
- unauthorized, disabled, deleted, collision, unhealthy-source, oversized-argument, and oversized-result tool calls;
- model attempt to supply its own approval, reused approval, mismatched draft, changed recipient, wrong session, and duplicate send;
- fourth Mail account rejection;
- bad TLS, bad credentials, UIDVALIDITY change, folder failure, network loss, process restart, ten-minute yield, and concurrent-account fairness;
- explicit proof that Mail tools and IMAP connector expose no delete/trash/expunge command or fallback;
- plugin disable/uninstall does not remove Mail data;
- Mail account delete does not disable or remove the first-party Mail skill/plugin;
- built-in delete attempt returns non-deletable truthfully;
- plugin-owned component delete identifies the owning source rather than mutating the package;
- management GET responses, logs, events, tool results, and quarantine reports contain no plaintext secret; and
- both Platform and subscription `web_search` fail closed when their selected access is unavailable.

### Structural completion rule

Build 7 is structurally complete only when another developer can start at `runtime/resono_runtime/application.py`, follow explicit constructor dependencies into each noun-owned package, inspect one migration/repository per stored concern, see one catalog projection feeding the Voice execution surface and the non-executing management projection, and trace every management mutation through one allowlisted route to one lifecycle owner. A feature that works only through a hard-coded list, a web invocation path, a plugin-owned data store, an untracked package directory, or a hidden credential mechanism fails this contract even if its happy-path demonstration succeeds.
# 07B Skill Import Completeness Gate

**Status:** required review before Skill archive intake implementation. This gate exists because a successful upload alone is not an acceptable import feature. No Plugin import work may start until this Skill lifecycle has implementation evidence and owner approval.

# 07B.0 Agent Audience Router Foundation

**Status:** implemented routing foundation. The product is Voice-first and Build 08 adds a delegated Background Agent, not a user-facing text-chat agent. An imported capability must never be implicitly limited to Voice or silently exposed to the Background Agent.

## Purpose

The **Agent Audience Router** is the one global owner of the user-selected answer to: **which R1 agent may receive this capability?** User-facing choices are `Voice`, `Background Agent`, and `Both`. The persisted/internal `text` value means Background Agent for compatibility; it does not authorize or imply a text-chat UI.

It is not an external-system connector. IMAP, SMTP, CalDAV, OAuth, and MCP transport remain Connections/Connectors. It is not a permission system, either. It cannot make a capability safe, grant a tool, start an agent, or execute a user action. It only projects a capability to the correct local agent audience after the normal lifecycle and permission checks succeed.

## One routing rule for every importable type

Every import or connection flow must ask for an intended agent audience before it becomes active. The selection is stored as explicit product data, never inferred from the package contents.

| Build 07 element | User selects audience? | Router controls | Does not control |
| --- | --- | --- | --- |
| Imported Agent Skill | Yes | Whether its instructions may be disclosed/activated for Voice, Background Agent, or both | Tool grants, package validity, execution |
| Imported Agent Plugin | Yes | Whether installed Skills and MCP components are projected to Voice, Background Agent, or both | Plugin decomposition, permissions, process lifetime |
| Direct MCP connection | Yes | Whether discovered MCP tools enter Voice, Background Agent, or both filtered Tool Catalogs | OAuth, network transport, tool permission intersection |
| Built-in Mail tools | Yes, during Mail agent-access setup | Whether approved Mail tools appear to Voice, Background Agent, or both | Mail sync, credentials, send confirmation, deletion prohibition |
| Built-in `web_search` | Yes, during tool access setup | Whether the built-in tool appears to Voice, Background Agent, or both | Search provider behavior and permission policy |
| Imported Creation | Yes, for agent-facing bridge access | Whether a compatible Creation may request an agent-facing bridge for Voice, Background Agent, or both | Cards rendering, sandbox, storage, hardware bridge, user data access |
| Built-in Calendar, Contacts, and Reminders tools | Yes, when those domains land | Whether domain tools appear to Voice, Background Agent, or both | Connector sync and canonical domain data |

No selection means **not exposed to either agent**. A Creation may still appear as a Cards artifact when it has no agent exposure; Cards presentation and agent access are independent settings.

## Code structure and dependency direction

```text
runtime/resono_runtime/agents/
    audience.py        # stable `voice` / `text` value model and validation
    routing.py         # AgentAudienceRouter query and projection contract

runtime/resono_runtime/storage/
    agent_audiences.py # durable binding records and audit history
    migrations/
    v006_agent_audiences.py

runtime/resono_runtime/skills/activation.py
runtime/resono_runtime/mcp/tool_adapter.py
runtime/resono_runtime/domains/*/tools.py
runtime/resono_runtime/creations/bridge_access.py
    # consumers: ask the router; never duplicate an audience flag
```

The dependency direction is one way: imported/package/domain owners publish a stable resource reference; the Router answers whether it belongs in a named agent projection; each agent's registry consumes that projection. The Router never imports Skills, Plugins, MCP clients, Mail, domain services, or Android/UI code.

## Stable public contract

```text
AgentAudience := voice | text | both
ResourceReference := { kind, stable_id, revision_id? }

set_audience(resource, audience, changed_by, reason)
get_audience(resource) -> audience | none
is_exposed(resource, agent_kind) -> bool
list_for(agent_kind, resource_kind?) -> [ResourceReference]
remove_resource(resource, changed_by, reason)
```

`kind` is a closed product vocabulary, initially: `skill`, `plugin`, `mcp_connection`, `domain_tool_set`, and `creation`. The router rejects unknown kinds rather than becoming a generic metadata bag. `stable_id` and `revision_id` are created by the owning catalog/lifecycle, not supplied as arbitrary browser paths.

`both` is stored as one deliberate selection, not duplicated rows whose state can diverge. The Background Agent consumes the same selected capability records as Voice; it does not receive a second, unreviewed import path.

## Import and lifecycle sequencing

1. The importer validates and quarantines a candidate.
2. The user chooses `voice`, `text`, or `both` through the future management API.
3. The owning lifecycle creates a canonical resource/revision.
4. In the same success path, it writes the Router binding.
5. The capability can be enabled only when it has a valid audience binding and passes its own permission/lifecycle rules.
6. Disabling removes it from both agent projections while retaining the selected audience for a future re-enable.
7. Deleting removes the binding first, then the owner removes active material and retains its audit tombstone.

Changing audience is an auditable lifecycle action. It takes effect dynamically at the next agent tool/Skill catalog projection. It does not require a device reboot and does not restart a running conversation; the next Voice or text turn receives the revised catalog.

## Non-negotiable safeguards

- The web management interface configures audience but never impersonates Voice or the Background Agent to run a capability.
- The router cannot bypass `ToolCatalog` permission intersection, explicit send confirmation, resource quarantine, or a domain's safety rules.
- Mail retains no-delete enforcement regardless of its selected audience.
- A Plugin's selected audience is an upper bound. Its individual components may be more restricted but never broader.
- A Skill's `allowed-tools` remains a declaration only; choosing `both` does not grant those tools to either agent.
- A Creation receives no new Android, filesystem, credential, Mail, Memory, or hardware authority through an audience selection.
- Build 08 Background Agent execution must consume this existing contract rather than add a second per-feature `text_enabled` flag.

## Required evidence before 07B.1 resumes

1. Unit tests for every value, invalid audience/kind, projection, replacement, disable/remove transition, and audit record.
2. Storage migration and tests proving one resource binding cannot affect another.
3. An application composition point that supplies the Router to the existing Voice projection without changing its current available-tool behavior.
4. A documented management API contract that accepts an audience selection but does not add a web execution endpoint.
5. A future-text-agent integration note that identifies the single router query it will use.

## Codebase review and implementation decision

This section is derived from the present product codebase, not a proposed parallel architecture.

### Existing seams found

| Existing code | What it owns today | Router integration decision |
| --- | --- | --- |
| `runtime/resono_runtime/application.py` (`RuntimeApplication`) | The single Python runtime composition root. It starts storage, providers, local MCP, pairing, HTTP, and runtime lifecycle. | Construct one `AgentAudienceRouter` here, after database migrations and before providers/MCP are composed. Pass its narrow query interface to projections. Do not construct routers in route handlers, domain services, or Android. |
| `runtime/resono_runtime/tools/catalog.py` (`ToolCatalog`) | The shared tool definition and projection boundary already used for MCP and Realtime Voice. | Add an agent-target projection method here, supplied with the Router query. The router says whether a resource may appear; Tool Catalog still applies schema and permission filtering. Do not put audience state in individual tool definitions. |
| `runtime/resono_runtime/mcp/server.py` (`LocalMcpServer`) | Local MCP initialization, session validation, tool listing, and tool calls through the Tool Catalog. | Request the named agent projection when it supplies tools to an R1 agent. It must not directly read audience tables or decide permissions. |
| `runtime/resono_runtime/providers/controller.py` (`ProviderController`) | Existing Agents SDK proof turn and native Realtime Voice session creation. | Realtime receives the `voice` projection. Build 08 Background Agent execution receives the same projection contract through internal audience value `text`; it does not create another tool/Skill registry. The legacy proof turn is not a user-facing text agent. |
| `runtime/resono_runtime/agents/runner.py` | The existing text-runner adapter. | The future device text-agent work wires its catalog and Skills request through `AgentAudienceRouter.is_exposed(..., "text")`. No text UI work belongs in the router checkpoint. |
| `runtime/resono_runtime/storage/database.py` | Canonical SQLite connection and ordered, idempotent migration application. | Add `v006_agent_audiences.py`; the router repository receives the existing database owner rather than opening its own SQLite connection. |
| `runtime/resono_runtime/api/routes.py` and `api/http_server.py` | Authenticated local management transport. | A later narrow route module accepts an audience choice and delegates to the owning lifecycle. It remains configuration-only. No agent-execution endpoint and no web UI work in this checkpoint. |
| `runtime/resono_runtime/api/events.py` (`RuntimeEventStream`) | Runtime-to-management live state publication. | Lifecycle owners publish an audience-changed event after a committed change so a future management interface can refresh; the router itself does not know HTTP/SSE. |
| `android/feature/voice/.../VoicePageView.java` | Native Voice UI, WebRTC, transcript and tool event handling. | No Android change now. The existing Realtime tool catalog becomes audience-filtered in the runtime. A later Text feature creates its own UI/module but consumes the same runtime contract. |

### Final module layout

```text
runtime/resono_runtime/
    agents/
        audience.py
        routing.py
    storage/
        agent_audiences.py
        migrations/
            v006_agent_audiences.py
    tools/
        catalog.py                 # consumer projection only
    skills/
        activation.py              # future consumer projection only
    mcp/
        tool_adapter.py            # future consumer projection only
    api/
        agent_audience_routes.py  # later configuration transport only
```

`agents/audience.py` contains the closed value objects and validation (`voice`, `text`, `both`; closed resource kinds). `storage/agent_audiences.py` owns SQL records and audit history. `agents/routing.py` owns the business rule that turns a stored selection into an allow/deny answer for one agent. This prevents either the Tool Catalog or a future Skills/Plugins module from becoming a second database-backed router.

**Canonical-item correction:** the Router stores one binding per `(resource_kind, resource_id)`, never a binding per revision. A resource replacement updates that one binding inside the owner's confirmed atomic replacement. The import owner alone retains a single private rollback copy when needed; the Router retains audit events, not a revision catalog.

### Database design

`v006_agent_audiences.py` adds two tables only:

```text
agent_audience_bindings
    resource_kind
    resource_id
    audience                 # voice | text | both
    changed_at
    changed_by
    change_reason
    active

agent_audience_audit
    audit_id
    resource_kind
    resource_id
    previous_audience nullable
    new_audience nullable
    action                   # set | disable | remove
    changed_at
    changed_by
    change_reason
```

The binding uniqueness key is `(resource_kind, resource_id)`. It is written inside the owning import/lifecycle transaction, never from a browser-provided SQL identifier. Deactivation preserves the selected audience. Removal writes the audit event and removes the active binding before an owner deletes its installed resource. No foreign key points from this global table into a not-yet-built Plugin, Mail, MCP, or Creation table; owners pass stable identifiers, keeping migration order clean.

### Runtime flow

```text
Management configuration API
    -> owning import/domain lifecycle validates resource and selected audience
    -> AgentAudienceRepository commits binding + audit entry
    -> owning lifecycle publishes its change event

Realtime Voice or Background Agent run
    -> ToolCatalog / Skill activation asks AgentAudienceRouter
    -> only matching resources continue to normal permission filtering
    -> provider runner receives already-filtered Skills and tools
```

For the present device, the app composes the `voice` query into the Realtime tool projection. Current built-in device-status behavior is preserved through an explicit bootstrap binding owned by the Tool Catalog migration, not an unrecorded default. The Background Agent asks for internal audience `text` at exactly the same projection point. No active run changes its immutable tool projection; the next run receives the revised catalog.

### Decisions that prevent drift

- This is named **Agent Audience Router**, not Connector, because “Connector” already means a bridge to an external service or file format.
- It routes *capabilities*, not agents themselves. Voice and Background Agent execution remain owned by the existing provider/agent runtime.
- It is global only for the one cross-cutting question of audience. Package validation, OAuth, file extraction, Mail sync, Cards rendering, and permissions stay with their existing/future domain owners.
- Plugin selection is an upper limit; individual bundled components may be disabled or more narrowly routed, never broadened beyond the Plugin’s audience.
- Imported Creation card visibility is separate from agent-bridge audience. A Creation can appear in Cards without access to either agent.
- The future management UI uses the same API but cannot run a selected capability.

### Implementation finding: router foundation is not yet an accepted checkpoint

Initial source locations have been created for `agents/audience.py`, `agents/routing.py`, `storage/agent_audiences.py`, and `storage/migrations/v006_agent_audiences.py`. Before this becomes an accepted runtime foundation, implementation must complete the following codebase-specific work:

1. Register `v006_agent_audiences.py` in the existing ordered migration application list in `runtime/resono_runtime/storage/database.py`; an unregistered migration is not durable product behavior.
2. Wire one repository/router instance in `RuntimeApplication` after migrations, then supply its query-only interface to the existing Voice tool projection. No route, Android, or web component may construct it.
3. Complete the revision identity implementation so the SQLite uniqueness key stores the normalized revision identifier as well as the nullable display value. Otherwise two revisions of one resource would collide, which violates the immutable-revision contract.
4. Add focused tests before changing any existing agent/tool behavior. No claim of runtime activation, migration application, or preservation of existing Voice behavior is valid until those tests pass.

This finding keeps the code change contained and prevents a partially wired router from being treated as an active product feature.

### 07B.0 implementation record

**Implemented source owners**

| File | Implemented responsibility |
| --- | --- |
| `runtime/resono_runtime/agents/audience.py` | Closed `voice`, `text`, and `both` values plus closed imported-capability resource kinds. |
| `runtime/resono_runtime/agents/routing.py` | Query-only router and narrow durable-store protocol. It does not execute an agent or grant a permission. |
| `runtime/resono_runtime/storage/agent_audiences.py` | One canonical SQLite binding per resource identity and append-only `set`, `disable`, and `remove` audit events. |
| `runtime/resono_runtime/storage/migrations/v006_agent_audiences.py` | Version 6 schema for bindings and audit history. |
| `runtime/resono_runtime/storage/migrations/__init__.py` | Registers migration 6 in the existing ordered migration list. |
| `runtime/resono_runtime/application.py` | Creates exactly one router from the canonical runtime database after startup migration; explicitly bootstraps the current built-in tool set to `both` so accepted device-status behavior is retained. |
| `runtime/resono_runtime/tools/catalog.py` | Projects tool definitions and calls for a named agent audience. The catalog still owns tool schemas and invocation checks. |
| `runtime/resono_runtime/tools/definitions.py` and `tools/builtins.py` | Associate current built-in tools with one explicit `builtin-tools` resource rather than assuming Voice-only availability. |
| `runtime/resono_runtime/mcp/server.py` | Passes its named agent audience into Tool Catalog listing and invocation. Build 08 Background Agent MCP composition uses internal audience `text`; Realtime Voice uses `voice`. |

**Current behavioral boundary**

- The current Voice Realtime projection reads the `voice` audience through the existing Tool Catalog callback.
- The existing text runner remains unchanged because the future on-device text-agent UI/turn contract is not part of Build 07B.0. It has one prepared runtime projection API to consume: `ToolCatalog.mcp_definitions(AgentKind.TEXT)` and agent-scoped invocation.
- No importer, UI notification, management route, Plugin, MCP connection, Mail account, Skill activation, or Creation bridge has been added by this checkpoint. Those owners will write their own audience binding only after their validation and confirmed replace workflow succeed.
- No tests were run during this implementation pass. Required focused router, migration, Tool Catalog, and current Voice-regression tests remain the next evidence step before 07B.0 can be accepted.

### 07B.0 focused evidence record

The router foundation was tested after implementation with:

```bash
PYTHONPATH=runtime python3 -m unittest \
  tests.runtime.test_agent_audiences \
  tests.runtime.test_tool_catalog \
  tests.runtime.test_mcp_server \
  tests.runtime.test_openai_realtime_session
```

Result: `Ran 10 tests ... OK`.

The test group proves migration 6 applies, a resource retains one canonical binding when its audience changes, `voice`/`text`/`both` projection is enforced at Tool Catalog listing and invocation, disable/remove remove access, existing Tool Catalog behavior remains available when no router is supplied, local MCP remains covered, and current Realtime session coverage remains green. The first run exposed only a new test assertion expecting a list from the established tuple-returning Realtime API; the assertion was corrected and the same focused group passed.

**Checkpoint state:** implementation and focused evidence are complete. Do not begin Skill archive intake until the owner approves moving from 07B.0 to 07B.1.

# Global Import Conflict and Explicit Overwrite Contract

**Status:** mandatory policy for every Build 07 importer and every future importable product type. An import name collision is never an automatic replacement.

## Canonical-item rule

Each stable identity has exactly **one installed item**. The catalog never displays or accumulates duplicate items, side-by-side micro-revisions, or a user-managed revision history. This rule supersedes any earlier wording in this contract that implied normal imports create a growing set of installed revisions.

The currently installed item has one current content hash. Its audit log records replacement events and old/new hashes. During a replacement, the runtime may retain exactly one private last-known-good rollback copy until the new item is proven installed and enabled; it is not a second catalog item and is removed when no longer needed. Long-term audit keeps metadata and hashes, not a growing archive of package copies.

## What happens before import changes anything

Every importer performs a read-only **preflight** after safe archive/connection inspection and before it creates an active revision, overwrites files, replaces an audience binding, updates a catalog entry, or enables a capability.

The preflight result is one of:

| Result | Meaning | Required user action |
| --- | --- | --- |
| `new` | No installed item has the same stable identity. | User may confirm import. |
| `identical` | Same identity and identical canonical content hash already installed. | User may cancel or explicitly retain/re-enable the existing item; no duplicate is silently created. |
| `conflict` | Same identity exists but metadata, content, endpoint, components, permissions, or audience differs. | User must inspect the comparison and explicitly choose `cancel` or `replace`. |
| `blocked` | Validation, quarantine, policy, or ownership rule failed. | Import cannot continue. |

The confirmation response includes an unguessable preflight token bound to the inspected candidate, target identity, comparison hashes, selected agent audience, and short expiry. A browser cannot submit a bare “overwrite” flag, and the importer rechecks the token and installed revision immediately before its atomic commit.

## Replace means one atomic canonical replacement

`replace` updates the one canonical item only after the UI has obtained user confirmation. It keeps the existing item active while the new candidate is validated and staged, preserves at most one private rollback copy, switches the canonical item atomically, and writes one audit event with the old/new hashes and selected audience. There is no duplicate catalog record and no normal revision list.

If confirmation is absent, expired, or no longer matches the installed state, the importer stops without changing the current item. A same-name import can therefore never overwrite a user item by accident.

## Applies to every product type

| Import type | Stable identity compared during preflight | Comparison shown before `replace` |
| --- | --- | --- |
| Agent Skill | standard Skill name | content hash, description, declared `allowed-tools`, requested audience, revision history |
| Agent Plugin | standard Plugin id/name from manifest | package hash, component list, requested permissions, MCP definitions, requested audience |
| Direct MCP connection | user-owned connection name plus canonical endpoint identity | endpoint/transport, authentication requirement, discovered tool names, requested audience |
| Mail account setup | local mailbox slot and normalized account identity | account label, address, server settings, selected agent access; credentials are never returned or displayed |
| Creation | Creation identity derived by its owner compatibility record | artifact hash, Cards metadata, requested bridge audience, storage/data implications |
| Calendar, Contacts, and Reminders connections | user-owned connection name plus normalized remote identity | connector type, account/endpoint, sync scope, selected agent access |

## Ownership and implementation shape

`runtime/resono_runtime/imports/preflight.py` will own the generic immutable preflight result, token binding, expiry validation, and comparison model. Each type-specific importer owns identity extraction and its safe comparison details. The generic module never opens archives, connects to MCP, decrypts credentials, reads Mail, or mutates a catalog. Owning lifecycles call it before their one atomic install/replace transaction.

This policy is independent of the Agent Audience Router: preflight displays and binds a chosen `voice`, `text`, or `both` selection, while the Router persists that selection only inside a successful owner lifecycle commit.

## UI responsibility

The runtime exposes `new`, `identical`, `conflict`, and `blocked` preflight results. The future management UI owns notification wording, comparison presentation, and the explicit replacement control. No notification screen is part of this runtime checkpoint. The runtime's responsibility is simply to refuse replacement until it receives a valid confirmation bound to that exact inspected candidate.



## Skill document filename compatibility

The canonical installed form is the industry-standard `SKILL.md` at the Skill root. To make import practical for existing user work, the importer also accepts one standalone Skill document named `SKILL.md`, `SKILLS.MD`, or `skills.md`, whether supplied directly or as the sole Skill document in an archive. It records the source filename, validates the same front matter and body, and installs a canonical `SKILL.md` copy without altering the original uploaded archive. If more than one case variant is present, import fails as ambiguous. This is an R1 import compatibility rule, not a new Skill format: exported and installed Skills always use standard `SKILL.md`.

## The complete user outcome

A user can upload one standard Agent Skill archive through the future management API, inspect exactly what was accepted, choose whether it is enabled for Voice, remove it later, and understand any failure without the runtime becoming unsafe or inconsistent. The web interface will render these APIs in its later overhaul; it will not execute a Skill, invoke a tool, or make a side-effect approval.

## Required path, in order

1. **Receive:** accept a raw ZIP or TAR-family archive at the management boundary. Reject unsupported media types, an empty body, and bodies above the documented transport limit before archive processing.
2. **Inspect safely:** enumerate entries without extracting into a live directory. Reject absolute paths, parent-directory traversal, duplicate normalized paths, links, special files, oversized entry counts, oversized expanded content, and archives whose compression ratio signals a decompression bomb.
3. **Find one Skill root:** accept exactly one directory containing `SKILL.md`; reject a bare ambiguous collection, multiple Skills, or a package layout that tries to smuggle unrelated executable content into the accepted root.
4. **Validate the standard document:** parse front matter with the standard Skill rules already implemented in `runtime/resono_runtime/skills/specification.py`. Enforce the Skill-name/directory match, required name and description, allowed metadata shape, and preserved-but-never-granting `allowed-tools` declaration.
5. **Build a review record:** calculate content hashes; record archive type, received size, expanded size, every retained path, parsed metadata, source provenance supplied by the user, validation result, and the proposed immutable revision identifier. Do not trust user-provided IDs or paths.
6. **Quarantine first:** store the inspected archive and extracted candidate outside the active Skill directory. A malformed, blocked, or incomplete candidate remains inspectable for the owner but is never loadable by the agent.
7. **Install atomically:** only a fully valid candidate is copied into the canonical Skill store and committed with its immutable revision in one storage transaction. A failed write leaves neither a visible catalog entry nor an active filesystem tree.
8. **Register without granting:** catalog metadata may be made visible to the Voice runtime only after install. The importer does not grant any tool, network, credential, data, or agent permission. Tool availability remains the intersection at the Tool Catalog boundary.
9. **Enable and disable:** enabling makes the Skill eligible for relevant Voice turns; disabling immediately removes it from the disclosed/activatable Skill set while retaining its installed revision and audit record. Neither action changes canonical user data or connection credentials.
10. **Delete deliberately:** deletion is a separate lifecycle action. It must first disable the Skill, prove it has no active use, remove its active files and catalog visibility, retain an audit tombstone and integrity metadata, and never delete another revision or any user data. An immutable revision is never edited in place.
11. **Recover predictably:** an interrupted install, failed activation, or invalid upgrade rolls back to the last enabled revision. Quarantine is retained with an explicit reason and time, not silently discarded.
12. **Report truthfully:** the future API returns stable states such as `received`, `quarantined`, `installed`, `enabled`, `disabled`, `removed`, and `failed`, plus safe human-readable reason codes. It never reports an imported Skill as usable before the activation boundary has accepted it.

## Explicit non-goals for this checkpoint

- No Plugin archive intake, Plugin installation, MCP connection creation, Mail work, Creation import, or web UI implementation.
- No proprietary replacement for the Agent Skills directory and `SKILL.md` format.
- No arbitrary code execution, shell process, executable script, or automatic tool invocation from a Skill archive.
- No silent update of an installed Skill; every replacement creates a revision and follows the same validation/quarantine path.
- No deletion shortcut that erases audit history, user data, credentials, or unrelated package files.

## Required code ownership before implementation starts

| Concern | Owner | Responsibility |
| --- | --- | --- |
| Standard document parsing | `runtime/resono_runtime/skills/specification.py` | Parses and validates only `SKILL.md`; does not unpack archives, mutate storage, or grant access. |
| Archive intake safety | `runtime/resono_runtime/skills/archives.py` | Reads archive entries and creates a quarantined candidate; no database or agent dependency. |
| Durable records | `runtime/resono_runtime/storage/skills.py` and a versioned storage migration | Persists revisions, lifecycle state, hashes, audit events, and tombstones. |
| Lifecycle decisions | `runtime/resono_runtime/skills/lifecycle.py` | Coordinates validate, quarantine, atomic install, enable, disable, rollback, and delete through the dedicated owners. |
| Voice eligibility | `runtime/resono_runtime/skills/activation.py` | Projects only enabled, valid Skills to the Voice agent; cannot change lifecycle state or tool grants. |
| Future management transport | `runtime/resono_runtime/api/skill_routes.py` | Receives raw archive bytes and lifecycle requests, validates transport limits, and delegates. It does not contain archive or lifecycle logic. |

## Evidence required before the next checkpoint

1. Tests for every rejection listed above, including traversal, duplicate paths, links, multiple roots, compression limits, malformed front matter, interruption, rollback, disable, and delete.
2. Tests proving an imported Skill cannot add tools or permissions and cannot execute archive content.
3. Tests proving deletion cannot affect another revision, Mail, connections, or user data.
4. A documented API request/response contract with stable state and error names before any web screen is built.
5. An implementation record naming each changed file, migration version, focused test command, result, and any donor code provenance. No donor code may be copied without that record.

## 07B.1a Safe Archive Intake Record

**Status:** complete. This is the first separate implementation unit inside 07B.1; it does not authorize progress to Plugin work.

| File | Responsibility |
| --- | --- |
| `runtime/resono_runtime/skills/archives.py` | Receives raw bytes and a source filename; accepts a standalone `SKILL.md`, `SKILLS.MD`, or `skills.md`, or one ZIP/TAR-family archive; validates before extracting; writes a unique quarantined candidate only. |
| `tests/runtime/test_skill_archives.py` | Covers standalone compatibility input, one valid ZIP Skill root, traversal rejection, multiple-document rejection, and TAR link rejection. |

The archive owner has no database, API, permission, Tool Catalog, Plugin, MCP, Mail, Creation, or agent dependency. It cannot install, enable, execute, or overwrite a Skill. It preserves the source document name in quarantine and reports `SKILL.md` as the required canonical installed filename for the later lifecycle owner.

Focused evidence:

```bash
PYTHONPATH=runtime python3 -m unittest \
  tests.runtime.test_skill_archives \
  tests.runtime.test_skill_specification
```

Result: `Ran 7 tests ... OK`.

**Next separate unit:** `07B.1b`, canonical Skill catalog and lifecycle storage. It must implement one installed item per Skill name, preflight-only collision detection, explicit replacement handoff to the future UI, enable/disable/delete, and one private rollback copy without creating duplicate catalog entries. No Plugin work may begin.

## 07B.1b Canonical Skill Catalog Record

**Historical implementation record:** prototype only; not accepted. This record established one installed catalog item per standard Skill name, but the later full-phase review found that the catalog, filesystem, rollback, quarantine, and audience writes do not yet form one recoverable replacement operation.

| File | Responsibility |
| --- | --- |
| `runtime/resono_runtime/skills/specification.py` | Adds `parse_skill_document()` so a standalone `SKILL.md`, `SKILLS.MD`, or `skills.md` can be validated before its eventual standard install directory exists. `parse_skill()` retains the directory-name validation for canonical installed Skills. |
| `runtime/resono_runtime/storage/migrations/v007_skill_catalog.py` | Adds one-row-per-name `skill_catalog` and append-only `skill_catalog_audit` tables. |
| `runtime/resono_runtime/storage/skills.py` | Owns canonical Skill catalog persistence and audit records. A same-name save updates the current row and appends an audit event; it does not create a second catalog item. |
| `runtime/resono_runtime/storage/migrations/__init__.py` | Registers migration 7 in the ordered runtime migration chain. |
| `tests/runtime/test_skill_catalog.py` | Covers standalone document parsing and one-item same-name replacement behavior. |

Focused evidence:

```bash
PYTHONPATH=runtime python3 -m unittest \
  tests.runtime.test_skill_specification \
  tests.runtime.test_skill_archives \
  tests.runtime.test_skill_catalog
```

Result: `Ran 9 tests ... OK`.

**Next separate unit:** `07B.1c`, the Skill lifecycle coordinator. It will consume a quarantined candidate, calculate the comparison hash, return `new`/`identical`/`conflict`/`blocked` preflight results without mutation, require the later UI's explicit confirmation for a same-name replacement, atomically install one canonical filesystem tree, retain at most one private rollback copy, and then coordinate enable/disable/delete with the Agent Audience Router. No Plugin work may begin.

## 07B.1c Skill Lifecycle Record

**Historical implementation record:** prototype only; not accepted. The future management route/UI remains responsible for displaying preflight results and collecting explicit replacement confirmation. The implementation must still bind confirmation to the exact inspected current hash and selected audience, clean consumed/expired quarantine, and provide interruption recovery across filesystem and database state.

| File | Responsibility |
| --- | --- |
| `runtime/resono_runtime/config.py` | Adds canonical workspace paths for Skills, Skill quarantine, and one private Skill rollback location. |
| `runtime/resono_runtime/storage/skills.py` | Adds deliberate catalog removal with an audit record. |
| `runtime/resono_runtime/skills/lifecycle.py` | Owns preflight comparison, 10-minute preflight tokens, explicit same-name replacement confirmation, staged canonical filesystem install, one private rollback copy, selected `voice`/`text`/`both` audience binding, enable, disable, and delete. |
| `tests/runtime/test_skill_lifecycle.py` | Covers new install, selected audience, same-name conflict/no-mutation, confirmed replacement, one current catalog item, private rollback, enable, disable, and delete. |

### Lifecycle facts

- `preflight()` returns `new`, `identical`, `conflict`, or `blocked` without altering a catalog row, active filesystem tree, router binding, or current installed Skill.
- `confirm()` consumes the one-time 10-minute preflight token. A `conflict` cannot proceed unless the caller explicitly supplies `replace=True`; an identical item cannot create a duplicate.
- A successful replacement changes `workspace/skills/<skill-name>/` only after source validation/staging. The old canonical directory becomes the one private `workspace/skill-rollbacks/<skill-name>/` copy; an older rollback copy is replaced rather than accumulated.
- The database retains one `skill_catalog` row per name and append-only audit hash events. It does not expose a user revision list.
- The selected Agent Audience Router binding is restored on enable, deactivated on disable, and removed before delete. Skill instructions/tools are still not yet projected into either agent; the next activation unit owns that separate concern.
- No management API route, browser UI notification, Plugin, direct MCP connection, Mail, web search, Creation, or arbitrary archive code execution was added.

Focused evidence:

```bash
PYTHONPATH=runtime python3 -m unittest \
  tests.runtime.test_skill_lifecycle \
  tests.runtime.test_skill_archives \
  tests.runtime.test_skill_catalog \
  tests.runtime.test_skill_specification \
  tests.runtime.test_agent_audiences \
  tests.runtime.test_tool_catalog
```

Result: `Ran 18 tests ... OK`.

The first run exposed a missing reactivation path: `enable()` changed the catalog state but did not restore the already-selected audience after `disable()`. The lifecycle now restores that saved audience through the Router before recording `enabled`; the same focused group then passed.

**Next separate unit:** `07B.1d`, Skill activation and agent projections. It must disclose only enabled, standard validated Skill metadata/instructions to the selected Voice/text projection and must not give `allowed-tools` any granting power. Management API transport is after this projection is proved.

## 07B.1d Skill Activation and Agent Projection Record

**Status:** complete. This unit makes installed, enabled Skills usable through the existing agent/tool boundaries without adding a web execution path.

| File | Responsibility |
| --- | --- |
| `runtime/resono_runtime/skills/activation.py` | Lists only enabled Skills whose Audience Router selection includes the requesting agent; emits metadata disclosure; validates and loads full instructions only for that selected agent. |
| `runtime/resono_runtime/tools/definitions.py` and `tools/catalog.py` | Add agent-aware tool availability and handler support. This enables one local read-only loader tool to enforce the actual requesting `voice` or `text` audience at both listing and call time. |
| `runtime/resono_runtime/providers/controller.py` | Adds the Voice Skill-disclosure callback to the existing Realtime session instruction construction. |
| `runtime/resono_runtime/application.py` | Composes one Skill catalog/activation owner and registers the loader in the existing shared Tool Catalog. |
| `tests/runtime/test_skill_activation.py` | Proves Voice disclosure/full instruction loading and Text denial for a Voice-only Skill. |
| `tests/runtime/test_openai_provider.py` | Proves the existing Voice Provider Controller receives Skill disclosure text without full Skill instruction bodies. |

### Activation contract now implemented

1. A Skill in `installed` or `disabled` state is not disclosed and cannot be loaded.
2. An `enabled` Skill is disclosed to only the selected audience as `name` and `description`.
3. Full `SKILL.md` instructions are loaded just in time through `load_agent_skill({"name": "..."})`, not copied wholesale into the Realtime session prompt.
4. The loader has no side effects and returns no permission grant. `allowed-tools` remains a standard declarative field; it does not add a tool to either agent.
5. The same `SkillActivation.disclosures(AgentKind.TEXT)` and agent-scoped loader path are the integration surface Build 08 Background Agent execution uses. `TEXT` is the stable internal audience value; it does not create a user-facing text agent or a second Skill registry.
6. The existing Voice Provider Controller appends only selected Voice disclosures to session instructions; when no Voice Skills are enabled, it appends nothing and the loader is absent from the Voice tool catalog.
7. The management site still cannot invoke the loader or run a Skill.

Focused evidence:

```bash
PYTHONPATH=runtime python3 -m unittest \
  tests.runtime.test_skill_activation \
  tests.runtime.test_skill_lifecycle \
  tests.runtime.test_skill_archives \
  tests.runtime.test_skill_catalog \
  tests.runtime.test_skill_specification \
  tests.runtime.test_agent_audiences \
  tests.runtime.test_tool_catalog \
  tests.runtime.test_mcp_server \
  tests.runtime.test_openai_realtime_session \
  tests.runtime.test_openai_provider
```

Result: `Ran 33 tests ... OK`.

The first expanded run exposed two stale Provider test doubles that did not accept the already-established `tool_definitions` parameter. The doubles were aligned with the real provider boundary; the same group then passed. No production behavior was loosened.

**Next separate unit:** `07B.1e`, authenticated management API transport for Skill preflight, confirmed import, inspect/list, enable, disable, and delete. It must remain configuration-only: no Skill execution endpoint, no browser agent invocation, and no UI screen in this Build 07 code unit.

## 07B.1e Skill Management API Record

**Historical implementation record:** API prototype only; not accepted. It does not expose an endpoint that executes a Skill, invokes an agent tool, sends an action, or returns full Skill instructions, but its preflight transport does not yet bind the selected audience into the token and its raw-body boundary lacks the required read deadline and complete cleanup behavior.

### Implemented ownership

| File | Responsibility |
| --- | --- |
| `runtime/resono_runtime/api/skill_routes.py` | Owns only `/v1/management/skills` transport, request validation, stable response/error views, and delegation to the existing Skill archive/lifecycle owners. |
| `runtime/resono_runtime/api/routes.py` | Delegates the narrow Skill route module without adding archive/lifecycle logic to the general route table. Extends the transport protocol with bounded raw bytes. |
| `runtime/resono_runtime/api/http_server.py` | Implements bounded raw request reading while retaining loopback bearer authorization and the existing pairing/CSRF checks. |
| `runtime/resono_runtime/application.py` | Composes one Skill archive inspector, lifecycle, and route owner from existing runtime configuration paths. |
| `tests/runtime/test_skill_routes.py` | Covers management-only raw preflight, confirmation, metadata-only response, and unclaimed non-Skill route behavior. |

### Public route contract

| Method and path | Required protection | Request | Response | Explicitly does not do |
| --- | --- | --- | --- | --- |
| `GET /v1/management/skills` | paired browser session | none | canonical catalog metadata list | no full instructions, agent execution, or tool listing |
| `GET /v1/management/skills/{name}` | paired browser session | none | one canonical catalog item | no full instructions or execution |
| `POST /v1/management/skills/preflight` | paired browser session plus CSRF | raw body, `X-ReSono-Skill-Filename`, explicit ZIP/TAR/Markdown/octet-stream type | `new`, `identical`, `conflict`, or `blocked` comparison with candidate/current metadata and a bounded preflight token when valid | no install/replace, enable, tool grant, or execution |
| `POST /v1/management/skills/confirm` | paired browser session plus CSRF | JSON `preflightToken`, `audience`, `replace` | one canonical installed item | no automatic same-name overwrite; `conflict` requires `replace: true` |
| `POST /v1/management/skills/{name}/enable` | paired browser session plus CSRF | JSON object | catalog metadata | no web execution |
| `POST /v1/management/skills/{name}/disable` | paired browser session plus CSRF | JSON object | catalog metadata | no deletion of data or audit history |
| `DELETE /v1/management/skills/{name}` | paired browser session plus CSRF | none | `{name, deleted: true}` | no deletion of another item, connection, Mail data, or agent history |

The raw preflight endpoint rejects an absent/invalid body length, inputs over 16 MiB, unsupported media types, invalid filenames, unsafe archive structures, and archive failures before lifecycle mutation. The archive inspector retains accepted candidates in quarantine; a standard-document validation failure is returned as `blocked` and cannot be confirmed.

Focused evidence:

```bash
PYTHONPATH=runtime python3 -m unittest \
  tests.runtime.test_skill_routes \
  tests.runtime.test_skill_activation \
  tests.runtime.test_skill_lifecycle \
  tests.runtime.test_skill_archives \
  tests.runtime.test_skill_catalog \
  tests.runtime.test_skill_specification \
  tests.runtime.test_agent_audiences \
  tests.runtime.test_tool_catalog \
  tests.runtime.test_mcp_server \
  tests.runtime.test_openai_realtime_session \
  tests.runtime.test_openai_provider \
  tests.runtime.test_runtime_lifecycle \
  tests.runtime.test_management_pairing
```

Result: `Ran 44 tests ... OK`.

**07B.1 corrected state:** a functional prototype exists, but it is not accepted. Standard parsing and Voice disclosure are reusable; archive containment, shared preflight binding, replacement recovery, cleanup, lifecycle storage, API error contracts, and required negative evidence must be corrected before Plugin work may depend on it. The web management UI remains deliberately absent pending its separate overhaul.

# 07B.2 Standard Agent Plugin Normative Baseline

**Source frozen for this checkpoint:** Agent Plugins Specification v1.0.0, published specification and official schemas. The R1 implements the standard package model; it does not invent a replacement ReSono Plugin format.

## Required package facts

1. A Plugin is one directory with exactly one root `plugin.json` manifest. No other file replaces, supplements, or overrides its core manifest fields.
2. Root `plugin.json` is loaded and validated before component discovery. It requires the v1 canonical `$schema` value `https://agent-plugins.org/schemas/1.0.0/plugin.schema.json` and a valid standard Plugin `name`.
3. The manifest's portable top-level vocabulary is closed: `$schema`, `name`, `version`, `description`, `author`, `homepage`, `repository`, `license`, `keywords`, and `extensions`. Unknown fields must be reported and ignored, never interpreted as R1 behavior.
4. Agent Plugins v1 defines exactly two portable component types: immediate `skills/*/SKILL.md` directories and root `mcp.json`. Calendar, Mail, Contacts, Reminders, Connections, and Creations are not Plugin component types.
5. A missing `skills/` or `mcp.json` is not an error. An invalid individual Skill is skipped while valid sibling Skills/components continue. An invalid `mcp.json` disables only the Plugin MCP component. A fatal root manifest failure rejects the Plugin before component discovery.
6. Root/package paths and fixed component paths must resolve within the Plugin root. Archive links and unsafe paths are rejected before install. Plugin-relative MCP paths must begin with `./` and remain within the installed Plugin root.
7. Root `mcp.json`, when present, requires the v1 canonical MCP schema identifier and a closed object containing only `$schema` and `mcpServers`. Its schema version must match `plugin.json`; invalid individual server entries are skipped rather than invalidating valid components.
8. R1 will support Plugin package discovery before any MCP process/network connection. A Plugin import never launches a stdio command, makes an HTTP request, expands placeholders, or accepts credentials. Those belong to later MCP/Connection lifecycle work.
9. Portable Plugin packages contain no OAuth credential-reference format. R1 credentials remain in the separate encrypted Connection owner; package headers/environment values are visible package data and must never be treated as secrets.
10. A Plugin audience selection is an upper bound for its installed Skill/MCP components. A component can be narrower or disabled, but can never be exposed more broadly than its parent Plugin selection.

## 07B.2a next code unit

Create one safe Plugin package inspector that accepts the R1 raw ZIP/TAR compatibility transport, identifies exactly one Plugin root, validates root manifest/schema/name, discovers only standard fixed component locations, and quarantines the candidate. It will not install, enable, connect MCP, execute a process, or expose any component to an agent.

## 07B.2a Plugin Package Inspection Record

**Historical implementation record:** incomplete prototype; not accepted. It does not start a process, connect MCP, or accept a credential, but it is not a standards-conformant Plugin inspector because it does not validate optional manifest fields, contained Skills, or individual MCP server entries and it reads expanded archive members into memory before enforcing the aggregate limit.

| File | Responsibility |
| --- | --- |
| `runtime/resono_runtime/plugins/archives.py` | Validates ZIP/TAR package safety, exactly one Plugin root, required standard `plugin.json`, canonical v1 schema identifier, standard Plugin name, and fixed `skills/`/`mcp.json` discovery. |
| `tests/runtime/test_plugin_archives.py` | Covers valid standard manifest/Skill/MCP discovery and root-manifest rejection. |

Current behavior follows the Plugin v1 failure boundaries: a fatal root manifest failure rejects the package; an absent component is not an error; an invalid discovered Skill is reported separately; an invalid `mcp.json` is reported as an MCP component problem rather than executing or discarding a valid Plugin manifest/Skill component. Unknown root manifest fields are retained only as ignored-field diagnostics and are assigned no R1 behavior.

Focused evidence:

```bash
PYTHONPATH=runtime python3 -m unittest \
  tests.runtime.test_plugin_archives \
  tests.runtime.test_skill_archives \
  tests.runtime.test_skill_specification
```

Result: `Ran 9 tests ... OK`.

**Next separate unit:** `07B.2b`, one-canonical-item Plugin catalog, preflight conflict/replace, audience upper-bound storage, and lifecycle state. It must not yet start stdio MCP, connect remote MCP, or make Plugin Skills separately active; those component handoffs follow their own acceptance checkpoints.

## 07B.2b Plugin Canonical Lifecycle Record

**Historical implementation record:** incomplete prototype; not accepted. Plugin components remain inert, and the lifecycle lacks enable, disable, delete, rollback/recovery, management API composition, component handoff, and enforcement of the parent Plugin audience upper bound.

Implemented `plugin_catalog`/audit migration 8, `PluginCatalogRepository`, and `PluginLifecycle`. The lifecycle creates one canonical Plugin directory per standard manifest name, returns `new`/`identical`/`conflict` preflight, requires explicit replacement for a same-name different package, retains one private rollback directory, records the Plugin-level Agent Audience Router upper bound, and never starts MCP or activates bundled Skills.

Focused evidence:

```bash
PYTHONPATH=runtime python3 -m unittest \
  tests.runtime.test_plugin_lifecycle \
  tests.runtime.test_plugin_archives \
  tests.runtime.test_agent_audiences
```

Result: `Ran 6 tests ... OK`.

**Next separate unit:** Plugin component handoff. It must preserve the Plugin audience as an upper bound and hand validated bundled Skills to the existing Skill lifecycle/activation boundary and validated MCP definitions to the later MCP connection boundary. It must not run an MCP process or make a network connection in Build 07B.

## 07C.1 MCP Configuration Boundary Record

**Corrected status:** incomplete prototype; not accepted.

Migration 10 introduces canonical MCP connection/audit storage. `runtime/resono_runtime/mcp/connections.py` validates standard `streamable-http`, legacy `sse`, and `stdio` configuration structure without connecting, spawning a process, expanding placeholders, or storing credentials. Remote endpoints require HTTPS except exact loopback HTTP; URL credentials/fragments and shell-command strings are rejected.

Focused evidence: `PYTHONPATH=runtime python3 -m unittest tests.runtime.test_mcp_connections tests.runtime.test_mcp_server` resulted in `Ran 5 tests ... OK`.

## 07C.2a MCP Tool Discovery Record

**Corrected status:** incomplete prototype; not accepted.

`runtime/resono_runtime/mcp/tool_adapter.py` validates a standard MCP `tools/list` response into connection-scoped normalized records. It rejects malformed or duplicate tool names and does not itself expose, invoke, or grant any discovered tool. Focused evidence: `PYTHONPATH=runtime python3 -m unittest tests.runtime.test_mcp_tool_adapter tests.runtime.test_mcp_connections tests.runtime.test_mcp_server` resulted in `Ran 6 tests ... OK`.

# Build 07 Full Implementation Review and Stop Gate

**Review status:** failed. The earlier per-checkpoint completion labels are implementation notes, not acceptance. Build 07, 07B.1, 07B.2, and 07C must not be represented as complete until the findings below are corrected and re-reviewed. This section supersedes conflicting completion language later in this draft.

## Critical findings

1. **Plugin completion was claimed without a complete Plugin lifecycle.** `PluginLifecycle` implements only preflight and confirm. It has no enable, disable, delete, rollback command, management API, application composition, health projection, or component activation/deactivation. The parent Plugin audience is recorded but is not enforced as an upper bound when bundled components are consumed.
2. **Historical audit finding, since resolved: MCP/Connections was not wired into the product runtime.** At the time of this checkpoint, discovered remote tools could not appear in Voice or the future Background Agent. Later Build 07 implementation composed and projected MCP tools through the shared Tool Catalog; current implementation state is governed by the Build 08 execution ledger, not this historical finding.
3. **MCP credential ownership is absent.** There is no generic Keystore-backed Connection credential envelope, OAuth flow, write-only secret API, rotation behavior, or redaction proof. Direct configured headers reject a few common secret names but that is not credential security and does not support authenticated MCP servers.
4. **The MCP client is not a conformant Streamable HTTP implementation.** It assumes every response body is plain JSON, does not handle `text/event-stream`, does not send the initialized notification, does not fully negotiate protocol versions/capabilities, has no redirect-origin/header protection, and has no session termination/reconnect behavior. `sse` and `stdio` configurations are accepted even though no corresponding client runtime exists.
5. **The direct MCP import contract is incomplete.** `validate_connection_configuration()` validates one server object, not a standard root `mcp.json` document with canonical `$schema` and `mcpServers`. Plugin `mcp.json` and direct MCP configuration therefore do not yet share one standards-based parser/failure boundary.
6. **Skill and Plugin replacement are not atomic across filesystem, catalog, audit, and Agent Audience Router.** Filesystem moves, catalog writes, component writes, and audience writes use separate transactions. A later database/router failure can restore files while leaving catalog or audience state pointing at the failed replacement.
7. **Preflight confirmation is not fully bound to the inspected current state.** Skill and Plugin preflight store the candidate hash but not the exact existing hash/identity that was compared. If a current item changes to a third value between preflight and confirmation, the confirmation can replace a different state than the user reviewed.

## High findings

8. **Plugin validation is not Agent Plugins v1.0.0 conformant.** Manifest optional field types and `extensions` rules are not fully validated; bundled Skills are counted by file existence without running the Agent Skills validator; `mcp.json` validates only its top level and does not validate individual server variants, paths, placeholders, duplicate headers, secrets, or supported transport. Invalid-component reporting therefore overstates validation.
9. **Archive limits are applied after potentially expensive expansion.** Skill and Plugin ZIP/TAR readers may read full entry contents into memory before enforcing aggregate expanded-size limits. TAR compression-ratio protection is absent. This does not prove decompression-bomb resistance.
10. **Quarantine and rollback retention are incomplete.** Successful imports do not remove consumed quarantine candidates; rejected/expired candidates have no bounded cleanup policy; deleting a Skill does not remove its private rollback directory. Long-running devices can accumulate sensitive or stale package data.
11. **Plugin component records can outlive their parent.** `plugin_components` has no foreign key/cascade to the Plugin catalog, no removal path, and no transactional replacement with the parent catalog row.
12. **MCP configuration identity is incomplete.** Earlier hashes omit headers, environment, and working directory, so materially different connection configurations can compare as identical. The stored configuration path is not yet consistently populated by the lifecycle.
13. **MCP tool identity/projection is unfinished.** Discovered tools have no collision-safe exposed-name policy, durable grant/permission intersection, Tool Catalog registration/removal, effect classification, health availability, or connection-scoped invocation dispatcher.
14. **Historical audit finding: built-in agent exposure was too coarse for the Background Agent.** `builtin-tools` was bootstrapped to `both`, grouping device status and memory lookup under one audience binding. Later migrations separated built-in/domain resource identities. Current implementation state is governed by the Build 08 execution ledger.

## Structural and evidence findings

15. **The new Plugin and MCP code does not meet the project's clean-code acceptance bar.** Several files compress multiple statements onto single lines, omit public models/error contracts, and mix lifecycle coordination with filesystem/database details. They require cleanup before another feature is layered on top.
16. **The authoritative document contradicts itself.** Earlier sections require immutable revisions/active pointers, while later owner direction requires one canonical user-visible item and at most one private rollback copy. The final storage and rollback rule must be stated once and conflicting text removed.
17. **Focused tests were too narrow to justify completion.** Plugin lifecycle evidence covered one happy replacement. MCP transport evidence uses a small mocked JSON response and does not cover SSE framing, handshake failure, redirects, auth, timeout, reconnect, duplicate tools, disable/delete, restart restoration, or Tool Catalog projection.
18. **The complete runtime suite is not green in the current host environment.** `PYTHONPATH=runtime python3 -m unittest discover -s tests/runtime -p 'test_*.py'` ran 89 tests with one failure because the host is not Python 3.13. This is an environment-specific failure, but it means there is no clean full-suite result for the current workspace. Android/Chaquopy packaging and physical runtime evidence were not run in this review.
19. **No Build 07 Android/API/package acceptance exists.** There is no APK packaging proof for migrations 6-12 and new modules, no authenticated Plugin/MCP management API capture, no restart recovery proof, and no physical Voice tool proof.

## Corrected phase status

- `07A`: implemented foundation; retain its recorded focused evidence.
- `07B.0`: implemented foundation, but built-in audience granularity requires remediation.
- `07B.1`: functional prototype, not accepted; atomicity, preflight binding, cleanup, and packaging evidence remain.
- `07B.2`: incomplete and not accepted.
- `07C`: incomplete and not accepted.
- `07D` through `07F`: not started.

## Mandatory recovery order

1. Freeze one canonical replacement/rollback rule and remove contradictory revision language.
2. Repair archive streaming limits, quarantine cleanup, preflight state binding, and cross-owner transaction/compensation rules.
3. Complete and retest the Skill lifecycle before treating 07B.1 as accepted.
4. Replace the partial Plugin parser with schema-accurate manifest, Skill, and MCP component validators; finish Plugin lifecycle/API/removal and parent-component enforcement.
5. Define one standard MCP configuration parser used by Plugin and direct imports.
6. Add the generic Keystore-backed Connection credential boundary before authenticated MCP connections.
7. Implement only supported MCP transports truthfully, then add discovery, persistence, health, Tool Catalog projection, invocation, disable/delete, restart restoration, and management APIs.
8. Run focused negative tests, full runtime tests in the required Python environment, Android packaging/boundary checks, and physical acceptance before advancing to Mail.

## Code-to-contract correction map

This map is the controlling implementation handoff for recovery. Earlier implementation records describe what was attempted; they do not authorize another layer to depend on unfinished behavior.

| Concern | Current code finding | Disposition | Required owner and wiring |
| --- | --- | --- | --- |
| Shared import preflight | Skills, Plugins, and MCP each keep unrelated in-memory token tuples. Tokens do not bind the exact current hash and selected audience. | **Replace** the duplicated token logic. | Add `runtime/resono_runtime/imports/preflight.py` as the sole token/comparison/expiry owner. Type-specific lifecycles provide identity, candidate hash, expected current hash, safe comparison data, and requested audience. Confirmation must fail if any bound value changed. |
| Shared archive containment | Skill and Plugin readers duplicate containment rules. Plugin extraction reads every expanded member into memory before checking the aggregate limit. Neither implementation consistently rejects nested archives or package content outside the one accepted root. | **Replace** duplicated low-level archive enumeration with one streaming, limit-enforcing owner; retain type-specific layout validation. | Add a narrow `runtime/resono_runtime/imports/archives.py`. It owns entry enumeration, normalized-path uniqueness, links/special files, depth, nested/encrypted archives, per-entry/aggregate expansion, compression ratio, streamed quarantine writes, and cleanup. Skill/Plugin/Creation owners decide their allowed layout and content. |
| Skill parser | `skills/specification.py` is small and correctly keeps `allowed-tools` non-authoritative. | **Keep and harden** against the pinned Agent Skills fixtures. | `skills/specification.py` remains the only Skill document parser. It must be used for standalone and Plugin-contained Skills. |
| Skill archive layout | `skills/archives.py::_find_skill_document` accepts a root-level document and does not prove that every retained entry belongs to the one Skill root. It also preserves nested archives/scripts without the required compatibility/findings classification. | **Rewrite** layout validation on the shared archive owner. | `skills/archives.py` accepts the explicit standalone-document compatibility path or exactly one Skill directory. Installed output is canonical `SKILL.md`; scripts are inventoried and never executed. |
| Skill replacement | `skills/lifecycle.py` moves files, then commits catalog and audience changes in independent database transactions. Failure or process death can split them. It leaves consumed quarantine and rollback content behind. | **Rewrite** as a recoverable operation, not a chain of best-effort calls. | `skills/lifecycle.py` owns a durable operation state, staged tree, prior catalog/audience snapshots, atomic active-path switch, commit/compensation, restart reconciliation, and bounded quarantine/rollback cleanup. Repositories must expose transaction-scoped operations rather than opening their own connections for every step. |
| Skill API | `api/skill_routes.py` is correctly separated from execution, but audience is supplied only at confirmation and the body reader has no concern-specific read deadline. | **Keep transport separation; change contract.** | Preflight must receive and bind `voice`, `text`, or `both`; confirm supplies only the token and explicit replace decision. Stable errors distinguish invalid, expired, stale-current, identical, and ownership conflict. |
| Built-in audience identities | Historical checkpoint: `tools/builtins.py` bound device status and memory lookup to one `builtin-tools` resource. | **Resolved by later resource-specific migration; retain regression coverage.** | Each built-in/domain tool set has a stable source resource and explicit default. The Background Agent receives only resources selected for internal audience `text`; Voice uses `voice`. |
| Tool Catalog | The catalog is the correct shared projection seam, but `voice_available` gates every agent and its hand-written schema check implements only a small JSON Schema subset. It has no durable imported-tool grant/effect model. | **Keep the seam; rewrite the availability/grant model.** | `tools/catalog.py` remains the only list/invoke owner. Source enabled state, source audience, per-tool grant, effect classification, health, and caller agent are intersected before listing or invocation. Standard JSON Schema validation is used for imported MCP input. |
| Plugin inspection | `plugins/archives.py` checks only a small manifest subset, treats a Skill as valid when a file exists, and checks only the `mcp.json` top level. | **Rewrite against bundled pinned schemas.** | Split package intake from `plugins/specification.py` manifest/component validation. Reuse the Skill parser and the one MCP configuration parser. Report independent component failures without overstating validation. |
| Plugin lifecycle | `plugins/lifecycle.py` implements only preflight/confirm, uses independent catalog/component/audience commits, and is not composed into the application or API. | **Rewrite and complete before composition.** | Plugin lifecycle owns install, enable, disable, delete, one private rollback, recovery, component handoff/withdrawal, source ownership, and parent-audience upper bound. Plugin components use a foreign key/cascade and are committed with their parent. |
| MCP configuration | `mcp/connections.py` validates one server object rather than the standard root document. The lifecycle hash omits headers, env, and cwd, and `confirm()` currently constructs a stored record without its configuration, so `configuration_json` becomes `{}`. | **Replace with one standard parser and complete identity.** | `mcp/specification.py` parses pinned root `$schema` plus `mcpServers`, then validates each closed server variant. Plugin and direct import use it. Canonical hashes cover every non-secret option. Secret material is referenced through Connections and excluded from package/config hashes only by an explicit field rule. |
| MCP transport | `mcp/client.py` is a JSON-only urllib proof, omits the initialized notification and SSE response handling, follows redirects without origin/header policy, and has no session termination/reconnect lifecycle. | **Replace; do not patch incrementally.** | Implement only pinned and proven Streamable HTTP behavior first. Unsupported SSE and stdio definitions remain visible-but-disabled findings. The client enforces protocol negotiation, SSE/JSON responses, session ID/version headers, redirects, DNS/IP SSRF checks, timeouts, response limits, shutdown, and secret redaction. |
| MCP discovered tools | `mcp/tool_adapter.py` retains only name/description/schema and has no durable grant, collision policy, annotations, protocol/server identity, health, or forwarding path. | **Rewrite and wire through the Tool Catalog.** | Discovery records source connection, original name, deterministic exposed name, schema, annotations, server/protocol identity, timestamp, health, and disabled/ungranted defaults. Forwarding can occur only through the local catalog invocation boundary. |
| Connection credentials | No generic Keystore-backed connection credential envelope exists. | **Missing dependency; build before authenticated MCP or Mail.** | `runtime/resono_runtime/connections/` owns safe records/lifecycle and the only Python credential-envelope bridge. Android Keystore retains the key; SQLite stores ciphertext envelopes only. Domain-specific APIs own credential intake and deletion. |
| Runtime/API composition | `RuntimeApplication` composes Skills only. Plugin and outbound MCP objects have no startup restoration, shutdown, health, routes, or Tool Catalog registration. | **Do not compose prototypes.** | Compose each owner only after its lifecycle and tests satisfy this map. `application.py` wires owners; it does not absorb their logic. `api/routes.py` delegates narrow route modules. Android proxy allowlists the exact authenticated management prefixes only when real APIs exist. |
| Tests and evidence | Current focused tests prove happy paths and small units, not the failure boundaries used to claim completion. | **Replace completion claims with evidence gates.** | Add negative fixtures for schema, archive bombs, stale preflight, interruption points, rollback, restart, source ownership, component withdrawal, SSRF/redirect/auth/SSE, grants, collisions, and delete isolation. Then run the required Python environment, Android packaging/boundary checks, API captures, and physical Voice evidence. |

## Additional audit findings

20. `skills/archives.py` does not enforce the contract's one-root rule. A root-level Skill document or unrelated sibling root can enter the quarantined content tree and influence the canonical content hash/install.
21. The current Skill and Plugin archive paths do not implement the documented nested-archive and executable/script findings policy. The absence of execution in today's code does not make an unclassified executable package safe or standards-truthful.
22. Raw upload reads are bounded by declared byte count but have no archive-specific read deadline. A paired client can hold a runtime request thread open with an incomplete body.
23. Outbound MCP URL validation checks syntax and HTTPS but not resolved address classes, DNS rebinding, redirect targets, or cross-origin forwarding of headers. It does not meet the donor-derived SSRF boundary.
24. `McpConnectionLifecycle.confirm()` does not persist the validated full configuration: the positional `StoredMcpConnection` construction leaves `configuration` unset, and repository storage writes an empty object.
25. The MCP configuration hash excludes headers, environment, and working directory. A materially changed server definition can be reported as identical and bypass the required comparison.
26. `plugin_components` has no foreign key to `plugin_catalog`; replacing parent and components uses separate transactions. A component catalog can therefore describe a package state that was never successfully installed.
27. The generic Tool Catalog's `voice_available` flag remains internally misnamed and also participates in Background Agent projections. Build 08 must not expose that name as a public Background Agent contract; any cleanup must preserve behavior and focused coverage.
28. The hand-written tool argument checker is not a JSON Schema implementation. Imported MCP schemas using arrays, nested objects, enums, unions, numeric constraints, or references would be listed but not validated correctly.
29. Plugin-contained Skills are not source-owned Skill catalog records, so the required `409 source_owned` delete boundary and parent disable/uninstall withdrawal behavior cannot currently exist.
30. No durable import-operation record exists. The runtime cannot reconcile a process death between filesystem switching and database/audience commits, so the current use of `os.replace` alone is not an atomic lifecycle proof.
31. The pinned Agent Plugins schema artifacts are not present in this repository, the referenced Voice donor, or the drift-protection repository. Attempts from the current environment to retrieve the two official schema URLs returned no content. Plugin parser replacement is therefore stopped at a material authority gate: implementation may not reconstruct or approximate the official schemas from memory.

## Recovery implementation record - shared preflight and first Skill corrections

**Status:** implemented but not yet validated or accepted. This record does not advance the checkpoint.

| File | Correction |
| --- | --- |
| `runtime/resono_runtime/imports/preflight.py` | Adds the one shared 10-minute opaque preflight registry. A record binds stable identity, candidate hash, exact expected current hash, selected `voice`/`text`/`both` audience, comparison state, expiry, and owner payload. Confirmation compares the current hash before consuming the token. |
| `runtime/resono_runtime/skills/lifecycle.py` | Uses the shared preflight owner, obtains the current Skill by the token-bound identity rather than scanning the catalog, preserves the preflight-bound audience, removes blocked/expired/consumed quarantine candidates, and removes the private rollback directory on deletion. |
| `runtime/resono_runtime/api/skill_routes.py` | Moves audience selection to Skill preflight through `X-ReSono-Agent-Audience`; confirmation no longer accepts a mutable audience value. Invalid audience input is a bounded management error. |
| `runtime/resono_runtime/skills/archives.py` | Requires exactly one top-level Skill directory for archives, rejects unrelated sibling roots and nested archives, and adds aggregate TAR compression-ratio enforcement. The explicit standalone `SKILL.md`/`SKILLS.MD`/`skills.md` compatibility path remains separate. |
| `runtime/resono_runtime/tools/builtins.py` and `runtime/resono_runtime/application.py` | Replace the coarse `builtin-tools` audience identity with `device-status` and `memory`. Device status preserves `both`; memory defaults to Voice only. |

The first attempted preflight integration contained a wrong catalog scan and a missing `secrets` import. That patch was not treated as evidence. It was corrected immediately after owner authorization: confirmation now peeks the bound identity, fetches only that item, compares its exact current hash, then consumes the token. No test or acceptance claim is made here.

Still required before `07B.1` can pass: durable import-operation storage, transaction-scoped catalog/audience writes, restart reconciliation for process death around the filesystem switch, complete negative tests, required-Python execution, Android packaging, and physical/API evidence.
## Implementation closure record - 2026-08-20

This is the implementation handoff. It narrows planning language to code that exists and does not waive physical acceptance.

### Canonical owners and wiring

| Concern | Canonical owner | Connection |
|---|---|---|
| Agent audience | `runtime/resono_runtime/agents/audience.py`, `agents/routing.py` | Filters Skill activation and Tool Catalog projection for Voice, Text, or Both |
| Shared import | `runtime/resono_runtime/imports/preflight.py`, `imports/recovery.py` | Ten-minute preflight, exact replacement, swap journal, startup reconciliation |
| Skills | `runtime/resono_runtime/skills/` | Standard Skill parsing/catalog/lifecycle/activation and management API |
| Plugins | `runtime/resono_runtime/plugins/` | Agent Plugins 1.0 package lifecycle; delegates contained Skills and MCP definitions |
| MCP | `runtime/resono_runtime/mcp/` | Standard `mcp.json`, Streamable HTTP discovery/calls, explicit grants, Tool Catalog |
| Connections | `runtime/resono_runtime/connections/`, `api/connection_routes.py` | Mail/MCP state and authenticated unified health projection; encrypted envelopes remain separate and write-only |
| Tools | `runtime/resono_runtime/tools/` | One JSON-Schema-validating projection/dispatch authority for Voice and future Text |
| Mail | `runtime/resono_runtime/domains/mail/` | Local domain/store, IMAP/SMTP connector, scheduler, Voice tools, management APIs |
| Web search | `runtime/resono_runtime/tools/web_search.py` | Shared OpenAI access resolver; Platform JSON and subscription Codex SSE |
| Creations | `runtime/resono_runtime/creations/` | Static ZIP inspection, catalog, recovery, audience, generation, authenticated APIs |
| Cards | `android/feature/cards/` | Runtime Creation catalog/assets, Voice/Cards navigation, touch/wheel input |
| Management transport | `runtime/resono_runtime/api/*_routes.py`, `android/runtime-host/.../ManagementRuntimeProxy.java` | Authenticated APIs only; no Build 07 management UI |

### Global import contract

1. Parse and validate in quarantine before canonical state changes.
2. Derive stable identity from the package; never create revision-suffixed duplicates.
3. Preflight returns `new`, `unchanged`, or `replace_required`, hashes/current record, and a one-use ten-minute token.
4. Replacement requires explicit `replace=true`. The future UI owns the warning; the runtime always enforces confirmation.
5. Confirmed replacement atomically keeps one canonical identity. Enable, disable, inspect, list, and delete are separate lifecycle actions.
6. Audience is selected at preflight as `voice`, `text`, or `both`; one router filters activation and tools without creating another agent loop.
7. Skills, Plugins, MCP, and Creations reload dynamically. No reboot is required.

Accepted shapes:

- Skill: standard directory/ZIP or a single case-insensitive `SKILL.md` file; canonical manifest remains `SKILL.md`.
- Plugin: Agent Plugins 1.0 ZIP with `plugin.json`, optional `skills/`, and optional `mcp.json`.
- MCP: standard `mcp.json`; proprietary connection JSON is rejected.
- Creation: bounded static-site ZIP with root `index.html` or one enclosing directory. Unsafe paths, links, encryption, executables, unsupported suffixes, excessive expansion, and unsafe compression ratios are rejected.

### Mail invariants

- Account four is rejected transactionally before credentials persist; public projections never expose plaintext.
- Five-minute scheduling, ten-minute reclaimable leases, paged durable checkpoints, and fair resume cover every discoverable folder and UID.
- Complete-folder reconciliation uses a temporary UID table, avoiding SQLite parameter limits on large mailboxes.
- Agent reads use SQLite. Attachment bytes require explicit bounded retrieval.
- SMTP occurs once after exact draft confirmation. Sent retry reuses exact MIME and checks Message-ID before IMAP append, preventing SMTP resend and duplicate Sent copies.
- Draft composition records the trusted native utterance sequence. Sending requires a strictly later explicit affirmative transcription from the same Voice session; the model has no `approved` argument and stale utterances cannot authorize a later draft.
- `runtime/resono_runtime/plugins/bundled/resono-mail/` ships the standards-valid first-party Mail Plugin and `voice-mail` Skill. Runtime bootstrap installs it through the same quarantine/preflight/lifecycle path as an upload. An owner deletion is retained as a catalog tombstone and is never undone on restart.
- No Mail delete/trash/expunge/purge tool, service action, or provider mutation exists.

### Creations compatibility boundary

Build 07 implements static Creation import/catalog/display/delete and dynamic Cards reload. Imported content receives only authenticated local assets and focused wheel/side browser events; external navigation, file/content access, DOM/database storage, and Android JavaScript objects are blocked.

The SDK also documents privileged globals for LLM/journal messaging, native touch injection, persistent plain/secure storage, and accelerometer access. This static vertical does not fake or silently expose them. They require separate narrow owners, per-Creation grants, encrypted storage, sensor lifecycle enforcement, and a Creation-specific Agents SDK path with no inherited personal-data tools. Imports requiring those globals are therefore not yet compatible.

### Evidence

- Focused audited Build 07 runtime tests: 26 passed, including unpaired denial across every Build 07 management route group, opaque credential persistence, and bundled Plugin deletion persistence.
- Full host runtime suite: 112 executed; 111 passed. Only `test_runtime_environment` failed because the host is Python 3.11 and production requires Python 3.13.
- Android build: `BUILD SUCCESSFUL`, 196 tasks, `standalone Android boundaries: OK`, `embedded runtime package: OK`; packaged runtime is Python 3.13.
- Candidate: `artifacts/local-builds/ReSonoR1-build07-final-audit2-20260820T180000Z.apk`.
- SHA-256: `f26407acc926be0a3c1842f6033d49ad529f7b3ecfdcf8864f96ae5dcbcfe5b2`.

### Open acceptance

Physical proof remains required for real multi-client Mail sync/Sent visibility, Voice draft review and exact send confirmation, both web-search access paths, encrypted credentials on device, dynamic import/replace/delete, and native Cards rendering/input. No management UI import/setup surface is part of this contract.

### Physical Voice account-selection correction

Mail tools never expose or request an internal account UUID from the user. With one available account, the runtime selects it automatically. With multiple accounts, the tool result names each configured account by label and email address and instructs Voice to ask which human-readable account the user wants; subsequent calls accept that label or email address as the optional `mailAccount` selector.

### Deleted-message visibility correction

Complete provider synchronization still retains remote mailbox state, but Trash/Deleted folders and messages carrying the IMAP `\\Deleted` flag are excluded at the canonical Voice repository boundary. They cannot enter folder listings, message lists, unread results, search, contact lookup, reads, attachment retrieval, or Voice mutations. The agent has no tool that can reveal or act on deleted mail.

The first deployed form of this correction contained malformed Python SQL-string construction. Gradle packaged the source without compiling every embedded module, so Android assembly passed while runtime import failed before port 8765 bound. `android/scripts/check_runtime_package.sh` now extracts the exact packaged `app.imy` and compiles the complete `resono_runtime` tree with the production Python 3.13 build host. Any future embedded Python syntax failure now fails the canonical APK build before deployment.

Physical preflight on 2026-08-20 returned an empty `adb devices -l` list and `adb: no devices/emulators found`. Therefore no candidate was installed and no physical claim was inferred. Real Mail credentials and both configured OpenAI access paths are also required for the remaining provider evidence.
# Physical implementation finding: WebView provider selection

The 2026-08-20 physical Build 07 install exposed a system-image prerequisite:
`com.android.webview` was present, enabled, and framework-valid, but
WebViewUpdateService had selected no current provider. Constructing the real
Cards surface consequently crashed HOME with `MissingWebViewPackageException`.
Selecting `com.android.webview` through WebViewUpdateService restored HOME and
loaded its sandboxed Chromium process successfully. Final image acceptance must
therefore prove a selected, initialized AOSP WebView provider before Cards and
Creations acceptance; an application mock or disconnected fallback is not an
acceptable substitute.

The same physical pass found that Android's 320-dpi WebView scaling did not
match the native 480x640 composition. Physical captures established 120% as
the host-owned Cards deck's native/reference match; a naive 50% density ratio
overcorrected and was rejected. Imported Rabbit Creations retain their separate
SDK-native WebView scale; the runtime must not rewrite or globally zoom Creation
packages.

Physical correction evidence: candidate
`artifacts/local-builds/ReSonoR1-build07-cards-scale-final-20260820T1253.apk`,
SHA-256 `9d71f3cfc75334e2f16f0a83cc6488788df3c640a9da003667ee93a8bf48da20`,
installed with application data preserved. The 196-task Android build,
standalone boundary check, and embedded-runtime package check passed. HOME and
Cards launched without `MissingWebViewPackageException` or another fatal
exception, and the 480x640 capture showed the complete header, tabs, empty
catalog state, and both navigation controls without clipping.

**Owner rejection after physical inspection:** the 120% scale candidate is not
accepted. Switching pages still exposes a renderer/resolution change, and the
HTML Cards header does not match the native Voice header. Android's
`WebView.setInitialScale()` explicitly does not account for screen density, so a
measured percentage is not an authoritative product layout contract.

Required correction boundary:

- One native product chrome must own the Voice mark/title, device icon, Voice /
  Cards tabs, divider, active indicator, touch targets, typography, and colors.
- Voice and Cards content must render below that one chrome; neither page may
  redraw its own header or tabs.
- The built-in Cards catalog/deck is product UI and should render natively from
  the real Creation catalog. It must not require WebView zoom.
- Only an activated imported Creation uses the isolated WebView host. Rabbit's
  SDK reference canvas is 240x282 CSS pixels, so that host must preserve the
  Creation's standard logical viewport rather than inherit a Cards-shell zoom.
- The rejected 120% scale remains evidence only and must not be promoted as the
  accepted Build 07 candidate.

## Implemented correction: one native screen with tabs

Voice and Cards are not separate pages. `ProductRootView` owns one persistent
native `ProductChromeView`, and tab selection swaps only the native content
view beneath it. `VoicePageView` no longer draws product chrome. The built-in
Cards catalog is a native `CardsDeckView` driven by the real
`CreationCatalogClient`; the obsolete HTML deck and `setInitialScale` workaround
were removed. Only activation of an imported Creation opens
`CreationWebViewHost`, sized to the Rabbit SDK's 240x282 logical canvas, and the
native chrome returns when that Creation closes.

Physical candidate:
`artifacts/local-builds/ReSonoR1-build07-native-tabs-final-20260820T1315.apk`,
SHA-256 `83fcbeab84e045e479905f89bdd8ac0be0c6bee7003d87037680aa848973c91f`.
The 196-task Android build, standalone boundary check, and embedded-runtime
package check passed. The candidate installed with data preserved; Voice and
Cards captures show one unchanged native header/tab geometry with only the
selected-tab treatment and content changing, and logcat contains no fatal
exception. Owner visual/interaction acceptance remains required.

## Rabbit Creation QR interoperability finding

Rabbit's official Creations support and open-source QR generator establish a
second real distribution form in addition to a local archive. The QR payload is
JSON with these fields:

```json
{
  "title": "Required display title",
  "url": "Required hosted HTTPS Creation entry URL",
  "description": "Display description",
  "iconUrl": "Optional HTTPS icon URL",
  "themeColor": "Optional #RRGGBB accent"
}
```

The QR does not contain or guarantee a downloadable Creation archive. Its `url`
points to the hosted HTML application. Build 07 must therefore distinguish two
Creation source types without creating two catalogs:

- `local_archive`: the existing validated archive is copied into canonical
  device storage and served through the local Creation asset route.
- `rabbit_qr_link`: the validated Rabbit descriptor is stored in the same
  Creation catalog and launches its HTTPS URL in the isolated Creation runner.

Both source types use the same catalog identity, overwrite preflight/confirm,
enable/disable, generation refresh, Cards presentation, and delete lifecycle.
Creation confirmation now completes in the `enabled` state for every Creation
source type. Import therefore makes the Creation immediately available in Cards;
the canonical lifecycle `disable` action remains the sole implementation behind
management's **Turn off** control, and `enable` restores it without reinstalling.
Deleting a linked Creation removes its descriptor and grants; it does not
attempt to delete the publisher's remote site. Purging the linked origin's
WebView DOM storage remains a required device acceptance item and must not be
claimed complete from host-only evidence.

Import boundary for the future management UI:

- The browser may scan an uploaded QR image locally or accept pasted QR JSON /
  a Rabbit QR-generator share URL.
- The management UI submits only the decoded descriptor to the authenticated
  Creation preflight API. QR image decoding is presentation work and does not
  belong in the runtime lifecycle.
- The runtime validates the exact field contract, requires HTTPS, applies URL /
  public-address safety checks before confirmation, shows the resolved origin
  and overwrite impact, and never installs before explicit confirmation.
- The device camera is not a Build 07 dependency. Camera scanning can be added
  after the deferred camera defect is resolved, using the same descriptor
  preflight contract rather than a second install path.
- Rabbit's public gallery may supply QR descriptors, but R1 must not scrape or
  depend on an undocumented Rabbit gallery API. Gallery browsing remains an
  external discovery step unless Rabbit publishes a stable catalog contract.

The linked runner must preserve the Rabbit SDK's 240x282 logical viewport, deny
cleartext URLs and local/file/content access, expose only explicitly implemented
Creation SDK globals, and keep the native Voice/Cards shell outside the WebView.
This is interoperability with Rabbit's published QR format, not a claim that a
remote Creation has been downloaded for offline use.

### QR implementation map

- `runtime/resono_runtime/creations/descriptors.py` owns strict Rabbit QR JSON
  parsing, normalization, identity, canonical hashing, HTTPS/public-origin
  validation, and quarantine candidate creation. It does not perform lifecycle
  writes or HTTP routing.
- `runtime/resono_runtime/creations/lifecycle.py` remains the only Creation
  preflight/confirm/overwrite/enable/disable/delete owner. Both archive and QR
  candidates use its existing ten-minute token, recovery, audience, audit, and
  generation boundaries.
- `runtime/resono_runtime/storage/migrations/v025_creation_sources.py` adds the
  source discriminator and linked metadata to the existing catalog. No second
  linked-Creation table or registry is permitted.
- `runtime/resono_runtime/storage/creations.py` remains the canonical catalog
  repository and maps the new columns into `StoredCreation`.
- `runtime/resono_runtime/api/creation_routes.py` adds authenticated
  `POST /v1/management/creations/qr/preflight`; the existing confirm, list,
  enable/disable, and delete routes remain shared.
- `runtime/resono_runtime/application.py` constructs and injects the descriptor
  inspector. No network/import logic belongs in application composition.
- `android/runtime-host/.../CreationCatalogClient.java` continues to fetch one
  normalized catalog; it does not create a second QR client.
- `android/feature/cards/.../CardsDeckView.java` continues to render source-
  neutral native cards.
- `android/feature/cards/.../CardsPageView.java` selects the entry value and
  opens the single isolated runner.
- `android/feature/cards/.../CreationWebViewHost.java` owns local-versus-linked
  navigation policy. Local assets remain `https://resono.local`; linked entries
  require HTTPS and cannot navigate to file/content/local/private literals.
- `tests/runtime/test_creations.py` mirrors archive and QR lifecycle behavior,
  overwrite across source types, validation rejection, dynamic generation, and
  deletion.

The runtime API accepts decoded descriptor JSON, not PNG/JPEG QR images. Browser
image decoding belongs to the later management-interface overhaul; device image
decoding belongs to the later camera work. Both feed this same preflight route.

Host implementation evidence on 2026-08-20: migration 25, strict descriptor
inspection, shared lifecycle/catalog persistence, authenticated QR preflight,
native source-neutral Cards selection, and isolated linked HTTPS runner wiring
are implemented. The focused Creation/auth tests pass (`Ran 4 tests ... OK`),
the focused Build 07 owner suite passes (`Ran 27 tests ... OK`), and the Android
build passes all 196 tasks plus standalone-boundary and embedded-runtime checks.
The exact uninstalled host candidate is
`artifacts/local-builds/ReSonoR1-build07-rabbit-qr-host-20260820T1345.apk`,
SHA-256 `86c6e1ee588e01d78aa2ef295ee256611c47b6191b9fa8a7deb79a7137c2614b`.
The R1 was intentionally unplugged for owner review, so real QR import, remote
rendering, persistent DOM storage, delete storage purge, and physical Cards
refresh remain unaccepted device evidence.

### Physical Voice web-search correction and acceptance

Physical R1 testing on 2026-08-20 proved the subscription-backed `web_search`
path through the canonical Voice Tool Catalog. The tool used the shared
ChatGPT/Codex subscription access resolver, returned current search content to
the live Realtime session, and the Voice session remained live after the
answer.

Two native bridge defects were found and corrected during that proof:

- the Android MCP client abandoned a valid long-running search after 10
  seconds, causing the runtime HTTP response to encounter `BrokenPipeError`;
  the read deadline is now 65 seconds while the runtime provider retains its
  bounded search deadline;
- native Voice sent `response.create` while Realtime still owned an active
  response. The first attempted correction added a 150 ms delay after
  `response.done`; repeated physical sessions proved that change incomplete and
  not donor-equivalent. The later correction assigns all client-originated
  response creation to `RealtimeResponseCoordinator` and serializes tool
  execution.

The provider rejection was captured exactly as
`conversation_already_has_active_response`; provider error payloads are now
logged before the session enters its truthful error state. The rebuilt APK
passed all 299 Android build tasks, standalone-boundary checks, and embedded
runtime-package checks before deployment. One owner test returned a search
answer and retained the session, but later sessions reproduced the
active-response rejection. Web-search execution is proved; stable multi-session
Voice continuation requires renewed acceptance.

This accepts only the ChatGPT/Codex subscription path. A separately selected
OpenAI Platform credential search, citation/source presentation, revoked-access
failure, and restart recovery remain required evidence.

### Global Voice approval authorization

Tasks, Calendar, and Mail previously compared the latest transcription against
separate exact English phrase lists. Physical Tasks transcripts proved that
ordinary affirmative intent was rejected. Those lexical gates are removed.
The Voice agent remains responsible for calling a confirmation tool only after
the user approves the exact reviewed action. Runtime authorization remains
fail-closed through the exact action or draft identity and content hash, same
trusted Voice session, strictly newer native utterance sequence, expiry where
defined, and one-use transactional claim. No confirmation tool accepts a model
supplied approval flag.

### Mail folder classification and Inbox-default reads

Physical SQLite inspection found the provider returned `INBOX` with
`["\\HasChildren"]` and no `\\Inbox` flag, leaving `special_use` empty. Sent
was correctly labeled and contained a newer outgoing message, so time-only
Mail queries selected Sent ahead of Inbox.

Folder classification now runs for every synchronization and uses both
provider special-use flags and canonical delimiter-aware folder names. Literal
`INBOX` becomes `special_use=inbox` even when the provider omits the flag; the
same fallback recognizes conventional Sent, Drafts, Archive, Junk, and Trash
leaf names. The normal sync upsert repairs existing folder metadata on the next
sync. Repository reads also recognize literal `INBOX`, so correct default
selection does not depend on waiting for that repair.

`email_check`, `email_get_unread`, `email_search`, and contact lookup now query
Inbox by default. Sent, Drafts, Archive, Junk, or another folder is searched
only when the user explicitly requests it and the agent supplies that folder's
ID. Folder listing and explicit non-Inbox access remain available; destructive
Mail capabilities remain absent. Focused coverage includes a provider that
omits `\\Inbox` and a newer Sent message that must not outrank Inbox by default.
