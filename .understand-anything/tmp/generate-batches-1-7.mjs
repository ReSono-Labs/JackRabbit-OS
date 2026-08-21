import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const manifest = JSON.parse(fs.readFileSync(path.join(root, ".understand-anything/intermediate/batches.json"), "utf8"));

const words = value => value
  .replace(/\.[^.]+$/, "")
  .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
  .replace(/^_+/, "")
  .replace(/[_-]+/g, " ")
  .trim()
  .toLowerCase();

function domainFor(filePath) {
  const p = filePath.toLowerCase();
  if (p.includes("/migrations/")) return "database migration";
  if (p.includes("background_agent")) return "background agent";
  if (p.includes("/providers/openai/")) return "OpenAI provider";
  if (p.includes("/memory/")) return "memory pipeline";
  if (p.includes("/mcp/")) return "MCP integration";
  if (p.includes("/plugins/")) return "plugin lifecycle";
  if (p.includes("/skills/")) return "skill lifecycle";
  if (p.includes("/storage/")) return "SQLite persistence";
  if (p.includes("/api/")) return "runtime HTTP API";
  if (p.includes("/tools/")) return "agent tool system";
  if (p.includes("android/feature/voice")) return "native Voice interface";
  if (p.includes("android/feature/settings")) return "native settings interface";
  if (p.includes("android/feature/cards")) return "native Cards interface";
  if (p.includes("android/feature/camera")) return "native camera integration";
  if (p.includes("android/feature/calendar")) return "native calendar interface";
  if (p.includes("android/feature/tasks")) return "native tasks interface";
  if (p.includes("android/runtime-host")) return "Android runtime host";
  if (p.includes("android/core/input")) return "R1 hardware input";
  if (p.includes("android/core/motor")) return "R1 motor control";
  if (p.includes("android/core/design")) return "native design system";
  if (p.includes("android/app")) return "Android HOME composition";
  if (p.includes("/connections/")) return "connection management";
  if (p.includes("/imports/")) return "safe import workflow";
  if (p.includes("/agents/")) return "agent execution";
  if (p.includes("/security/")) return "runtime security";
  return "runtime application";
}

function tagsFor(filePath, kind, name = "") {
  const p = `${filePath}/${name}`.toLowerCase();
  const tags = [];
  if (p.includes("test")) tags.push("test", "validation");
  if (p.includes("migration")) tags.push("database", "migration", "schema-definition");
  else if (p.includes("background_agent")) tags.push("background-agent", "agent-execution", "lifecycle");
  else if (p.includes("openai")) tags.push("openai", "provider-adapter", "integration");
  else if (p.includes("memory")) tags.push("memory", "retrieval", "data-pipeline");
  else if (p.includes("mcp")) tags.push("mcp", "tool-protocol", "integration");
  else if (p.includes("plugin")) tags.push("plugin", "lifecycle", "validation");
  else if (p.includes("skill")) tags.push("agent-skill", "lifecycle", "validation");
  else if (p.includes("storage")) tags.push("database", "repository", "persistence");
  else if (p.includes("/api/")) tags.push("api-handler", "http", "runtime");
  else if (p.includes("/tools/")) tags.push("agent-tools", "tool-catalog", "mcp");
  else if (p.startsWith("android/")) tags.push("android", "native-ui", "device-integration");
  else tags.push("runtime", "service", "application");
  if (kind === "class") tags.push("data-model");
  if (kind === "function") tags.push("utility");
  if (filePath.endsWith("/__init__.py")) tags.push("barrel", "entry-point");
  return [...new Set(tags)].slice(0, 5);
}

function fileSummary(f) {
  const base = path.basename(f.path);
  const domain = domainFor(f.path);
  const symbols = [...(f.classes || []).map(x => words(x.name)), ...(f.functions || []).map(x => words(x.name))].slice(0, 3);
  if (f.path.includes("/migrations/") && base !== "__init__.py") {
    const subject = words(base.replace(/^v\d+_/, ""));
    return `Applies the versioned SQLite migration for ${subject}, evolving the on-device runtime schema in a deterministic order.`;
  }
  if (base === "__init__.py") return `Defines the public package surface for the ${domain}, collecting the module's supported imports in one place.`;
  if (symbols.length) return `Implements ${domain} responsibilities centered on ${symbols.join(", ")}. It provides the concrete behavior represented by this module within the standalone R1 runtime.`;
  return `Defines supporting ${domain} behavior and contracts for the standalone R1 product runtime.`;
}

function symbolSummary(filePath, kind, item) {
  const label = words(item.name);
  const domain = domainFor(filePath);
  if (kind === "class") {
    const methods = (item.methods || []).filter(x => !x.startsWith("__")).slice(0, 4).map(words);
    return methods.length
      ? `Owns ${label} behavior for the ${domain}, including ${methods.join(", ")}.`
      : `Represents the ${label} contract or immutable state used by the ${domain}.`;
  }
  if (item.name === "apply" && filePath.includes("/migrations/")) return `Applies this schema revision to the active SQLite connection.`;
  return `Performs ${label} behavior used by the ${domain}.`;
}

function complexity(lines, structure = 0) {
  if (lines > 200 || structure > 15) return "complex";
  if (lines >= 50 || structure > 5) return "moderate";
  return "simple";
}

function build(batch) {
  const extracted = JSON.parse(fs.readFileSync(path.join(root, `.understand-anything/tmp/ua-file-extract-results-${batch.batchIndex}.json`), "utf8"));
  if (!extracted.scriptCompleted) throw new Error(`batch ${batch.batchIndex}: extractor incomplete`);
  const nodes = [];
  const edges = [];
  for (const f of extracted.results) {
    const fileId = `file:${f.path}`;
    const structuralCount = (f.functions || []).length + (f.classes || []).length;
    nodes.push({id:fileId,type:"file",name:path.basename(f.path),filePath:f.path,summary:fileSummary(f),tags:tagsFor(f.path,"file"),complexity:complexity(f.nonEmptyLines,structuralCount)});
    const exported = new Set((f.exports || []).map(x => x.name));
    for (const [kind, items] of [["function", f.functions || []], ["class", f.classes || []]]) {
      for (const item of items) {
        const lineCount = item.endLine - item.startLine + 1;
        const significant = exported.has(item.name) || (kind === "function" ? lineCount >= 10 : lineCount >= 20 || (item.methods || []).length >= 2);
        if (!significant) continue;
        const id = `${kind}:${f.path}:${item.name}`;
        nodes.push({id,type:kind,name:item.name,filePath:f.path,lineRange:[item.startLine,item.endLine],summary:symbolSummary(f.path,kind,item),tags:tagsFor(f.path,kind,item.name),complexity:complexity(lineCount,(item.methods || []).length)});
        edges.push({source:fileId,target:id,type:"contains",direction:"forward",weight:1.0});
        if (exported.has(item.name)) edges.push({source:fileId,target:id,type:"exports",direction:"forward",weight:0.8});
      }
    }
    for (const target of batch.batchImportData[f.path] || []) {
      if (target === f.path) continue;
      edges.push({source:fileId,target:`file:${target}`,type:"imports",direction:"forward",weight:0.7});
    }
  }
  return {nodes, edges, skipped: extracted.filesSkipped || []};
}

function writeParts(batch, graph) {
  const sortedFiles = [...batch.files].map(x => x.path).sort();
  let parts = Math.ceil(Math.max(graph.nodes.length / 60, graph.edges.length / 120));
  while (parts < sortedFiles.length) {
    const chunkSize = Math.ceil(sortedFiles.length / parts);
    let fits = true;
    for (let k = 0; k < parts; k++) {
      const fileSet = new Set(sortedFiles.slice(k * chunkSize, (k + 1) * chunkSize));
      const nodeIds = new Set(graph.nodes.filter(n => fileSet.has(n.filePath)).map(n => n.id));
      const edgeCount = graph.edges.filter(e => nodeIds.has(e.source)).length;
      if (nodeIds.size > 60 || edgeCount > 120) fits = false;
    }
    if (fits) break;
    parts++;
  }
  const chunkSize = Math.ceil(sortedFiles.length / parts);
  const written = [];
  for (let k = 0; k < parts; k++) {
    const fileSet = new Set(sortedFiles.slice(k * chunkSize, (k + 1) * chunkSize));
    const nodes = graph.nodes.filter(n => fileSet.has(n.filePath));
    const nodeIds = new Set(nodes.map(n => n.id));
    const edges = graph.edges.filter(e => nodeIds.has(e.source));
    const payload = {nodes, edges};
    const suffix = parts === 1 ? "" : `-part-${k + 1}`;
    const output = path.join(root, `.understand-anything/intermediate/batch-${batch.batchIndex}${suffix}.json`);
    fs.writeFileSync(output, JSON.stringify(payload, null, 2) + "\n");
    written.push({output:path.relative(root, output),nodes:nodes.length,edges:edges.length});
  }
  return written;
}

const report = [];
for (const batch of manifest.batches.filter(x => x.batchIndex >= 1 && x.batchIndex <= 7)) {
  const graph = build(batch);
  const expectedImports = Object.entries(batch.batchImportData).reduce((n, [source, targets]) => n + targets.filter(target => target !== source).length, 0);
  const actualImports = graph.edges.filter(x => x.type === "imports").length;
  if (expectedImports !== actualImports) throw new Error(`batch ${batch.batchIndex}: imports ${actualImports}/${expectedImports}`);
  const written = writeParts(batch, graph);
  report.push({batchIndex:batch.batchIndex,totalNodes:graph.nodes.length,totalEdges:graph.edges.length,skipped:graph.skipped,written});
}
console.log(JSON.stringify(report, null, 2));
