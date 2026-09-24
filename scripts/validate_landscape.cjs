const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const validator=require(process.env.GLTF_VALIDATOR_MODULE||'gltf-validator');
const edition=process.argv[2]||'landscape';assert(['landscape','architecture','waterside'].includes(edition));
(async()=>{
  const bytes=fs.readFileSync(path.join(root,`assets/${edition}/island_${edition}.glb`));
  const gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
  const meta=JSON.parse(fs.readFileSync(path.join(root,`assets/${edition}/scene.json`)));
  const names=new Set(gltf.nodes.map(n=>n.name));
  for(const name of [...meta.independentNodes,'island_scenery'])assert(names.has(name),`Missing node ${name}`);
  const triangles=gltf.meshes.flatMap(m=>m.primitives).reduce((n,p)=>n+gltf.accessors[p.indices].count/3,0);
  assert.equal(triangles,meta.webTriangles);assert(triangles<(edition==='waterside'?750000:edition==='architecture'?700000:650000));assert(bytes.length<(meta.architectureRevision?42000000:28000000));
  if(meta.architectureRevision){
    assert(gltf.materials.filter(m=>m.normalTexture).length>=15);
    for(const name of ['house_main_001','cafe_pavilion_001']){
      const node=gltf.nodes.find(n=>n.name===name);assert(node?.mesh!==undefined);
      const prims=gltf.meshes[node.mesh].primitives;assert(prims.some(p=>gltf.materials[p.material].normalTexture));
      for(const p of prims)if(gltf.materials[p.material].normalTexture){assert(p.attributes.TEXCOORD_0!==undefined);assert(p.attributes.TANGENT!==undefined);}
    }
    const old=JSON.parse(fs.readFileSync(path.join(root,'assets/landscape/scene.json')));
    for(const key of ['terrain','trees','blossomTree','lifeSites','plots','bridge','shelters'])assert.deepEqual(meta[key],old[key],`Unintended landscape change: ${key}`);
  }
  // Check exported alpha, not just node wiring: alpha-only Blender color
  // attributes can silently export as fully opaque.
  const waterfall=gltf.nodes.find(n=>n.name==='waterfall_ribbons'),binaryStart=28+bytes.readUInt32LE(12);
  for(const p of gltf.meshes[waterfall.mesh].primitives){
    const a=gltf.accessors[p.attributes.COLOR_0];assert(a&&a.type==='VEC4');assert([5121,5123,5126].includes(a.componentType));
    const size={5121:1,5123:2,5126:4}[a.componentType],v=gltf.bufferViews[a.bufferView],start=binaryStart+(v.byteOffset||0)+(a.byteOffset||0),stride=v.byteStride||4*size;
    let min=1,max=0;for(let i=0;i<a.count;i++){const offset=start+i*stride+3*size,alpha=size===1?bytes[offset]/255:size===2?bytes.readUInt16LE(offset)/65535:bytes.readFloatLE(offset);min=Math.min(min,alpha);max=Math.max(max,alpha);}
    assert(min<.03&&max>.97,'Waterfall must fade from opaque to transparent');assert.equal(gltf.materials[p.material].alphaMode,'BLEND');
  }
  const report=await validator.validateBytes(new Uint8Array(bytes),{maxIssues:100});
  fs.writeFileSync(path.join(root,`reports/${edition}_gltf_validation.json`),JSON.stringify(report,null,2));
  console.log(JSON.stringify({bytes:bytes.length,triangles,independentNodes:meta.independentNodes.length,errors:report.issues.numErrors,warnings:report.issues.numWarnings},null,2));
  assert.equal(report.issues.numErrors,0);assert.equal(report.issues.numWarnings,0);
})().catch(e=>{console.error(e);process.exitCode=1;});
