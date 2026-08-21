import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const source = JSON.parse(fs.readFileSync(".understand-anything/intermediate/batches.json", "utf8"));

const words = value => value
  .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
  .replace(/[_./-]+/g, " ")
  .replace(/\btest\b/gi, "")
  .trim()
  .toLowerCase();

function topic(file) {
  const base = path.basename(file.path).replace(/\.(java|py|json|xml|kts|md|css|js|html|pro|aidl|properties)$/i, "");
  return words(base) || "project configuration";
}

function complexity(result) {
  const n = result.nonEmptyLines ?? result.totalLines ?? 0;
  if (n > 200 || (result.classes?.length ?? 0) > 8) return "complex";
  if (n >= 50) return "moderate";
  return "simple";
}

function fileType(file) {
  if (file.fileCategory === "config") return ["config", `config:${file.path}`];
  if (file.fileCategory === "docs") return ["document", `document:${file.path}`];
  return ["file", `file:${file.path}`];
}

function fileSummary(file, result) {
  const p = file.path;
  const t = topic(file);
  if (p.endsWith(".whl")) return `Prebuilt Android arm64 Python wheel for ${t}, embedded into the on-device runtime host.`;
  if (p.includes("docs/planning/")) {
    const title = result.sections?.[0]?.heading ?? path.basename(p);
    return `${title} records the scoped outcome, decision gates, dependency order, evidence, and rollback conditions for its delivery concern.`;
  }
  if (p.includes("docs/research/")) return `Research record for ${t}, documenting observed hardware behavior, recovery constraints, and evidence relevant to implementation decisions.`;
  if (p.endsWith("README.md")) return `Concise entry-point documentation for the ${p.split("/")[0]} portion of the project and its ownership boundaries.`;
  if (p.endsWith("build.gradle.kts")) return `Gradle module configuration for ${t}, declaring its Android build settings and module dependencies.`;
  if (p.endsWith("settings.gradle.kts")) return "Gradle settings for the Android project, registering the clean application, core, feature, runtime-host, and system modules.";
  if (p.endsWith("gradle.properties")) return "Project-wide Gradle properties controlling Android build behavior and JVM settings.";
  if (p.endsWith("AndroidManifest.xml")) return `Android manifest declaring the components, permissions, and process metadata for ${t}.`;
  if (p.endsWith("styles.xml")) return "Android resource styles defining the application theme and window presentation.";
  if (p.endsWith("network_security_config.xml")) return "Android network-security policy defining trusted traffic behavior for the application.";
  if (p.endsWith(".schema.json")) return `JSON Schema defining and validating the standard ${t} document contract.`;
  if (p.endsWith("plugin.json")) return "Manifest for the bundled ReSono Mail plugin, declaring its identity, version, and standard components.";
  if (p.endsWith("SKILL.md")) return "Agent Skill instructions that constrain Voice Mail behavior, tool use, and user-facing interaction.";
  if (p.endsWith(".css")) return `Stylesheet implementing ${t} visual tokens, layout, responsive behavior, and component presentation for the management interface.`;
  if (p.endsWith("index.html")) return "Management-site document shell that loads the shared design styles and real management application controls.";
  if (p.endsWith(".js")) return `Browser-side controller for ${t}, loading real runtime data and updating the management interface through authenticated APIs.`;
  if (p.includes("/test") || path.basename(p).startsWith("test_")) return `Automated tests for ${t}, covering its positive behavior, rejection paths, and persistence or lifecycle invariants.`;
  if (p.endsWith("__init__.py")) return `Python package marker establishing the ${p.split("/").slice(-2,-1)[0]} runtime namespace.`;
  if (p.endsWith(".aidl")) return `Android Binder interface contract for ${t}, defining the motor-service calls shared across process boundaries.`;
  if (p.endsWith(".understandignore")) return "Understand-Anything ignore rules excluding generated, binary, donor-reference, and evidence paths from source analysis.";
  if (p.endsWith("scan-result.json")) return "Generated repository scan inventory containing detected files, languages, frameworks, sizes, and complexity estimates used to plan graph batches.";
  if (p.endsWith("proguard-rules.pro")) return "Application shrinker configuration; currently retains the default empty/minimal rule set.";
  return `${path.basename(p)} implements ${t} behavior within the ${p.startsWith("android/") ? "Android product" : "on-device runtime"}.`;
}

function fileTags(file) {
  const p = file.path;
  if (p.endsWith(".whl")) return ["runtime-dependency", "android", "python-package"];
  if (file.fileCategory === "docs") return ["documentation", "planning", p.includes("research") ? "hardware-research" : "delivery-contract"];
  if (file.fileCategory === "config") return ["configuration", p.includes("schema") ? "schema-definition" : "runtime-config", p.includes("AndroidManifest") ? "android-manifest" : "validation"];
  if (p.includes("/test") || path.basename(p).startsWith("test_")) return ["test", "validation", "regression"];
  if (p.endsWith(".css") || p.endsWith(".html")) return ["component", "browser-voice", "management-ui"];
  if (p.endsWith(".js")) return ["component", "api-handler", "management-ui"];
  if (p.endsWith("build.gradle.kts") || p.endsWith("settings.gradle.kts")) return ["configuration", "android", "build-system"];
  if (p.endsWith(".aidl")) return ["type-definition", "android-binder", "motor-control"];
  if (p.endsWith("__init__.py")) return ["entry-point", "python-package", "runtime"];
  return ["service", p.startsWith("android/") ? "android" : "runtime", "product-code"];
}

function memberSummary(kind, name, file) {
  const t = words(name);
  if (kind === "class") {
    if (name.endsWith("Test") || file.includes("/test") || path.basename(file).startsWith("test_")) return `Test fixture grouping assertions for ${t}, including success and failure-path behavior.`;
    return `${name} owns ${t} behavior and keeps its related state and operations within one focused component.`;
  }
  if (name.startsWith("test")) return `Verifies ${t}, asserting the expected contract and relevant failure behavior.`;
  if (name.startsWith("_")) return `Test support routine that constructs or supplies ${t} data for deterministic assertions.`;
  return `Implements ${t} as part of ${path.basename(file)}.`;
}

function memberTags(kind, name, file) {
  if (name.includes("Test") || name.startsWith("test") || file.includes("/test") || path.basename(file).startsWith("test_")) return ["test", "validation", kind === "class" ? "test-fixture" : "test-case"];
  if (kind === "class") return ["service", "encapsulation", "product-code"];
  return ["function", "runtime-logic", "product-code"];
}

function emittedMembers(result) {
  const exported = new Set((result.exports ?? []).map(x => x.name));
  const classes = (result.classes ?? []).filter(x => exported.has(x.name) || (x.methods?.length ?? 0) >= 2 || x.endLine - x.startLine + 1 >= 20);
  const functions = (result.functions ?? []).filter(x => exported.has(x.name) || x.endLine - x.startLine + 1 >= 10);
  return {classes, functions, exported};
}

for (const batch of source.batches.filter(b => b.batchIndex >= 15 && b.batchIndex <= 21)) {
  const extraction = JSON.parse(fs.readFileSync(`.understand-anything/tmp/ua-file-extract-results-${batch.batchIndex}.json`, "utf8"));
  const byPath = new Map(extraction.results.map(x => [x.path, x]));
  const nodes = [];
  const edges = [];
  for (const file of batch.files) {
    const result = byPath.get(file.path);
    const [type, id] = fileType(file);
    nodes.push({id, type, name:path.basename(file.path), filePath:file.path, summary:fileSummary(file,result), tags:fileTags(file), complexity:complexity(result)});
    if (file.fileCategory !== "code") continue;
    const members = emittedMembers(result);
    for (const [kind, list] of [["class", members.classes], ["function", members.functions]]) {
      for (const item of list) {
        const memberId = `${kind}:${file.path}:${item.name}`;
        nodes.push({id:memberId,type:kind,name:item.name,filePath:file.path,lineRange:[item.startLine,item.endLine],summary:memberSummary(kind,item.name,file.path),tags:memberTags(kind,item.name,file.path),complexity:item.endLine-item.startLine+1 > 200 ? "complex" : item.endLine-item.startLine+1 >= 50 ? "moderate" : "simple"});
        edges.push({source:id,target:memberId,type:"contains",direction:"forward",weight:1.0});
        if (members.exported.has(item.name)) edges.push({source:id,target:memberId,type:"exports",direction:"forward",weight:0.8});
      }
    }
    for (const target of batch.batchImportData[file.path] ?? []) edges.push({source:id,target:`file:${target}`,type:"imports",direction:"forward",weight:0.7});
  }
  const partCount = Math.ceil(Math.max(nodes.length / 60, edges.length / 120, 1));
  const sortedFiles = [...batch.files].sort((a,b) => a.path.localeCompare(b.path));
  const chunkSize = Math.ceil(sortedFiles.length / partCount);
  for (let k=0;k<partCount;k++) {
    const paths = new Set(sortedFiles.slice(k*chunkSize,(k+1)*chunkSize).map(x=>x.path));
    const partNodes = nodes.filter(x => paths.has(x.filePath));
    const ids = new Set(partNodes.map(x=>x.id));
    const partEdges = edges.filter(x => ids.has(x.source));
    const suffix = partCount === 1 ? "" : `-part-${k+1}`;
    fs.writeFileSync(`.understand-anything/intermediate/batch-${batch.batchIndex}${suffix}.json`, JSON.stringify({nodes:partNodes,edges:partEdges},null,2)+"\n");
  }
  console.log(`${batch.batchIndex}: ${nodes.length} nodes, ${edges.length} edges, ${partCount} part(s)`);
}
