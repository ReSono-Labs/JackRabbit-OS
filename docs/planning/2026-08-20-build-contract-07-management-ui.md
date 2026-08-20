# Build Contract 07: Web Management UI Overhaul

**Status:** implementation contract
**Authority:** UI companion to `2026-08-20-build-contract-07-extensions-mail.md`; this document cannot expand Build 07
**Surface:** paired, same-LAN HTTPS management site

## Outcome

Replace the inherited single-column settings page with one coherent responsive application. It exposes every completed Build 07 management capability without becoming an alternate agent experience. Voice remains the primary product interaction. The site configures the device, imports portable capabilities, reviews conflicts, manages connections, and reports real runtime state.

No count, status, row, or action may be simulated. Every visible feature must be backed by the on-device API named here.

This is a configuration surface, not a feature-use surface. It must not provide an agent chat box, read or compose Mail, run imported tools, launch Creations, or execute Skills/Plugins. Those capabilities are used by the on-device Voice agent and the later text agent. Management may only configure their availability and audience.

## Exact visual contract

The exact desktop authority is the donor phase `phases/2026-08-10_consumer_dashboard_simplicity_overhaul/visuals/01-home-desktop.png`, `03-agents-desktop.png`, and `05-devices-desktop.png`, together with the current R1 Browser Voice/native interface. The earlier card-heavy implementation matched colors but failed the composition. It is rejected as a reference: management must use the donor's quiet full-height rail, simple line icons, restrained headings, large negative space, flat sections, and hairline-separated rows. Rounded containers are reserved for inputs, explicit buttons, dialogs, and the active navigation item; ordinary information and catalog text must not be wrapped in dashboard cards.

| Role | Value | Use |
| --- | --- | --- |
| Canvas | `#031426` | page background |
| Deep canvas | `#020d19` | edge depth |
| Panel | `#07182a` | primary surfaces |
| Raised panel | `#0b2035` | rows and controls |
| Hairline | `#26384c` | borders and separators |
| Primary type | `#f3f7fb` | headings and values |
| Secondary type | `#a9b8d3` | explanation and metadata |
| Aqua | `#79f2dd` | shell identity, active, ready, primary action |
| Yellow | `#ffd166` | pending import and attention |
| Purple | `#c792ff` | Plugin/MCP differentiation only |
| Red | `#ff6b6b` | destructive action and failure only |

Accents are controlled semantic highlights. They never recolor whole pages. Typography uses the R1's geometric rounded character through `Avenir Next`, `Century Gothic`, and `Trebuchet MS` fallbacks. Inter, Roboto, Arial, and default platform stacks are not the target.

## Information architecture

One persistent header and one navigation model own five work areas:

1. **Overview**: device health, build contract, database version, HTTPS certificate, user name, restart.
2. **AI & Voice**: Platform access, ChatGPT subscription, models, reasoning, and memory administration.
3. **Library**: Skills, Plugins, MCP tools, tool visibility, and Creations.
4. **Connections**: configured service endpoints, encrypted sign-in presence, and health.
5. **Personal Data**: Mail account setup and five-minute sync status. It never renders messages.

On mobile, navigation becomes a horizontal tab strip. Content reflows without browser zoom or resolution changes.

## Plain-language labels

| Internal term | User label |
| --- | --- |
| `voice` | Voice agent |
| `text` | Text agent |
| `both` | Voice and text agents |
| `preflight` | Review import |
| `replace` | Replace existing item |
| `enabled` | Available |
| `disabled` | Turned off |
| `credentialPresent` | Sign-in saved securely |
| `rabbit_qr_link` | Rabbit QR link |
| `local_archive` | Uploaded package |
| `health_state` | Connection status |

Raw enums, JSON keys, database identifiers, exceptions, and HTTP codes never appear as primary UI copy.

## Authoritative API map

| Area | Read | Mutation |
| --- | --- | --- |
| Device | `GET /v1/management/status` | `POST /v1/management/restart` |
| Profile | `GET /v1/management/profile` | `POST /v1/management/profile` |
| OpenAI | `GET /v1/management/openai` | existing `/v1/management/openai/*` routes |
| Memory | existing `/v1/management/memory*` routes | existing finalize, reindex, delete routes |
| Skills | `GET /v1/management/skills` | preflight, confirm, enable/disable, delete |
| Plugins | `GET /v1/management/plugins` | preflight, confirm, enable/disable, delete |
| MCP | `GET /v1/management/mcp/connections` | import preflight/confirm and lifecycle routes |
| Tools | `GET /v1/management/tools` | only mutations already supplied by the API |
| Connections | `GET /v1/management/connections` | owned connection endpoints |
| Mail | `GET /v1/management/mail/accounts` | account create/update/delete |
| Creations | `GET /v1/management/creations` | archive/QR preflight, confirm, enable/disable, delete |

Mutations use the paired session CSRF token. Credentials may be submitted but are never returned. Browser code never duplicates server policy.

## Global import flow

1. Select a supported file or enter decoded Rabbit QR details.
2. Select Voice agent, Text agent, or both where applicable.
3. Send input to its standard-specific preflight endpoint.
4. Server validates, quarantines unsafe input, detects canonical-name conflict, and issues a ten-minute token.
5. Show a review containing human name, type, source, audience, returned components/permissions, and conflict result.
6. Install nothing until the user selects **Install** or **Replace existing item**.
7. Cancel discards browser state. Expired tokens require another review.
8. Refresh the authoritative catalog after confirmation; never append a guessed row.

Inputs remain exactly those accepted by Build 07: standard Skill ZIP or `SKILL.md`/`skills.md`; standard Agent Plugin ZIP; standard `mcp.json`; supported Creation archive or decoded official Rabbit QR descriptor. The same canonical name always requires disclosed replacement and never creates numbered duplicates.

## Catalog and deletion

All catalogs share one row grammar: accent rail, human name, description, textual state, audience/source metadata, and actions. Enable/disable is reversible. Delete always names the item in a confirmation dialog.

Deleting a Mail account removes the connection and its local synchronized data through Mail ownership. It does not send provider-side message deletion. The Voice agent receives no delete-mail tool and this UI adds none.

## Source ownership

```text
web/management/index.html       semantic shell and real forms/dialogs
web/management/management.css  exact theme, layout, shared components
web/management/app.js          pairing, profile, OpenAI, text, memory
web/management/build07.js      Build 07 catalogs/imports/connections/mail
android/.../ManagementAssetStore.java  HTTPS asset allowlist and MIME mapping
android/scripts/build_debug.sh          canonical source-to-APK copy
```

This is intentionally small. Build 07 logic does not absorb pairing/provider/memory. No framework, bundler, parallel client state store, or facade API is introduced.

## Interaction and accessibility

- Pairing remains the only unauthenticated application state.
- Each area owns real loading, empty, populated, and error states.
- Failed sections do not erase successful sections.
- Busy mutations disable their trigger.
- Dialog focus is native; Escape and Cancel close uncommitted work.
- Status is never color-only.
- Touch targets are at least 44 CSS pixels.
- Aqua visible focus rings are mandatory.
- Reduced-motion preference removes transitions.
- Layout supports 320 CSS pixels without zooming.

## Acceptance boundary

Source completion requires every legacy control to use the new theme, every Build 07 catalog/setup flow to call a real endpoint, all assets to be packaged, and focused browser/Android checks to pass. Device visual acceptance remains a deployment gate and cannot be claimed while the R1 is unplugged.

## 2026-08-20 physical correction evidence

The first deployed overhaul was rejected because it copied the palette but not the donor composition: boxed dashboard cards, numbered navigation, heavy headings, and excessive rounded containers materially drifted from the approved simplicity-overhaul visuals. The replacement removes those patterns, adds flat line-icon navigation, uses flat sections and hairline-separated catalogs, reduces heading weight/scale, and reserves containers for controls and dialogs.

The corrected source rebuilt successfully with all 196 Android tasks, standalone boundary checks, and embedded runtime package checks passing. It installed successfully on physical R1 serial `919109A5P1600502814D`; the restarted process served `/` and `/management/management.css` with HTTP 200. These checks prove deployment and asset delivery. Owner visual acceptance remains authoritative.
