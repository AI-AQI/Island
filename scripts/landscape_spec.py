"""Relief and shoreline shared with the runtime through scene.json."""
import math
from layout_spec import RADIUS, RIVER, closest

HILLS=[[-3,18,8.8,6.2,4.1,1],[10.5,17,7.4,5.8,2.15,1],[-13,10,7.2,6.0,1.35,2],[18,9,6.0,5.5,.42,2],[-19,-12,7,6,.30,1],[0,-15,7,4,.35,1]]
OUTLINE=[[.038,3,.3],[.021,7,-.8],[.012,13,.6]]

def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)

def water_height(y):
    return 10.055+1.0*smooth(7,13,y)+1.25*smooth(14.2,15.8,y)+1.45*smooth(18.1,19.7,y)

WATER_HEIGHTS=[water_height(p[1]) for p in RIVER]

def outline(a):return 1+sum(m*math.sin(n*a+p) for m,n,p in OUTLINE)

def edge_y(x,upper=False):
    lo,hi=0,RADIUS[1]*1.15
    for _ in range(32):
        y=(lo+hi)*.5*(1 if upper else -1);a=math.atan2(y/RADIUS[1],x/RADIUS[0])
        r=math.hypot(x/RADIUS[0],y/RADIUS[1])
        if r<outline(a):lo=abs(y)
        else:hi=abs(y)
    return (lo+hi)*.5*(1 if upper else -1)

def ground(x,y):
    d,w,i,t=closest(x,y)
    base=10.72+.18*math.sin(x*.10)+.13*math.cos(y*.17)
    for cx,cy,rx,ry,h,e in HILLS:base+=h*math.exp(-(((x-cx)/rx)**2+((y-cy)/ry)**2)**e)
    water=WATER_HEIGHTS[i]+(WATER_HEIGHTS[i+1]-WATER_HEIGHTS[i])*t
    bank=base+max(0,water+.55-base)*math.exp(-((d/(w+2))**4))
    return bank-(bank-water+.60)*math.exp(-((d/(w+.20))**6))

def terrain_metadata():
    return dict(profile='garden-relief-v1',radius=list(RADIUS),walkRadius=[27.1,20.6],river=RIVER,waterHeights=WATER_HEIGHTS,hills=HILLS,outline=OUTLINE)
