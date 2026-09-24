import assert from 'node:assert/strict';
import fs from 'node:fs';
import { makeNavigation, groundHeight } from '../viewer/navigation.mjs';
import { createResident, routinePeriod } from '../viewer/resident.mjs';
import { newGame, restoreGame, migrateLayout } from '../viewer/game-state.mjs';

const meta=JSON.parse(fs.readFileSync(new URL('../assets/expanded/scene.json',import.meta.url)));
const nav=makeNavigation(meta),sites=meta.lifeSites,spawn=nav.nearestPoint(meta.spawn[0],-meta.spawn[1]);
const tests=[];
function test(name,fn){fn();tests.push(name);}
test('Expanded terrain grows 76.64% while house/cafe bounds retain their physical dimensions',()=>{
  const old=JSON.parse(fs.readFileSync(new URL('../assets/living/scene.json',import.meta.url)));
  assert(Math.abs(meta.terrainScale[0]*meta.terrainScale[1]-1.7664)<1e-6);
  for(const id of['house','cafe'])for(let i=0;i<3;i++)assert(Math.abs((meta[id][1][i]-meta[id][0][i])-(old[id][1][i]-old[id][0][i]))<.0001);
  assert.equal(groundHeight(10*1.28,8*1.38,meta.terrainScale),groundHeight(10,8));
  let oldArea=0,newArea=0;const oldNav=makeNavigation(old);
  for(let x=-32;x<32;x+=.3)for(let z=-20;z<20;z+=.3){oldArea+=oldNav.canWalk(x,z);newArea+=nav.canWalk(x,z);}
  assert(newArea>oldArea*1.7);console.log('WALKABLE_AREA_RATIO',newArea/oldArea);
});
test('All daily-life, crop and cafe destinations connect without crossing buildings, water or furniture',()=>{
  const targets=[spawn,...sites.map(s=>s.position),...meta.plots.map(p=>[p.approach[0],-p.approach[1]]),meta.cafeApproach];
  for(const to of targets)assert(nav.canWalk(...to),`Blocked destination ${to}`);
  for(const from of targets)for(const to of targets){
    const path=nav.findPath(from,to);assert(path.length,`Disconnected ${from} -> ${to}`);
    let p=[...from];
    for(const wp of path){
      let count=0;
      while(Math.hypot(wp[0]-p[0],wp[1]-p[1])>.065){
        assert(++count<1000,`Stuck ${from} -> ${to} at ${p}, waypoint ${wp}`);
        const d=Math.hypot(wp[0]-p[0],wp[1]-p[1]),amount=Math.min(d,.08);
        p=nav.move(p,(wp[0]-p[0])/d*amount,(wp[1]-p[1])/d*amount);assert(nav.canWalk(...p));
      }
    }
    assert(Math.hypot(p[0]-to[0],p[1]-to[1])<.15);
  }
  assert.equal(nav.canWalk(34,0),false);
  assert(nav.findPath(spawn,sites.find(s=>s.id==='orchard').position).some(p=>nav.onBridge(...p)));
});

function simulation(hour,weather='clear',start=spawn){
  const resident=createResident({nav,sites});let p=[...start],busy=0;const visits=new Set(),actions=new Set();let last;
  function run(seconds,hourNow=hour,weatherNow=weather){
    for(let i=0;i<seconds*20;i++){
      busy=Math.max(0,busy-.05);
      last=resident.update({dt:.05,position:p,hour:hourNow,weather:weatherNow,busy:busy>0});
      assert(nav.canWalk(...last.position));assert(Math.hypot(last.position[0]-p[0],last.position[1]-p[1])<=.101,'Teleport detected');
      p=last.position;
      if(last.phase==='dwelling')visits.add(last.site);
      if(last.action){actions.add(last.action);busy=2;}
    }
    return last;
  }
  return {run,resident,visits,actions,get position(){return [...p];}};
}
test('Daytime resident completes multiple activities and reaches both banks',()=>{
  const sim=simulation(12);sim.run(240);
  for(const id of['orchard','cafe','flowers','garden','overlook'])assert(sim.visits.has(id),`No visit to ${id}`);
  assert(sim.actions.has('Water'));assert(sim.actions.has('Harvest'));
});
test('Morning includes potting work; night settles at home without repeated wandering',()=>{
  assert.equal(routinePeriod(7),'morning');assert.equal(routinePeriod(18),'evening');assert.equal(routinePeriod(23),'night');
  const morning=simulation(7);morning.run(190);assert(morning.visits.has('yard'));assert(morning.actions.has('Plant'));
  const night=simulation(23,'clear',sites.find(s=>s.id==='orchard').position);
  let r=night.run(90);assert.equal(r.site,'home');assert.equal(r.phase,'dwelling');
  const p=night.position;night.run(180);assert.deepEqual(night.position,p);assert.equal(night.actions.size,0);
});
test('Rain interrupts a trip, reaches a real roof, waits and resumes when clear',()=>{
  const sim=simulation(12);sim.run(5);
  let r=sim.run(80,12,'rain');assert.equal(r.phase,'dwelling');assert(sites.find(s=>s.id===r.site).shelter);
  const shelter=meta.shelters.find(s=>Math.abs(s.position[0]-sim.position[0])<s.halfSize[0]&&Math.abs(s.position[1]-sim.position[1])<s.halfSize[1]);assert(shelter,'Resident must actually stand under a roof');
  const p=sim.position;sim.run(50,12,'rain');assert.deepEqual(sim.position,p);
  r=sim.run(2,12,'clear');assert.equal(r.site,'orchard');assert.equal(r.phase,'walking');
});
test('Pause and player handover preserve position, then replan from the player destination',()=>{
  const sim=simulation(12);sim.run(3);const p=sim.position;
  let r=sim.resident.update({dt:0,position:p,hour:12,weather:'clear'});assert.deepEqual(r.position,p);
  r=sim.resident.update({dt:.05,position:p,hour:12,weather:'clear',enabled:false});assert.deepEqual(r.position,p);assert.equal(r.phase,'controlled');
  const manual=sites.find(s=>s.id==='overlook').position;
  r=sim.resident.update({dt:.05,position:manual,hour:18,weather:'clear'});
  assert(Math.hypot(r.position[0]-manual[0],r.position[1]-manual[1])<=.101);
});
test('Old save migration transforms position once and preserves inventory, crops and orders',()=>{
  const old={...newGame(),position:[-10,7],inventory:5,coins:90,deliveries:3};delete old.layoutRevision;old.plots[1]={stage:'growing',wateredAt:Date.now()};
  const state=restoreGame(JSON.stringify(old));migrateLayout(state,meta.terrainScale);
  assert.deepEqual(state.position,[-12.8,9.66]);assert.equal(state.coins,90);assert.equal(state.inventory,5);assert.deepEqual(state.plots,old.plots);
  const saved=JSON.stringify(state);migrateLayout(state,meta.terrainScale);assert.equal(JSON.stringify(state),saved);assert.deepEqual(restoreGame(saved),state);
});
const result={passed:tests.length,tests};fs.writeFileSync(new URL('../reports/resident_logic_tests.json',import.meta.url),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
