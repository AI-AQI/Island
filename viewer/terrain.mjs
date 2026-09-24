/** Shared runtime sampling of the authored Blender river and terrain profile. */
export function makeTerrain(spec) {
  const points=spec.river;
  const segments=points.slice(0,-1).map((a,i)=>{const b=points[i+1],dx=b[0]-a[0],dy=b[1]-a[1];return{a,b,dx,dy,l2:dx*dx+dy*dy};});
  function riverAt(x,y){
    let best=Infinity,result;
    for(let i=0;i<segments.length;i++){
      const s=segments[i],u=Math.max(0,Math.min(1,((x-s.a[0])*s.dx+(y-s.a[1])*s.dy)/s.l2));
      const px=s.a[0]+u*s.dx,py=s.a[1]+u*s.dy,d2=(x-px)**2+(y-py)**2;
      if(d2<best){best=d2;const l=Math.sqrt(s.l2),waterHeight=spec.waterHeights?spec.waterHeights[i]+u*(spec.waterHeights[i+1]-spec.waterHeights[i]):10.055;result={distance:Math.sqrt(d2),width:s.a[2]+u*(s.b[2]-s.a[2]),x:px,y:py,nx:-s.dy/l,ny:s.dx/l,t:(i+u)/segments.length,waterHeight};}
    }
    return result;
  }
  function height(x,z){
    const y=-z,p=riverAt(x,y);let base=10.72+.18*Math.sin(x*.10)+.13*Math.cos(y*.17);
    if(!spec.hills)return base-1.20*Math.exp(-((p.distance/(p.width+.35))**6));
    for(const [cx,cy,rx,ry,h,e] of spec.hills){const r2=((x-cx)/rx)**2+((y-cy)/ry)**2;base+=h*Math.exp(-(r2**e));}
    const bank=base+Math.max(0,p.waterHeight+.55-base)*Math.exp(-((p.distance/(p.width+2))**4));
    return bank-(bank-p.waterHeight+.60)*Math.exp(-((p.distance/(p.width+.20))**6));
  }
  function along(t){const f=Math.max(0,Math.min(1,t))*segments.length,i=Math.min(segments.length-1,Math.floor(f)),u=f-i,s=segments[i],l=Math.sqrt(s.l2);return{x:s.a[0]+s.dx*u,y:s.a[1]+s.dy*u,width:s.a[2]+(s.b[2]-s.a[2])*u,nx:-s.dy/l,ny:s.dx/l,waterHeight:spec.waterHeights?spec.waterHeights[i]+u*(spec.waterHeights[i+1]-spec.waterHeights[i]):10.055};}
  function outline(angle){return 1+(spec.outline||[]).reduce((sum,[m,n,p])=>sum+m*Math.sin(n*angle+p),0);}
  return {riverAt,height,along,outline};
}
