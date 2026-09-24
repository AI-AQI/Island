import assert from 'node:assert/strict';
import fs from 'node:fs';
import {Vector3,Matrix4,Quaternion,Ray} from '../viewer/vendor/three/build/three.core.js';
import {makeNavigation} from '../viewer/navigation.mjs';
const root=new URL('../',import.meta.url),meta=JSON.parse(fs.readFileSync(new URL('assets/waterside/scene.json',root)));
const old=JSON.parse(fs.readFileSync(new URL('assets/architecture/scene.json',root))),nav=makeNavigation(meta),tests=[];
const bytes=fs.readFileSync(new URL('assets/waterside/island_waterside.glb',root)),jsonLength=bytes.readUInt32LE(12),gltf=JSON.parse(bytes.toString('utf8',20,20+jsonLength)),binaryStart=28+jsonLength;
function test(name,fn){fn();tests.push(name);}
function values(index){
  const a=gltf.accessors[index],v=gltf.bufferViews[a.bufferView],components={SCALAR:1,VEC2:2,VEC3:3,VEC4:4}[a.type],sizes={5121:1,5123:2,5125:4,5126:4},size=sizes[a.componentType],stride=v.byteStride||size*components,start=binaryStart+(v.byteOffset||0)+(a.byteOffset||0);
  return Array.from({length:a.count},(_,i)=>Array.from({length:components},(_,k)=>{const p=start+i*stride+k*size;return a.componentType===5126?bytes.readFloatLE(p):a.componentType===5125?bytes.readUInt32LE(p):a.componentType===5123?bytes.readUInt16LE(p):bytes[p];}));
}
function matrix(index){
  const n=gltf.nodes[index],local=n.matrix?new Matrix4().fromArray(n.matrix):new Matrix4().compose(new Vector3(...(n.translation||[0,0,0])),new Quaternion(...(n.rotation||[0,0,0,1])),new Vector3(...(n.scale||[1,1,1])));
  const parent=gltf.nodes.findIndex(n=>n.children?.includes(index));return parent<0?local:matrix(parent).multiply(local);
}
test('Accepted buildings, terrain, trees, bridge route and living sites are preserved',()=>{
  for(const key of ['house','cafe','terrain','trees','blossomTree','bridge','lifeSites','plots','shelters'])assert.deepEqual(meta[key],old[key],key);
  for(const rock of meta.waterDetails.newBankObstacles)assert(!nav.canWalk(rock.position[0],-rock.position[1]),'New bank rock has no collision');
});
test('Exported stone bridge deck matches walking height across both lanes and crown',()=>{
  const index=gltf.nodes.findIndex(n=>n.name==='stone_bridge_001'),node=gltf.nodes[index],transform=matrix(index),triangles=[];
  for(const p of gltf.meshes[node.mesh].primitives){
    const positions=values(p.attributes.POSITION).map(v=>new Vector3(...v).applyMatrix4(transform)),ids=values(p.indices).flat();
    for(let i=0;i<ids.length;i+=3)triangles.push([positions[ids[i]],positions[ids[i+1]],positions[ids[i+2]]]);
  }
  const b=meta.bridge,co=Math.cos(b.angle),si=Math.sin(b.angle);let samples=0;
  // Sample stone centers rather than intentional narrow mortar seams.
  for(let i=1;i<25;i+=2)for(const v of [-.80,.16,.80]){
    const u=-b.halfLength+(i+.5)*b.halfLength*2/26,x=b.position[0]+co*u-si*v,z=-b.position[1]-si*u-co*v;
    const ray=new Ray(new Vector3(x,30,z),new Vector3(0,-1,0));let top=-Infinity;
    for(const tri of triangles){const hit=ray.intersectTriangle(...tri,false,new Vector3());if(hit)top=Math.max(top,hit.y);}
    assert(Number.isFinite(top),'Hole in bridge wearing course');assert(Math.abs(top-nav.height(x,z))<.065,`Foot height mismatch: ${top} vs ${nav.height(x,z)}`);assert(nav.canWalk(x,z));samples++;
  }
  assert(samples>=30);
});
test('River exports real shallow/deep color variation and a continuous waterfall lip',()=>{
  const node=gltf.nodes.find(n=>n.name==='stream_surface'),p=gltf.meshes[node.mesh].primitives[0];
  assert(p.attributes.COLOR_0!==undefined);const colors=values(p.attributes.COLOR_0),reds=colors.map(c=>c[0]);assert(Math.max(...reds)-Math.min(...reds)>.08);
  assert.equal(meta.waterfallLip.length,33);for(let i=1;i<meta.waterfallLip.length;i++)assert(Math.hypot(...meta.waterfallLip[i].map((v,k)=>v-meta.waterfallLip[i-1][k]))<.45);
});
const report={passed:tests.length,tests};fs.writeFileSync(new URL('reports/waterside_geometry_tests.json',root),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
