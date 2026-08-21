const fs=require('fs');
const [,,source,out]=process.argv;
const g=JSON.parse(fs.readFileSync(source,'utf8'));
const allowed=new Set(['file','config','document','service','pipeline','table','schema','resource','endpoint']);
const fileNodes=g.nodes.filter(n=>n.filePath&&allowed.has(n.type));
const ids=new Set(fileNodes.map(n=>n.id));
const allEdges=g.edges.filter(e=>ids.has(e.source)&&ids.has(e.target));
fs.writeFileSync(out,JSON.stringify({fileNodes,importEdges:allEdges.filter(e=>e.type==='imports'),allEdges},null,2)+'\n');
