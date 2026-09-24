import assert from 'node:assert/strict';
import fs from 'node:fs';
import { makeTerrain } from '../viewer/terrain.mjs';
import { makeNavigation } from '../viewer/navigation.mjs';
const meta=JSON.parse(fs.readFileSync(new URL('../assets/landscape/scene.json',import.meta.url)));
const old=JSON.parse(fs.readFileSync(new URL('../assets/layout/scene.json',import.meta.url)));
const terrain=makeTerrain(meta.terrain),nav=makeNavigation(meta),tests=[];
function test(name,fn){fn();tests.push(name);}
test('Blender and runtime share terrain heights, including elevated house, hills and shallows',()=>{
  for(const p of meta.heightSamples)assert(Math.abs(terrain.height(...p.position)-p.height)<1e-6,`Mismatch at ${p.position}`);
  assert(terrain.height(-6.6,-18.7)>terrain.height(-1,4)+2.5);
  assert(terrain.height(-12,-10)>terrain.height(-1,4)+1);
  for(const p of [...meta.lifeSites.map(s=>s.position),...meta.plots.map(p=>[p.approach[0],-p.approach[1]])])assert(Math.abs(nav.height(...p)-terrain.height(...p)-.10)<1e-6);
});
test('Recovered pink tree and additional groves leave the central common open',()=>{
  assert.equal(meta.blossomTree.source,'assets/source/tree_blossom.blend');
  assert(meta.trees.length>=old.trees.length+12);assert(meta.trees.some(t=>t.name===meta.blossomTree.name));
  const [x,y]=meta.blossomTree.position;assert(!nav.canWalk(x,-y));assert(x>-7&&x<4&&y>4);
  let open=0,n=0;for(let x=-5;x<5;x+=.5)for(let z=-1;z<7;z+=.5){open+=nav.canWalk(x,z);n++;}assert(open/n>.9);
});
test('Water descends from the spring; river samples follow its height and shoreline stays safe',()=>{
  const heights=meta.terrain.waterHeights;assert(heights[0]-heights.at(-1)>3.5);
  for(let i=1;i<heights.length;i++)assert(heights[i]<=heights[i-1]+1e-9);
  for(let i=0;i<heights.length;i++)assert(Math.abs(terrain.along(i/(heights.length-1)).waterHeight-heights[i])<1e-9);
  for(let i=0;i<180;i++){
    const a=i*Math.PI/90,r=terrain.outline(a),[rx,ry]=meta.terrain.radius;
    assert(!nav.canWalk(rx*r*Math.cos(a),-ry*r*Math.sin(a)));
  }
});
const report={passed:tests.length,tests};fs.writeFileSync(new URL('../reports/landscape_geometry_tests.json',import.meta.url),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
