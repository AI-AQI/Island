import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { createEnvironment } from './environment.js';
import { createWorld } from './world.js';
import { loadCharacter } from './character.js';
import { makeNavigation } from './navigation.mjs';
import { createResident } from './resident.mjs';
import { newGame, restoreGame, migrateReferenceLayout, plotStatus, tendPlot, deliver, GROW_MS, SAVE_KEY } from './game-state.mjs';

const $=s=>document.querySelector(s),canvas=$('#scene');
const renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true,powerPreference:'high-performance'});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.setSize(innerWidth,innerHeight);
renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.22;
renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFShadowMap;
const scene=new THREE.Scene(),camera=new THREE.OrthographicCamera(-30,30,22.5,-22.5,.1,650);
const controls=new OrbitControls(camera,canvas);controls.enableDamping=true;controls.dampingFactor=.08;controls.minZoom=.65;controls.maxZoom=3;controls.maxPolarAngle=Math.PI*.48;controls.minPolarAngle=.15;
const hemisphere=new THREE.HemisphereLight('#e6d6ef','#80795f',2.15);scene.add(hemisphere);
const sun=new THREE.DirectionalLight('#ffe0ae',3);sun.position.set(30,28,-9);sun.target.position.set(0,9,0);scene.add(sun,sun.target);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);
Object.assign(sun.shadow.camera,{left:-42,right:42,top:37,bottom:-36,near:1,far:130});sun.shadow.bias=-.0003;sun.shadow.normalBias=.04;
const fill=new THREE.DirectionalLight('#c0c7ec',.8);fill.position.set(-22,26,25);scene.add(fill);
const views={hero:{p:[16,69,94],t:[0,8.5,0],span:49.5},farm:{p:[-10,34,44],t:[-17,10.5,5],span:24},cafe:{p:[33,32,22],t:[18,11,-7],span:22},top:{p:[0,85,.01],t:[0,9,0],span:52},water:{p:[29,30,41],t:[12,6,12],span:26}};
let currentView='hero',playing=false,paused=false,elapsed=0,last=performance.now(),uiTimer=0,fpsTime=0,frames=0;
let model,meta,player,avatar,nav,environment,world,state,resident,residentStatus,context=null,route=[],walking=0,toastTimeout,saveDirty=false,observeFollow=false,observerView=null;
const keys=new Set(),cropNodes=[],markers=[],pickTargets=[];
const pointer=new THREE.Vector2(),ray=new THREE.Raycaster(),scratch=new THREE.Vector3();
const forward=new THREE.Vector3(),right=new THREE.Vector3(),up=new THREE.Vector3(0,1,0);
let savedView=null,cafeTarget=[17,6.4],petUntil=0;

function fit(){const aspect=innerWidth/innerHeight,span=playing?23:observeFollow?15:views[currentView].span,height=span*Math.max(1,(4/3)/aspect);camera.left=-height*aspect/2;camera.right=height*aspect/2;camera.top=height/2;camera.bottom=-height/2;camera.updateProjectionMatrix();}
function view(name){observeFollow=false;$('#follow-resident').setAttribute('aria-pressed','false');$('#follow-resident').textContent='看看她';currentView=name;const v=views[name];camera.position.set(...v.p);camera.zoom=1;controls.target.set(...v.t);fit();controls.update();document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===name));}
view('hero');
addEventListener('resize',()=>{fit();renderer.setSize(innerWidth,innerHeight);});
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>{if(playing)setPlaying(false);view(b.dataset.view);}));

function toast(message){$('#toast').textContent=message;$('#toast').classList.add('show');clearTimeout(toastTimeout);toastTimeout=setTimeout(()=>$('#toast').classList.remove('show'),3600);}
function save(){if(!state)return;state.position=player?[player.position.x,player.position.z]:null;try{localStorage.setItem(SAVE_KEY,JSON.stringify(state));$('#saved').textContent='进度已保存在此浏览器';}catch{$('#saved').textContent='浏览器无法保存，当前进度仅本次有效';}saveDirty=false;}
addEventListener('pagehide',save);
function setPlaying(value){
  if(!player)return;
  if(observeFollow)setObserverFollow(false);
  playing=value;route=[];keys.clear();document.body.classList.toggle('playing',value);
  closeJournal();
  resident?.suspend();avatar?.cancel();walking=0;
  $('#play').textContent=value?'退出漫游':'进入小岛';$('#play').setAttribute('aria-pressed',String(value));
  if(value){savedView={p:camera.position.clone(),t:controls.target.clone(),zoom:camera.zoom};camera.position.copy(player.position).add(new THREE.Vector3(10,18,24));controls.target.copy(player.position);camera.zoom=1;toast('WASD 移动，也可以点击地面。走近菜田，按 E 播种。');}
  else{save();if(savedView){camera.position.copy(savedView.p);controls.target.copy(savedView.t);camera.zoom=savedView.zoom;}}
  controls.mouseButtons.LEFT=value?null:THREE.MOUSE.ROTATE;controls.mouseButtons.RIGHT=THREE.MOUSE.ROTATE;
  controls.touches.ONE=value?null:THREE.TOUCH.ROTATE;controls.touches.TWO=THREE.TOUCH.DOLLY_ROTATE;
  fit();controls.update();updateUI();canvas.focus({preventScroll:true});
}
function setObserverFollow(value){
  if(!player||playing)return;
  observeFollow=value;
  if(value){observerView={p:camera.position.clone(),t:controls.target.clone(),zoom:camera.zoom};camera.position.copy(player.position).add(new THREE.Vector3(9,12,19));controls.target.copy(player.position);camera.zoom=1;}
  else if(observerView){camera.position.copy(observerView.p);controls.target.copy(observerView.t);camera.zoom=observerView.zoom;}
  $('#follow-resident').setAttribute('aria-pressed',String(value));$('#follow-resident').textContent=value?'回到全岛':'看看她';fit();controls.update();
}
$('#follow-resident').addEventListener('click',()=>setObserverFollow(!observeFollow));
function closeJournal(){document.body.classList.remove('journal-open');$('#journal-toggle').setAttribute('aria-expanded','false');}
$('#journal-toggle').addEventListener('click',()=>{const open=document.body.classList.toggle('journal-open');$('#journal-toggle').setAttribute('aria-expanded',String(open));});
$('#play').addEventListener('click',()=>setPlaying(!playing));
$('#go-garden').addEventListener('click',()=>{goTo([meta.plots[1].approach[0],-meta.plots[1].approach[1]]);canvas.focus({preventScroll:true});});
$('#go-cafe').addEventListener('click',()=>{goTo(cafeTarget);canvas.focus({preventScroll:true});});
for(const id of['orchard','overlook'])$(`#go-${id}`).addEventListener('click',()=>{goTo(meta.lifeSites.find(s=>s.id===id).position);canvas.focus({preventScroll:true});});
$('#pause').addEventListener('click',()=>{paused=!paused;$('#pause').textContent=paused?'继续风景':'暂停风景';$('#pause').setAttribute('aria-pressed',String(paused));keys.clear();route=[];});
$('#quality').addEventListener('change',e=>{const low=e.target.value==='low';renderer.setPixelRatio(Math.min(devicePixelRatio,low?1:1.5));sun.shadow.mapSize.set(low?1024:2048,low?1024:2048);sun.shadow.map?.dispose();sun.shadow.map=null;world?.setQuality(low);});
$('#help-button').addEventListener('click',()=>$('#help-dialog').showModal());
$('#close-help').addEventListener('click',()=>$('#help-dialog').close());
$('#reset').addEventListener('click',()=>$('#reset-dialog').showModal());
$('#cancel-reset').addEventListener('click',()=>$('#reset-dialog').close());
$('#confirm-reset').addEventListener('click',()=>{state=newGame();migrateReferenceLayout(state,nav,[meta.spawn[0],-meta.spawn[1]]);resident?.suspend();avatar?.cancel();placePlayer(...state.position);route=[];save();updateUI();$('#reset-dialog').close();canvas.focus({preventScroll:true});toast('新的小岛日记开始了。');});
addEventListener('keydown',e=>{
  if(document.querySelector('dialog[open]')||['INPUT','SELECT','TEXTAREA'].includes(document.activeElement?.tagName))return;
  if(['KeyW','KeyA','KeyS','KeyD','ArrowUp','ArrowDown','ArrowLeft','ArrowRight','ShiftLeft'].includes(e.code)){if(playing)e.preventDefault();keys.add(e.code);route=[];}
  if(e.code==='KeyE'&&!e.repeat)interact();
  if(e.code==='Escape'&&playing)setPlaying(false);
  if(!playing&&['Digit1','Digit2','Digit3','Digit4','Digit5'].includes(e.code))view(Object.keys(views)[Number(e.code.slice(-1))-1]);
});
addEventListener('keyup',e=>keys.delete(e.code));addEventListener('blur',()=>keys.clear());
document.addEventListener('visibilitychange',()=>{keys.clear();last=performance.now();if(document.hidden)save();});
function placePlayer(x,z){if(!nav.canWalk(x,z))[x,z]=nav.nearestPoint(x,z);player.position.set(x,nav.height(x,z),z);}
function movePlayer(dt){
  if(!playing||paused||avatar?.busy)return;
  let dx=0,dz=0;
  if(keys.size){
    camera.getWorldDirection(forward);forward.y=0;if(forward.lengthSq()<.01)forward.set(0,0,-1);forward.normalize();right.crossVectors(forward,up).normalize();
    const f=+(keys.has('KeyW')||keys.has('ArrowUp'))-+(keys.has('KeyS')||keys.has('ArrowDown')),r=+(keys.has('KeyD')||keys.has('ArrowRight'))-+(keys.has('KeyA')||keys.has('ArrowLeft'));
    dx=forward.x*f+right.x*r;dz=forward.z*f+right.z*r;
  }else if(route.length){dx=route[0][0]-player.position.x;dz=route[0][1]-player.position.z;if(Math.hypot(dx,dz)<.13){route.shift();dx=0;dz=0;}}
  const length=Math.hypot(dx,dz),speed=keys.has('ShiftLeft')?4.6:3.1,before=player.position.clone();
  if(length>.001){const distance=Math.min(speed*dt,route.length?length:Infinity),p=nav.move([player.position.x,player.position.z],dx/length*distance,dz/length*distance);placePlayer(...p);}
  const moved=player.position.distanceTo(before)>.002;walking=THREE.MathUtils.damp(walking,moved?1:0,12,dt);
  if(moved){const angle=Math.atan2(player.position.x-before.x,player.position.z-before.z);player.rotation.y+=Math.atan2(Math.sin(angle-player.rotation.y),Math.cos(angle-player.rotation.y))*(1-Math.exp(-dt*15));saveDirty=true;}
  avatar.setMoving(moved,keys.has('ShiftLeft')?1.75:1.25);
  const follow=player.position.clone();follow.y+=.65;const shift=follow.sub(controls.target).multiplyScalar(1-Math.exp(-dt*4));camera.position.add(shift);controls.target.add(shift);
}

function moveResident(dt){
  if(playing||!resident)return;
  residentStatus=resident.update({dt,position:[player.position.x,player.position.z],...world.snapshot(),busy:avatar.busy});
  const r=residentStatus;
  placePlayer(...r.position);
  if(r.facing!==null)player.rotation.y+=Math.atan2(Math.sin(r.facing-player.rotation.y),Math.cos(r.facing-player.rotation.y))*(1-Math.exp(-dt*7));
  avatar.setMoving(r.moving,.82);if(r.action)avatar.act(r.action);if(r.moving)saveDirty=true;
  if(observeFollow){const shift=player.position.clone().add(new THREE.Vector3(0,.65,0)).sub(controls.target).multiplyScalar(1-Math.exp(-dt*4));camera.position.add(shift);controls.target.add(shift);}
}

function marker(label,position,target){const button=document.createElement('button');button.className='world-marker';button.type='button';button.setAttribute('aria-label',label);button.textContent=label;$('#world-labels').append(button);button.addEventListener('click',()=>{if(!playing)setPlaying(true);goTo(target);canvas.focus({preventScroll:true});});markers.push({button,position,target});return button;}
function goTo(target){if(paused){toast('先继续风景，再出发吧。');return;}const destination=nav.canWalk(...target)?target:nav.nearestPoint(...target);route=nav.findPath([player.position.x,player.position.z],destination);if(!route.length)toast('这里暂时走不过去，试试沿小路前进。');else closeJournal();}
let pointerStart;
canvas.addEventListener('pointerdown',e=>{if(e.button===0)pointerStart=[e.clientX,e.clientY];});
canvas.addEventListener('pointerup',e=>{
  if(!playing||paused||!pointerStart||e.button!==0||Math.hypot(e.clientX-pointerStart[0],e.clientY-pointerStart[1])>8)return;
  pointerStart=null;const rect=canvas.getBoundingClientRect();pointer.set((e.clientX-rect.left)/rect.width*2-1,-(e.clientY-rect.top)/rect.height*2+1);ray.setFromCamera(pointer,camera);
  const hits=ray.intersectObjects(pickTargets,true);if(hits.length)goTo([hits[0].point.x,hits[0].point.z]);
});
function findContext(){
  if(!playing)return null;const x=player.position.x,z=player.position.z;let nearest=null,distance=2.15;
  meta.plots.forEach((p,i)=>{const d=Math.hypot(x-p.approach[0],z+p.approach[1]);if(d<distance){nearest={type:'plot',index:i};distance=d;}});
  if(Math.hypot(x-cafeTarget[0],z-cafeTarget[1])<2.3)nearest={type:'cafe'};
  const cat=model.getObjectByName('garden_cat');if(!nearest&&cat&&Math.hypot(x-cat.position.x,z-cat.position.z)<1.8)nearest={type:'cat'};
  return nearest;
}
function interact(){
  if(!playing||paused||avatar?.busy||document.querySelector('dialog[open]'))return;context=findContext();if(!context)return;
  if(context.type==='plot'){
    const result=tendPlot(state,context.index),messages={planted:'种子入土了。再按 E 浇水，让它慢慢长大。',watered:'浇好水了，18 秒后就能收获。可以先去照料另一块田。',harvested:'收获 +1 · 新鲜蔬菜放进了篮子。',waiting:'作物正在长大，去岛上散散步吧。'};toast(messages[result]);
    const clip={planted:'Plant',watered:'Water',harvested:'Harvest'}[result];
    if(clip){route=[];keys.clear();const p=meta.plots[context.index].position;player.rotation.y=Math.atan2(p[0]-player.position.x,-p[1]-player.position.z);avatar.act(clip);}
  }else if(context.type==='cafe'){if(deliver(state))toast('订单完成！云边咖啡收到了你的蔬菜，获得 30 枚金币。');else toast(`云边咖啡需要 3 份蔬菜，还差 ${3-state.inventory} 份。`);}
  else{petUntil=elapsed+1.5;toast('小猫蹭了蹭你的手。喵～');}
  save();updateUI();
}
$('#interact').addEventListener('click',()=>{interact();canvas.focus({preventScroll:true});});
function updateUI(){
  if(!state)return;const now=Date.now();context=findContext();$('#inventory').textContent=state.inventory;$('#coins').textContent=state.coins;
  $('#journal-basket').textContent=state.inventory;
  $('#resident-status').textContent=paused?'风景暂停，她也歇一会儿':residentStatus?.label||'在小岛上开始新的一天';
  $('#resident-life').dataset.phase=playing?'controlled':residentStatus?.phase||'idle';
  $('#resident-life').dataset.site=residentStatus?.site||'';
  $('#quest-title').textContent=state.deliveries?'云边的日常':'第一份晚餐';$('#quest-text').textContent=state.inventory>=3?'带着收获穿过石桥，送到云边咖啡。':'播种 → 浇水 → 收获，给云边咖啡准备 3 份蔬菜。';
  $('#quest-count').textContent=`${Math.min(state.inventory,3)} / 3`;$('#quest-progress').style.width=`${Math.min(state.inventory/3,1)*100}%`;$('#delivered').textContent=state.deliveries?`已完成 ${state.deliveries} 份订单`:'每份订单 · 30 金币';
  meta.plots.forEach((p,i)=>{
    const plot=state.plots[i],status=plotStatus(plot,now),seconds=Math.max(0,Math.ceil((GROW_MS-(now-plot.wateredAt))/1000)),title={empty:'播种',planted:'待浇水',growing:`${seconds}s`,ready:'可收获'}[status];
    markers[i].button.textContent=`${p.name} · ${title}`;markers[i].button.setAttribute('aria-label',`${p.name} · ${title}`);markers[i].button.classList.toggle('ready',status==='ready');
    const scale=status==='empty'?0:status==='planted'?.16:status==='ready'?1:.20+.70*Math.min(1,(now-plot.wateredAt)/GROW_MS);
    cropNodes[i].forEach(({o,scale:base})=>{o.visible=scale>0;o.scale.copy(base).multiplyScalar(Math.max(.01,scale));});
  });
  let title='',label='';
  if(context?.type==='plot'){const status=plotStatus(state.plots[context.index],now);title=meta.plots[context.index].name;label={empty:'播下种子',planted:'浇水',growing:'正在生长',ready:'收获蔬菜'}[status];}
  else if(context?.type==='cafe'){title='云边咖啡';label=state.inventory>=3?'交付蔬菜 · +30 金币':`还需要 ${3-state.inventory} 份蔬菜`;}
  else if(context?.type==='cat'){title='一只亲人的小猫';label='摸摸小猫';}
  $('#interaction').hidden=!context||paused;$('#interaction-title').textContent=title;$('#interaction-action').textContent=avatar?.busy?'正在照料菜田…':label;$('#interact').disabled=avatar?.busy||(context?.type==='plot'&&plotStatus(state.plots[context.index],now)==='growing');
}
function labels(){for(const item of markers){scratch.copy(item.position).project(camera);const visible=playing&&scratch.z<1&&scratch.z>-1&&Math.abs(scratch.x)<1.1&&Math.abs(scratch.y)<1.1;item.button.hidden=!visible;if(visible)item.button.style.transform=`translate(-50%,-100%) translate(${(scratch.x*.5+.5)*innerWidth}px,${(-scratch.y*.5+.5)*innerHeight}px)`;}}

async function init(){
  try{
    const response=await fetch('../assets/waterside/scene.json');if(!response.ok)throw new Error('场景配置未找到');meta=await response.json();
    const gltf=await new Promise((resolve,reject)=>new GLTFLoader().load('../assets/waterside/island_waterside.glb',resolve,xhr=>{$('#progress').style.width=`${xhr.total?100*xhr.loaded/xhr.total:45}%`;},reject));model=gltf.scene;
    model.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;for(const m of Array.isArray(o.material)?o.material:[o.material])if(m.transparent){m.depthWrite=false;o.castShadow=false;}}});
    scene.add(model);model.updateMatrixWorld(true);const previousPlayer=model.getObjectByName('player');if(!previousPlayer)throw new Error('人物节点缺失');previousPlayer.visible=false;
    $('#error').textContent='正在为雏菊整理草帽与裙摆…';avatar=await loadCharacter({scale:1.35});player=new THREE.Group();player.name='player_controller';player.add(avatar.root);scene.add(player);nav=makeNavigation(meta);
    try{state=restoreGame(localStorage.getItem(SAVE_KEY));}catch{state=newGame();}migrateReferenceLayout(state,nav,[meta.spawn[0],-meta.spawn[1]]);const spawn=state.position||[meta.spawn[0],-meta.spawn[1]];placePlayer(...spawn);
    meta.plots.forEach((p,i)=>{cropNodes[i]=p.cropNodes.map(name=>{const o=model.getObjectByName(name);if(!o)throw new Error(`作物节点缺失: ${name}`);return{o,scale:o.scale.clone()};});marker(p.name,new THREE.Vector3(p.position[0],p.position[2]+1.3,-p.position[1]),[p.approach[0],-p.approach[1]]);});
    cafeTarget=meta.cafeApproach;marker('云边咖啡 · 交付订单',new THREE.Vector3(cafeTarget[0],13,cafeTarget[1]-2),cafeTarget);
    for(const id of['orchard','overlook']){const site=meta.lifeSites.find(s=>s.id===id);marker(site.label,new THREE.Vector3(site.position[0],nav.height(...site.position)+1.5,site.position[1]),site.position);}
    pickTargets.push(model.getObjectByName('island_scenery'));environment=createEnvironment(scene,model,meta);
    $('#error').textContent='正在铺开云海，点亮远处的小岛…';world=await createWorld({scene,model,camera,renderer,sun,fill,hemisphere,meta,nav,environment});world.setQuality($('#quality').value==='low');
    resident=createResident({nav,sites:meta.lifeSites});$('#resident-life').hidden=false;$('#follow-resident').disabled=false;
    $('#world-toggle').disabled=false;$('#play').disabled=false;$('#loading').classList.add('hide');$('#loading').setAttribute('aria-hidden','true');$('#stats').textContent='花园与弯溪 · 自在生活';updateUI();save();
    if(matchMedia('(prefers-reduced-motion: reduce)').matches){paused=true;$('#pause').textContent='继续风景';$('#pause').setAttribute('aria-pressed','true');}
    window.dispatchEvent(new Event('island-ready'));
  }catch(err){console.error(err);$('#error').textContent=`载入失败：${err.message||'模型无法读取'}。请通过项目的本地服务器打开。`;$('#retry').hidden=false;}
}
$('#retry').addEventListener('click',()=>location.reload());
function frame(now){
  requestAnimationFrame(frame);const realDt=Math.max(0,(now-last)/1000),dt=Math.min(realDt,.05);last=now;if(document.hidden)return;
  if(model&&environment){
    const active=!paused&&!document.querySelector('dialog[open]');
    if(active){elapsed+=dt;movePlayer(dt);moveResident(dt);avatar.update(dt);const cat=model.getObjectByName('garden_cat');if(cat)cat.rotation.z=elapsed<petUntil?Math.sin(elapsed*9)*.08:0;}
    controls.update();world?.update(Math.min(realDt,60),elapsed,active);environment.update(elapsed,camera);labels();uiTimer+=dt;fpsTime+=dt;frames++;
    if(uiTimer>.15){updateUI();uiTimer=0;}if(fpsTime>2){$('#status').textContent=paused?'风景已暂停':`${Math.round(frames/fpsTime)} FPS`;if(saveDirty)save();fpsTime=0;frames=0;}
  }else controls.update();if(world)world.render();else renderer.render(scene,camera);
}
requestAnimationFrame(frame);init();
