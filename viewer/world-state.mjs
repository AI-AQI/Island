// Time and weather are independent of crop saves and real-world growth timers.
export const WORLD_KEY='island-world-v1';
export const DAY_SECONDS=30*60;
export const WEATHER={
  clear:{label:'晴天',cloud:.25,mist:0,rain:0,wind:.65},
  cloudy:{label:'多云',cloud:.82,mist:.15,rain:0,wind:1.05},
  mist:{label:'薄雾',cloud:.58,mist:1,rain:0,wind:.35},
  rain:{label:'小雨',cloud:1,mist:.46,rain:1,wind:1.45},
};
export const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
export const wrapHour=h=>((h%24)+24)%24;
export const smooth=(a,b,x)=>{const t=clamp((x-a)/(b-a));return t*t*(3-2*t);};
export function newWorld(){return{version:1,hour:10,day:1,running:true,speed:1,weather:'clear'};}
export function restoreWorld(raw){
  try{
    const s=JSON.parse(raw);
    if(s?.version!==1||!Number.isFinite(s.hour)||s.hour<0||s.hour>=24||!Number.isInteger(s.day)||s.day<1||typeof s.running!=='boolean'||![.5,1,4].includes(s.speed)||!Object.hasOwn(WEATHER,s.weather))return newWorld();
    return{version:1,hour:s.hour,day:s.day,running:s.running,speed:s.speed,weather:s.weather};
  }catch{return newWorld();}
}
export function advanceWorld(state,seconds){
  if(!state.running||!Number.isFinite(seconds)||seconds<=0)return;
  const total=state.hour+seconds*24/DAY_SECONDS*state.speed;
  state.day+=Math.floor(total/24);state.hour=wrapHour(total);
}
export function daylight(hour){
  const h=wrapHour(hour),elevation=Math.sin((h-6)/12*Math.PI);
  const day=smooth(-.16,.28,elevation),night=1-smooth(-.20,.08,elevation);
  return{day,night,elevation,warm:Math.exp(-(((elevation-.06)/.26)**2))*(1-night*.7)};
}
export function timeLabel(hour){const m=Math.floor(wrapHour(hour)*60);return`${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`;}
export function periodLabel(hour){const h=wrapHour(hour);return h<5?'深夜':h<8?'清晨':h<16.5?'白天':h<19.5?'黄昏':'夜晚';}
export function blendWeather(current,target,seconds){
  const t=1-Math.exp(-Math.max(0,seconds)/2.2);
  for(const name of['cloud','mist','rain','wind'])current[name]+=(target[name]-current[name])*t;
  return current;
}
