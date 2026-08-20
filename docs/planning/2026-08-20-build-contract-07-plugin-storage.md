# Build Contract 07 Deferred Subphase - Isolated Plugin Storage

**Status:** Architecture accepted; implementation required before package storage is advertised or accepted

**Parent contract:** `docs/planning/2026-08-20-build-contract-07-plugin-card-extensions.md`

## Decision

An imported package may request persistent local storage, but it never receives SQL access, a filesystem path, or permission to modify the canonical R1 database.

The runtime allocates one host-owned SQLite database per stable package identity. Cards and tools owned by that package access the same isolated database only through a scoped host API.

```text
standard Agent Plugin package
        +
optional namespaced R1 storage declaration
        -> import preflight
        -> explicit user approval
        -> isolated package database
        -> scoped Package Storage API
        -> package Card and package tools
```

## Standards boundary

Agent Plugins does not define portable application database allocation. ReSono must not add storage fields to standard `plugin.json` or describe this extension as portable Agent Plugins behavior.

The optional declaration belongs in the existing ReSono client namespace:

```text
example-plugin/
├── plugin.json
├── skills/
├── mcp.json
└── com.resonolabs.cards/
    ├── card.json
    └── storage.json
```

A package without a Card may still use a future general ReSono namespace selected by a later standards review. Until that path is frozen, `com.resonolabs.cards/storage.json` is the only candidate location and must not be accepted by production import code.

## Version 1 declaration candidate

```json
{
  "contractVersion": 1,
  "schemaVersion": 1,
  "mode": "records",
  "quotaBytes": 5242880,
  "collections": [
    {
      "name": "documents",
      "indexes": ["filename", "updatedAt"]
    },
    {
      "name": "preferences",
      "indexes": []
    }
  ]
}
```

Version 1 supports only:

- `key_value`: key plus JSON value, with key/prefix lookup.
- `records`: host-managed JSON records in declared collections with a bounded set of declared indexes.

Arbitrary SQL, SQLite extensions, triggers, views, attached databases, executable migrations, and package-selected file paths are prohibited.

## Storage isolation

```text
runtime/data/resono.sqlite3
runtime/data/package-storage/<storage-id>.sqlite3
```

The canonical database stores only allocation and lifecycle metadata:

```text
package_storage_grants
├── package_id
├── contract_version
├── schema_version
├── storage_id
├── mode
├── quota_bytes
├── lifecycle_state
├── created_at
└── updated_at

package_storage_collections
├── package_id
├── collection_name
├── indexes_json
└── schema_version
```

Actual package records remain in the isolated package database. The runtime derives package identity from the authenticated execution context; a caller never supplies or overrides another package identity.

## Scoped host API

The initial API is declarative and bounded:

- `get(collection, key)`
- `put(collection, key, jsonValue)`
- `delete(collection, key)`
- `query(collection, filters, order, limit)`
- `transaction(operations)`

The host enforces package identity, declared collection, schema version, quota, maximum record size, query limits, and lifecycle state before every operation.

Storage permission grants no implicit access to Mail, Calendar, Contacts, Reminders, files, network, MCP tools, another package, or canonical R1 tables. Those remain separate declared and granted capabilities.

## Import and overwrite lifecycle

1. Validate the standard Agent Plugin package unchanged.
2. Detect the optional namespaced storage declaration.
3. Validate contract version, mode, quota, collections, indexes, and schema transition.
4. Include the request and any destructive consequences in global import preflight.
5. Notify the user before install or same-ID overwrite.
6. Allocate or reopen the database only after confirmation.
7. Activate the package only after storage setup succeeds.
8. If activation fails, restore the prior package and prior compatible storage contract.

The installer never rewrites the imported package with a database path. It records `package_id -> storage_id` in the canonical grant catalog.

Same package ID means replacement, not duplication. Compatible updates retain data. Quota increases and destructive schema transitions require explicit approval. Version 1 host-managed transitions may add a collection or index. Collection removal, field remapping, or data deletion is rejected until a later declarative migration contract is accepted.

## Removal

User-confirmed Plugin removal always removes its isolated storage. There is no retain-data option.

The Plugin lifecycle must treat removal as one coordinated operation:

1. Disable the Plugin and revoke all active Card/tool storage sessions.
2. Remove Plugin components and runtime projections.
3. Delete the isolated package database and its journal/WAL sidecar files through the package-storage allocation owner.
4. Delete collection metadata and the canonical storage grant.
5. Remove any package-storage credential or key material.
6. Complete Plugin removal only after storage cleanup succeeds.

If storage cleanup fails, removal must report a precise failure and retain a disabled, quarantined lifecycle record for retry. It must not report successful deletion while leaving an orphaned database. No future package may claim a removed package's storage.

## Card and tool sharing

A package Card and its agent tools may share the package database because the runtime binds both to the same installed package identity:

```text
package Card ─┐
              ├─ scoped Package Storage API ─ package database
package tools ┘
```

This allows a Card to render records while Voice/Text tools query or change those same records. It does not make the Card an agent tool or make storage an MCP server.

## Proposed code ownership

```text
runtime/resono_runtime/package_storage/
├── contract.py
├── allocation.py
├── records.py
├── quota.py
└── lifecycle.py

runtime/resono_runtime/storage/
├── package_storage_grants.py
└── migrations/v0xx_package_storage.py

runtime/resono_runtime/api/
└── package_storage_routes.py

runtime/resono_runtime/plugins/
└── storage_component.py
```

- `contract.py` validates the namespaced declaration.
- `allocation.py` owns opaque database allocation and path resolution.
- `records.py` is the only SQLite data-access owner for package databases.
- `quota.py` enforces limits before and after writes.
- `lifecycle.py` coordinates install, overwrite, rollback, and mandatory storage deletion.
- Plugin lifecycle calls the storage component; it does not implement storage directly.
- HTTP/Card/tool adapters depend on the scoped service, never SQLite.

Do not create a generic `manager`, `utils`, `helpers`, or shared arbitrary database service.

## Mandatory implementation gate

This contract must enter the actual Plugin import/runtime codebase before any package with `storage.json` is accepted. Until then:

- Import preflight must reject or ignore storage declarations according to the then-active contract; it must never imply storage was granted.
- No user-facing storage option may appear.
- No package Card or tool may receive a direct database/file path.
- No arbitrary package code may be introduced merely to provide storage access.

Required implementation order:

1. Freeze the namespace and JSON Schema.
2. Add allocation/grant migrations and repositories.
3. Add isolated database and quota owners.
4. Integrate storage declaration into Plugin preflight/confirm/rollback and mandatory remove cleanup.
5. Add authenticated Card/tool scoped APIs.
6. Add overwrite, retention, deletion, corruption, quota, and isolation tests.
7. Add management preflight/removal wording only after the APIs are real.

## Acceptance

- Two packages cannot read, write, attach, enumerate, or claim each other's storage.
- No package can access canonical R1 tables or obtain a storage path.
- Invalid declarations and arbitrary SQL are rejected before installation.
- Quotas and record/query limits are enforced transactionally.
- Same-ID compatible updates retain data without duplication.
- Failed updates restore the previous package/storage contract.
- User-confirmed Plugin removal deletes the isolated database, sidecars, grant metadata, and storage key material without leaving orphaned data.
- Cards and tools for one package see the same committed records.
- Restart does not lose grants or data.
- No storage capability expands Mail, Calendar, filesystem, network, or agent permissions.
