# First Build Product Deferrals

**Status:** Owner-directed scope boundary, 2026-08-20

The first integrated R1 build deliberately excludes the following product domains:

- Contacts
- Reminders
- External AI

Contacts and Reminders may return later as installable first-party packages. External AI will also be designed and delivered later as a package. None of these may appear as built-in placeholders, disconnected management controls, fake Cards, inactive tools, migrations, or implied first-build capabilities.

External AI deferral includes the public HTTPS MCP/OAuth gateway, external ChatGPT client connection, device bridge, outbox, and external-memory capture flow previously assigned to a later delivery slice. Existing OpenAI/ChatGPT credentials used internally by the R1 Voice platform are not External AI and remain in scope.

Any later package must receive its own accepted contract covering installation, credentials/connections, scoped tools, data ownership, Cards if applicable, removal, isolated storage, and security boundaries. Deferral does not authorize folding these capabilities into the current Plugin importer prematurely.

The first build therefore focuses on the native Voice platform, Skills/Plugins/MCP, Mail, Calendar, Creations/Cards, camera/direct handoff, memory, and the simple first-party Tasks package.
