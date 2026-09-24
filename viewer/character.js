import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

export const CHARACTER_VARIANTS={tripo:'../assets/character_tripo/runtime/daisy_tripo.glb',local:'../assets/character/daisy_character.glb'};

/** Reviewed Tripo model and the preserved local first draft share one controller. */
export async function loadCharacter({scale=1,onProgress,variant='tripo'}={}) {
  if(!Object.hasOwn(CHARACTER_VARIANTS,variant))throw new Error('未知的人物版本');
  const gltf=await new GLTFLoader().loadAsync(CHARACTER_VARIANTS[variant],onProgress);
  const root=gltf.scene;root.name='DaisyCharacter';root.scale.setScalar(scale);
  const mixer=new THREE.AnimationMixer(root),actions=new Map();
  for(const clip of gltf.animations)actions.set(clip.name,mixer.clipAction(clip));
  for(const name of ['Idle','Walk','Plant','Water','Harvest'])if(!actions.has(name))throw new Error(`角色缺少 ${name} 动作`);
  const can=root.getObjectByName('Watering_Can');
  if(!can)throw new Error('角色浇水壶缺失');
  root.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;o.frustumCulled=false;}});
  let current=null,gesture=null,moving=false,walkRate=1;
  function transition(name,once=false,restart=false){
    const next=actions.get(name);if(!next||next===current&&!restart)return;
    next.reset().setEffectiveWeight(1).setEffectiveTimeScale(name==='Walk'?walkRate:1);
    next.setLoop(once?THREE.LoopOnce:THREE.LoopRepeat,once?1:Infinity);next.clampWhenFinished=once;next.play();
    if(current&&current!==next){current.fadeOut(.20);next.fadeIn(.20);}
    current=next;can.visible=name==='Water';
  }
  mixer.addEventListener('finished',e=>{if(e.action===gesture){gesture=null;transition(moving?'Walk':'Idle');}});
  transition('Idle');mixer.update(0);
  return {
    root,mixer,clips:gltf.animations,
    get busy(){return !!gesture;},get clip(){return current?.getClip().name;},
    setMoving(value,rate=1.25){moving=!!value;walkRate=rate;if(!gesture)transition(moving?'Walk':'Idle');if(current===actions.get('Walk'))current.setEffectiveTimeScale(rate);},
    act(name){if(gesture||!actions.has(name))return false;moving=false;transition(name,true,true);gesture=current;return true;},
    cancel(){gesture=null;moving=false;transition('Idle',false,true);},
    preview(name){gesture=null;moving=name==='Walk';transition(name,false,true);},
    update(dt){mixer.update(dt);},
  };
}
