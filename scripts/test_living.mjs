import assert from 'node:assert/strict';
import fs from 'node:fs';
import { newGame, restoreGame, tendPlot, deliver, plotStatus, GROW_MS } from '../viewer/game-state.mjs';
import { makeNavigation, river, bend } from '../viewer/navigation.mjs';

const tests=[];
function test(name,fn){fn();tests.push(name);}
test('Complete plant/water/grow/harvest/order loop; no premature or duplicate harvest',()=>{
  const game=newGame(),t=100000;
  assert.equal(deliver(game),false);
  for(let i=0;i<3;i++){
    assert.equal(tendPlot(game,i,t),'planted');assert.equal(tendPlot(game,i,t),'watered');
    assert.equal(tendPlot(game,i,t+GROW_MS-1),'waiting');assert.equal(game.inventory,i);
    assert.equal(plotStatus(game.plots[i],t+GROW_MS),'ready');
    assert.equal(tendPlot(game,i,t+GROW_MS),'harvested');assert.equal(game.inventory,i+1);
  }
  assert.equal(deliver(game),true);assert.equal(game.coins,30);assert.equal(game.inventory,0);assert.equal(game.deliveries,1);
  assert.equal(deliver(game),false);assert.equal(game.coins,30);
  assert.equal(tendPlot(game,0,t+GROW_MS),'planted');assert.equal(game.inventory,0);
});
test('Saved crops and inventory restore; invalid storage recovers safely',()=>{
  const game=newGame();tendPlot(game,1,100);tendPlot(game,1,100);game.coins=30;game.position=[-5,6];
  const loaded=restoreGame(JSON.stringify(game));assert.deepEqual(loaded,game);assert.equal(plotStatus(loaded.plots[1],100+GROW_MS),'ready');
  for(const raw of ['broken','null','{}',JSON.stringify({...game,coins:-1}),JSON.stringify({...game,plots:[null,null,null]})])assert.deepEqual(restoreGame(raw),newGame());
});
const meta=JSON.parse(fs.readFileSync(new URL('../assets/living/scene.json',import.meta.url))),nav=makeNavigation(meta);
const spawn=nav.nearestPoint(meta.spawn[0],-meta.spawn[1]);
const destinations=meta.plots.map(p=>[p.approach[0],-p.approach[1]]);
destinations.push([(meta.cafe[0][0]+meta.cafe[1][0])/2,6.1]);
test('Every crop and cafe reachable; entire path and swept movement stay walkable',()=>{
  for(const from of[spawn,...destinations])for(const to of destinations){
    assert(nav.canWalk(...to));const route=nav.findPath(from,to);assert(route.length>0,`${from} to ${to}`);
    let pos=from;
    for(const waypoint of route){
      for(let i=0;i<1000&&Math.hypot(waypoint[0]-pos[0],waypoint[1]-pos[1])>.07;i++){
        const dx=waypoint[0]-pos[0],dz=waypoint[1]-pos[1],len=Math.hypot(dx,dz),next=nav.move(pos,dx/len*.05,dz/len*.05);
        assert(nav.canWalk(...next));assert(Math.hypot(next[0]-pos[0],next[1]-pos[1])>.001,'Path becomes stuck');pos=next;
      }
    }
    assert(Math.hypot(pos[0]-to[0],pos[1]-to[1])<.15);
  }
});
test('River and buildings block movement; bridge is the river crossing',()=>{
  for(const y of[-10,-1,4,9])assert.equal(nav.canWalk(river(y)+bend(y),-y),false);
  assert.equal(nav.canWalk((meta.house[0][0]+meta.house[1][0])/2,-4),false);
  assert.equal(nav.canWalk(25,0),false);assert(nav.canWalk(meta.bridge.position[0],-meta.bridge.position[1]));
  const route=nav.findPath(destinations[0],destinations[3]);assert(route.some(p=>nav.onBridge(...p)));
  const edge=nav.nearestPoint(-20,8);const final=nav.move(edge,-50,0);assert(nav.canWalk(...final));
});
const result={passed:tests.length,tests};
fs.writeFileSync(new URL('../reports/living_logic_tests.json',import.meta.url),JSON.stringify(result,null,2));
console.log(JSON.stringify(result,null,2));
