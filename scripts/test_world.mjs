import assert from 'node:assert/strict';
import fs from 'node:fs';
import {DAY_SECONDS,WEATHER,newWorld,restoreWorld,advanceWorld,daylight,blendWeather,timeLabel} from '../viewer/world-state.mjs';
const tests=[];
function test(name,fn){fn();tests.push(name);}
test('One real 30-minute cycle advances exactly one day, including multiple midnight crossings',()=>{
  const s=newWorld();advanceWorld(s,DAY_SECONDS);assert.equal(s.day,2);assert.equal(s.hour,10);
  s.hour=23.99;advanceWorld(s,2);assert.equal(s.day,3);assert(s.hour<.02);
  s.speed=4;advanceWorld(s,DAY_SECONDS);assert.equal(s.day,7);
});
test('Paused time and invalid deltas do not advance the world',()=>{
  const s=newWorld();s.running=false;advanceWorld(s,600);assert.equal(s.hour,10);
  s.running=true;for(const dt of[-1,NaN,Infinity,0])advanceWorld(s,dt);assert.equal(s.hour,10);
});
test('Independent world preferences restore and malformed storage recovers safely',()=>{
  const s={...newWorld(),hour:22.5,day:4,weather:'rain',running:false,speed:.5};assert.deepEqual(restoreWorld(JSON.stringify(s)),s);
  for(const raw of['null','broken','{}',JSON.stringify({...s,hour:24}),JSON.stringify({...s,weather:'unknown'}),JSON.stringify({...s,day:-1}),JSON.stringify({...s,speed:100})])assert.deepEqual(restoreWorld(raw),newWorld());
});
test('Daylight is continuous across midnight and distinguishes midday, dusk and night',()=>{
  assert(daylight(12).day>.99);assert(daylight(0).night>.99);assert(daylight(18).warm>daylight(12).warm);
  assert(Math.abs(daylight(23.999).night-daylight(.001).night)<.001);
  for(let h=0;h<24;h+=.05)for(const k of['day','night','warm'])assert(daylight(h)[k]>=0&&daylight(h)[k]<=1);
  assert.equal(timeLabel(23.99),'23:59');assert.equal(timeLabel(24),'00:00');
});
test('Weather changes gradually, remains bounded, and rain can fully clear',()=>{
  const w={...WEATHER.clear};blendWeather(w,WEATHER.rain,.1);assert(w.rain>0&&w.rain<.1);
  for(let i=0;i<180;i++)blendWeather(w,WEATHER.rain,.1);assert(w.rain>.999);
  for(let i=0;i<200;i++)blendWeather(w,WEATHER.clear,.1);assert(w.rain<.001);
  for(const k of['cloud','rain','mist'])assert(w[k]>=0&&w[k]<=1);
});
const report={passed:tests.length,tests};fs.writeFileSync(new URL('../reports/world_logic_tests.json',import.meta.url),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
