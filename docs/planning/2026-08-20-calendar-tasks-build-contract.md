# Calendar and Tasks Build Contract - Architecture Candidate

> **Owner scope correction, 2026-08-20:** Contacts and Reminders are suspended from the final integrated build and may return later as packages. Tasks is a distinct first-party local package, not a renamed Reminders domain. Its controlling implementation contract is `docs/planning/2026-08-20-first-party-tasks-package.md`. Any older unresolved Tasks/Reminders language below is superseded by this correction.

**Identity:** `R1-CALENDAR-TASKS-CONTRACT-v0.1-candidate`  
**Grounding:** `GROUNDING-BASELINE-v0.5`  
**Delivery slice:** 7 - Calendar, Contacts, and Reminders  
**Status:** Architecture candidate for owner discussion. Not active, accepted, implemented, or validated.  
**Prepared:** 2026-08-20  
**Predecessor:** Build Contract 07 must establish and prove the shared extension, connection, domain-tool, and personal-data boundaries before this implementation begins.

## Authority and purpose

This document records the proposed Calendar and Tasks architecture requested by the owner. It does not change the active contract, delivery order, or accepted baseline. `GROUNDING-BASELINE-v0.5` and delivery plan v0.3 remain controlling.

The purpose is to decide how Calendar and Tasks data can be available through both:

- the R1 Cards interface; and
- the Voice agent and later Text agent.

The solution must remain small, modular, standards-based, and understandable to community contributors. It must not redefine Agent Plugins or Rabbit Creations, duplicate canonical data, introduce another agent loop, or turn imported web content into an unrestricted trusted runtime.

## Owner observations and constraints

1. Mail does not require a Card on the small R1 screen and may remain a built-in agent capability.
2. Calendar and Tasks need useful Cards because their data benefits from a visual surface.
3. Calendar and Tasks must also be accessible to Voice and the later Text agent.
4. Users may import Rabbit Creations, including alternative Calendar-like interfaces.
5. A Creation developer may want the agent to access the same functionality or data shown by the Creation.
6. Standard Agent Skills, Agent Plugins, and MCP must remain standards-conforming.
7. The design must not overcomplicate a personal, primarily single-owner device.

## Governing external boundaries

### Agent Plugins 1.0

The portable [Agent Plugins specification](https://agent-plugins.org/specification) defines a package with `plugin.json` and optional standard `skills/` and `mcp.json` components. It does not define a portable Card or arbitrary UI component.

The specification permits client-specific extensions, but those extensions are not portable Agent Plugin components. Therefore ReSono must not claim that a ReSono Card extension is an industry-standard Plugin component.

### Rabbit Creations SDK

The [Rabbit Creations SDK repository](https://github.com/rabbit-hmi-oss/creations-sdk) demonstrates a small HTML/CSS/JavaScript application for the R1 screen. Its demonstrated host interface includes `PluginMessageHandler`, `window.onPluginMessage`, Creation-local storage, hardware events, sensors, and text-to-speech.

The reviewed SDK does not define a standard contract through which Creation JavaScript registers named agent tools with input schemas and executable handlers. `PluginMessageHandler` sends a request to the host/LLM; it is not an MCP server or a tool-publication API.

### Project standards rule

Any ReSono-specific association or host bridge must be small, versioned, explicitly identified as ReSono-specific, and must not be represented as part of the Agent Plugins or Rabbit Creations standards.

## Controlled entity decision

The following nouns remain separate:

| Entity | Meaning in this project |
|---|---|
| Domain | Trusted R1-owned canonical data and behavior, such as Calendar, Tasks, or Mail. |
| Connector | Code that synchronizes a Domain with an external service or format, such as ICS or CalDAV. |
| Connection | A configured account/endpoint, encrypted credentials, state, and health. |
| Tool | A typed operation exposed to the Voice agent, Text agent, or another approved caller. |
| Card | A device presentation registered in the R1 Cards catalog. |
| Creation | An imported Rabbit-compatible web Card/application hosted by the R1. |
| Skill | Standard instructions teaching an agent how to use capabilities. |
| Plugin | A standard portable package containing Skills and/or MCP server definitions. |
| MCP server | A standard provider of tools/context, normalized into the R1 Tool Catalog. |

### Normative ownership rule

```text
Domains own canonical data.
Connectors synchronize Domain data.
Tools expose Domain or MCP behavior to agents.
Cards present real Domain or Creation state.
Creations are imported Card applications.
Plugins distribute standard Skills and MCP definitions.
Plugins and Creations never own built-in canonical personal data.
```

## Selected architecture

### Calendar and Tasks are built-in Domains

Calendar and Tasks are not Creations and are not Plugins. Each is a built-in Domain with:

- one canonical SQLite repository;
- one service owning business behavior;
- applicable external connectors;
- one built-in agent tool set registered with the shared Tool Catalog; and
- one built-in Card projection registered with the shared Card Catalog.

Mail remains a built-in Domain and tool set without a required Card.

```text
Calendar Domain
|- canonical calendar data
|- ICS/CalDAV connectors
|- Voice/Text tools
`- built-in Calendar Card

Tasks Domain
|- canonical task data
|- applicable connectors/scheduling
|- Voice/Text tools
`- built-in Tasks Card

Mail Domain
|- canonical mail data
|- IMAP/SMTP connectors
`- Voice/Text tools
```

### A Card is not synonymous with a Creation

The Cards catalog must eventually contain more than imported Creations:

```text
Card Catalog
|- built-in Domain Cards
|  |- Calendar
|  `- Tasks
`- imported Creation Cards
   |- Quick Capture
   `- user-installed applications
```

Each catalog record identifies its source. A built-in Card opens a real domain-backed native surface. A Creation Card opens `CreationWebViewHost`.

Example built-in record:

```json
{
  "cardId": "calendar",
  "sourceType": "built_in",
  "title": "Calendar",
  "description": "Your upcoming events",
  "accent": "#79f2dd",
  "enabled": true
}
```

Example Creation projection:

```json
{
  "cardId": "quick-capture",
  "sourceType": "creation",
  "title": "Quick Capture",
  "description": "Capture a thought",
  "accent": "#ffd166",
  "enabled": true
}
```

The Card record is a projection, not a second owner of Calendar, Tasks, or Creation state.

## Why the alternatives are rejected

### Built-in Calendar implemented as a Creation - rejected

A Creation is replaceable imported web content with browser-local storage. Making it the canonical Calendar would couple personal data to an installable presentation and could create a second data store. Disabling or deleting the Creation must never delete or disable Calendar data or agent access.

### Calendar implemented as a Plugin - rejected

Agent Plugins 1.0 has no portable Card component. The built-in Calendar Domain also must not disappear when an instructional package or MCP definition is disabled. A first-party Calendar Plugin may later carry a standard Calendar Skill, but it must not own the Calendar repository, connectors, Card, or built-in tool handlers.

### Allow every Plugin to render arbitrary Cards - deferred/rejected for this vertical

A ReSono-specific plugin extension could associate a Plugin with a Card, but that is nonportable and introduces another trust boundary. It is not required to deliver built-in Calendar and Tasks. Do not add it while the smaller Domain plus Card plus Tool design satisfies the product outcome.

## User-built Creation and agent-access model

There are two materially different cases.

### Case A - Creation uses an existing R1 Domain

A user may build an alternative Calendar Creation. It remains a presentation over the existing Calendar Domain:

```text
Calendar Creation
       |
       | typed, allowlisted host request
       v
Creation Domain Bridge
       |
       v
Calendar Service
       |
       `- canonical Calendar repository

Voice/Text agent
       |
       v
Tool Catalog
       |
       v
calendar.* tools
       |
       v
same Calendar Service
```

The Creation and agents observe the same records. The Creation must not create a second Calendar database or publish competing built-in Calendar tools.

The bridge must be typed and allowlisted. Do not expose unrestricted `callTool(name, arguments)` access to arbitrary imported JavaScript. A suitable public shape is domain-scoped, for example:

```javascript
window.resono.calendar.listEvents(...)
window.resono.calendar.createEvent(...)
```

The final names and schemas require a separate bridge-contract freeze. Only Domain operations explicitly approved for Creation use may be exposed.

### Case B - Creation introduces a new capability

The visual application remains a Rabbit Creation. Agent-callable functionality is supplied through a standard MCP server in a standard Agent Plugin:

```text
User feature
|- Rabbit Creation
|  `- Card UI
`- Agent Plugin
   |- plugin.json
   |- optional skills/<name>/SKILL.md
   `- mcp.json
```

The management experience may associate the two installed artifacts, but they remain separate package contracts. A small ReSono-owned association record may link an installed Creation to an installed Plugin and its tool names:

```json
{
  "creationId": "example-calendar",
  "pluginName": "example-calendar-tools",
  "requiredTools": [
    "example_calendar.list_events",
    "example_calendar.create_event"
  ]
}
```

This record is local catalog metadata. It is not added to `plugin.json` and is not presented as an industry standard.

The current runtime supports live outbound MCP execution only for Streamable HTTP. Although the Agent Plugins schema can describe other MCP transports, the current R1 marks them unsupported. Local executable/stdio MCP hosting must not be advertised until a later accepted contract implements and proves it.

## Personal-device control boundary

The R1 does not need an enterprise role or organization authorization system for this work. It still requires:

- explicit import and overwrite confirmation;
- a truthful warning before a tool-bearing package is activated;
- selection of `Voice`, `Text`, or `Both` for real tool-bearing resources;
- no silent tool publication from imported JavaScript;
- conversational confirmation for destructive or externally visible side effects; and
- disabling agent exposure without deleting canonical Domain data.

These are local owner-intent and safety controls, not multi-user administration.

## Current repository findings

### Existing Plugin-to-MCP plumbing

`runtime/resono_runtime/plugins/lifecycle.py` already:

- validates standard Plugin components;
- installs each valid `mcp.json` server through `McpLifecycle`;
- records `plugin:<name>` as the MCP connection source owner;
- disables the associated MCP connections when the Plugin is disabled; and
- removes those connections when the Plugin is deleted.

`runtime/resono_runtime/mcp/lifecycle.py` already:

- discovers Streamable HTTP MCP tools;
- normalizes their names and schemas;
- persists individual tool grants/effect classes;
- projects connected and granted tools into the shared `ToolCatalog`; and
- removes the dynamic projection when disconnected or removed.

`runtime/resono_runtime/tools/catalog.py` already provides the correct central boundary for:

- tool schema and dispatch;
- atomic dynamic-source replacement;
- Voice/Text audience filtering;
- Realtime tool definitions;
- local MCP definitions; and
- management projections.

### Existing Cards limitation

The present Cards implementation is a Creation-only catalog:

- `android/feature/cards/src/main/java/com/resonolabs/feature/cards/CardsDeckView.java` reads only a `creations` array and labels every card `CREATION`.
- `android/runtime-host/src/main/java/com/resonolabs/runtime/host/CreationCatalogClient.java` calls only `GET /v1/creations/catalog`.
- `android/feature/cards/src/main/java/com/resonolabs/feature/cards/CardsPageView.java` can activate only `CreationWebViewHost`.
- `runtime/resono_runtime/api/creation_routes.py` returns only imported Creation records.

The current code cannot yet represent or activate a built-in Calendar or Tasks Card.

### Existing Creation-host limitation

`android/feature/cards/src/main/java/com/resonolabs/feature/cards/CreationWebViewHost.java` currently:

- renders linked HTTPS or locally imported static Creation content;
- forwards wheel/button events as browser events; and
- restricts local asset and linked-network loading.

It does not currently implement the Rabbit `PluginMessageHandler`, `window.onPluginMessage`, `creationStorage`, an R1 Domain bridge, tool registration, or agent-session handoff. Current imports therefore render Creation UI but do not provide complete Rabbit bridge compatibility or executable agent tools.

### Misleading current Creation audience state

`runtime/resono_runtime/api/creation_routes.py` accepts `X-ReSono-Agent-Audience`, and `runtime/resono_runtime/creations/lifecycle.py` stores the resulting Voice/Text/Both binding. No Creation tool definitions are registered with `ToolCatalog`, so the audience selection currently has no executable Creation capability to filter.

The contract must be corrected before this is represented to users:

- a presentation-only Creation has no agent audience; or
- an associated real tool-bearing Plugin/MCP resource owns the audience selection.

Do not imply that selecting Voice/Text/Both makes Creation JavaScript agent-callable.

### Text-agent tool projection gap

`runtime/resono_runtime/agents/runner.py` currently filters the Agents SDK MCP connection to only `get_device_status`. Dynamic MCP tools can exist in `ToolCatalog` without being available to the Text agent.

Before imported Plugin tools are claimed to work for Text, the runner must derive its allowed names from the audience-filtered Tool Catalog rather than a hard-coded single-tool list. The OpenAI Agents SDK remains the one text-agent loop.

### Missing domains

Only `runtime/resono_runtime/domains/mail/` currently exists. Calendar and Tasks/Reminders have not been implemented in the clean runtime tree. No current local source establishes their final repositories, schemas, connectors, tools, or Card behavior.

## Proposed source structure

The implementation should add owners rather than monoliths:

```text
runtime/resono_runtime/
|- cards/
|  |- records.py
|  |- catalog.py
|  `- routes.py
|
|- domains/
|  |- calendar/
|  |  |- models.py
|  |  |- repository.py
|  |  |- service.py
|  |  |- tools.py
|  |  `- card_projection.py
|  |
|  |- tasks/
|  |  |- models.py
|  |  |- repository.py
|  |  |- service.py
|  |  |- tools.py
|  |  `- card_projection.py
|  |
|  `- mail/
|     `- existing implementation
|
|- creations/
|  |- existing import lifecycle
|  `- card_projection.py
|
|- plugins/
|  `- existing standard lifecycle
|- mcp/
|  `- existing MCP lifecycle
`- tools/
   `- existing shared ToolCatalog
```

Android ownership:

```text
android/
|- feature/cards/
|  |- CardsPageView
|  |- CardsDeckView
|  |- BuiltInCardHost
|  `- CreationWebViewHost
|
`- runtime-host/
   |- CardCatalogClient
   |- CalendarClient
   `- TasksClient
```

Exact Java class/file changes remain implementation proposals until the Calendar and Tasks user flows are frozen. Do not create generic catch-all managers, helpers, or service facades.

## Proposed dependency direction

```text
Calendar repository <- Calendar service <- Calendar tools <- Tool Catalog
                                    `---- <- Calendar card projection <- Card Catalog

Tasks repository    <- Tasks service    <- Tasks tools    <- Tool Catalog
                                    `---- <- Tasks card projection    <- Card Catalog

Creation lifecycle  -------------------- <- Creation card projection <- Card Catalog

Plugin lifecycle -> MCP lifecycle -> normalized tools -> Tool Catalog
```

Domain services do not depend on Android, Cards, Plugins, agents, or web management. Card projections and tool definitions adapt the same service independently.

## Proposed public runtime contracts

### Card catalog

Add one combined loopback Card catalog, conceptually:

```text
GET /v1/cards/catalog
```

It returns enabled built-in Card projections and enabled Creation projections with one monotonic generation. Android refreshes it without rebooting. The existing Creation asset endpoint remains owned by the Creation boundary.

The management Creation APIs remain Creation-specific. Enabling/disabling a built-in Card requires a separate bounded Card preference API and must not disable its Domain or tools.

### Calendar and Tasks APIs

The exact endpoints and schemas are not frozen in this candidate. They must be divided by caller and responsibility:

- loopback/domain endpoints needed by the native Card;
- paired management endpoints for connections, sync state, and configuration;
- Tool Catalog handlers for agent operations; and
- a future narrow Creation Domain bridge if approved.

No browser or Android component accesses SQLite directly.

## Agent behavior principles to freeze before implementation

Calendar tools should distinguish reads from side effects. At minimum, the design discussion must decide:

- event listing/search windows;
- event detail retrieval;
- conflict checking;
- create/update semantics;
- delete/cancel semantics;
- recurrence handling;
- time-zone ownership;
- account/calendar selection; and
- exact confirmation requirements.

Tasks must similarly decide:

- whether the canonical product/domain noun is `Tasks` or baseline-required `Reminders`;
- task versus scheduled-reminder semantics;
- completion and reopening;
- due date/time/time zone;
- recurrence;
- list ownership; and
- delete confirmation.

No generic provider-action escape hatch may bypass these bounded operations.

## Material Decision Gate

### MDG-CT-01 - What owns built-in Calendar and Tasks?

- **Question:** Creation, Plugin, or built-in Domain?
- **Authority/evidence:** OD-25; baseline product-domain definition; Delivery Slice 7; Agent Plugins 1.0 component boundary; reviewed Creation SDK behavior; current local code.
- **Alternatives:** built-in Creation; Plugin-owned application; built-in Domain with independent Card and Tool projections.
- **Selection/function:** built-in Domain with one canonical repository and service, independently projected to Cards and Tool Catalog.
- **Counterexample:** deleting or disabling a Card/Plugin removes canonical Calendar data or makes the Domain unavailable.
- **Dependents:** database, connectors, native Cards, tools, management APIs, imports.
- **Result:** `CONTINUE` as an architecture candidate; owner acceptance is still required before implementation.

### MDG-CT-02 - Can a standard Plugin contain a Card?

- **Question:** Treat visual Cards as an Agent Plugins component?
- **Authority/evidence:** Agent Plugins 1.0 defines portable Skills and MCP server components, not Cards.
- **Alternatives:** redefine the standard; add a required ReSono extension; keep Card association outside the portable package.
- **Selection/function:** do not redefine the standard. A future optional ReSono association may link separately installed Creation and Plugin artifacts.
- **Counterexample:** another Agent Plugins client can portably discover and render the alleged Card from the standard package alone.
- **Dependents:** import schemas, public claims, lifecycle, management UI.
- **Result:** `CONTINUE`; plugin-rendered Cards remain out of the built-in Calendar implementation.

### MDG-CT-03 - How does a Creation become agent-accessible?

- **Question:** May Creation JavaScript directly publish agent tools?
- **Authority/evidence:** reviewed Rabbit SDK exposes host messaging but no tool registration standard; current `CreationWebViewHost` has no such bridge; Tool Catalog is the single executable authority.
- **Alternatives:** arbitrary JavaScript tool publication; use existing Domain APIs; pair the Creation with a standard MCP-bearing Plugin.
- **Selection/function:** existing-domain Creations use a narrow allowlisted Domain bridge; new capabilities use a separate standard Agent Plugin/MCP server.
- **Counterexample:** Rabbit publishes a stable, applicable tool-registration specification that supplies typed executable handlers and an adequate trust boundary.
- **Dependents:** Creation host, import UX, Tool Catalog, security, Voice/Text routing.
- **Result:** `CONDITIONAL`; the Domain bridge requires a separate frozen contract before implementation.

### MDG-CT-04 - Tasks or Reminders?

- **Question:** Is `Tasks` a user-facing label for the required Reminders Domain, or a distinct Domain?
- **Authority/evidence:** the baseline and delivery plan require Reminders; the owner currently refers to Tasks.
- **Alternatives:** rename Reminders to Tasks; one combined Tasks/Reminders Domain; separate Tasks and Reminders Domains.
- **Selection/function:** unresolved. This candidate uses Tasks as the requested working label without changing the baseline requirement.
- **Counterexample:** developers implement incompatible task and reminder stores because the noun was treated as settled.
- **Dependents:** schemas, routes, tools, connectors, Card copy, migrations, tests.
- **Result:** `BLOCKED/REOPEN` for Tasks implementation only. Calendar architecture discussion may continue.

## Proposed implementation subphases

No subphase starts until its predecessor is accepted and its required decisions are frozen.

### CT-1 - Freeze Calendar behavior and donor intake

**Entry:** Slice 6 boundary accepted or owner explicitly authorizes planning ahead.  
**Work:** Review exact Calendar donor files and revision; freeze records, time zones, recurrence, connectors, operations, confirmations, and Card flows; record provenance in `docs/DONOR_CODE_REFERENCE_MAP.md`.  
**Exit:** One accepted Calendar contract with no unresolved behavior needed by storage or public APIs.

### CT-2 - Shared Card Catalog

**Entry:** Card record and built-in activation contract accepted.  
**Work:** Add the combined runtime Card catalog; project existing Creations into it; update Android to render and activate records by `sourceType`; preserve dynamic generation refresh.  
**Exit:** Real imported Creations still work, and the catalog can truthfully represent a real built-in Card without placeholders or reboot.

### CT-3 - Calendar Domain

**Entry:** CT-1 and required migrations accepted.  
**Work:** Implement repository, service, bounded connectors, and authenticated/loopback APIs.  
**Exit:** Real local Calendar CRUD, persistence, restart, isolation, offline, sync, conflict, and failure behavior pass without agent or Card facades.

### CT-4 - Calendar tools

**Entry:** Calendar service behavior accepted.  
**Work:** Register built-in Calendar tool definitions in `ToolCatalog`; apply Voice/Text routing and exact confirmation rules; correct the Text runner's hard-coded tool filter.  
**Exit:** Voice and Text projections contain only allowed healthy Calendar operations and invoke the same Calendar service.

### CT-5 - Calendar Card

**Entry:** Calendar APIs and Card Catalog accepted.  
**Work:** Add the real native Calendar Card using the established 480x640 Browser Voice design language and physical R1 input model.  
**Exit:** The Card displays and changes real Calendar data, updates dynamically, and does not own or duplicate that data.

### CT-6 - Tasks/Reminders decision and Domain

**Entry:** MDG-CT-04 resolved by owner; Calendar boundary accepted as reusable.  
**Work:** Freeze and implement the selected Tasks/Reminders model, tools, connectors/scheduling, and Card using the same public boundaries without sharing domain-specific code incorrectly.  
**Exit:** Real accepted Tasks/Reminders flows pass through one canonical repository and service.

### CT-7 - Creation Domain bridge, if still required

**Entry:** A real accepted user flow requires a Creation to operate an existing Domain; bridge schema and origin/trust policy frozen.  
**Work:** Implement only the approved typed Domain methods in `CreationWebViewHost` and the loopback runtime. Do not add arbitrary tool invocation or tool publication.  
**Exit:** A real imported Creation operates explicitly allowed data against the same Domain while denied methods/origins fail safely.

## Required testing and evidence

Planning does not claim these tests pass. The eventual contract must include:

- repository CRUD, restart persistence, migration, duplicate, and isolation tests;
- time-zone, daylight-saving, recurrence, and conflict cases;
- connector initial/incremental sync, offline retry, stale cursor, duplicate, and remote conflict tests;
- Tool Catalog Voice/Text/Both projection and denied-tool tests;
- exact side-effect confirmation, changed-draft, stale-confirmation, and cancellation tests;
- Card catalog generation and dynamic refresh tests;
- built-in Card activation versus Creation activation tests;
- disabling a Card preserves Domain data and agent tools;
- disabling agent exposure preserves Domain data and Card behavior;
- deleting a Creation or Plugin cannot delete built-in Calendar/Tasks data;
- malicious/unapproved Creation bridge calls and origins are denied;
- physical R1 touch, wheel, button, rendering, orientation, restart, and live Voice-session evidence; and
- cross-client proof that Card and agent actions observe the same canonical records.

## Explicit non-scope of this candidate

- Implementing Calendar or Tasks now.
- Changing active build status.
- Treating a Card as a new Agent Plugins component.
- Allowing arbitrary imported JavaScript to publish or execute tools.
- A second agent loop.
- A general plugin UI framework.
- Local/stdio MCP execution before a separate accepted contract.
- Contacts implementation, which remains required by Delivery Slice 7 but needs its own domain contract.
- Fake Calendar or Tasks data, placeholder Cards, or disconnected controls.

## Open decisions for the next discussion

1. Is `Tasks` the product label for the baseline-required Reminders Domain, or are Tasks and Reminders materially different?
2. Which Calendar connectors are required in the first vertical: local-only plus ICS import/export, subscribed ICS, CalDAV, or a smaller accepted set?
3. Which Calendar mutations may Voice/Text perform, and which require exact confirmation?
4. What information and actions must the first Calendar Card show on the 480x640 device?
5. Should a Creation be allowed read-only Calendar access first, or are bounded mutations required in the initial Creation Domain bridge?

## Handoff

**Current result:** The architecture review supports a built-in Calendar and Tasks Domain design with independent Card and Tool projections. Existing Plugin-to-MCP-to-Tool plumbing is largely present, but the Text runner filter prevents complete dynamic Text exposure. The Cards implementation is Creation-only, the Creation host lacks the demonstrated Rabbit bridge, and Creation audience selection currently has no executable tool meaning.

**Next authorized action:** Owner discussion and correction of this candidate, beginning with the Calendar user behavior and the `Tasks` versus `Reminders` identity. No implementation readiness or acceptance is claimed.
# Management boundary and donor-proven R1 Calendar presentation

## Owner correction: Connections is the only management surface

The management site configures accounts and services. It is not a Mail reader, Calendar viewer, or application surface. There is no `Personal Data` management page in this contract.

- Mail account setup, connection health, last-sync state, and removal belong under **Connections**. Mail remains limited to three accounts.
- Calendar account setup, connection health, last-sync state, and removal belong under **Connections**. Calendar is limited to two configured connections total.
- The management API must never return message bodies, message lists, event lists, event descriptions, attendee data, or other synchronized record content for display by the management site.
- Mail and Calendar credentials remain encrypted at rest and are never returned to the browser.
- Removing a connection removes its local synchronized projection but must not delete remote mail or remote calendar data.
- An uploaded ICS file and an ICS subscription are configured in the Calendar subsection of Connections even though only the subscription has an ongoing remote endpoint.
- A Calendar control must not appear in the web UI until its real validation, encrypted persistence, synchronization, status, and removal API are wired. Mock connection controls are prohibited.

The existing Mail management block is moved intact from the removed Personal Data page into Connections. This is an information-architecture change only; it does not change Mail permissions or expose Mail content.

## Product ownership

Calendar is a built-in R1 domain, not a Creation and not a Plugin. It has separate, one-way-owned parts:

```text
Calendar connection configuration
        -> Calendar connector (ICS subscription/file or CalDAV)
        -> canonical Calendar repository
        -> Calendar service
        -> upcoming-event projection
        -> native Calendar Card

Calendar service
        -> permission-filtered Calendar tools
        -> shared Voice/Text Tool Registry
```

Plugins may later distribute a Card plus tool definitions under the separately frozen Plugin/Card extension contract. They do not own or replace the built-in Calendar database. Creations render Card experiences but do not implicitly gain Calendar data or agent-tool access.

The clean standalone locations are:

- `runtime/resono_runtime/domains/calendar/`: canonical account/event models, repository, service, and upcoming-event rules.
- `runtime/resono_runtime/connectors/calendar/`: ICS and CalDAV transport/parsing only.
- `runtime/resono_runtime/api/calendar_routes.py`: management connection/status endpoints and device Card event endpoints, with separate response DTOs.
- `runtime/resono_runtime/tools/calendar/`: Voice/Text-facing Calendar tools and confirmation policy.
- `android/feature/calendar/`: native 480x640 Calendar list/detail/edit presentation.
- `android/feature/cards/`: deck ownership and navigation only; it hosts the Calendar entry but does not query or interpret Calendar records.

Do not put Calendar logic into `feature/cards`, `ProductRootView`, the management JavaScript, a generic manager, or a Plugin/Creation registry.

## Donor evidence and provenance

The visually and physically validated donor implementation is not the current donor `CalendarCard.java` placeholder. The applicable implementation is the shared live-data renderer:

- Donor revision: `7e40a1cd5ff0e78cc0afd507c277531e9b0aa930` (`Improve R1 card readability`).
- Exact source: `app/rabbit_r1/android/feature/personal-data/src/main/java/com/resonolabs/feature/personaldata/VaultDataPageView.java`.
- Physical validation: `app/rabbit_r1/docs/22_R1_LIVE_DATA_READABILITY_AND_WORKSPACE_BROWSER_VALIDATION.md`.
- Supporting Calendar providers: `app/modules/integrations/calendar_ics_provider.py`, `app/modules/integrations/caldav_calendar_provider.py`, `app/vault_runtime/calendar_provider.py`, and `app/vault_runtime/calendar_sync.py`.

Retained behavior: readable five-row Calendar list, selected-row marquee, direct horizontal text pan, tap-to-open detail, wrapped and vertically scrollable detail, wheel navigation, live-data refresh behavior, friendly event times, and editability-controlled actions.

Omitted behavior: donor Vault ownership, hosted/business-agent policy, shared Contacts/Reminders renderer ownership, donor entitlement/billing machinery, and the donor's inclusion of past events.

Before donor code is copied, the source revision, exact source and destination, retained/omitted behavior, license decision, and mirrored tests must be recorded as required by the repository boundary.

## Exact 480x640 list contract

The Calendar Card uses the donor-proven fixed device canvas, not responsive web sizing:

- Canvas: 480x640.
- Header: y=0..82.
- Five rows per page.
- Row top: `92 + rowIndex * 96`.
- Row rectangle: x=18..462, height=84, corner radius 18.
- Calendar icon region: x=30..76, y=`rowTop + 17`..`rowTop + 63`.
- Text clip: x=92..444.
- Primary event title: 31 px, baseline `rowTop + 38`, clip y=`rowTop + 7`..`rowTop + 43`.
- Secondary line: 21 px, baseline `rowTop + 66`, clip y=`rowTop + 45`..`rowTop + 74`.
- Footer page/index text: x=456, y=608, 18 px.

The primary line is the event title. The secondary line is `EEE, MMM d · h:mm a`, followed by ` · location` only when a location exists. Missing/null values are omitted rather than replaced by fake text.

Only the selected row may animate. If a selected primary or secondary line overflows its clip, it pauses for 900 ms, moves right-to-left, and pauses for 900 ms. The travel distance is the measured overflow plus 18 px; primary travel uses 28 ms/px and secondary travel uses 34 ms/px, with a minimum 700 ms travel duration. The view invalidates at approximately 33 ms while animation is active. A horizontal drag beginning in the visible text region (x >= 88) directly pans the selected line and clamps to its measured overflow. Dragging selects but does not open or edit the event.

Wheel next/previous changes the selected event. Activate or a second tap on the already selected row opens its details. A first tap on another row only selects it.

## Exact event-detail contract

- Detail panel: x=18..462, y=95..510, radius 26, 2 px accent border.
- Content clip: x=30..450, y=106..506.
- Header back glyph: x=25/y=53 at 43 px.
- Header title: x=55/y=45 at 30 px.
- Header subtitle: x=56/y=67 at 16 px.
- Live indicator: dot x=372/y=40 radius 5; `LIVE` x=384/y=45 at 14 px.
- Event title: 32 px, 38 px line height, word wrapped.
- Field labels: 17 px.
- Field values: 25 px, 32 px line height, word wrapped.
- Fields, in order when present: `STARTS`, `ENDS`, `LOCATION`, `CALENDAR`, `ORGANIZER`, `DESCRIPTION`.
- Detail content vertically pans by direct finger drag and clamps to measured content height.
- The scroll cue occupies x=30..450, y=466..506 and must not overlap readable content.
- Actions occupy y=528..592. Edit is x=18..312. A destructive action is not rendered unless the connection and event genuinely support it and the product confirmation contract permits it.
- Back returns detail to list before leaving the Calendar Card.

The standalone implementation must not reproduce the donor's shared generic record renderer. It must implement these proven behaviors in the dedicated `android/feature/calendar` module with Calendar-specific view state and DTOs.

## Upcoming-only projection

The donor sorter included past events after future events. That behavior is explicitly not retained.

- Timed event inclusion: `end_at >= now`; when no end is present, `start_at >= now`.
- All-day event inclusion is evaluated in the event/calendar timezone and remains visible through the local end of its final day.
- Sort ascending by effective start instant, then stable event identifier.
- Cancelled events are excluded.
- The Card consumes only this server-produced projection. Android must not independently decide whether an event is upcoming.
- The repository retains synchronized records required for correct updates and sync bookkeeping; the device-facing list endpoint exposes upcoming events only.

## Calendar implementation checkpoints

1. **Management IA correction:** remove Personal Data, move the existing real Mail setup/status/removal surface to Connections, and preserve all Mail security and limits.
2. **Calendar connection contract:** implement at most two ICS-file, ICS-subscription, or CalDAV connections with validation, encrypted secrets, five-minute sync status, removal, and no event-content management response.
3. **Canonical Calendar domain:** add migrations, account/event repository, timezone-aware normalization, recurrence handling boundary, stable provider identifiers, upcoming-only projection, and connector-independent service methods.
4. **Agent tools:** register read/search/detail and confirmation-gated create/update tools through the shared Tool Registry for selectable Voice, future Text, or both. Do not invent a separate agent loop.
5. **Native Card:** add the dedicated Calendar feature module and wire its real upcoming projection into the existing Cards deck. Preserve the live Voice session while navigating Cards.
6. **Physical acceptance:** validate exact 480x640 list/detail readability, marquee and drag behavior, wheel/touch navigation, edit flow, sync refresh, two-account merge behavior, and no management-site content leakage.

Each checkpoint must update this contract with exact code locations and evidence before the next checkpoint begins. No disconnected UI is permitted.

## Implementation record

### Checkpoint 1: Management IA correction

Implemented on 2026-08-20:

- `web/management/index.html` removes the Personal Data navigation/page and places the existing Mail configuration surface under Connections.
- `web/management/build07.js` loads Mail and the cross-domain connection projection together when Connections becomes active.
- No Mail record content is added to the management contract.

### Checkpoint 2A: Canonical storage boundary

Implemented on 2026-08-20:

- `runtime/resono_runtime/storage/migrations/v028_calendar.py` owns Calendar account/event schema and indexes.
- `runtime/resono_runtime/domains/calendar/models.py` owns immutable Calendar account and event records.
- `runtime/resono_runtime/domains/calendar/repository.py` owns the transactional two-account limit, local account removal, atomic per-account event replacement, stable provider identities, and the upcoming-only query.
- Calendar credentials reference the existing device-sealed `connection_credential_envelopes` table; no new encryption mechanism was introduced.
- The general `connections` table remains a status/read projection. Calendar domain code owns Calendar mutation.
- Calendar routes and management controls remain intentionally unexposed until Checkpoint 2B supplies real connector validation, synchronization, and status transitions.

### Uniform Calendar tool package

Calendar tools are one built-in, versioned package rather than freely registered functions:

- Package owner: `runtime/resono_runtime/tools/calendar/`.
- Public registration entry point: `CalendarToolPackage.register(ToolCatalog)`.
- Stable audience resource: `domain_tool_set:calendar`.
- Version 1 tool set: `calendar_list_upcoming`, `calendar_search`, `calendar_read_event`, `calendar_create_event`, `calendar_update_event`, `calendar_delete_event`, and `calendar_confirm_action`.
- `contract.py` owns public names, descriptions, JSON Schemas, effects, and package version.
- `handlers.py` is the narrow application-service protocol; it owns no database or provider code.
- `package.py` must register the complete tuple or fail. Application composition must not register individual Calendar tools.
- The package is not wired into the live Tool Catalog until the real Calendar service and connectors satisfy every handler. This prevents advertised but disconnected tools.

All seven tools remain part of the uniform package for readable and writable providers. Create/update/delete prepare an immutable ten-minute action after capability checks. `calendar_confirm_action` executes that exact action only after a later explicit approval utterance in the same trusted agent session. Runtime handlers enforce the selected account's discovered capabilities and event-level editability. Read-only sources return a precise capability denial rather than removing tool vocabulary or silently switching calendars.

### Donor adaptation record: Calendar connectors

- Source revision: donor working tree corresponding to the reviewed 2026-08-20 R1 Calendar implementation; visual behavior is anchored separately to commit `7e40a1cd5ff0e78cc0afd507c277531e9b0aa930`.
- Exact donor ICS source: `app/modules/integrations/calendar_ics_provider.py`.
- Exact destination: `runtime/resono_runtime/connectors/calendar/ics.py`.
- Exact donor CalDAV source: `app/modules/integrations/caldav_calendar_provider.py`.
- Exact destination: `runtime/resono_runtime/connectors/calendar/caldav.py`.
- Retained behavior: public-URL/redirect validation, ICS unfolding and decoding, feed validation/fetch, CalDAV discovery, REPORT/GET reads, authenticated create/update/delete, safe event identifiers, and RFC-style event serialization.
- Omitted behavior: donor Vault credentials, Vault cache/import records, hosted error types, business/entitlement policy, and donor application-module imports.
- Standalone addition: `runtime/resono_runtime/security/outbound.py` is the single SSRF/redirect guard for connector traffic.
- Dependency decision: HTTPX is already packaged through the accepted `openai-agents==0.18.3` runtime dependency; no new Calendar-only dependency is introduced.
- License decision: no donor repository license file was present in the surveyed donor root. This is an owner-directed internal project adaptation, not an unreviewed third-party import. No external copyright header was removed.
- Required mirrored tests: public/private URL rejection, redirect restrictions, ICS folding/date parsing, CalDAV discovery, read fallback, write methods, and provider error preservation.

## Completed implementation map

### Connection and synchronization runtime

- Migration: `runtime/resono_runtime/storage/migrations/v028_calendar.py`.
- Models/repository/service/scheduler: `runtime/resono_runtime/domains/calendar/`.
- ICS and CalDAV connectors: `runtime/resono_runtime/connectors/calendar/`.
- Shared outbound SSRF guard: `runtime/resono_runtime/security/outbound.py`.
- Management/device routes: `runtime/resono_runtime/api/calendar_routes.py`.
- Runtime composition: `runtime/resono_runtime/application.py`, `api/routes.py`, and `api/http_server.py`.
- Management proxy allowlist: `android/runtime-host/src/main/java/com/resonolabs/runtime/host/ManagementRuntimeProxy.java`.

The scheduler checks due connections every 15 seconds; successful connections become due every five minutes. A ten-minute lease prevents overlap. Per-account event replacement is atomic. Failed synchronization preserves the previous projection, records a content-free failure, and retries after one minute.

ICS files and subscriptions are read-only. CalDAV discovers create/update/delete through DAV `current-user-privilege-set` and safely defaults missing privileges to denied. Remote denial remains authoritative.

### Uniform agent package

- Contract: `runtime/resono_runtime/tools/calendar/contract.py`.
- Handler boundary: `runtime/resono_runtime/tools/calendar/handlers.py`.
- Registration owner: `runtime/resono_runtime/tools/calendar/package.py`.
- Runtime composition contains one `CalendarToolPackage(...).register(self._tools)` call.
- Audience uses one `domain_tool_set:calendar` binding for Voice and Text.

Create/update/delete prepare immutable pending actions. The agent reviews the exact returned payload. `calendar_confirm_action` requires a later explicit approval utterance in the same trusted session, the exact content hash, and execution within ten minutes. Actions are single-use.

### Web management

`web/management/index.html` and `build07.js` place Mail and Calendar under Connections. Calendar supports an ICS subscription, local ICS file, or selected CalDAV calendar URL. Maximums are three Mail and two Calendar connections. Mail and Calendar are filtered from “Other connections” so rows do not duplicate. No management response or element renders messages or events.

### Native Calendar Card

- Module: `android/feature/calendar/`.
- Device client: `android/runtime-host/src/main/java/com/resonolabs/runtime/host/CalendarEventClient.java`.
- Cards integration: `android/feature/cards/CardsDeckView.java` and `CardsPageView.java`.

Calendar is a built-in Card, never a Creation record. Its native view uses the donor-proven 480x640 list/detail measurements, five rows, selected-line marquee, direct text pan, touch/wheel navigation, wrapped details, bounded vertical scrolling, and upcoming-only DTOs. Writable events expose `EDIT WITH VOICE`; Voice uses the uniform package for reviewed and confirmed changes. Read-only events show `READ ONLY · CONNECTED CALENDAR`.

Cards navigation does not construct or end the Voice session. Hiding Cards stops Calendar polling; returning restarts it. Local event projections refresh without an APK or runtime restart.

### Focused evidence owner

- Test: `tests/runtime/test_calendar_contract.py`.
- Command: `PYTHONPATH=runtime python3 -m unittest tests.runtime.test_calendar_contract`.
- Physical acceptance must still prove exact 480x640 rendering, touch/wheel behavior, marquee, two-account merge, live refresh, Voice edit handoff, provider denial, and Voice-session continuity.

## Implementation status

The scoped Calendar implementation is code-complete as of 2026-08-20:

- Connections-only management architecture is implemented.
- Two-account schema, encrypted credentials, provider validation, five-minute synchronization, and local removal are implemented.
- Upcoming-only canonical projection and device-only event APIs are implemented.
- Uniform Voice/Text Calendar tool package, provider capability denial, immutable review, explicit confirmation, ten-minute expiry, and single-use execution are implemented.
- Built-in native Calendar Card list/detail/Voice-edit flow is implemented without using Creation or Plugin ownership.
- Focused host contract tests are present.

Code-complete does not mean physically accepted. Host tests, Android compilation, APK deployment, real ICS/CalDAV provider validation, and 480x640 hardware acceptance have not been executed in this implementation pass. They remain validation evidence, not missing Calendar architecture or feature code.

## Owner physical test update - 2026-08-20

- Tasks Voice behavior passed owner testing.
- Calendar connection, synchronized Card list, detail navigation, and Voice behavior passed owner testing after the shared Cards Back and full-screen content corrections.
- Mail Voice behavior remains under active owner testing and is not accepted by this update.

## Shared approval boundary correction

Tasks, Calendar, and Mail no longer maintain domain-specific approval phrase
allowlists. Confirmation intent is interpreted by the Voice agent, while the
runtime authorizes execution only through structural evidence: unchanged
content hash, same trusted Voice session, strictly later native utterance
sequence, unexpired pending action, and single-use transactional claim.
Calendar provider capability and event editability checks remain authoritative
and unchanged. This avoids English-keyword coupling without turning approval
into a model-supplied boolean.
