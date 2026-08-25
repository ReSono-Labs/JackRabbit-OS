# Contributing to JackRabbit

JackRabbit welcomes focused, non-commercial community contributions. Keep
`main` stable and make changes through pull requests.

Before writing code, read:

1. [README.md](README.md) for the product and architecture boundaries.
2. [BUILDING.md](BUILDING.md) for the supported build path.
3. [Extension Development Guide](EXTENSION-DEVELOPMENT.md) when adding an
   integration, Skill, Plugin, MCP server, Tool, Creation, or Card.
4. [llm.md](llm.md) when using a coding assistant.

## Working together

- Create one branch per focused change. Do not push feature work directly to
  `main`.
- Open a draft pull request early so other contributors can see its scope and
  affected files.
- Keep each responsibility in its existing module. Avoid catch-all utility,
  helper, common, manager, or service files.
- If another pull request changes the same area, update your branch from the
  latest `main`, resolve the conflict there, and retest before review.
- Prefer small pull requests that preserve existing behavior. Separate local
  inference, STT/TTS, UI, and transport changes when they can be reviewed
  independently.

Git will flag conflicting edits to the same lines, but it cannot detect two
different implementations of the same responsibility. The draft pull request
and the extension decision in the template are how the project prevents that
larger kind of conflict.

## Choose the correct boundary

Do not overhaul the application when an existing extension point owns the
work:

- Use an instruction `SKILLS.MD` when the owner only needs to change how Voice
  or Background Agent behaves.
- Use an Agent Skill inside a Plugin for portable, reusable instructions.
- Use MCP when a model needs tools from an external or independently running
  service.
- Use a Plugin when Skills and MCP configuration should install and move
  through one lifecycle, or when the package also owns one JackRabbit Card.
- Use a standalone Creation for a bounded static Card that does not need a
  Plugin lifecycle.
- Add a built-in Tool only when the capability must be implemented and shipped
  inside the trusted on-device Python runtime.
- Change the Android or provider/runtime code only for behavior that cannot be
  truthfully implemented through those extension boundaries. Native audio,
  WebRTC/WebSocket transport, camera, hardware, and provider selection are not
  Skills or Creations.

The [Extension Development Guide](EXTENSION-DEVELOPMENT.md) contains the exact
supported layouts and current limitations.

## Implementation rules

- Connect every user-facing surface to real behavior. Do not add mock data,
  placeholder screens, simulated states, or facade endpoints.
- Preserve one canonical owner for configuration, state, and domain data.
- Skills provide instructions; they do not grant tools or permissions.
- MCP is the model-facing tool boundary. Do not route high-rate microphone or
  speaker audio through MCP.
- Keep ChatGPT/Codex device authorization separate from external MCP
  credentials.
- Treat imported packages and remote MCP servers as untrusted until their
  validation, audience, and permission gates pass.
- Record copied donor code before importing it: source revision, exact source
  and destination paths, retained and omitted behavior, license decision, and
  tests. Donor repositories are read-only.

## Tests and evidence

Run the smallest relevant tests while developing, then the applicable project
checks from [BUILDING.md](BUILDING.md). Extension work should normally include
the matching runtime tests under `tests/runtime/`.

Do not describe a device behavior as working merely because it compiles or
passes a host test. Identify what was host-tested, what was exercised against a
real service, and what was physically accepted on an R1.

## Pull requests

The pull-request description must explain:

- what user problem the change solves;
- why the selected extension or module is the correct owner;
- which existing behaviors remain unchanged;
- which files and contracts changed;
- how the change was tested;
- whether physical R1 acceptance is required or complete;
- whether dependencies, network destinations, permissions, credentials, or
  licenses changed.

Reviewers may ask for a large change to be split when it crosses independent
owners. A Plugin that includes a Skill, an MCP connection, and a Card may stay
together when those pieces form one coherent integration and share one
lifecycle.

## License

Contributions are accepted under the repository's
[PolyForm Noncommercial License 1.0.0](LICENSE). JackRabbit is a
source-available noncommercial project and its license is not OSI-approved.
Agent Skills, Agent Plugins, and MCP are open standards; using those formats
does not change JackRabbit's project license.

Commercial use, monetized distribution, and commercial sublicensing are not
accepted. Verify that new dependencies and bundled assets can legally be
distributed under this noncommercial project model.

Questions and early design discussion are welcome in the
[JackRabbit Discord community](https://discord.gg/HeKGmh5mC).
