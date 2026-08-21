const fs = require('fs');
const [,, inputPath, outputPath] = process.argv;
const {fileNodes} = JSON.parse(fs.readFileSync(inputPath, 'utf8'));

const specs = [
  ['layer:runtime-application', 'Runtime Application and API', 'Composes the on-device Python runtime and exposes its HTTP, event, agent, provider, MCP, and tool execution boundaries.'],
  ['layer:runtime-domain', 'Runtime Domains and Extensions', 'Implements ReSono domain behavior, external connectors, memory, creations, imports, skills, plugins, and standards-based extension lifecycles.'],
  ['layer:data-security', 'Data and Security Foundation', 'Owns SQLite migrations and repositories, runtime configuration, credential protection, pairing, outbound policy, logging, and supervised execution foundations.'],
  ['layer:android-experience', 'Android Product Experience', 'Implements the native HOME composition, Browser Voice-derived design system, hardware input routing, and working Voice, Cards, Calendar, Tasks, Settings, and Camera surfaces.'],
  ['layer:android-platform', 'Android Platform Integration', 'Bridges the native product to the local runtime, HTTPS management service, Android lifecycle, display power, motor hardware, and system-service contracts.'],
  ['layer:web-management', 'Web Management Experience', 'Implements the browser management application, shared design tokens, responsive styling, assets, and client-side runtime interactions.'],
  ['layer:contracts-config', 'Contracts and Configuration', 'Defines build manifests, package metadata, Android resources, plugin manifests, and machine-readable schemas that configure implementation boundaries.'],
  ['layer:release-infrastructure', 'Build and Release Infrastructure', 'Contains Android and system-image build scripts, image overlays, inventories, candidate assembly inputs, and release verification tooling.'],
  ['layer:test', 'Verification', 'Exercises runtime contracts, Android behavior, architecture boundaries, packaging, and integration behavior across the product implementation.'],
  ['layer:documentation', 'Documentation and Architecture Metadata', 'Records contributor-facing implementation guidance and generated architecture metadata without treating planning records as implementation authority.']
];
const buckets = Object.fromEntries(specs.map(([id]) => [id, []]));

function layer(n) {
  const p=n.filePath, low=p.toLowerCase();
  if (n.type === 'document' || low.startsWith('docs/') || low.startsWith('.understand-anything/')) return 'layer:documentation';
  if (low.startsWith('tests/') || /\/src\/test\//.test(low) || /(^|\/)(test_[^/]+|[^/]+test)\.[^.]+$/.test(low)) return 'layer:test';
  if (low.startsWith('web/')) return 'layer:web-management';
  if (low.startsWith('image/') || /(^|\/)scripts\//.test(low)) return 'layer:release-infrastructure';
  if (low.startsWith('android/')) {
    if (n.type === 'config' || /(^|\/)(build\.gradle\.kts|settings\.gradle\.kts|gradle\.properties|proguard-rules\.pro)$/.test(low)) return 'layer:contracts-config';
    if (low.startsWith('android/runtime-host/') || low.startsWith('android/core/motor/') || low.startsWith('android/core/power/') || low.startsWith('android/system/') || /mainactivity|bootreceiver|systemsetupstate/.test(low)) return 'layer:android-platform';
    return 'layer:android-experience';
  }
  if (low.startsWith('runtime/')) {
    if (n.type === 'config' || /plugin\.json$|schema\.json$/.test(low)) return 'layer:contracts-config';
    if (/runtime\/resono_runtime\/(storage|security|core)\//.test(low) || /runtime\/resono_runtime\/(config|application)\.py$/.test(low)) return 'layer:data-security';
    if (/runtime\/resono_runtime\/(domains|connectors|connections|creations|handoff|imports|memory|plugins|skills|standards)\//.test(low)) return 'layer:runtime-domain';
    return 'layer:runtime-application';
  }
  if (n.type === 'config' || /(^|\/)(pyproject\.toml|package\.json|.*\.gradle\.kts|.*\.ya?ml|.*\.json)$/.test(low)) return 'layer:contracts-config';
  if (/readme|contributing|changelog|license/.test(low)) return 'layer:documentation';
  return 'layer:release-infrastructure';
}

for (const n of fileNodes) buckets[layer(n)].push(n.id);
const layers=specs.map(([id,name,description])=>({id,name,description,nodeIds:buckets[id]})).filter(x=>x.nodeIds.length);
const assigned=layers.flatMap(x=>x.nodeIds);
if (layers.length < 3 || layers.length > 10) throw new Error(`Invalid layer count: ${layers.length}`);
if (assigned.length !== fileNodes.length || new Set(assigned).size !== fileNodes.length) throw new Error(`Assignment mismatch: ${assigned.length}/${fileNodes.length}, unique ${new Set(assigned).size}`);
fs.writeFileSync(outputPath, JSON.stringify(layers,null,2)+'\n');
console.log(JSON.stringify({total:fileNodes.length,layers:layers.map(x=>({name:x.name,count:x.nodeIds.length}))},null,2));
