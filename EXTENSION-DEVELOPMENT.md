# JackRabbit Extension Development Guide

This is the authoritative contributor guide for JackRabbit instruction
documents, Agent Skills, Agent Plugins, MCP connections, built-in Tools,
Creations, and Plugin-owned Cards. It describes the formats and behavior the
current code accepts; it does not promise a marketplace or arbitrary plugin
code execution.

JackRabbit implements three open standards within their actual scope:

- [Agent Skills](https://agentskills.io/specification) for portable
  `SKILL.md` instruction packages.
- [Agent Plugins 1.0.0](https://agent-plugins.org/specification) for portable
  Plugin identity, Skills, and MCP declarations.
- [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25)
  for model-facing tools and connection lifecycle.

The JackRabbit Card extension and Rabbit Creation import are product-specific
formats layered beside those standards. JackRabbit itself remains licensed as
a source-available noncommercial project.

## Pick one owner before building

| Need | Correct owner | Imported without rebuilding JackRabbit? |
|---|---|---:|
| Change instructions for one device owner | `SKILLS.MD` instruction document | Yes |
| Package reusable agent instructions | Agent Skill inside a Plugin | Yes |
| Connect model-facing capabilities from a service | MCP `mcp.json` | Yes |
| Ship related Skills, MCP configuration, and one Card together | Agent Plugin | Yes |
| Add a bounded static Card | Creation ZIP | Yes |
| Add a static Card owned by a Plugin lifecycle | Plugin Card extension | Yes |
| Add trusted on-device Python behavior | Built-in Tool package | No |
| Add or change an AI provider | Provider/runtime module | No |
| Change native audio, WebRTC/WebSocket, camera, or hardware | Android/runtime feature | No |

A local OpenAI-compatible inference service normally belongs behind the
provider boundary when it replaces the selected AI provider. It may instead be
an MCP server when it exposes optional tools to the existing agent. Local
STT/TTS and a WebRTC-to-WebSocket transport change are native/provider work,
not a Skill or Creation. A Plugin can package supporting instructions and an
MCP connection, but it cannot make a native transport change by itself.

## How imports work

Open **Management → Library**, choose the matching tab, select the intended
agent audience, and upload the package. Every mutating import follows two
steps:

1. Preflight validates and quarantines the candidate without activating it.
2. Confirmation installs it or explicitly replaces the item with the same
   identity.

Installed items retain ownership records. Enable, disable, replacement, and
removal follow that ownership. A Plugin-owned Card is therefore managed from
the Plugin, not from the standalone Creations tab.

## Owner instruction documents (`SKILLS.MD`)

The current **Skills** tab is an owner instruction-document feature. It is not
the standalone Agent Skill package importer.

Create a UTF-8 Markdown file named exactly `SKILLS.MD`. It may contain normal
Markdown instructions and must be no larger than 256 KiB. Import it for either
Voice or Background Agent. Each destination has one slot; importing another
document into that slot requires replacement confirmation.

```markdown
# Household preferences

Use concise spoken answers. When reading calendar events, say the local time
before the event title.
```

These instructions do not grant tools, permissions, filesystem access, or the
ability to override platform safety boundaries.

Relevant implementation:

- `runtime/resono_runtime/skills/documents.py`
- `runtime/resono_runtime/api/skill_routes.py`
- `web/management/build07.js`

## Agent Skills (`SKILL.md`)

A standard Agent Skill is a directory whose name matches the `name` in its
required `SKILL.md` frontmatter. JackRabbit currently activates standard Skills
when they are packaged under an Agent Plugin's `skills/` directory.

```text
calendar-summary/
└── SKILL.md
```

```markdown
---
name: calendar-summary
description: Summarize upcoming events when the user asks about their schedule.
license: CC-BY-NC-4.0
compatibility: Requires the JackRabbit Calendar tool set.
metadata:
  author: example-author
---

# Calendar summary

Use the calendar tools only when a configured calendar is available. State the
time zone when it could be ambiguous.
```

JackRabbit validates:

- UTF-8 YAML frontmatter closed by `---`;
- a 1–64 character lowercase, digit, and hyphen `name` matching the directory;
- a non-empty `description` of at most 1,024 characters;
- optional `license`, `compatibility` up to 500 characters, string-to-string
  `metadata`, and `allowed-tools` string.

`allowed-tools` is descriptive standard metadata. It does not grant access in
JackRabbit. The selected audience and canonical Tool/MCP permission gates still
decide what the agent can invoke.

The runtime discloses only the names and descriptions of relevant enabled
Skills. It loads the full instructions just in time through
`load_agent_skill`. Keep `SKILL.md` focused and place larger reference material
in relative files inside the same Skill directory.

Relevant implementation:

- `runtime/resono_runtime/skills/specification.py`
- `runtime/resono_runtime/skills/activation.py`
- `runtime/resono_runtime/plugins/bundled/resono-mail/skills/voice-mail/SKILL.md`

## Agent Plugins

Use a Plugin when related Skills, MCP configuration, and optionally one Card
should install, enable, disable, replace, and uninstall together.

The archive must contain exactly one top-level directory and a `plugin.json`
at that directory's root:

```text
local-assistant/
├── plugin.json
├── skills/
│   └── local-assistant/
│       └── SKILL.md
├── mcp.json
└── com.resonolabs.cards/
    ├── card.json
    ├── index.html
    ├── app.js
    └── styles.css
```

All components are optional except `plugin.json`. A minimal manifest is:

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "local-assistant",
  "version": "1.0.0",
  "description": "Instructions, tools, and a Card for a local assistant.",
  "author": {
    "name": "Example Author"
  },
  "license": "CC-BY-NC-4.0"
}
```

The accepted Plugin name is 1–64 lowercase letters, digits, periods, or
hyphens, without leading/trailing punctuation, `..`, or `--`. The manifest is
closed: client-specific metadata belongs under its `extensions` object, not in
new top-level fields.

For the current Management UI, create a ZIP that retains the top-level Plugin
directory:

```bash
zip -r local-assistant.zip local-assistant/
```

Plugin uploads are limited to 16 MiB compressed, 64 MiB expanded, 512 files,
and a 100:1 per-entry compression ratio. Unsafe paths, duplicate paths,
encrypted ZIP entries, links, and non-regular TAR entries are rejected.

Invalid Skills or MCP entries are reported as component failures during
preflight. A Plugin Skill also cannot collide with an independently installed
Skill or a Skill owned by another Plugin.

Relevant implementation and pinned schemas:

- `runtime/resono_runtime/plugins/archives.py`
- `runtime/resono_runtime/plugins/lifecycle.py`
- `runtime/resono_runtime/plugins/specification.py`
- `runtime/resono_runtime/standards/agent_plugins/plugin.schema.json`
- `runtime/resono_runtime/standards/agent_plugins/mcp.schema.json`

## MCP connections

Use MCP when an external or independently running service should expose
model-facing tools. A standalone import is one Agent Plugins 1.0.0 `mcp.json`
document:

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
  "mcpServers": {
    "local-inference-tools": {
      "type": "streamable-http",
      "url": "https://inference.example.net/mcp",
      "headers": {
        "X-Client": "jackrabbit"
      }
    }
  }
}
```

The schema recognizes `streamable-http`, `sse`, and `stdio`, but the current R1
runtime can discover, enable, and call only `streamable-http`. Importing another
transport records it as unsupported; it does not make that transport runnable.

Use HTTPS for non-loopback servers. The URL cannot contain embedded
credentials or a fragment. Do not put secrets in `mcp.json`: configure
credential headers separately in Management so Android Keystore-backed storage
owns them. Authorization, cookie, proxy-authorization, and API-key headers are
rejected from the public configuration for this reason.

After import:

1. Add any credential headers in the MCP connection controls.
2. Run discovery.
3. Review the discovered tools.
4. Grant only the intended tools and effect classes.
5. Enable the connection for the intended Voice, Background Agent, or shared
   audience.

The R1 client requires MCP protocol revision `2025-11-25`, rejects redirects,
limits responses to 2 MiB, validates public HTTPS destinations, and exposes
only discovered, individually enabled tools through the canonical Tool
catalog.

Relevant implementation:

- `runtime/resono_runtime/mcp/imports.py`
- `runtime/resono_runtime/mcp/connections.py`
- `runtime/resono_runtime/mcp/client.py`
- `runtime/resono_runtime/mcp/lifecycle.py`
- `runtime/resono_runtime/mcp/tool_adapter.py`

## Built-in Tools

A built-in Tool is trusted Python product code, not an importable package. Use
it only when the capability must ship in the on-device runtime and cannot be an
external MCP service.

Every Tool is a `ToolDefinition` with:

- a stable, versioned `tool_id`;
- a unique model-visible `name`;
- a clear `description`;
- a valid JSON Schema object for `input_schema`;
- a handler returning `ToolInvocationResult`;
- an effect class, normally `read` unless the tool mutates state;
- an audience resource or availability rule.

```python
ToolDefinition(
    tool_id="builtin.example-status.v1",
    name="get_example_status",
    description="Read the current example integration status.",
    input_schema={
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
    handler=read_example_status,
    effect_class="read",
    audience_resource=EXAMPLE_TOOL_SET,
)
```

Keep schema/contracts, handlers, and package registration separate, following
`runtime/resono_runtime/tools/calendar/` or `tools/tasks/`. Register the package
once in the application composition root. Do not add a second dispatcher: the
single `ToolCatalog` validates input, applies audience and live-session gates,
projects definitions to MCP and Realtime, and dispatches the handler.

Built-in Tool changes require code review, runtime tests, an APK/runtime build,
and physical R1 acceptance for hardware or live-provider claims.

Relevant implementation:

- `runtime/resono_runtime/tools/definitions.py`
- `runtime/resono_runtime/tools/catalog.py`
- `runtime/resono_runtime/tools/builtins.py`
- `runtime/resono_runtime/tools/calendar/`
- `runtime/resono_runtime/tools/tasks/`

## Standalone Creations

A standalone Creation is a bounded static site rendered as a Card. Put
`index.html` at the ZIP root or inside one top-level directory:

```text
quick-notes/
├── index.html
├── app.js
├── styles.css
└── icon.svg
```

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Quick Notes</title>
    <meta name="description" content="A small local note surface">
    <link rel="stylesheet" href="styles.css">
  </head>
  <body>
    <main>Quick Notes</main>
    <script src="app.js"></script>
  </body>
</html>
```

Package and import it from **Library → Creations**:

```bash
zip -r quick-notes.zip quick-notes/
```

The filename or single directory becomes a lowercase, hyphenated Creation ID.
The HTML `<title>` supplies the displayed title and a
`<meta name="description">` supplies the description.

Creation ZIPs are limited to 16 MiB compressed, 64 MiB expanded, 512 files,
and a 100:1 compression ratio. Accepted files are HTML, CSS, JavaScript, JSON,
common web images/fonts, icons, and text. Executables, links, encrypted files,
unsafe paths, and unsupported extensions are rejected.

Static assets load from the R1's confined `https://resono.local` origin. File
and content access are disabled, mixed content is blocked, and navigation
outside that origin is denied. JavaScript is available. The R1 dispatches
`scrollUp`, `scrollDown`, and `sideClick` window events for physical input.

```javascript
window.addEventListener("scrollDown", () => window.scrollBy(0, 120));
window.addEventListener("scrollUp", () => window.scrollBy(0, -120));
window.addEventListener("sideClick", () => document.activeElement?.click());
```

There is currently no JavaScript bridge from a Creation to JackRabbit Tools or
canonical domain data. Do not simulate that data in the Card. If real data is
required, use an implemented product contract or propose the smallest new
contract separately.

Rabbit-compatible QR descriptors are a second Creation source. JackRabbit
accepts `title`, public HTTPS `url`, optional `description`, public HTTPS
`iconUrl`, and `themeColor` in `#RRGGBB` form. It tolerates and discards the
Boondit compatibility fields `author` and `installConfirmUrl`; JackRabbit does
not call the analytics URL.

Relevant implementation:

- `runtime/resono_runtime/creations/archives.py`
- `runtime/resono_runtime/creations/descriptors.py`
- `runtime/resono_runtime/creations/lifecycle.py`
- `runtime/resono_runtime/api/creation_routes.py`
- `android/feature/cards/src/main/java/com/resonolabs/feature/cards/CreationWebViewHost.java`

## Add a Card to a Plugin

Agent Plugins standardizes Skills and MCP components. JackRabbit adds one
client-specific Card extension using the standard's reverse-domain extension
namespace mechanism. Put it at `com.resonolabs.cards/` inside the Plugin root.

```json
{
  "$schema": "https://resono.local/schemas/cards/1.0/card.schema.json",
  "schemaVersion": 1.0,
  "cardId": "local-assistant",
  "title": "Local Assistant",
  "description": "Status from the local assistant integration.",
  "entrypoint": "index.html",
  "accent": "#79F2DD",
  "requiredTools": ["local.status"],
  "optionalTools": []
}
```

Rules:

- `cardId` must exactly equal the owning Plugin's `name`.
- `entrypoint` must be a relative `.html` or `.htm` file inside the extension
  directory.
- Title is 1–100 characters and description is 1–240 characters.
- Accent is `#RRGGBB`.
- Required and optional Tool names must be unique and cannot overlap.
- Assets use the same static allowlist as Creations and cannot be symbolic
  links.

`requiredTools` and `optionalTools` currently declare Card dependencies for
validation and future capability negotiation. They do not create a JavaScript
Tool bridge, grant a Tool, or make Plugin MCP results directly available to the
Card. Build only a static Card with the current contract unless the required
real data path is separately implemented and reviewed.

The Card appears in the same native Cards catalog as Creations but has source
type `plugin_card`. Enabling or disabling the Plugin does the same to its Card,
and uninstalling the Plugin removes it. Replacing a Plugin Card with another
Card works. There is one current lifecycle defect: replacing a Plugin that had
a Card with a package that has no Card can leave the former Card registered in
a disabled state. A standalone Creation cannot replace a Plugin-owned Card.

Relevant implementation and schema:

- `runtime/resono_runtime/plugins/cards.py`
- `runtime/resono_runtime/plugins/card_lifecycle.py`
- `runtime/resono_runtime/standards/resono_cards/card.schema.json`
- `tests/runtime/test_plugin_archives.py`
- `tests/runtime/test_plugin_lifecycle.py`

## Validate before a pull request

At minimum, inspect the package through the same parser used by the product and
run the focused runtime tests:

```bash
PYTHONPATH=runtime uv run \
  --with pydantic==2.12.2 \
  --with PyYAML==6.0.3 \
  --with jsonschema \
  --with pytest \
  -- python -m pytest -q \
  tests/runtime/test_skill_archives.py \
  tests/runtime/test_skill_lifecycle.py \
  tests/runtime/test_plugin_archives.py \
  tests/runtime/test_plugin_lifecycle.py \
  tests/runtime/test_mcp_connections.py \
  tests/runtime/test_mcp_lifecycle.py \
  tests/runtime/test_creations.py
```

At the time this guide was written, that focused group has one known failing
test: the no-Card Plugin replacement defect described above. Do not hide or
silently update that expectation in a contribution; either preserve it as a
known failure or fix the lifecycle and its test together.

Then follow [BUILDING.md](BUILDING.md) for the applicable project build and
checks. State separately whether the result was parser-tested, host-tested,
tested against a real MCP/provider service, or physically accepted on an R1.

For contribution workflow and review expectations, read
[CONTRIBUTING.md](CONTRIBUTING.md).
