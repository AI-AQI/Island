import * as THREE from 'three';

// Keep flow tied to the authored centerline: t alone would make the current
// speed change wherever the original spline samples are more tightly spaced.
export function createDetailedWater(model,terrain,meta,clock){
  const rain={value:0},distances=[0],points=meta.terrain.river;
  for(let i=1;i<points.length;i++)distances.push(distances.at(-1)+Math.hypot(points[i][0]-points[i-1][0],points[i][1]-points[i-1][1]));
  const noise=`
    float waterHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
    float waterNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);
      return mix(mix(waterHash(i),waterHash(i+vec2(1.,0.)),f.x),mix(waterHash(i+vec2(0.,1.)),waterHash(i+vec2(1.,1.)),f.x),f.y);}
  `;
  function stream(obj){
    const position=obj.geometry.attributes.position,flow=new Float32Array(position.count*4),world=new THREE.Vector3();obj.updateWorldMatrix(true,false);
    for(let i=0;i<position.count;i++){
      world.fromBufferAttribute(position,i).applyMatrix4(obj.matrixWorld);const r=terrain.riverAt(world.x,-world.z),f=r.t*(points.length-1),k=Math.min(points.length-2,Math.floor(f));
      const u=((world.x-r.x)*r.nx+(-world.z-r.y)*r.ny)/r.width,s=distances[k]+(distances[k+1]-distances[k])*(f-k);
      flow.set([u,s,r.ny,r.nx],i*4);
    }
    obj.geometry.setAttribute('aRiverFlow',new THREE.BufferAttribute(flow,4));
    const mat=new THREE.MeshStandardMaterial({name:'water_stream_runtime',color:'#ffffff',roughness:.27,metalness:.08,vertexColors:true,side:THREE.DoubleSide});
    mat.onBeforeCompile=shader=>{
      shader.uniforms.uWaterTime=clock;shader.uniforms.uWaterRain=rain;
      shader.vertexShader='attribute vec4 aRiverFlow; varying vec4 vRiverFlow; varying vec3 vWaterWorld;\n'+shader.vertexShader;
      shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\nvRiverFlow=aRiverFlow;vWaterWorld=(modelMatrix*vec4(transformed,1.)).xyz;');
      shader.fragmentShader='uniform float uWaterTime,uWaterRain; varying vec4 vRiverFlow; varying vec3 vWaterWorld;\n'+noise+shader.fragmentShader;
      shader.fragmentShader=shader.fragmentShader.replace('#include <color_fragment>',`#include <color_fragment>
        float u=vRiverFlow.x,s=vRiverFlow.y-uWaterTime*.72;
        float n=waterNoise(vec2(u*5.5,s*1.05));
        float contour=abs(sin(s*4.2+sin(u*8.0+s*.36)*1.8+n*2.0));
        float shimmer=pow(max(0.,1.-contour),7.)*smoothstep(.40,.75,n);
        float edge=pow(clamp(abs(u),0.,1.),4.0);
        diffuseColor.rgb*=.96+.10*n;
        diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.69,.86,.80),shimmer*(.24+edge*.13));
        float rainRings=pow(max(0.,sin(length(fract(vWaterWorld.xz*.8)-.5)*42.-uWaterTime*9.)),18.);
        diffuseColor.rgb+=rainRings*uWaterRain*.035;
      `);
      shader.fragmentShader=shader.fragmentShader.replace('#include <normal_fragment_begin>',`#include <normal_fragment_begin>
        float ws=vRiverFlow.y-uWaterTime*.72,wu=vRiverFlow.x;
        vec2 tangent=vRiverFlow.zw;
        float slope=sin(ws*4.2+sin(wu*8.+ws*.36)*1.8)*.043;
        vec2 wave=tangent*slope+vec2(-tangent.y,tangent.x)*sin(wu*19.+ws*1.3-uWaterTime)*.027;
        normal=normalize(normal+mat3(viewMatrix)*vec3(wave.x,0.,wave.y));
      `);
    };
    mat.customProgramCacheKey=()=> 'waterside-stream-v1';obj.material=mat;obj.castShadow=false;obj.receiveShadow=true;
  }
  function falling(obj){
    const mat=new THREE.MeshStandardMaterial({name:'waterfall_runtime',color:'#ffffff',roughness:.32,metalness:.02,vertexColors:true,transparent:true,depthWrite:false,side:THREE.DoubleSide});
    mat.onBeforeCompile=shader=>{
      shader.uniforms.uWaterTime=clock;shader.vertexShader='varying vec3 vWaterWorld;\n'+shader.vertexShader;
      shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>',`#include <begin_vertex>
        vWaterWorld=(modelMatrix*vec4(transformed,1.)).xyz;
        transformed.x+=sin(vWaterWorld.y*1.8+uWaterTime*3.2+vWaterWorld.x*4.)*.016*(1.-smoothstep(0.,10.,vWaterWorld.y));`);
      shader.vertexShader='uniform float uWaterTime;\n'+shader.vertexShader;
      shader.fragmentShader='uniform float uWaterTime;varying vec3 vWaterWorld;\n'+noise+shader.fragmentShader;
      shader.fragmentShader=shader.fragmentShader.replace('#include <color_fragment>',`#include <color_fragment>
        float wave=waterNoise(vec2(vWaterWorld.x*8.,vWaterWorld.y*1.1+uWaterTime*4.4));
        float streak=pow(.5+.5*sin(vWaterWorld.x*34.+wave*1.3),3.);
        diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.83,.94,.95),streak*.28);
        diffuseColor.a*=.86+.14*wave;
      `);
    };
    mat.customProgramCacheKey=()=> 'waterside-fall-v1';obj.material=mat;obj.castShadow=false;obj.receiveShadow=false;
  }
  function foam(obj){
    const mat=new THREE.MeshStandardMaterial({name:'river_foam_runtime',color:'#ffffff',roughness:.64,vertexColors:true,transparent:true,depthWrite:false,side:THREE.DoubleSide,polygonOffset:true,polygonOffsetFactor:-1});
    mat.onBeforeCompile=shader=>{
      shader.uniforms.uWaterTime=clock;shader.vertexShader='varying vec3 vFoamWorld;\n'+shader.vertexShader;
      shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\nvFoamWorld=(modelMatrix*vec4(transformed,1.)).xyz;');
      shader.fragmentShader='uniform float uWaterTime;varying vec3 vFoamWorld;\n'+shader.fragmentShader;
      shader.fragmentShader=shader.fragmentShader.replace('#include <color_fragment>','#include <color_fragment>\ndiffuseColor.a*=.64+.30*sin(vFoamWorld.x*2.3+vFoamWorld.z*3.-uWaterTime*1.7);');
    };
    mat.customProgramCacheKey=()=> 'waterside-foam-v1';obj.material=mat;obj.castShadow=false;obj.receiveShadow=true;
  }
  for(const [name,setup]of [['stream_surface',stream],['waterfall_ribbons',falling],['river_foam',foam],['waterfall_lip_foam',foam]])model.getObjectByName(name)?.traverse(obj=>{if(obj.isMesh)setup(obj);});
  return {setAtmosphere(value){rain.value=value.rain||0;}};
}
