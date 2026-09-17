// Portable normal quantization; geometry positions and triangle indices are unchanged.
// KHR_mesh_quantization: https://github.com/KhronosGroup/glTF/tree/main/extensions/2.0/Khronos/KHR_mesh_quantization
const fs=require('fs');
const path=require('path');

function optimize(filename){
  const input=fs.readFileSync(filename);
  if(input.readUInt32LE(0)!==0x46546c67)throw new Error('Expected a GLB file');
  const jsonLength=input.readUInt32LE(12);
  const gltf=JSON.parse(input.toString('utf8',20,20+jsonLength));
  if(gltf.animations?.length||gltf.skins?.length||gltf.buffers.length!==1)throw new Error('This packer only accepts the static single-buffer scene');
  const binary=input.subarray(28+jsonLength);
  const oldViews=gltf.bufferViews,oldAccessors=gltf.accessors;
  const used=new Set(),normals=new Set();
  // Blender's scalar bump node is not a tangent-space normal map.
  for(const mat of gltf.materials??[])delete mat.normalTexture;
  for(const mesh of gltf.meshes)for(const prim of mesh.primitives){
    const mat=gltf.materials[prim.material];
    const textured=mat?.pbrMetallicRoughness?.baseColorTexture||mat?.pbrMetallicRoughness?.metallicRoughnessTexture||mat?.emissiveTexture||mat?.occlusionTexture;
    if(!textured)for(const key of Object.keys(prim.attributes))if(key.startsWith('TEXCOORD_'))delete prim.attributes[key];
    for(const a of Object.values(prim.attributes))used.add(a);
    used.add(prim.indices);normals.add(prim.attributes.NORMAL);
  }
  const chunks=[],views=[],accessors=[],viewMap=new Map(),accessorMap=new Map();let offset=0;
  function append(data,metadata={}){
    const padded=Buffer.alloc(Math.ceil(data.length/4)*4);data.copy(padded);
    const idx=views.length;views.push({...metadata,buffer:0,byteOffset:offset,byteLength:data.length});chunks.push(padded);offset+=padded.length;return idx;
  }
  function copyView(index){
    if(viewMap.has(index))return viewMap.get(index);
    const v=oldViews[index];const {byteOffset=0,byteLength,buffer,...meta}=v;
    const result=append(binary.subarray(byteOffset,byteOffset+byteLength),meta);viewMap.set(index,result);return result;
  }
  for(const index of [...used].sort((a,b)=>a-b)){
    const a={...oldAccessors[index]};if(a.sparse)throw new Error('Sparse attributes need a separate packer');
    if(normals.has(index)&&a.componentType===5126){
      const v=oldViews[a.bufferView],stride=v.byteStride??12,start=(v.byteOffset??0)+(a.byteOffset??0),data=Buffer.alloc(a.count*4);
      for(let i=0;i<a.count;i++){
        const xyz=[0,1,2].map(k=>binary.readFloatLE(start+i*stride+k*4));const length=Math.hypot(...xyz)||1;
        for(let k=0;k<3;k++)data.writeInt8(Math.round(Math.max(-1,Math.min(1,xyz[k]/length))*127),i*4+k);
      }
      a.bufferView=append(data,{byteStride:4,target:34962});a.componentType=5120;a.normalized=true;a.byteOffset=0;delete a.min;delete a.max;
    }else a.bufferView=copyView(a.bufferView);
    accessorMap.set(index,accessors.length);accessors.push(a);
  }
  for(const mesh of gltf.meshes)for(const prim of mesh.primitives){
    for(const key of Object.keys(prim.attributes))prim.attributes[key]=accessorMap.get(prim.attributes[key]);
    prim.indices=accessorMap.get(prim.indices);
  }
  for(const img of gltf.images??[])if(img.bufferView!==undefined)img.bufferView=copyView(img.bufferView);
  gltf.accessors=accessors;gltf.bufferViews=views;gltf.buffers=[{byteLength:offset}];
  gltf.extensionsUsed=[...new Set([...(gltf.extensionsUsed??[]),'KHR_mesh_quantization'])];
  gltf.extensionsRequired=[...new Set([...(gltf.extensionsRequired??[]),'KHR_mesh_quantization'])];
  const raw=Buffer.from(JSON.stringify(gltf)),json=Buffer.alloc(Math.ceil(raw.length/4)*4,0x20);raw.copy(json);
  const bin=Buffer.concat(chunks);const header=Buffer.alloc(20);header.writeUInt32LE(0x46546c67,0);header.writeUInt32LE(2,4);header.writeUInt32LE(28+json.length+bin.length,8);header.writeUInt32LE(json.length,12);header.writeUInt32LE(0x4e4f534a,16);
  const bh=Buffer.alloc(8);bh.writeUInt32LE(bin.length,0);bh.writeUInt32LE(0x004e4942,4);
  const result=Buffer.concat([header,json,bh,bin]);fs.writeFileSync(filename+'.tmp',result);fs.renameSync(filename+'.tmp',filename);
  const triangles=gltf.meshes.flatMap(m=>m.primitives).reduce((n,p)=>n+gltf.accessors[p.indices].count/3,0);
  return {file:path.basename(filename),before:input.length,after:result.length,triangles};
}

if(require.main===module){
  const root=path.resolve(__dirname,'..');
  const files=process.argv.slice(2);
  const results=(files.length?files:[path.join(root,'island_dusk_refined.glb'),...fs.readdirSync(path.join(root,'assets/refined/glb')).filter(x=>x.endsWith('.glb')).map(x=>path.join(root,'assets/refined/glb',x))]).map(optimize);
  const reportPath=path.join(root,'reports/refined_scene.json');
  if(fs.existsSync(reportPath)){
    const report=JSON.parse(fs.readFileSync(reportPath));report.glb_bytes=fs.statSync(path.join(root,'island_dusk_refined.glb')).size;
    const scene=results.find(x=>x.file==='island_dusk_refined.glb');if(scene)report.web_triangles=scene.triangles;
    report.original_budget_pass=report.web_triangles<=600000&&report.glb_bytes<=25000000;report.web_packing='8-bit normalized normals; unused UVs removed; positions and topology unchanged';fs.writeFileSync(reportPath,JSON.stringify(report,null,2));
  }
  console.log(JSON.stringify(results,null,2));
}
module.exports={optimize};
