import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const batchesDoc = JSON.parse(fs.readFileSync(path.join(root, ".understand-anything/intermediate/batches.json"), "utf8"));

const summaries = {
  "runtime/resono_runtime/connectors/calendar/__init__.py": "Defines the public calendar connector surface by re-exporting the CalDAV and read-only ICS provider clients and their credential and event contracts.",
  "runtime/resono_runtime/connectors/calendar/caldav.py": "Implements the writable CalDAV provider client, including discovery, capability checks, event CRUD, XML parsing, ICS serialization, authentication fallback, and redirect-safe outbound requests.",
  "runtime/resono_runtime/connectors/calendar/ics.py": "Implements read-only public ICS feed validation, retrieval, unfolding, parsing, and normalization into the runtime calendar event contract.",
  "runtime/resono_runtime/creations/__init__.py": "Exposes the creation archive inspection, descriptor inspection, and lifecycle APIs used to install and manage user-provided web creations.",
  "runtime/resono_runtime/creations/archives.py": "Validates creation ZIP archives, enforces safe bounded paths, derives the content root, and extracts normalized HTML metadata for installation preflight.",
  "runtime/resono_runtime/creations/descriptors.py": "Fetches and validates remote creation descriptors, resolving bounded HTTPS entry and icon URLs into a normalized archive inspection result.",
  "runtime/resono_runtime/creations/lifecycle.py": "Coordinates real creation preflight, import confirmation, catalog state, enablement, deletion, recovery, generation tracking, and content hashing.",
  "runtime/resono_runtime/domains/calendar/__init__.py": "Defines the public calendar domain surface by re-exporting calendar models and repository types.",
  "runtime/resono_runtime/domains/calendar/models.py": "Defines immutable calendar account, capability, and synchronized event records shared by storage, services, routes, and connectors.",
  "runtime/resono_runtime/domains/calendar/repository.py": "Owns SQLite persistence and state transitions for calendar accounts, capabilities, synchronization leases, events, pending mutations, and upcoming-event queries.",
  "runtime/resono_runtime/domains/calendar/scheduler.py": "Runs periodic calendar synchronization on a stoppable background thread by selecting due accounts and delegating each sync to the calendar service.",
  "runtime/resono_runtime/domains/calendar/service.py": "Orchestrates calendar account setup, credential handling, provider selection, synchronization, event search, and capability-gated event mutations.",
  "runtime/resono_runtime/security/outbound.py": "Enforces SSRF-resistant outbound networking by validating HTTPS URLs, resolving public hosts, rejecting private or special-use addresses, and checking redirects.",
  "android/app/src/main/java/com/resonolabs/voice/MainActivity.java": "Hosts the native R1 Voice surface, starts and probes the on-device runtime, applies display policy, and refreshes real management pairing state during the activity lifecycle.",
  "android/app/src/main/java/com/resonolabs/voice/ReSonoBootReceiver.java": "Restarts the foreground on-device runtime after boot or package replacement so local Voice and management services remain available.",
  "android/core/power/src/main/java/com/resonolabs/ui/power/DisplayPolicy.java": "Applies the R1 window power contract, including keep-screen-on behavior, explicit brightness control, and the verified Rabbit user-activity input flag.",
  "android/feature/settings/src/main/java/com/resonolabs/feature/settings/ManagementPairingState.java": "Defines the compact immutable state record used by native settings to render management pairing status, code, address, and expiry.",
  "android/runtime-host/src/main/java/com/resonolabs/runtime/host/RuntimeHealthClient.java": "Polls the authenticated loopback health endpoint off the main thread and returns the versioned runtime and database readiness contract to Android UI code.",
  "android/runtime-host/src/main/java/com/resonolabs/runtime/host/RuntimeManagementClient.java": "Provides asynchronous authenticated loopback access to pairing and OpenAI management endpoints while advertising only active Wi-Fi or Ethernet HTTPS addresses.",
  "android/runtime-host/src/main/java/com/resonolabs/runtime/host/RuntimeService.java": "Owns the Android foreground runtime process, local token and credential bridges, HTTPS management server, embedded Python host, restart scheduling, and startup failure limiting.",
  "runtime/resono_runtime/domains/mail/__init__.py": "Defines the public mail domain surface by re-exporting mail models and repository types.",
  "runtime/resono_runtime/domains/mail/connector.py": "Implements bounded IMAP and SMTP integration, including folder discovery, incremental message synchronization, MIME parsing, attachment handling, mutations, and safe outbound connection rules.",
  "runtime/resono_runtime/domains/mail/models.py": "Defines immutable mail account and message records shared across synchronization, persistence, tools, and API views.",
  "runtime/resono_runtime/domains/mail/repository.py": "Owns SQLite persistence for mail accounts, folders, messages, attachments, sync checkpoints, mutation state, search, and bounded account lifecycle operations.",
  "runtime/resono_runtime/domains/mail/scheduler.py": "Runs periodic mail synchronization on a stoppable background thread by selecting due accounts and delegating sync work to the mail service.",
  "runtime/resono_runtime/domains/mail/service.py": "Coordinates mail account connection, encrypted credentials, provider validation, synchronization, and user-facing mail actions across repository and network boundaries.",
  "runtime/resono_runtime/domains/mail/tools.py": "Registers the real mail tool package and implements typed agent-facing search, read, draft, send, reply, move, flag, and delete operations.",
  "runtime/resono_runtime/domains/tasks/__init__.py": "Defines the public built-in Tasks domain surface by re-exporting task models, repository, service, and tool registration.",
  "runtime/resono_runtime/domains/tasks/models.py": "Defines the immutable text-only task record used by storage, service, routes, tools, and Cards presentation.",
  "runtime/resono_runtime/domains/tasks/repository.py": "Owns SQLite persistence and ordered queries for the deliberately text-only Tasks domain, including creation, completion, reopening, deletion, and active-task listing.",
  "runtime/resono_runtime/domains/tasks/service.py": "Provides the task application service and registers the uniform agent-facing task tool package over the repository.",
  ".understand-anything/config.json": "Stores the Understand Anything output-language preference for generated knowledge graph text.",
  ".understand-anything/diff-overlay.json": "Records the current incremental-analysis overlay, including base branch, changed files and nodes, affected nodes, generation time, and schema version.",
  ".understand-anything/fingerprints.json": "Stores per-file content fingerprints with the analyzed commit and generation metadata for deterministic incremental graph updates.",
  ".understand-anything/knowledge-graph.json": "Contains the assembled ReSono Labs R1 Voice knowledge graph, including project metadata, file and semantic nodes, typed edges, architectural layers, and guided tour data.",
  ".understand-anything/meta.json": "Records the analyzed commit, timestamp, file count, and graph metadata version used to determine analysis freshness.",
  "README.md": "Introduces JackRabbit as the standalone ReSono R1 Voice product and documents scope, architecture, security boundaries, setup, build flow, current acceptance state, and non-commercial licensing.",
  "SKILLS.md": "Provides operational build, deployment, focused-test, recovery, and physical-device verification commands across accepted and active delivery contracts.",
  "skills.md": "Redirects readers to the canonical uppercase SKILLS.md deployment, build, and ADB verification guide.",
  "android/scripts/build_android_agent_wheels.sh": "Cross-compiles pinned arm64 Android wheels for the native Python dependencies required by openai-agents, verifies source hashes, normalizes extension suffixes, and packages outputs.",
  "android/scripts/build_debug.sh": "Stages canonical web assets, enforces a pinned Java and Android toolchain, builds and unit-tests the debug APK, then runs boundary and embedded-runtime package checks.",
  "android/scripts/check_boundaries.sh": "Statically enforces standalone product boundaries, foreground-runtime and TLS invariants, local-only cleartext, LAN-only management advertising, phase exclusions, and clean module naming.",
  "android/scripts/check_runtime_package.sh": "Inspects the built APK for required arm64 Python libraries, management assets, Build 7 standards, importable Python source, expected native extensions, and forbidden ABI artifacts.",
  "android/scripts/sign_motor_service_for_r1.sh": "Platform-signs the R1 motor service APK with supplied keys and deletes the output unless its signer certificate matches the pinned production digest."
};

const tagMap = [
  [/calendar\/caldav/, ["calendar", "caldav", "provider-client", "synchronization"]],
  [/calendar\/ics/, ["calendar", "ics", "provider-client", "serialization"]],
  [/domains\/calendar\/models/, ["calendar", "data-model", "type-definition"]],
  [/domains\/calendar\/repository/, ["calendar", "repository", "database", "synchronization"]],
  [/domains\/calendar\/scheduler/, ["calendar", "scheduler", "background-worker"]],
  [/domains\/calendar\/service/, ["calendar", "service", "credentials", "synchronization"]],
  [/creations\/archives/, ["creations", "validation", "archive", "security"]],
  [/creations\/descriptors/, ["creations", "validation", "provider-client"]],
  [/creations\/lifecycle/, ["creations", "service", "lifecycle", "recovery"]],
  [/security\/outbound/, ["security", "validation", "ssrf-protection", "networking"]],
  [/domains\/mail\/connector/, ["mail", "provider-client", "imap", "smtp"]],
  [/domains\/mail\/models/, ["mail", "data-model", "type-definition"]],
  [/domains\/mail\/repository/, ["mail", "repository", "database", "synchronization"]],
  [/domains\/mail\/scheduler/, ["mail", "scheduler", "background-worker"]],
  [/domains\/mail\/service/, ["mail", "service", "credentials", "synchronization"]],
  [/domains\/mail\/tools/, ["mail", "agent-tools", "tool-catalog", "service"]],
  [/domains\/tasks\/models/, ["tasks", "data-model", "type-definition"]],
  [/domains\/tasks\/repository/, ["tasks", "repository", "database"]],
  [/domains\/tasks\/service/, ["tasks", "service", "agent-tools"]],
  [/android\/app.*MainActivity/, ["android", "entry-point", "component", "lifecycle"]],
  [/BootReceiver/, ["android", "event-handler", "boot", "runtime"]],
  [/DisplayPolicy/, ["android", "display", "power-policy", "hardware"]],
  [/ManagementPairingState/, ["android", "data-model", "pairing"]],
  [/RuntimeHealthClient/, ["android", "provider-client", "health-check", "runtime"]],
  [/RuntimeManagementClient/, ["android", "provider-client", "management", "networking"]],
  [/RuntimeService/, ["android", "service", "foreground-service", "runtime"]],
  [/\.understand-anything\//, ["configuration", "knowledge-graph", "analysis-metadata"]],
  [/README\.md$/, ["documentation", "entry-point", "architecture", "setup"]],
  [/SKILLS\.md$/, ["documentation", "build-system", "deployment", "device-testing"]],
  [/skills\.md$/, ["documentation", "redirect", "build-system"]],
  [/build_android_agent_wheels/, ["build-system", "android", "cross-compilation", "python"]],
  [/build_debug/, ["build-system", "android", "validation", "packaging"]],
  [/check_boundaries/, ["validation", "architecture", "security", "build-system"]],
  [/check_runtime_package/, ["validation", "packaging", "android", "python"]],
  [/sign_motor_service/, ["android", "signing", "security", "deployment"]],
  [/__init__\.py$/, ["entry-point", "barrel", "type-definition"]]
];

function tagsFor(file) {
  for (const [pattern, tags] of tagMap) if (pattern.test(file)) return tags;
  return ["source-code", "service", "runtime"];
}

function complexity(lines) {
  return lines > 200 ? "complex" : lines >= 50 ? "moderate" : "simple";
}

function nodeType(category, file) {
  if (category === "config") return "config";
  if (category === "docs") return "document";
  return "file";
}

function words(name) {
  return name.replace(/^_+/, "").replace(/([a-z0-9])([A-Z])/g, "$1 $2").replaceAll("_", " ").toLowerCase();
}

function itemSummary(kind, name, file) {
  const phrase = words(name);
  const domain = file.includes("calendar") ? "calendar" : file.includes("mail") ? "mail" : file.includes("tasks") ? "task" : file.includes("creation") ? "creation" : file.includes("android") ? "Android" : "runtime";
  return kind === "class"
    ? `Defines the ${phrase} abstraction used by the ${domain} implementation.`
    : `Implements ${phrase} behavior for the ${domain} implementation.`;
}

for (let index = 8; index <= 14; index++) {
  const batch = batchesDoc.batches.find(entry => entry.batchIndex === index);
  if (!batch) throw new Error(`Missing batch ${index}`);
  const files = batch.batchFiles ?? batch.files;
  const extracted = JSON.parse(fs.readFileSync(path.join(root, `.understand-anything/tmp/ua-file-extract-results-${index}.json`), "utf8"));
  if (!extracted.scriptCompleted || extracted.filesSkipped.length) throw new Error(`Extraction incomplete for batch ${index}`);
  const byPath = new Map(extracted.results.map(result => [result.path, result]));
  const nodes = [];
  const edges = [];
  for (const spec of files) {
    const result = byPath.get(spec.path);
    if (!result) throw new Error(`Missing extraction result: ${spec.path}`);
    const type = nodeType(spec.fileCategory, spec.path);
    const fileId = `${type}:${spec.path}`;
    nodes.push({id:fileId,type,name:path.basename(spec.path),filePath:spec.path,summary:summaries[spec.path],tags:tagsFor(spec.path),complexity:complexity(result.nonEmptyLines ?? spec.sizeLines)});
    if (!summaries[spec.path]) throw new Error(`Missing summary: ${spec.path}`);
    const exported = new Set((result.exports ?? []).map(item => item.name));
    const items = [
      ...(result.functions ?? []).filter(item => exported.has(item.name) || item.endLine - item.startLine + 1 >= 10).map(item => ({...item,kind:"function"})),
      ...(result.classes ?? []).filter(item => exported.has(item.name) || item.endLine - item.startLine + 1 >= 20 || (item.methods?.length ?? 0) >= 2).map(item => ({...item,kind:"class"}))
    ];
    const nameCounts = new Map();
    for (const item of items) nameCounts.set(`${item.kind}:${item.name}`, (nameCounts.get(`${item.kind}:${item.name}`) ?? 0) + 1);
    for (const item of items) {
      const duplicate = nameCounts.get(`${item.kind}:${item.name}`) > 1;
      const signature = duplicate
        ? `__${(item.params ?? []).map(param => String(param).replace(/[^A-Za-z0-9]+/g, "_").replace(/^_|_$/g, "").toLowerCase()).join("_") || `line_${item.startLine}`}`
        : "";
      const id = `${item.kind}:${spec.path}:${item.name}${signature}`;
      const size = item.endLine - item.startLine + 1;
      nodes.push({id,type:item.kind,name:item.name,filePath:spec.path,lineRange:[item.startLine,item.endLine],summary:itemSummary(item.kind,item.name,spec.path),tags:[...tagsFor(spec.path).slice(0,2),item.kind === "class" ? "data-model" : "utility"],complexity:complexity(size)});
      edges.push({source:fileId,target:id,type:"contains",direction:"forward",weight:1.0});
      if (exported.has(item.name)) edges.push({source:fileId,target:id,type:"exports",direction:"forward",weight:0.8});
    }
    for (const target of batch.batchImportData[spec.path] ?? []) {
      edges.push({source:fileId,target:`file:${target}`,type:"imports",direction:"forward",weight:0.7});
    }
  }
  const fragment = {nodes,edges};
  const output = path.join(root, `.understand-anything/intermediate/batch-${index}.json`);
  if (nodes.length > 60 || edges.length > 120) throw new Error(`Batch ${index} requires splitting: ${nodes.length} nodes, ${edges.length} edges`);
  fs.writeFileSync(output, JSON.stringify(fragment, null, 2) + "\n");
}
