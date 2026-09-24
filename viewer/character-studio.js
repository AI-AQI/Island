import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { loadCharacter, CHARACTER_VARIANTS } from './character.js';

const canvas=document.querySelector('canvas'),stage=document.querySelector('.stage'),status=document.querySelector('#load-status');
const requestedVariant=new URLSearchParams(location.search).get('model'),variant=Object.hasOwn(CHARACTER_VARIANTS,requestedVariant)?requestedVariant:'tripo';
document.querySelectorAll('[data-model]').forEach(a=>{if(a.dataset.model===variant)a.setAttribute('aria-current','page');});
document.querySelector('#version-description').textContent=variant==='tripo'?'依据参考图生成精细造型，在本地 Blender 调整骨骼、裙摆和发束权重，并接入小岛动作。':'保留的本地 Blender 初版，用于比较造型和材质的变化。';
const renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.75));renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;
renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFShadowMap;
const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(30,1,.01,50);
const controls=new OrbitControls(camera,canvas);controls.enableDamping=true;controls.minDistance=.45;controls.maxDistance=7;controls.maxPolarAngle=Math.PI*.54;controls.target.set(0,.95,0);
scene.add(new THREE.HemisphereLight('#fff2dd','#9e9178',2.4));
for(const [color,intensity,pos] of [['#ffe7c7',3,[-3,5,4]],['#d4e0ff',1,[3,2,2]],['#ffe1b0',2,[1,4,-3]]]){
  const light=new THREE.DirectionalLight(color,intensity);light.position.set(...pos);scene.add(light);
  if(intensity===3){light.castShadow=true;light.shadow.mapSize.set(2048,2048);Object.assign(light.shadow.camera,{left:-1.5,right:1.5,top:2.5,bottom:-.5,near:.1,far:12});light.shadow.normalBias=.008;light.shadow.bias=-.0001;}
}
const ground=new THREE.Mesh(new THREE.PlaneGeometry(200,200),new THREE.ShadowMaterial({opacity:.14}));ground.rotation.x=-Math.PI/2;ground.position.y=.002;ground.receiveShadow=true;scene.add(ground);
let avatar,paused=matchMedia('(prefers-reduced-motion: reduce)').matches,speed=1,last=performance.now(),view='full';
const captions={Idle:'轻轻呼吸',Walk:'沿着小路，去看看菜园',Plant:'种下明天的小期待',Water:'给小小的愿望浇水',Harvest:'把今天的收获带回家'};
function cameraView(name){view=name;const aspect=stage.clientWidth/stage.clientHeight,extra=Math.max(1,.65/aspect);
  controls.target.set(0,name==='face'?1.55:.95,0);camera.position.set(...(name==='face'?[.05,1.57,1.02*extra]:name==='back'?[-.55,1.55,-4.1*extra]:[.7,1.65,4.1*extra]));controls.update();
  document.querySelectorAll('[data-camera]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.camera===name)));
}
new ResizeObserver(()=>{renderer.setSize(stage.clientWidth,stage.clientHeight,false);camera.aspect=stage.clientWidth/stage.clientHeight;camera.updateProjectionMatrix();cameraView(view);}).observe(stage);
document.querySelectorAll('[data-camera]').forEach(b=>b.addEventListener('click',()=>cameraView(b.dataset.camera)));
document.querySelectorAll('[data-clip]').forEach(b=>b.addEventListener('click',()=>{if(!avatar)return;avatar.preview(b.dataset.clip);document.querySelectorAll('[data-clip]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));document.querySelector('#current-pose').textContent=captions[b.dataset.clip];}));
function pauseUI(){const b=document.querySelector('#pause-character');b.textContent=paused?'继续动作':'暂停动作';b.setAttribute('aria-pressed',String(paused));}
document.querySelector('#pause-character').addEventListener('click',()=>{paused=!paused;pauseUI();});pauseUI();
document.querySelector('#speed').addEventListener('change',e=>speed=Number(e.target.value));
document.addEventListener('visibilitychange',()=>last=performance.now());
try{avatar=await loadCharacter({variant});scene.add(avatar.root);status.hidden=true;document.body.dataset.ready='true';document.body.dataset.model=variant;}catch(e){console.error(e);status.textContent=`人物未能载入：${e.message}。请通过本地服务器打开。`;status.classList.add('error');}
function frame(now){requestAnimationFrame(frame);const dt=Math.min((now-last)/1000,.05);last=now;if(document.hidden)return;if(avatar&&!paused)avatar.update(dt*speed);controls.update();renderer.render(scene,camera);}requestAnimationFrame(frame);
