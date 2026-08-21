const fs = require('fs');

const [inputPath, outputPath] = process.argv.slice(2);
if (!inputPath || !outputPath) process.exit(1);

try {
  const graph = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
  const nodes = graph.nodes || [];
  const edges = graph.edges || [];
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const fanIn = new Map(nodes.map((node) => [node.id, 0]));
  const fanOut = new Map(nodes.map((node) => [node.id, 0]));
  for (const edge of edges) {
    if (fanOut.has(edge.source)) fanOut.set(edge.source, fanOut.get(edge.source) + 1);
    if (fanIn.has(edge.target)) fanIn.set(edge.target, fanIn.get(edge.target) + 1);
  }
  const rank = (counts, field) => [...counts].map(([id, value]) => ({id, [field]: value, name: byId.get(id)?.name || id})).sort((a,b) => b[field]-a[field] || a.id.localeCompare(b.id)).slice(0,20);
  const outValues = [...fanOut.values()].sort((a,b)=>a-b);
  const inValues = [...fanIn.values()].sort((a,b)=>a-b);
  const out90 = outValues[Math.floor(outValues.length * .9)] || 0;
  const in25 = inValues[Math.floor(inValues.length * .25)] || 0;
  const entryNames = new Set(['index.ts','index.js','main.ts','main.js','app.ts','app.js','server.ts','server.js','mod.rs','main.go','main.py','main.rs','manage.py','app.py','wsgi.py','asgi.py','run.py','__main__.py','Application.java','Main.java','Program.cs','config.ru','index.php','App.swift','Application.kt','main.cpp','main.c']);
  const candidates = [];
  for (const node of nodes) {
    let score = 0;
    const path = node.filePath || '';
    const depth = path.split('/').length;
    if (node.type === 'file') {
      if (entryNames.has(node.name)) score += 3;
      if (depth <= 2) score += 1;
      if ((fanOut.get(node.id)||0) >= out90) score += 1;
      if ((fanIn.get(node.id)||0) <= in25) score += 1;
    } else if (node.type === 'document') {
      if (path === 'README.md') score += 5;
      else if (depth === 1 && path.endsWith('.md')) score += 2;
    }
    if (score) candidates.push({id:node.id, score, name:node.name, summary:node.summary||''});
  }
  candidates.sort((a,b)=>b.score-a.score || a.id.localeCompare(b.id));
  const start = candidates.find((item)=>byId.get(item.id)?.type === 'file')?.id || null;
  const allowed = new Set(['imports','calls']);
  const adjacency = new Map();
  for (const edge of edges) if (allowed.has(edge.type)) {
    if (!adjacency.has(edge.source)) adjacency.set(edge.source, []);
    adjacency.get(edge.source).push(edge.target);
  }
  const order = [], depthMap = {}, byDepth = {};
  if (start) {
    const queue = [start]; depthMap[start] = 0;
    while (queue.length) {
      const id = queue.shift(); order.push(id);
      const depth = depthMap[id]; (byDepth[depth] ||= []).push(id);
      for (const target of adjacency.get(id)||[]) if (byId.has(target) && depthMap[target] === undefined) { depthMap[target]=depth+1; queue.push(target); }
    }
  }
  const item = (node) => ({id:node.id,name:node.name,type:node.type,summary:node.summary||''});
  const nonCodeFiles = {
    documentation:nodes.filter(n=>n.type==='document').map(item),
    infrastructure:nodes.filter(n=>['service','pipeline','resource'].includes(n.type)).map(item),
    data:nodes.filter(n=>['table','schema','endpoint'].includes(n.type)).map(item),
    config:nodes.filter(n=>n.type==='config').map(item)
  };
  const reciprocal = new Map();
  for (const edge of edges) if (allowed.has(edge.type)) reciprocal.set(`${edge.source}\u0000${edge.target}`, true);
  const clusters = [];
  const seenPairs = new Set();
  for (const edge of edges) if (allowed.has(edge.type) && reciprocal.has(`${edge.target}\u0000${edge.source}`)) {
    const pair = [edge.source,edge.target].sort(); const key=pair.join('\u0000');
    if (!seenPairs.has(key)) { seenPairs.add(key); clusters.push({nodes:pair,edgeCount:edges.filter(e=>pair.includes(e.source)&&pair.includes(e.target)).length}); }
  }
  clusters.sort((a,b)=>b.edgeCount-a.edgeCount);
  const nodeSummaryIndex = Object.fromEntries(nodes.map(n=>[n.id,{name:n.name,type:n.type,summary:n.summary||''}]));
  const result = {scriptCompleted:true,entryPointCandidates:candidates.slice(0,5),fanInRanking:rank(fanIn,'fanIn'),fanOutRanking:rank(fanOut,'fanOut'),bfsTraversal:{startNode:start,order,depthMap,byDepth},nonCodeFiles,clusters:clusters.slice(0,10),layers:{count:(graph.layers||[]).length,list:(graph.layers||[]).map(({id,name,description})=>({id,name,description}))},nodeSummaryIndex,totalNodes:nodes.length,totalEdges:edges.length};
  fs.writeFileSync(outputPath, JSON.stringify(result,null,2));
} catch (error) {
  process.stderr.write(String(error.stack || error));
  process.exit(1);
}
