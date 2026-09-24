import * as THREE from 'three';
import { bend, river } from './navigation.mjs';
import { makeTerrain } from './terrain.mjs';
import { createDetailedWater } from './water.js';

export function createEnvironment(scene, model, meta) {
  const [terrainX,terrainZ]=meta.terrainScale||[1,1];
  const terrain=meta.terrain?makeTerrain(meta.terrain):null;
  const clock={value:0},wind={value:1},atmosphere={night:0,wind:1,rain:0},windMaterials=new Set();
  model.traverse(o=>{
    if(!o.isMesh)return;
    for(const m of Array.isArray(o.material)?o.material:[o.material]){
      if(/^(leaf|grass|flower|lavender)/.test(m.name)&&!windMaterials.has(m)){
        windMaterials.add(m);
        m.onBeforeCompile=shader=>{
          shader.uniforms.uIslandTime=clock;
          shader.uniforms.uIslandWind=wind;
          shader.vertexShader='uniform float uIslandTime,uIslandWind;\n'+shader.vertexShader;
          shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>',`#include <begin_vertex>
            vec3 breezeWorld=(modelMatrix*vec4(transformed,1.0)).xyz;
            transformed.x+=sin(uIslandTime*1.4+breezeWorld.x*.65+breezeWorld.z*.45)*.045*uIslandWind;
            transformed.z+=cos(uIslandTime*.9+breezeWorld.x)*.028*uIslandWind;`);
        };
        m.customProgramCacheKey=()=> 'living-wind-v2';
      }
    }
  });
  function movingWater(name,fall){
    model.getObjectByName(name)?.traverse(o=>{
      if(!o.isMesh)return;
      const curved=terrain&&!fall;
      if(curved){const positions=o.geometry.attributes.position,coords=new Float32Array(positions.count*2),p=new THREE.Vector3();o.updateWorldMatrix(true,false);
        for(let i=0;i<positions.count;i++){p.fromBufferAttribute(positions,i).applyMatrix4(o.matrixWorld);const r=terrain.riverAt(p.x,-p.z);coords[i*2]=((p.x-r.x)*r.nx+(-p.z-r.y)*r.ny)/r.width;coords[i*2+1]=r.t;}
        o.geometry.setAttribute('aRiverUV',new THREE.BufferAttribute(coords,2));}
      const vertexWater=fall&&!!o.geometry.attributes.color;
      const mat=new THREE.MeshStandardMaterial({color:vertexWater?'#ffffff':fall?'#85cad4':'#4fadb5',roughness:.24,metalness:.1,side:THREE.DoubleSide,transparent:fall,depthWrite:!fall,vertexColors:vertexWater});
      mat.onBeforeCompile=shader=>{
        shader.uniforms.uIslandTime=clock;
        shader.vertexShader='varying vec3 vFlowWorld;\n'+shader.vertexShader;
        shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\nvFlowWorld=(modelMatrix*vec4(transformed,1.0)).xyz;');
        if(curved){shader.vertexShader='attribute vec2 aRiverUV;varying vec2 vRiverUV;\n'+shader.vertexShader;shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\nvRiverUV=aRiverUV;');shader.fragmentShader='varying vec2 vRiverUV;\n'+shader.fragmentShader;}
        shader.fragmentShader='uniform float uIslandTime; varying vec3 vFlowWorld;\n'+shader.fragmentShader;
        shader.fragmentShader=shader.fragmentShader.replace('#include <color_fragment>',`#include <color_fragment>
          float ripple=sin(${curved?'vRiverUV.y*210.0':`vFlowWorld.${fall?'y':'z'}*6.0`} ${fall?'+':'-'} uIslandTime*${fall?'6.0':'2.4'}+sin(${curved?'vRiverUV.x*7.0':'vFlowWorld.x*5.0'})*1.7);
          float ripple2=sin(${curved?'vRiverUV.x*13.0+vRiverUV.y*63.0':`vFlowWorld.x*9.0+vFlowWorld.${fall?'y':'z'}*2.0`} ${fall?'+':'-'} uIslandTime*3.0);
          float foam=pow(max(0.0,ripple*ripple2),9.0);
          diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.73,.95,.91),foam*.75);
          ${fall?`float strand=pow(.5+.5*sin(vFlowWorld.x*30.0+sin(vFlowWorld.y*2.0+uIslandTime*3.0)*.5),5.0);
          diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.81,.95,.93),strand*.75);
          diffuseColor.a*=smoothstep(-5.0,-1.0,vFlowWorld.y)*(.65+.35*strand);`:''}`);
      };
      mat.customProgramCacheKey=()=>fall?'living-fall-v2':curved?'curved-stream-v2':'living-stream-v1';
      o.material=mat;o.castShadow=false;
    });
  }
  const detailedWater=meta.waterRevision?createDetailedWater(model,terrain,meta,clock):null;
  if(!detailedWater){movingWater('stream_surface',false);movingWater('waterfall_ribbons',true);}
  const canvas=document.createElement('canvas');canvas.width=canvas.height=64;
  const ctx=canvas.getContext('2d'),gradient=ctx.createRadialGradient(32,32,0,32,32,32);
  gradient.addColorStop(0,'rgba(255,255,255,1)');gradient.addColorStop(.3,'rgba(255,255,255,.65)');gradient.addColorStop(1,'rgba(255,255,255,0)');
  ctx.fillStyle=gradient;ctx.fillRect(0,0,64,64);
  const texture=new THREE.CanvasTexture(canvas),groups=[];
  function particles(count,color,size,opacity,update,additive=false,landscape=false){
    const data=new Float32Array(count*3),geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(data,3));
    const material=new THREE.PointsMaterial({map:texture,color,size,transparent:true,opacity,depthWrite:false,blending:additive?THREE.AdditiveBlending:THREE.NormalBlending});
    const points=new THREE.Points(geometry,material);points.frustumCulled=false;scene.add(points);const sample=landscape?(i,t)=>{const p=update(i,t);return[p[0]*terrainX,p[1],p[2]*terrainZ];}:update;const group={data,geometry,count,update:sample,material,size,points};groups.push(group);return group;
  }
  const [sx,sy,sz]=meta.smokeOrigin;
  particles(32,'#e9d8ce',.95,.17,(i,t)=>{const q=(i/32+t*.075)%1;return[sx+q*1.4+Math.sin(i*5.3+t*.65)*q*.25,sz+q*3.4,-sy+Math.sin(i*2.7+t*.4)*q*.35];});
  const fx=river(-13.25)+bend(-13.25);
  if(terrain){
    const lip=meta.waterfallLip;
    function lipAt(u){const f=u*(lip.length-1),i=Math.min(lip.length-2,Math.floor(f)),a=lip[i],b=lip[i+1],q=f-i;return[a[0]+(b[0]-a[0])*q,a[1]+(b[1]-a[1])*q];}
    particles(300,'#dbfcf1',.09,.65,(i,t)=>{const q=(i*.618033+t*.30)%1,p=lipAt((Math.sin(i*17.3)+1)*.5);return[p[0]+Math.sin(i)*q*.25,10.05-q*15,-p[1]+1.55*(1-Math.exp(-q*7))+.4*q];});
    particles(55,'#edf5ee',1.1,.13,(i,t)=>{const q=(i/55+t*.1)%1,p=lipAt((Math.sin(i*11)+1)*.5);return[p[0]+Math.sin(i)*q,-3-q*2,-p[1]+1.7+q];});
    particles(meta.waterRevision?55:150,'#e0faf4',meta.waterRevision?.055:.085,meta.waterRevision?.36:.7,(i,t)=>{const r=terrain.along((i*.236067+t*.014)%1),u=Math.sin(i*16.9)*r.width*.68;return[r.x+r.nx*u,r.waterHeight+.045,-r.y-r.ny*u];});
  }else{
  particles(260,'#dbfcf1',.095,.65,(i,t)=>{const q=(i*.618033+t*.40)%1;return[fx+Math.sin(i*43.13)*1.95+Math.sin(t*1.8+i)*q*.2,10-q*10,13.23+1.7*(1-Math.exp(-q*8))+.32*q+Math.sin(i*8.7)*.3];},false,true);
  particles(50,'#edf5ee',1,.11,(i,t)=>{const q=(i/50+t*.1)%1;return[fx+Math.sin(i*17)*(.7+q*2),.5-q*1.6,15.3+Math.cos(i*14)*q*1.1];},false,true);
  particles(110,'#e0faf4',.085,.7,(i,t)=>{const y=12.3-((i*.236067+t*.052)%1)*25.4;return[river(y)+bend(y)+Math.sin(i*16.9)*1.38,10.075,-y];},false,true);
  }
  const fireflies=particles(55,'#ffe5a1',.10,.75,(i,t)=>[Math.sin(i*17.34)*(terrain?25:19)+Math.sin(t*.3+i)*.45,11.6+(Math.sin(i*3.76)+1)*1.5+Math.sin(t*.8+i)*.3,Math.cos(i*16.23)*(terrain?18:9)+Math.cos(t*.24+i)*.6],true,!terrain);
  const boat=model.getObjectByName('boat_hull'),ropes=[];
  if(boat)for(const side of[-1,1]){const rope=new THREE.Mesh(new THREE.CylinderGeometry(.021,.021,1,5),new THREE.MeshStandardMaterial({color:'#b4a17c',roughness:.9}));scene.add(rope);ropes.push({rope,side});}
  const up=new THREE.Vector3(0,1,0),bottom=new THREE.Vector3(),top=new THREE.Vector3(),delta=new THREE.Vector3();
  const sheep=['sheep_001','sheep_002','sheep_003'].map(n=>model.getObjectByName(n)).filter(Boolean).map(o=>({o,rotation:o.rotation.clone(),y:o.position.y}));
  function update(t,camera){
    clock.value=t;
    const pixelScale=innerHeight/(camera.top-camera.bottom)*camera.zoom;
    for(const g of groups){for(let i=0;i<g.count;i++)g.data.set(g.update(i,t),i*3);g.geometry.attributes.position.needsUpdate=true;g.material.size=g.size*pixelScale;}
    wind.value=atmosphere.wind;fireflies.material.opacity=atmosphere.night*.75*(1-atmosphere.rain*.85);fireflies.points.visible=fireflies.material.opacity>.01;
    if(boat){boat.rotation.z=Math.sin(t*.65)*.024;boat.updateMatrixWorld(true);for(const{rope,side}of ropes){top.copy(boat.position).add(new THREE.Vector3(side*1.3,0,0));bottom.set(side*1.3,-2.6,0).applyMatrix4(boat.matrixWorld);delta.subVectors(bottom,top);rope.position.copy(top).add(bottom).multiplyScalar(.5);rope.scale.y=delta.length();rope.quaternion.setFromUnitVectors(up,delta.normalize());}}
    sheep.forEach(({o,rotation,y},i)=>{o.rotation.y=rotation.y+Math.sin(t*.32+i*2)*.08;o.position.y=y+Math.max(0,Math.sin(t*.9+i))*.015;});
  }
  return{update,setAtmosphere:value=>{Object.assign(atmosphere,value);detailedWater?.setAtmosphere(value);}};
}
