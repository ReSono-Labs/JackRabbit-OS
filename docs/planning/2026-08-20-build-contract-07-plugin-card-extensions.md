# Build Contract 07 Subphase - Agent Plugin Card Extensions

**Identity:** `R1-BUILD-07-PLUGIN-CARD-EXTENSION-v0.1-draft`  
**Grounding:** `GROUNDING-BASELINE-v0.5`  
**Parent:** `R1-BUILD-CONTRACT-07-v0.7-audited-implementation`  
**Status:** Code review complete; implementation authorized by owner; not accepted or validated  
**Date:** 2026-08-20

## Outcome

A user imports one Agent Plugin ZIP. The package remains valid under the standard Agent Plugins contract and may additionally carry one explicitly ReSono-specific Card extension. One confirmed import installs the Plugin's standard Skills and MCP definitions plus its Card as one lifecycle-owned unit. The Card appears dynamically on the R1 Cards page without a reboot.

This subphase precedes Calendar implementation. It establishes the reusable package path for community applications that need both a Card and Voice/Text agent tools.

## Package contract

```text
file-browser.zip
`- file-browser/
   |- plugin.json
   |- skills/
   |  `- file-browser/
   |     `- SKILL.md
   |- mcp.json
   `- com.resonolabs.cards/
      |- card.json
      |- index.html
      |- app.js
      `- styles.css
```

The following remain standard and unmodified:

- `plugin.json`;
- `skills/`; and
- `mcp.json`.

The Card is a file-only client-specific Agent Plugin extension. Agent Plugins 1.0 requires client files to live in a top-level directory whose name exactly matches the reverse-domain namespace. It does not use a generic `extensions/` directory. ReSono uses the stable namespace `com.resonolabs.cards`. The extension is never described as a portable Agent Plugins component, and no `card` property is added to `plugin.json`.

## Card manifest candidate

```json
{
  "$schema": "https://resono.local/schemas/cards/1.0/card.schema.json",
  "schemaVersion": "1.0",
  "cardId": "file-browser",
  "title": "Files",
  "description": "Browse files on your computer",
  "entrypoint": "index.html",
  "accent": "#79f2dd",
  "requiredTools": ["files.list", "files.read"],
  "optionalTools": ["files.search", "files.write"]
}
```

The pinned local schema describes presentation and tool dependencies; it never defines executable tool handlers or embeds live application data. `cardId` must equal the owning Plugin name so replacement, ownership, rollback, and deletion cannot diverge.

## Import and lifecycle requirements

```text
inspect ZIP
  -> validate standard Plugin
  -> detect exact com.resonolabs.cards/card.json path
  -> validate Card manifest and bounded static assets
  -> show one complete overwrite-aware preflight
  -> confirm once
  -> activate Plugin components and Card
  -> publish new dynamic catalog generation
```

Required behavior:

1. The Card extension is optional.
2. A visual-only package remains a Rabbit Creation, not an empty Plugin.
3. The Plugin name remains the canonical package identity. Card identity collisions fail preflight unless the user confirms replacement of the same owning Plugin.
4. Install, same-name replace, enable, disable, rollback, and delete apply coherently to the Card and standard Plugin components.
5. Disabling hides the Card and removes the Plugin's enabled agent-tool projection without deleting externally owned data.
6. Deleting removes installed Card assets and catalog state with the owning Plugin.
7. Failure must not leave an orphaned Card or a partially activated Plugin.
8. Catalog changes are dynamic and report `restartRequired: false`.
9. Imported Card JavaScript receives no unrestricted tool or filesystem access.
10. The existing Rabbit Creation import contract remains separate and compatible.

## Runtime registration

```text
one Plugin package
|- Skills -> Skill Registry
|- MCP definitions -> MCP Lifecycle -> Tool Catalog -> Voice/Text
`- ReSono Card extension -> Card catalog -> R1 Cards page
```

The Card and Voice/Text agents use the same MCP-backed Tool Catalog. A later bounded Card bridge may call only tools declared by the Card and granted by the runtime. That execution bridge is not silently included in this ingestion subphase unless the code review proves it is already available and correctly bounded.

## Current scope

- Card-extension discovery and validation inside Agent Plugin ingestion.
- Persistence and lifecycle ownership of installed Plugin Cards.
- Dynamic projection into the existing R1 Cards experience.
- Static asset delivery through the authenticated loopback runtime.
- Management projection of the Card component during Plugin preflight and inspection.
- Focused unit tests for archive rejection, lifecycle, ownership, replacement, disable/delete, and dynamic catalog behavior.

## Explicit non-scope

- Calendar or Tasks implementation.
- A new top-level proprietary App package.
- Modification of the Agent Plugins schemas.
- Arbitrary JavaScript tool publication.
- A general plugin UI framework.
- Local `stdio` MCP execution.
- Management-site redesign.
- Build, deployment, or physical acceptance in this subphase.

## Completed code review

### Existing owners

- `runtime/resono_runtime/plugins/archives.py` owns quarantined Plugin archive inspection and already enforces a single root, bounded archive size/expansion/count, duplicate/path/link rejection, and standard component validation.
- `runtime/resono_runtime/plugins/lifecycle.py` owns Plugin install, same-name replacement, enable, disable, removal, component handoff, and recovery.
- `runtime/resono_runtime/storage/plugin_components.py` is the existing Plugin-component ownership catalog. Its database constraint currently permits only `skill` and `mcp`; migration 27 must add `card`.
- `runtime/resono_runtime/storage/creations.py` owns the only dynamic visual catalog and its monotonic generation. Creating another Card registry would duplicate refresh authority, so it will also store records with source `plugin_card` while retaining the legacy class/table name in this bounded change.
- `runtime/resono_runtime/api/creation_routes.py` owns catalog and static-asset delivery. It will expose a generic `/v1/cards/catalog` alias/projection while keeping Creation management limited to standalone Creations.
- `android/feature/cards/` polls the visual catalog every two seconds and opens local static content without reboot. It currently assumes every item is a Creation and must branch on `sourceType` for labels and activation.

### Findings and corrections

1. The earlier `extensions/ai.resono.cards/` proposal was incorrect. The Agent Plugins client-extension contract requires a top-level namespace directory. The frozen path is `com.resonolabs.cards/`.
2. The current `creation_catalog` already supplies the required monotonic dynamic generation. It is the smallest safe shared visual projection for this subphase; Plugin ownership remains in `plugin_components` rather than being inferred from paths.
3. Standalone Creation import, enable/disable, and delete routes must reject `plugin_card` records. Only the owning Plugin lifecycle may mutate them.
4. A Plugin Card ID collision with a standalone Creation or another Plugin is rejected during preflight. Same-name replacement is allowed only when the same Plugin owns the existing Card.
5. Replacement of a Plugin that removes or changes its Card must remove the previous Card projection. Disable hides it; enable restores it; delete removes it before installed files are removed.
6. Existing local asset routing can safely serve Plugin Card assets after `plugin_card` is admitted as a local source. The installed path remains under the owning Plugin root.
7. Android should consume `/v1/cards/catalog`, prefer the `cards` array, label Plugin Cards as `APP`, and continue opening standalone Creations unchanged.
8. The Card tool bridge remains out of this ingestion change. `requiredTools` and `optionalTools` are validated metadata and future dependencies, not executable access.

### Files authorized for this implementation

- `runtime/resono_runtime/plugins/cards.py` - strict Card manifest/asset validation.
- `runtime/resono_runtime/plugins/card_lifecycle.py` - Plugin-owned visual-catalog projection.
- `runtime/resono_runtime/plugins/archives.py` - extension discovery.
- `runtime/resono_runtime/plugins/lifecycle.py` - lifecycle handoff.
- `runtime/resono_runtime/api/plugin_routes.py` - preflight/inspection projection.
- `runtime/resono_runtime/api/creation_routes.py` - generic Card catalog and ownership guards.
- `runtime/resono_runtime/storage/plugin_components.py` and migration 27 - Card ownership.
- `runtime/resono_runtime/storage/migrations/__init__.py` - migration registration.
- `runtime/resono_runtime/application.py` - one shared visual catalog and lifecycle wiring.
- the existing Android Cards host/client/view files - generic Card naming and `plugin_card` activation.
- focused existing Plugin/Creation tests.

### Validation status

The owner explicitly prohibited build and deployment. Tests are being authored as implementation evidence but will not be executed in this task. No passing, build, device, or acceptance claim may be made.

**Review gate result:** `CONTINUE` for the bounded ingestion and dynamic Card-registration implementation.

## Required deferred final diagnostics phase

Unified user-facing logs for all imported/user-added packages and execution paths, plus the optional read-only Diagnostic Trace agent, are deliberately not part of this Build 07 subphase. They must be implemented near the end of the overall project, after package, Card, Domain, connector, Voice/Text, and runtime contracts are stable and before final release hardening.

The controlling deferred document is:

## Required deferred isolated package-storage subphase

Community packages that need a Card and agent tools may also need shared local persistence. That capability is not part of Agent Plugins and must not be improvised inside `plugin.json`, the canonical R1 database, Card WebView storage, or individual tool implementations.

The accepted architecture and mandatory future code gate are defined in:

`docs/planning/2026-08-20-build-contract-07-plugin-storage.md`

Before package storage can be advertised or accepted, the Plugin importer and lifecycle must implement that contract: an optional namespaced declaration, preflight and explicit approval, one isolated host-owned database per stable package ID, scoped record APIs, quotas, compatible overwrite, rollback, and mandatory database deletion when the user removes the Plugin. Packages never receive SQL or filesystem paths.

`docs/planning/2026-08-20-final-diagnostics-trace-agent-contract.md`

That phase owns structured causal events, exact management-page error reasons, redaction, retention/export/delete, the version-matched documentation/code graph, user-triggered read-only tracing, scoped trace chat, and the mandatory warning that AI diagnoses may be incomplete or incorrect. Earlier builds must retain support-safe errors but must not pull the final Trace agent or unified diagnostics UI into their scope.
