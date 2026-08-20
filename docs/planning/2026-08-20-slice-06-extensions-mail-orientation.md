# Slice 6 Orientation — Standard Extensions and Real Mail (pre-contract research)

**Date:** 2026-08-20
**Status:** Orientation only. No contract drafted, no code copied, no donor files modified.
**Governing slice:** Delivery Slice 6 in `2026-08-14-r1-standalone-delivery-plan.md` (standard extensions and real Mail; exit = grounding scenarios 9, 10, 12 through one public extension boundary).
**Donor surveyed (read-only):** `/home/christian/Documents/Projects/ReSono-Labs-Voice/project-3d3354dadcad/workspace/`

## Entry-condition status

| Condition | State |
|---|---|
| Slice 4 accepted | Met |
| Slice 5 (BC-06) accepted | Open — physical credential-backed memory proof is in owner testing |
| Agent Skills / Agent Plugins specifications frozen | Unknown — owner asked whether spec documents are available |
| Exact Mail donor import record | Paths identified below; intake record is drafted with the contract |

## Donor findings — Mail vertical (strong reuse candidates)

Self-contained, pure-stdlib, ~16 files / ~4.2k LOC on the vault side. This is the proven live path.

| Concern | Donor path | Notes |
|---|---|---|
| IMAP/SMTP connector | `app/vault_runtime/email_provider.py` (1250 lines) | `imaplib`/`smtplib`, UID-based fetch, RFC-822 parsing, HTML→text, MIME compose/send, IPv4-preferred sockets, SSRF guard via `app/core/security/outbound.py::validate_public_host` |
| Canonical mail store | `app/vault_runtime/email_store.py` (1104 lines) | Scope-bound records, deterministic `uuid5` IDs |
| Store schema | `app/vault_runtime/datastore/schema.py:181-300+` | `vault_email_mailbox_accounts` (`mailbox_role IN ('normal_email','agent_mail')`), `vault_email_folders`, `vault_email_messages`, `vault_email_attachments`, `vault_email_send_requests` |
| Sync/compose/send orchestration | `app/vault_runtime/email_service.py` (896 lines) | Compose→pending→send; **send requires a caller-owned provider action id (explicit user approval)** |
| Voice query routing | `app/vault_runtime/mail_query_policy.py` (83 lines) | Cache vs live-provider heuristics |
| Voice tool sets | `app/vault_runtime/signals/email/session_tools.py` | Read tools (status/list/check/unread/search/read/attachment/contact lookup) vs side-effect tools (mark read, compose, send_pending, archive, folder ops) |
| Tool routing/adapters | `app/vault_runtime/tool_registry.py:165,239,272`; `app/vault_runtime/session_tools/email_adapters.py` | `email_*` prefix dispatch |
| Credentials | `app/vault_runtime/provider_credentials.py` | Scoped per account+workspace, status flips |

**Proposed scope line (owner to confirm):** normal email only. Drop `agent_mail` per-agent mailboxes (`app/modules/agent_mail_signal/`, `signals/agent_mail/`), the LangGraph communications agent, and the autonomy extras (`app/modules/autonomy/email_settings.py`, `email_review.py`).

**UI reality:** the donor has no dedicated mail UI; mail is voice/tool-driven. R1 parity: web management UI is the canonical mail/extension surface; native remains voice-driven (same split as memory in BC-06).

## Donor findings — extension machinery (copy patterns, not files wholesale)

| Concern | Donor path | Assessment |
|---|---|---|
| Permission intersection at install | `app/modules/skill_catalog/service.py::_evaluate_install` (line 1532) | Core pattern to lift: requested ⊆ required, else blocked; persists `InstalledSkillPermissionModel`. The file itself (1766 lines) is entangled with billing/entitlements — copy the gate, not the file |
| Skill lifecycle | `app/modules/skill_catalog/service.py` (`install/enable/disable/remove/remove-and-purge/suspend`) | Lifecycle vocabulary to mirror |
| Skill/signal ORM | `app/modules/skill_catalog/models.py` | `SkillModel`, versions, permissions, allowlist, installed-skill, installation events, storage namespaces/artifacts |
| Declarative per-skill config | `app/modules/skill_catalog/configuration.py` | `SIGNAL_CONFIGURATION_SPECS` pattern for skill settings |
| Quarantine | `app/modules/developer_publishing/quarantine_storage.py` | Immutable staged write/commit/discard — the scenario-12 (editable recovery) mechanism |
| Safe extraction | `app/modules/developer_publishing/extraction.py:192-214` (+ `archive_detection.py`, `extraction_limits.py`) | Path-traversal guards, escape-root verification |
| Secret scanning | `app/modules/developer_publishing/scanner_rule_runtime.py` | `SECRET_PATTERNS` regexes, `secrets.hardcoded_secret` finding |
| Other scanners | `scanner_rule_manifest.py`, `scanner_rule_policy.py` | Prompt-bypass, abuse, storage-migration risk findings |
| Signed approvals | `app/modules/agent_packages/approval_signing.py` | HMAC-SHA256 versioned approvals (reference) |

**Avoid importing wholesale:** `app/modules/agent_packages/` + `app/vault_runtime/agent_packages/` (~140 files: eval gates, release pipelines, sandbox/cgroups, multi-party platform machinery), `developer_publishing` review console/analysis orchestration, and the `skill_catalog` entitlement/billing branches. Trusted vs user separation is hard-coded first-party builtins plus allowlisted third-party through submission→quarantine→scan→review→runtime gate.

## Donor findings — editable workspace, lifecycle surfaces, bundled vs installed (2026-08-20 follow-up)

**Editable agents/prompts/config — immutable revisions + active pointer (never in-place editing):**
- `app/modules/agent_packages/models.py` — `AgentPackageConfigSchemaModel` (schema pinned per version, sha256) and `AgentPackageConfigRevisionModel` (monotonic `revision` per install; values split into `support_safe_values_jsonb` vs `vault_private_ref_jsonb` so support-visible config never carries secrets). The install row's `active_config_revision_id` points at the live revision; **rollback = re-point to an older revision**.
- `app/modules/agent_packages/lifecycle_service.py` — `_ensure_default_config_revision` (revision 1 at install), `select_operator_install_version` (cut-over with optimistic concurrency, upgrade/rollback modes), `roll_back_operator_package_cutover` (explicit rollback), `select_user_private_install_version` (user-editable path). Every edit creates a new revision; every activation is an audited lifecycle transition embedded in signed evidence. No free-form "save and live" path exists.
- R1 takeaway: the scenario-12 "editable recovery" pattern is *revisioned config + pointer rollback*, matching the quarantine mechanism; both belong in the BC-07 design.

**CLI vs web lifecycle:**
- The install/enable/disable/remove lifecycle is **API-only** in the donor (`skill_catalog/router.py`); no CLI exists for it. `app/cli/` is ops/diagnostic only (`developer_sandbox.py` dry-runs a package through validators locally — the closest thing to a dev CLI; `vault_signal_inventory.py` is read-only comparison).
- Web surfaces: user catalog (`frontend/src/features/app/CapabilitiesPage.tsx`, `CapabilityDetailPage.tsx`), per-signal config/data (`signal-detail/*`), admin review (`admin/AdminSignalsPage.tsx`, `AdminSignalReviewsPage.tsx`), developer submission (`developer/DeveloperSignalsPage.tsx`).
- R1 takeaway: the plan's "one shared CLI/web lifecycle" maps to web management UI as the canonical surface; any CLI would be new, not ported.

**Bundled vs user-installed:**
- Builtins ship as **seeded catalog rows + in-code specs**, not installed packages: seed migrations (`0036`/`0037` + one per builtin), canonical list `app/modules/skill_catalog/builtin_signals.py`, runtime specs `app/modules/skill_runtime/builtins.py`; `owner_type` distinguishes builtin/first-party from developer-owned.
- Nothing auto-installs at first run; users install from the catalog (`installed_skills` rows + permission grants + install-owned storage). Per-workspace `workspace_builtin_capabilities` (migration `0018`) is the closest "on-by-default bundled capability" mechanism.
- R1 takeaway: first-party extensions (e.g., the Mail plugin) follow the same split — in-code spec + catalog row; user-installed packages go through validate→install→grant with install-owned storage.

## Hard requirement (owner, 2026-08-20) — real on-device Mail client

The R1 Mail deliverable is a **real on-device mail client**, not a mail query
tool. This is a must and overrides any donor behavior that falls short of it:

- It must sync like any phone/desktop mail client: account folders and
  message state are synchronized over standard IMAP/SMTP, not fetched
  ad hoc per question.
- State is **bidirectional and global**: marking a message read on the R1
  marks it read on every other device/client on the account, and vice versa.
- Messages sent from the R1 must appear in the account's **Sent items folder
  on other devices** — i.e. send via SMTP **and** append the message to the
  Sent folder over IMAP, exactly as a real mobile client does.
- Local storage is the client's synchronized mailbox, not a voice-answer
  cache. Voice/agent access reads and acts on that real mailbox state.

Consequence for donor adaptation: the donor's mail path is voice/query
oriented (`mail_query_policy.py` routes between cache and live queries); it
is the transport/store foundation, **not** the acceptance bar. BC-07 must
prove real client semantics (sync, global read state, Sent-folder parity)
physically on device. A mail feature that only answers questions about mail
fails this slice.

## Open decisions for the BC-07 draft (candidate MDGs)

1. **Extension format:** one manifest covering Skills (prompts/config) and Plugins (MCP tools) per the frozen Agent Skills / Agent Plugins standards — a ReSono proprietary format is forbidden by the plan. Blocked on spec availability.
2. **Mail credential storage:** Keystore-bridge (OpenAI parity) vs runtime-encrypted store (donor used scoped DB credentials).
3. **Scope line:** normal email only (drop `agent_mail` and autonomy extras) — pending owner confirmation.
4. **Editable recovery on-device:** quarantine directory + registry rollback, adapted from `quarantine_storage.py`.
5. **Voice tools:** port the donor read/side-effect tool split onto the R1 `agents/sdk_runner.py` + on-device MCP path; send always requires explicit user confirmation (donor's caller-owned action id pattern).
6. **R1 structural placement:** extension loaders/validators as new owners beside `agents/` and `mcp/`; mail as `runtime/resono_runtime/mail/` with storage migrations; routes in `api/routes.py`; credentials through `providers/openai/access.py`-style canonical handling where applicable.

## Next step

After BC-06 physical acceptance: draft `R1-BUILD-CONTRACT-07` (donor-freeze table from the paths above, MDGs 1–6, checkpoints, offline-test plan) for owner review and freeze.
