const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const validator=require(process.env.GLTF_VALIDATOR_MODULE||'gltf-validator');
const detailed=process.argv.includes('--tripo'),boneCount=detailed?37:27,reportPrefix=detailed?'tripo_character':'character';
(async()=>{
  const bytes=fs.readFileSync(path.join(root,detailed?'assets/character_tripo/runtime/daisy_tripo.glb':'assets/character/daisy_character.glb'));
  const gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
  const clips=gltf.animations.map(a=>a.name).sort();
  assert.deepEqual(clips,['Harvest','Idle','Plant','Walk','Water']);
  assert.equal(gltf.skins.length,1);assert.equal(gltf.skins[0].joints.length,boneCount);
  for(const anim of gltf.animations){
    const rotating=anim.channels.filter(c=>c.target.path==='rotation');
    assert(rotating.length>=boneCount,`${anim.name} must animate all bones`);
    assert(anim.samplers.some(s=>gltf.accessors[s.input].count>10),`${anim.name} has no sampled motion`);
  }
  const names=new Set(gltf.nodes.map(n=>n.name));
  for(const name of detailed?['Daisy_Detailed','Watering_Can']:['Face','Wavy_Hair','Woven_Straw_Hat','Sage_Embroidered_Dress','Watering_Can'])assert(names.has(name),`Missing ${name}`);
  let triangles=0;
  for(const m of gltf.meshes)for(const p of m.primitives){
    assert(p.attributes.JOINTS_0!==undefined&&p.attributes.WEIGHTS_0!==undefined,`${m.name} is not skinned`);
    triangles+=gltf.accessors[p.indices].count/3;
  }
  assert(triangles<180000);assert(bytes.length<(detailed?20000000:12000000));
  assert(gltf.images.length>=(detailed?3:8),'Material maps missing');
  const report=await validator.validateBytes(new Uint8Array(bytes),{maxIssues:1000});
  fs.writeFileSync(path.join(root,`reports/${reportPrefix}_gltf_validation.json`),JSON.stringify(report,null,2));
  const summary={bytes:bytes.length,triangles,bones:gltf.skins[0].joints.length,clips,errors:report.issues.numErrors,warnings:report.issues.numWarnings};
  fs.writeFileSync(path.join(root,`reports/${reportPrefix}_web.json`),JSON.stringify(summary,null,2));
  console.log(JSON.stringify(summary,null,2));
  if(summary.errors||summary.warnings){console.log(JSON.stringify(report.issues.messages.filter(m=>m.severity<2).slice(0,20),null,2));process.exitCode=1;}
})().catch(error=>{console.error(error);process.exitCode=1;});
