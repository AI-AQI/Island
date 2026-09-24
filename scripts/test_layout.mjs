import assert from 'node:assert/strict';
import fs from 'node:fs';
import { makeNavigation } from '../viewer/navigation.mjs';
import { createResident } from '../viewer/resident.mjs';
import { newGame, restoreGame, migrateReferenceLayout } from '../viewer/game-state.mjs';

const edition=process.argv[2]||'layout';
if(!['layout','landscape','architecture','waterside'].includes(edition))throw new Error('Unknown scene edition');
const meta=JSON.parse(fs.readFileSync(new URL(`../assets/${edition}/scene.json`,import.meta.url)));
const nav=makeNavigation(meta),sites=meta.lifeSites,spawn=[meta.spawn[0],-meta.spawn[1]],tests=[];
function test(name,fn){fn();tests.push(name);}

test('Reference districts retain building scale and surround an open central common',()=>{
  const old=JSON.parse(fs.readFileSync(new URL('../assets/living/scene.json',import.meta.url)));
  for(const id of ['house','cafe'])for(let i=0;i<3;i++){
    const delta=(meta[id][1][i]-meta[id][0][i])-(old[id][1][i]-old[id][0][i]);
    // The architecture pass softens tiny edge corners and deliberately lowers
    // only the cafe roof. Ground footprint and navigation stay unchanged.
    if(meta.architectureRevision&&id==='cafe'&&i===2)assert(delta<-.2&&delta>-.5);
    else assert(Math.abs(delta)<(meta.architectureRevision?.003:.001));
  }
  const d=Object.fromEntries(meta.districts.map(d=>[d.id,d.position]));
  assert(d.home[0]<d.common[0]&&d.home[1]<d.common[1]);
  assert(d.garden[0]<d.common[0]&&d.garden[1]>d.common[1]);
  assert(d.cafe[0]>d.common[0]&&d.cafe[1]<d.common[1]);
  assert(d.bridge[0]>d.common[0]&&d.bridge[1]>d.common[1]);
  let open=0,total=0;for(let x=-5;x<=4;x+=.5)for(let z=-1;z<=7;z+=.5){total++;open+=nav.canWalk(x,z);}
  assert(open/total>.90,`Common only ${open/total} walkable`);
});
test('Narrow upper-left inlet meanders horizontally and widens toward the lower-right outlet',()=>{
  const river=meta.terrain.river,first=river[0],last=river.at(-1);
  assert(first[0]<0&&last[0]>10&&first[1]>20&&last[1]<-19);
  assert(last[2]/first[2]>4);
  assert(river.some((p,i)=>i>0&&p[1]<-3&&p[1]>-8&&Math.abs(p[0]-river[i-1][0])>2*Math.abs(p[1]-river[i-1][1])));
  for(const [x,y] of river)if(!nav.onBridge(x,-y))assert(!nav.canWalk(x,-y),'River permits walking');
});
test('Every life site and crop is reachable by continuous movement; cross-bank routes use the rotated bridge',()=>{
  const targets=[spawn,...sites.map(s=>s.position),...meta.plots.map(p=>[p.approach[0],-p.approach[1]])];
  for(const to of targets)assert(nav.canWalk(...to),`Blocked ${to}`);
  for(const from of targets)for(const to of targets){
    const path=nav.findPath(from,to);assert(path.length,`No route ${from} -> ${to}`);let p=[...from];
    for(const wp of path){let tries=0;while(Math.hypot(wp[0]-p[0],wp[1]-p[1])>.065){
      assert(++tries<1000,`Stuck at ${p} toward ${wp}`);
      const dx=wp[0]-p[0],dz=wp[1]-p[1],d=Math.hypot(dx,dz),s=Math.min(d,.08)/d;
      p=nav.move(p,dx*s,dz*s);assert(nav.canWalk(...p));
    }}
    assert(Math.hypot(p[0]-to[0],p[1]-to[1])<.15);
  }
  assert(nav.findPath(spawn,meta.cafeApproach).some(p=>nav.onBridge(...p)));
  const b=meta.bridge;assert(nav.height(b.position[0],-b.position[1])-meta.waterfallLip[0][2]>1.4,'Bridge must clear the water');
});

function simulation(hour,weather='clear',start=spawn){
  const resident=createResident({nav,sites});let p=[...start],busy=0,last;const visits=new Set(),actions=new Set();
  function run(seconds,h=hour,w=weather){for(let i=0;i<seconds*20;i++){
    busy=Math.max(0,busy-.05);last=resident.update({dt:.05,position:p,hour:h,weather:w,busy:busy>0});
    assert(nav.canWalk(...last.position));assert(Math.hypot(last.position[0]-p[0],last.position[1]-p[1])<=.101);
    p=last.position;if(last.phase==='dwelling')visits.add(last.site);if(last.action){actions.add(last.action);busy=2;}
  }return last;}
  return{run,resident,visits,actions,get position(){return [...p];}};
}
test('Day and morning routines visit both banks, gardens and potting table without getting stuck',()=>{
  const day=simulation(12);day.run(330);
  for(const id of ['orchard','cafe','flowers','garden','overlook'])assert(day.visits.has(id),`Missing ${id}`);
  assert(day.actions.has('Water')&&day.actions.has('Harvest'));
  const morning=simulation(7);morning.run(260);assert(morning.visits.has('yard'));assert(morning.actions.has('Plant'));
});
test('Rain reaches a real roof and night returns home; player handover preserves position',()=>{
  const s=simulation(12);s.run(6);let r=s.run(100,12,'rain');assert.equal(r.phase,'dwelling');
  assert(meta.shelters.some(roof=>Math.abs(roof.position[0]-s.position[0])<roof.halfSize[0]&&Math.abs(roof.position[1]-s.position[1])<roof.halfSize[1]));
  const p=s.position;s.run(30,12,'rain');assert.deepEqual(s.position,p);
  r=s.resident.update({dt:.05,position:p,hour:12,weather:'rain',enabled:false});assert.deepEqual(r.position,p);assert.equal(r.phase,'controlled');
  const night=simulation(23,'clear',meta.cafeApproach);r=night.run(120);assert.equal(r.site,'home');assert.equal(r.phase,'dwelling');
});
test('Layout migration rescues unsafe positions, runs once and preserves crops, money and inventory',()=>{
  const old={...newGame(),position:[meta.bridge.position[0],0],inventory:5,coins:90,deliveries:3};
  old.plots[1]={stage:'growing',wateredAt:123456};const state=restoreGame(JSON.stringify(old));
  migrateReferenceLayout(state,nav,spawn);assert(nav.canWalk(...state.position));assert.equal(state.layoutRevision,3);
  for(const k of ['plots','inventory','coins','deliveries'])assert.deepEqual(state[k],old[k]);
  const saved=JSON.stringify(state);migrateReferenceLayout(state,nav,spawn);assert.equal(JSON.stringify(state),saved);assert.deepEqual(restoreGame(saved),state);
});
const report={passed:tests.length,tests};fs.writeFileSync(new URL(`../reports/${edition}_logic_tests.json`,import.meta.url),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
