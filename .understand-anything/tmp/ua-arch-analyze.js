const fs = require('fs');
const path = require('path');

const [,, inputPath, outputPath] = process.argv;
try {
  const raw = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
  const fileNodes = raw.fileNodes || raw.nodes.filter(n => n.filePath && ['file','config','document','service','pipeline','table','schema','resource','endpoint'].includes(n.type));
  const ids = new Set(fileNodes.map(n => n.id));
  const allEdges = (raw.allEdges || raw.edges).filter(e => ids.has(e.source) && ids.has(e.target));
  const importEdges = (raw.importEdges || allEdges).filter(e => e.type === 'imports');
  const paths = fileNodes.map(n => n.filePath);
  const split = paths.map(p => p.split('/'));
  let common = split.length ? split[0].slice(0, -1) : [];
  for (const parts of split.slice(1)) {
    let i = 0;
    while (i < common.length && common[i] === parts[i]) i++;
    common = common.slice(0, i);
  }
  const groupOf = n => {
    const parts = n.filePath.split('/').slice(common.length);
    if (parts.length > 1) return parts[0];
    const b = parts[0] || n.filePath;
    if (/test_|_test\.|\.test\.|\.spec\./i.test(b)) return 'test';
    if (/config|\.ya?ml$|\.toml$|\.json$/i.test(b)) return 'config';
    return 'root';
  };
  const directoryGroups = {}, nodeTypeGroups = {}, nodeGroup = {};
  for (const n of fileNodes) {
    const g = groupOf(n); nodeGroup[n.id] = g;
    (directoryGroups[g] ||= []).push(n.id);
    (nodeTypeGroups[n.type] ||= []).push(n.id);
  }
  const fanIn = {}, fanOut = {}, pair = {}, involved = {};
  for (const n of fileNodes) { fanIn[n.id] = 0; fanOut[n.id] = 0; }
  for (const e of importEdges) {
    fanOut[e.source]++; fanIn[e.target]++;
    const a=nodeGroup[e.source], b=nodeGroup[e.target];
    pair[`${a}\u0000${b}`]=(pair[`${a}\u0000${b}`]||0)+1;
    (involved[a] ||= new Set()).add(e); (involved[b] ||= new Set()).add(e);
  }
  const interGroupImports = Object.entries(pair).filter(([k]) => { const [a,b]=k.split('\u0000'); return a!==b; }).map(([k,count])=>{const [from,to]=k.split('\u0000');return {from,to,count};}).sort((a,b)=>b.count-a.count);
  const intraGroupDensity = {};
  for (const g of Object.keys(directoryGroups)) {
    const internalEdges=pair[`${g}\u0000${g}`]||0, totalEdges=(involved[g]||new Set()).size;
    intraGroupDensity[g]={internalEdges,totalEdges,density:totalEdges?internalEdges/totalEdges:0};
  }
  const types = Object.fromEntries(fileNodes.map(n=>[n.id,n.type]));
  const cross = {};
  for (const e of allEdges) if (types[e.source]!==types[e.target]) { const k=`${types[e.source]}\u0000${types[e.target]}\u0000${e.type}`; cross[k]=(cross[k]||0)+1; }
  const crossCategoryEdges=Object.entries(cross).map(([k,count])=>{const [fromType,toType,edgeType]=k.split('\u0000');return {fromType,toType,edgeType,count};});
  const patterns={routes:'api',api:'api',controllers:'api',endpoints:'api',handlers:'api',services:'service',core:'service',lib:'service',domain:'service',logic:'service',models:'data',db:'data',data:'data',persistence:'data',repository:'data',entities:'data',components:'ui',views:'ui',pages:'ui',ui:'ui',layouts:'ui',screens:'ui',middleware:'middleware',plugins:'middleware',interceptors:'middleware',guards:'middleware',utils:'utility',helpers:'utility',common:'utility',shared:'utility',tools:'utility',config:'config',constants:'config',env:'config',settings:'config',tests:'test',test:'test',spec:'test',specs:'test',types:'types',interfaces:'types',schemas:'types',contracts:'types',dtos:'types',hooks:'hooks',store:'state',state:'state',reducers:'state',actions:'state',slices:'state',assets:'assets',static:'assets',public:'assets',migrations:'data',docs:'documentation',documentation:'documentation',wiki:'documentation',deploy:'infrastructure',deployment:'infrastructure',infra:'infrastructure',infrastructure:'infrastructure','.github':'ci-cd',k8s:'infrastructure',kubernetes:'infrastructure',helm:'infrastructure',charts:'infrastructure',terraform:'infrastructure',tf:'infrastructure',docker:'infrastructure',sql:'data',database:'data',schema:'data',cmd:'entry',bin:'entry',internal:'service',pkg:'utility'};
  const patternMatches={}; for (const g of Object.keys(directoryGroups)) patternMatches[g]=patterns[g.toLowerCase()]||null;
  const p = n => n.filePath.toLowerCase();
  const infraFiles=fileNodes.filter(n=>/(^|\/)(dockerfile|docker-compose|makefile)|\.tf(vars)?$|(^|\/)k8s\/|(^|\/)helm\/|(^|\/)image\/|(^|\/)scripts\//i.test(n.filePath)||['service','pipeline','resource'].includes(n.type)).map(n=>n.filePath);
  const deploymentTopology={hasDockerfile:fileNodes.some(n=>/(^|\/)dockerfile/i.test(n.filePath)),hasCompose:fileNodes.some(n=>/docker-compose/i.test(n.filePath)),hasK8s:fileNodes.some(n=>/(^|\/)(k8s|kubernetes|helm|charts)\//i.test(n.filePath)),hasTerraform:fileNodes.some(n=>/\.tf(vars)?$/i.test(n.filePath)),hasCI:fileNodes.some(n=>/(^|\/)\.github\/workflows\/|\.gitlab-ci|jenkinsfile/i.test(n.filePath)||n.type==='pipeline'),infraFiles};
  const dataPipeline={schemaFiles:fileNodes.filter(n=>['schema','table'].includes(n.type)||/\.(sql|graphql|gql|proto|prisma)$/i.test(n.filePath)).map(n=>n.filePath),migrationFiles:fileNodes.filter(n=>/(^|\/)migrations?\//i.test(n.filePath)).map(n=>n.filePath),dataModelFiles:fileNodes.filter(n=>/(^|\/)(models?|entities|storage)\//i.test(n.filePath)||/(model|repository|database|storage)/.test(p(n))).map(n=>n.filePath),apiHandlerFiles:fileNodes.filter(n=>/(^|\/)(api|routes|controllers|endpoints|handlers)\//i.test(n.filePath)||n.type==='endpoint').map(n=>n.filePath)};
  const docs=fileNodes.filter(n=>n.type==='document'||/\.(md|rst)$/i.test(n.filePath));
  const documented=new Set(); for(const d of docs){const parts=d.filePath.split('/'); if(parts.length>1&&parts[0]!=='docs') documented.add(parts[0]); for(const g of Object.keys(directoryGroups)) if((d.summary||'').toLowerCase().includes(g.toLowerCase())) documented.add(g);}
  const groups=Object.keys(directoryGroups), docCoverage={groupsWithDocs:groups.filter(g=>documented.has(g)).length,totalGroups:groups.length,coverageRatio:groups.length?groups.filter(g=>documented.has(g)).length/groups.length:0,undocumentedGroups:groups.filter(g=>!documented.has(g))};
  const dependencyDirection=[]; const seen=new Set(); for(const x of interGroupImports){const key=[x.from,x.to].sort().join('\u0000');if(seen.has(key))continue;seen.add(key);const reverse=pair[`${x.to}\u0000${x.from}`]||0;if(x.count>reverse)dependencyDirection.push({dependent:x.from,dependsOn:x.to});else if(reverse>x.count)dependencyDirection.push({dependent:x.to,dependsOn:x.from});}
  const results={scriptCompleted:true,directoryGroups,nodeTypeGroups,crossCategoryEdges,interGroupImports,intraGroupDensity,patternMatches,deploymentTopology,dataPipeline,docCoverage,dependencyDirection,fileStats:{totalFileNodes:fileNodes.length,filesPerGroup:Object.fromEntries(Object.entries(directoryGroups).map(([k,v])=>[k,v.length])),nodeTypeCounts:Object.fromEntries(Object.entries(nodeTypeGroups).map(([k,v])=>[k,v.length]))},fileFanIn:fanIn,fileFanOut:fanOut};
  fs.writeFileSync(outputPath, JSON.stringify(results,null,2)+'\n');
} catch (e) { console.error(e.stack||e); process.exit(1); }
