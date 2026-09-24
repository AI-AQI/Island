const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const validator=require(process.env.GLTF_VALIDATOR_MODULE||'gltf-validator');
(async()=>{
  const bytes=fs.readFileSync(path.join(root,'assets/layout/island_layout.glb'));
  const gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
  const meta=JSON.parse(fs.readFileSync(path.join(root,'assets/layout/scene.json')));
  const names=new Set(gltf.nodes.map(n=>n.name));
  for(const name of [...meta.independentNodes,'island_scenery'])assert(names.has(name),`Missing node ${name}`);
  const triangles=gltf.meshes.flatMap(m=>m.primitives).reduce((n,p)=>n+gltf.accessors[p.indices].count/3,0);
  assert.equal(triangles,meta.webTriangles);assert(triangles<550000);assert(bytes.length<25000000);
  const report=await validator.validateBytes(new Uint8Array(bytes),{maxIssues:100});
  fs.writeFileSync(path.join(root,'reports/layout_gltf_validation.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify({bytes:bytes.length,triangles,independentNodes:meta.independentNodes.length,errors:report.issues.numErrors,warnings:report.issues.numWarnings},null,2));
  assert.equal(report.issues.numErrors,0);assert.equal(report.issues.numWarnings,0);
})().catch(e=>{console.error(e);process.exitCode=1;});
