import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { WORLD_KEY, WEATHER, newWorld, restoreWorld, advanceWorld, daylight, timeLabel, periodLabel, blendWeather, smooth } from './world-state.mjs';

const noiseGLSL=`
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float noise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x),f.y);}
float fbm(vec2 p){float a=.5,v=0.;for(int i=0;i<4;i++){v+=a*noise(p);p=mat2(1.6,-1.2,1.2,1.6)*p+3.1;a*=.5;}return v;}
`;
function random(seed){return()=>{seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;};}
const color=c=>new THREE.Color(c);
const skyKeys=[
  [0,'#111c39','#526486','#879bb7','#374765'],
  [4.5,'#1a284b','#70738e','#a6a1b9','#5b6383'],
  [6,'#889abf','#f5c7ae','#fff1d9','#a8a5bd'],
  [8,'#82b5d7','#dfebeb','#fff9eb','#aabed0'],
  [12,'#74b2de','#deedf1','#fffbed','#a4bed3'],
  [16.5,'#83b0d1','#f1dec4','#fff0d4','#acb5c4'],
  [18,'#7c84b5','#f5ba97','#ffe0bd','#a59ab9'],
  [19.5,'#303d68','#a38da3','#b8b2c9','#606684'],
  [21,'#142341','#596c8d','#8e9fbc','#3b4e6c'],
  [24,'#111c39','#526486','#879bb7','#374765'],
].map(([h,...c])=>[h,...c.map(color)]);
function palette(hour){
  let a=skyKeys[0],b=skyKeys[1];
  for(let i=1;i<skyKeys.length;i++)if(hour<skyKeys[i][0]){a=skyKeys[i-1];b=skyKeys[i];break;}
  const t=smooth(a[0],b[0],hour);return a.slice(1).map((c,i)=>c.clone().lerp(b[i+1],t));
}

function createSky(){
  const uniforms={uTop:{value:color('#7fb8dc')},uHorizon:{value:color('#e0eced')},uCloud:{value:color('#fff8ea')},uShade:{value:color('#aabed0')},uNight:{value:0},uCoverage:{value:.25},uTime:{value:0},uAspect:{value:1},uRotation:{value:new THREE.Matrix3()},uSun:{value:new THREE.Vector3(1,1,0).normalize()}};
  const material=new THREE.ShaderMaterial({depthTest:false,depthWrite:false,uniforms,
    vertexShader:'varying vec2 vUv;void main(){vUv=uv;gl_Position=vec4(position.xy,1.0,1.0);}',
    fragmentShader:`varying vec2 vUv;uniform vec3 uTop,uHorizon,uCloud,uShade,uSun;uniform float uNight,uCoverage,uTime,uAspect;uniform mat3 uRotation;${noiseGLSL}
    void main(){
      vec2 p=vUv*2.-1.;vec3 ray=normalize(uRotation*vec3(p.x*uAspect*.65,p.y*.65,-1.));
      float altitude=smoothstep(0.,1.,vUv.y);
      vec3 result=mix(uHorizon,uTop,altitude*.88);
      vec2 sky=vec2(atan(ray.z,ray.x)*2.4,ray.y*4.5);
      vec2 drift=vec2(uTime*.004,0.);
      float field=fbm(sky*1.45+drift);
      float billow=fbm(sky*3.8-drift*.35);
      float clouds=smoothstep(.59-uCoverage*.16,.77-uCoverage*.19,field+billow*.14);
      float detail=fbm(sky*5.+drift);
      result=mix(result,mix(uShade,uCloud,smoothstep(.23,.68,detail+vUv.y*.17)),clouds*(.7+uCoverage*.28));
      float sunDot=max(0.,dot(ray,uSun));
      result+=vec3(1.,.75,.43)*pow(sunDot,16.)*.12*(1.-uNight)*(1.-clouds);
      result+=vec3(1.,.90,.64)*smoothstep(.9994,.99985,sunDot)*(1.-uNight)*(1.-clouds)*2.;
      vec3 moon=-uSun;float moonDot=max(0.,dot(ray,moon));
      result+=vec3(.7,.81,1.)*pow(moonDot,22.)*.05*uNight;
      result+=vec3(.76,.85,1.)*smoothstep(.9990,.9995,moonDot)*uNight*(1.-clouds);
      vec2 starUV=vec2(atan(ray.z,ray.x)*31.,asin(clamp(ray.y,-1.,1.))*31.);vec2 cell=floor(starUV);
      vec2 spot=fract(starUV)-vec2(.2+.6*hash(cell),.2+.6*hash(cell+17.));
      float star=(1.-smoothstep(.005,.055,length(spot)))*step(.91,hash(cell+3.1));
      result+=vec3(.8,.87,1.)*star*uNight*(1.-clouds)*(1.-uCoverage*.7)*(.55+.2*sin(uTime*.7+hash(cell)*40.));
      gl_FragColor=vec4(result,1.);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }`});
  const scene=new THREE.Scene();const quad=new THREE.Mesh(new THREE.PlaneGeometry(2,2),material);quad.frustumCulled=false;scene.add(quad);
  return{scene,camera:new THREE.Camera(),uniforms};
}

function createCloudSea(scene,texture){
  const rng=random(91826),count=42,geometry=new THREE.InstancedBufferGeometry();
  const plane=new THREE.PlaneGeometry(1,1);geometry.index=plane.index;geometry.attributes.position=plane.attributes.position;geometry.attributes.uv=plane.attributes.uv;
  const centers=[],spans=[],seeds=[];
  for(let i=0;i<count;i++){
    const a=i*2.399963,r=i<12?32+rng()*20:60+rng()*78;
    centers.push(Math.cos(a)*r,-14-rng()*13,Math.sin(a)*r);spans.push(23+rng()*28,8+rng()*9);seeds.push(rng()*100);
  }
  geometry.setAttribute('aCenter',new THREE.InstancedBufferAttribute(new Float32Array(centers),3));geometry.setAttribute('aSpan',new THREE.InstancedBufferAttribute(new Float32Array(spans),2));geometry.setAttribute('aSeed',new THREE.InstancedBufferAttribute(new Float32Array(seeds),1));geometry.instanceCount=count;
  const uniforms={uCloudMap:{value:texture},uRight:{value:new THREE.Vector3()},uUp:{value:new THREE.Vector3()},uTime:{value:0},uWind:{value:1},uColor:{value:color('#fff9ee')},uShade:{value:color('#bac8d6')},uFog:{value:color('#dce5eb')},uFogNear:{value:100},uFogFar:{value:230},uCoverage:{value:.25}};
  const material=new THREE.ShaderMaterial({uniforms,transparent:true,depthWrite:false,side:THREE.DoubleSide,
    vertexShader:`attribute vec3 aCenter;attribute vec2 aSpan;attribute float aSeed;uniform vec3 uRight,uUp;uniform float uTime,uWind;varying vec2 vUv;varying float vSeed,vDepth;
      void main(){vUv=uv;vSeed=aSeed;vec3 c=aCenter;c.x+=sin(uTime*.008+aSeed)*2.5*uWind;c.z+=cos(uTime*.005+aSeed)*1.8;
      vec3 world=c+uRight*position.x*aSpan.x+uUp*position.y*aSpan.y;
      vec4 mv=viewMatrix*vec4(world,1.);vDepth=-mv.z;gl_Position=projectionMatrix*mv;}`,
    fragmentShader:`varying vec2 vUv;varying float vSeed,vDepth;uniform sampler2D uCloudMap;uniform vec3 uColor,uShade,uFog;uniform float uFogNear,uFogFar,uCoverage;
      void main(){vec2 uv=vUv;if(mod(vSeed,2.)>1.)uv.x=1.-uv.x;vec4 cloud=texture2D(uCloudMap,uv);
        float edge=smoothstep(0.,.05,min(min(vUv.x,1.-vUv.x),min(vUv.y,1.-vUv.y)));
        float alpha=cloud.a*(.90+uCoverage*.1)*edge;
        if(alpha<.005)discard;
        float light=clamp(cloud.r*.92+.08,0.,1.);
        vec3 c=mix(uShade,uColor,light);c=mix(c,uFog,smoothstep(uFogNear,uFogFar,vDepth)*.62);
        gl_FragColor=vec4(c,alpha);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`});
  const clouds=new THREE.Mesh(geometry,material);clouds.name='world_cloud_sea';clouds.frustumCulled=false;clouds.renderOrder=3;scene.add(clouds);
  return{uniforms,setQuality:low=>geometry.instanceCount=low?26:count};
}

function createRain(scene,meta,nav){
  const rng=random(9180918),count=850,data=new Float32Array(count*6),drops=[];
  const scale=meta.terrainScale||[1,1];
  for(let i=0;i<count;i++){
    const x=(rng()-.5)*(meta.terrain?meta.terrain.radius[0]*2:49*scale[0]),z=(rng()-.5)*(meta.terrain?meta.terrain.radius[1]*2:32*scale[1]);let floor=nav.canWalk(x,z)?nav.height(x,z):5;
    for(const box of[meta.house,meta.cafe])if(x>box[0][0]-.4&&x<box[1][0]+.4&&-z>box[0][1]-.4&&-z<box[1][1]+.4)floor=box[1][2]+.25;
    for(const shelter of meta.shelters||[])if(Math.abs(x-shelter.position[0])<shelter.halfSize[0]&&Math.abs(z-shelter.position[1])<shelter.halfSize[1])floor=shelter.roofHeight;
    drops.push({x,z,floor,phase:rng(),length:.35+rng()*.5});
  }
  const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(data,3).setUsage(THREE.DynamicDrawUsage));
  const material=new THREE.LineBasicMaterial({color:'#c7dfeb',transparent:true,opacity:0,depthWrite:false});
  const rain=new THREE.LineSegments(geometry,material);rain.name='world_rain';rain.frustumCulled=false;scene.add(rain);let limit=count;
  return{
    setQuality(low){limit=low?340:count;geometry.setDrawRange(0,limit*2);},
    update(t,amount,wind,day){rain.visible=amount>.015;if(!rain.visible)return;material.opacity=amount*(.43+day*.24);
      for(let i=0;i<limit;i++){const d=drops[i],q=(d.phase+t*.56)%1,top=32,y=d.floor+(top-d.floor)*(1-q),x=d.x+q*.7*wind;data.set([x,y,d.z,x+.025*wind,Math.max(d.floor,y-d.length),d.z],i*6);}
      geometry.attributes.position.needsUpdate=true;
    }
  };
}

export async function createWorld({scene,model,camera,renderer,sun,fill,hemisphere,meta,nav,environment}){
  let state;try{state=restoreWorld(localStorage.getItem(WORLD_KEY));}catch{state=newWorld();}
  const weather={...WEATHER[state.weather]},sky=createSky(),rain=createRain(scene,meta,nav);
  const [archipelago,cloudMap]=await Promise.all([new GLTFLoader().loadAsync('../assets/world/distant_islands.glb'),new THREE.TextureLoader().loadAsync('../assets/world/cloud_bank.png')]);
  cloudMap.colorSpace=THREE.SRGBColorSpace;cloudMap.anisotropy=Math.min(4,renderer.capabilities.getMaxAnisotropy());
  const clouds=createCloudSea(scene,cloudMap),distant=archipelago.scene;distant.name='distant_archipelago';scene.add(distant);
  distant.children.forEach(o=>o.scale.multiplyScalar(.53));
  const timeUniform={value:0};distant.traverse(o=>{if(!o.isMesh)return;o.castShadow=false;o.receiveShadow=false;
    const mats=Array.isArray(o.material)?o.material:[o.material];
    for(const m of mats)if(m.name==='far_water'&&!m.userData.flow){
      m.userData.flow=true;m.side=THREE.DoubleSide;m.roughness=.28;
      m.onBeforeCompile=shader=>{shader.uniforms.uWorldTime=timeUniform;shader.vertexShader='varying vec3 vFarPosition;\n'+shader.vertexShader;shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\nvFarPosition=(modelMatrix*vec4(transformed,1.)).xyz;');shader.fragmentShader='uniform float uWorldTime;varying vec3 vFarPosition;\n'+shader.fragmentShader;shader.fragmentShader=shader.fragmentShader.replace('#include <color_fragment>','#include <color_fragment>\ndiffuseColor.rgb*=.85+.15*sin(vFarPosition.y*4.+uWorldTime*3.);');};
      m.customProgramCacheKey=()=> 'far-water-v1';
    }
  });
  // Orthographic projection does not make distant objects smaller or hazier.
  // The authored scale and aerial tint keep the surrounding islands subordinate.
  const hazeColor={value:color('#dce5eb')},hazeTop={value:color('#83b4d6')},hazeHeight={value:innerHeight*renderer.getPixelRatio()},hazeAmount={value:.38},farMaterials=new Set();
  distant.traverse(o=>{if(!o.isMesh)return;for(const m of Array.isArray(o.material)?o.material:[o.material])if(!farMaterials.has(m)){
    farMaterials.add(m);m.fog=false;const compile=m.onBeforeCompile.bind(m),key=m.customProgramCacheKey();
    m.onBeforeCompile=(shader,r)=>{compile(shader,r);shader.uniforms.uFarHazeColor=hazeColor;shader.uniforms.uFarHazeTop=hazeTop;shader.uniforms.uFarHazeHeight=hazeHeight;shader.uniforms.uFarHazeAmount=hazeAmount;shader.fragmentShader='uniform vec3 uFarHazeColor,uFarHazeTop;uniform float uFarHazeAmount,uFarHazeHeight;\n'+shader.fragmentShader;shader.fragmentShader=shader.fragmentShader.replace('#include <opaque_fragment>','#include <opaque_fragment>\nvec3 distantSky=mix(uFarHazeColor,uFarHazeTop,smoothstep(0.,uFarHazeHeight,gl_FragCoord.y)*.88);\ngl_FragColor.rgb=mix(gl_FragColor.rgb,distantSky,min(.94,uFarHazeAmount+smoothstep(70.,210.,length(vViewPosition))*.26));');};
    m.customProgramCacheKey=()=>key+'-aerial-v2';
  }});
  const wetMaterials=new Map(),glow=new Set();
  model.traverse(o=>{if(!o.isMesh)return;for(const m of Array.isArray(o.material)?o.material:[o.material]){if(/^(rock|wood|roof|soil)/.test(m.name)&&!wetMaterials.has(m))wetMaterials.set(m,m.roughness);if(m.name.startsWith('glow'))glow.add(m);}});
  distant.traverse(o=>{if(o.isMesh)for(const m of Array.isArray(o.material)?o.material:[o.material])if(m.name==='far_window'){m.emissive.set('#f6bd74');glow.add(m);}});
  const lamps=[];
  for(const position of meta.lampPositions||[[-8,13,1],[16.5,13,5.5],[-16,12.4,7],[1,12.2,8]]){const lamp=new THREE.PointLight('#ffcb84',0,9,2);lamp.position.set(position[0]*(meta.terrainScale?.[0]||1),position[1],position[2]*(meta.terrainScale?.[1]||1));scene.add(lamp);lamps.push(lamp);}
  scene.fog=new THREE.Fog('#deedf1',100,250);
  const moon=new THREE.DirectionalLight('#a7c1ee',0);scene.add(moon);moon.target=sun.target;
  const direction=new THREE.Vector3(),warmColor=color('#ffc48c'),dayColor=color('#fff1d2');
  const gray=color('#98acba');let uiElapsed=1,saveElapsed=0,low=false;
  const $=s=>document.querySelector(s),slider=$('#world-time'),panel=$('#world-panel'),toggle=$('#world-toggle');
  function save(){try{localStorage.setItem(WORLD_KEY,JSON.stringify(state));}catch{/* Gameplay remains usable if storage is disabled. */}}
  function sync(){
    $('#world-clock').textContent=timeLabel(state.hour);$('#world-period').textContent=periodLabel(state.hour);$('#world-day').textContent=`第 ${state.day} 天`;
    $('#world-weather-label').textContent=WEATHER[state.weather].label;
    $('#world-time-output').textContent=timeLabel(state.hour);if(document.activeElement!==slider)slider.value=String(Math.round(state.hour*60));
    slider.setAttribute('aria-valuetext',`${periodLabel(state.hour)} ${timeLabel(state.hour)}`);
    $('#world-time-running').textContent=state.running?'暂停时间':'继续时间';$('#world-time-running').setAttribute('aria-pressed',String(!state.running));$('#world-speed').value=String(state.speed);
    document.querySelectorAll('[data-weather]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.weather===state.weather)));
    document.querySelectorAll('[data-hour]').forEach(b=>b.setAttribute('aria-pressed',String(Math.abs(state.hour-Number(b.dataset.hour))<.15)));
    document.body.dataset.period=periodLabel(state.hour);document.body.dataset.weather=state.weather;document.body.classList.toggle('world-night',daylight(state.hour).night>.4);
  }
  function selectHour(hour){state.hour=hour;state.running=false;sync();save();}
  toggle.addEventListener('click',()=>{panel.hidden=!panel.hidden;toggle.setAttribute('aria-expanded',String(!panel.hidden));});
  $('#world-close').addEventListener('click',()=>{panel.hidden=true;toggle.setAttribute('aria-expanded','false');toggle.focus();});
  addEventListener('keydown',e=>{if(e.code==='Escape'&&!panel.hidden){panel.hidden=true;toggle.setAttribute('aria-expanded','false');}});
  slider.addEventListener('input',()=>selectHour(Number(slider.value)/60));
  document.querySelectorAll('[data-hour]').forEach(b=>b.addEventListener('click',()=>selectHour(Number(b.dataset.hour))));
  document.querySelectorAll('[data-weather]').forEach(b=>b.addEventListener('click',()=>{state.weather=b.dataset.weather;sync();save();}));
  $('#world-time-running').addEventListener('click',()=>{state.running=!state.running;sync();save();});
  $('#world-speed').addEventListener('change',e=>{state.speed=Number(e.target.value);save();});
  addEventListener('pagehide',save);sync();
  const api={
    snapshot(){return{hour:state.hour,weather:state.weather,day:state.day};},
    setQuality(value){low=value;clouds.setQuality(low);rain.setQuality(low);distant.children.forEach((o,i)=>o.visible=!low||i<8);},
    update(dt,t,active=true){
      if(active)advanceWorld(state,dt);
      // Manual time/weather selection still updates the picture while scenery is paused.
      blendWeather(weather,WEATHER[state.weather],dt);const light=daylight(state.hour),[top,horizon,cloud,shade]=palette(state.hour);
      const storm=weather.cloud*.24+weather.rain*.25;
      gray.copy(horizon).lerp(shade,.55);top.lerp(gray,storm).multiplyScalar(1-light.night*.08);horizon.lerp(shade,storm*.55);
      cloud.lerp(shade,weather.rain*.50);shade.lerp(horizon,weather.mist*.22);
      const a=(state.hour-6)/12*Math.PI;direction.set(Math.cos(a)*.86,Math.sin(a),Math.sin(a)*.28).normalize();
      sky.uniforms.uSun.value.copy(direction);sky.uniforms.uNight.value=light.night;sky.uniforms.uTop.value.copy(top);sky.uniforms.uHorizon.value.copy(horizon);sky.uniforms.uCloud.value.copy(cloud);sky.uniforms.uShade.value.copy(shade);sky.uniforms.uCoverage.value=weather.cloud;sky.uniforms.uTime.value=t;sky.uniforms.uAspect.value=innerWidth/innerHeight;camera.updateMatrixWorld();sky.uniforms.uRotation.value.setFromMatrix4(camera.matrixWorld);
      sun.position.copy(direction).multiplyScalar(62).add(sun.target.position);sun.color.copy(dayColor).lerp(warmColor,light.warm);
      sun.intensity=smooth(-.03,.10,light.elevation)*(.12+Math.max(0,light.elevation)*3.05)*(1-weather.cloud*.35-weather.rain*.32);
      moon.position.copy(direction).multiplyScalar(-62).add(sun.target.position);moon.intensity=light.night*.85*(1-weather.rain*.25);
      sun.shadow.radius=weather.cloud> .5?3:1.7;
      hemisphere.color.copy(horizon).lerp(color('#e1eaf1'),light.day*.50);hemisphere.groundColor.copy(color('#929579')).lerp(color('#596583'),light.night);hemisphere.intensity=(.85+light.day*1.15)*(1-weather.rain*.15);
      fill.color.copy(shade);fill.intensity=.32+light.day*.4;renderer.toneMappingExposure=1.12+light.night*.08;
      const fogNear=100-weather.mist*25-weather.rain*12,fogFar=270-weather.mist*110-weather.rain*38;
      scene.fog.color.copy(horizon);scene.fog.near=fogNear;scene.fog.far=fogFar;
      hazeColor.value.copy(horizon);hazeTop.value.copy(top);hazeHeight.value=innerHeight*renderer.getPixelRatio();hazeAmount.value=.39+weather.mist*.33+weather.rain*.11;
      const u=clouds.uniforms;u.uRight.value.setFromMatrixColumn(camera.matrixWorld,0);u.uUp.value.setFromMatrixColumn(camera.matrixWorld,1);u.uTime.value=t;u.uWind.value=weather.wind;u.uColor.value.copy(cloud);u.uShade.value.copy(shade);u.uFog.value.copy(horizon);u.uFogNear.value=fogNear;u.uFogFar.value=fogFar;u.uCoverage.value=weather.cloud;
      for(const [m,roughness] of wetMaterials)m.roughness=THREE.MathUtils.lerp(roughness,Math.max(.28,roughness*.56),weather.rain);
      for(const m of glow)m.emissiveIntensity=.07+light.night*2.25;
      for(const lamp of lamps)lamp.intensity=light.night*(low?9:15);
      environment.setAtmosphere({night:light.night,wind:weather.wind,rain:weather.rain});rain.update(t,weather.rain,weather.wind,light.day);timeUniform.value=t;
      uiElapsed+=dt;saveElapsed+=dt;if(uiElapsed>.3){sync();uiElapsed=0;}if(saveElapsed>10){save();saveElapsed=0;}
    },
    render(){renderer.autoClear=false;renderer.clear();renderer.render(sky.scene,sky.camera);renderer.clearDepth();renderer.render(scene,camera);},
  };
  api.update(0,0,false);return api;
}
