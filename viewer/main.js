import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const canvas=document.querySelector('#scene');
const renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true,powerPreference:'high-performance'});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));
renderer.setSize(innerWidth,innerHeight);
renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure=1.15;
renderer.shadowMap.enabled=true;
renderer.shadowMap.type=THREE.PCFSoftShadowMap;
const scene=new THREE.Scene();
// glTF uses Y up. These camera positions are the exported Blender camera axes.
const camera=new THREE.PerspectiveCamera(36,innerWidth/innerHeight,.1,500);
const controls=new OrbitControls(camera,canvas);
controls.enableDamping=true;controls.dampingFactor=.075;
controls.minDistance=9;controls.maxDistance=160;controls.maxPolarAngle=Math.PI*.86;
const hemi=new THREE.HemisphereLight('#e8d9f6','#997e77',1.85);scene.add(hemi);
const sun=new THREE.DirectionalLight('#ffd9a0',3.4);sun.position.set(35,18,12);sun.target.position.set(0,8,0);scene.add(sun,sun.target);
sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);
Object.assign(sun.shadow.camera,{left:-36,right:36,top:31,bottom:-31,near:1,far:110});
sun.shadow.bias=-.00035;sun.shadow.normalBias=.045;
const fill=new THREE.DirectionalLight('#b8bddf',.75);fill.position.set(-25,30,10);scene.add(fill);
const views={hero:{p:[38.5,44,65],t:[0,8,0]},house:{p:[-22,25,19],t:[-8,13,-3]},cafe:{p:[34,24,22],t:[17,13,1]},top:{p:[0,83,.1],t:[0,6,0]}};
function view(name){const v=views[name];camera.position.set(...v.p);controls.target.set(...v.t);controls.update();document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===name));}
view('hero');
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>view(b.dataset.view)));
addEventListener('keydown',e=>{if(['1','2','3','4'].includes(e.key))view(Object.keys(views)[Number(e.key)-1]);});
addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);});
let loaded=false,last=performance.now(),frames=0,samples=[],triangles=0,bytes=0;
const loading=document.querySelector('#loading');
new GLTFLoader().load('../island_dusk.glb',gltf=>{
  gltf.scene.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;const materials=Array.isArray(o.material)?o.material:[o.material];materials.forEach(m=>{if(m.transparent){m.depthWrite=false;o.castShadow=false;}if(m.name.startsWith('glow'))m.emissiveIntensity=1.5;});triangles+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;}});
  scene.add(gltf.scene);loaded=true;loading.classList.add('hide');loading.setAttribute('aria-hidden','true');
  document.querySelector('#stats').textContent=`${Math.round(triangles).toLocaleString()} 三角面 · ${(bytes/1e6).toFixed(2)} MB`;
},xhr=>{bytes=xhr.total||xhr.loaded;document.querySelector('#progress').style.width=`${xhr.total?100*xhr.loaded/xhr.total:60}%`;},err=>{console.error(err);document.querySelector('#error').textContent='场景载入失败。请通过项目根目录的本地服务器打开 /viewer/，并确认 island_dusk.glb 已生成。';document.querySelector('#status').textContent='载入失败';});
function frame(now){requestAnimationFrame(frame);controls.update();renderer.render(scene,camera);if(loaded){frames++;if(now-last>1000){const fps=frames*1000/(now-last);samples.push(fps);if(samples.length>30)samples.shift();document.querySelector('#status').textContent=`${Math.round(fps)} FPS · ${renderer.info.render.calls} 次绘制`;frames=0;last=now;}}else last=now;}
requestAnimationFrame(frame);
