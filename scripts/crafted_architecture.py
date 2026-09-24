"""Reference-led architectural details, kept as editable local geometry."""
import math,random
from math import pi,sin,cos
from geometry import Mesh
import assets
import refined_assets as detail

def window(m,x,y,z,w=1.4,h=1.65,arched=True):
    if arched:
        m.arch((x,y,z-.04),w+.26,h+.18,.19,'wood_dark',28)
        m.arch((x,y-.115,z+.05),w-.02,h-.02,.055,'glow',28)
    else:
        m.box((x,y,z+h/2),(w+.22,.20,h+.18),'wood_dark')
        m.box((x,y-.115,z+h/2),(w,.05,h),'glow')
    # Multiple narrow panes and transoms replace the large unbroken light panel.
    count=4 if w>1.7 else 3
    for i in range(count+1):
        dx=-w/2+w*i/count
        top=h-w/2+math.sqrt(max(0,(w/2)**2-dx*dx)) if arched else h
        m.box((x+dx,y-.175,z+.03+top/2),(.055 if i not in [0,count] else .08,.095,top+.04),'wood_light')
    for v in [.08,.39,.72]:
        hh=h*v;half=w/2
        if arched and hh>h-w/2:half=math.sqrt(max(0,(w/2)**2-(hh-(h-w/2))**2))
        m.box((x,y-.18,z+hh),(half*2+.06,.105,.06),'wood_light')
    if arched:
        pts=[(x-w/2,y-.19,z),(x-w/2,y-.19,z+h-w/2)]
        pts += [(x+w/2*cos(t),y-.19,z+h-w/2+w/2*sin(t)) for t in [pi-i*pi/28 for i in range(29)]]
        pts.append((x+w/2,y-.19,z));m.tube(pts,.052,'wood_light',8)
    m.box((x,y-.23,z-.07),(w+.40,.49,.16),'rock_light')
    # Folded linen at the sides reads behind the small panes.
    for side in [-1,1]:
        for k in range(4):
            xx=x+side*(w*.40-k*.035)
            m.beam((xx,y-.144,z+.16),(xx+side*.04,y-.145,z+h*.75),.027,'curtain_linen',n=6)

def umbrella(m,x,y,z,r=1.7):
    m.beam((x,y,z),(x,y,z+2.85),.04,'wood_light',n=12)
    m.sphere((x,y,z+.035),(.36,.36,.06),'rock',16,4)
    for sector in range(12):
        start=len(m.v);steps=4;rings=8
        for j in range(rings+1):
            u=j/rings
            for k in range(steps+1):
                f=k/steps;a=(sector+f)*math.tau/12
                zz=z+2.87-.59*u**1.35-.065*sin(pi*f)*u**3
                m.v.append((x+r*u*cos(a),y+r*u*sin(a),zz))
        for j in range(rings):
            for k in range(steps):
                a=start+j*(steps+1)+k;m.face((a,a+1,a+steps+2,a+steps+1),'pink' if sector%2 else 'cream',True)
        a=sector*math.tau/12
        pts=[(x+r*u*cos(a),y+r*u*sin(a),z+2.845-.59*u**1.35) for u in [i/12 for i in range(13)]]
        m.tube(pts,.011,'wood_light',6)
        edge=[(x+r*cos((sector+f)*math.tau/12),y+r*sin((sector+f)*math.tau/12),z+2.28-.065*sin(pi*f)) for f in [i/8 for i in range(9)]]
        m.tube(edge,.022,'cream',6)
    m.sphere((x,y,z+2.93),(.065,.065,.105),'brass',12,6)

def foliage(m,points,seed,flowers=True):
    rng=random.Random(seed);m.tube(points,.026,'wood_dark',6)
    for a,b in zip(points,points[1:]):
        for i in range(6):
            t=(i+.5)/6;p=[a[k]+(b[k]-a[k])*t for k in range(3)]
            for side in [-1,1]:
                xx=p[0]+side*rng.uniform(.04,.17);zz=p[2]+rng.uniform(-.07,.07)
                detail.petal(m,(xx,p[1]-.055,zz),rng.uniform(.18,.28),rng.uniform(.10,.17),side*.8,1.0,rng.choice(['leaf','leaf_light','leaf_dark']))
                if flowers and rng.random()<.22:
                    for petal in range(5):
                        angle=petal*math.tau/5;m.sphere((xx+.041*cos(angle),p[1]-.10,zz+.041*sin(angle)),(.038,.023,.038),rng.choice(['flower_white','flower_pink']),7,4)
                    m.sphere((xx,p[1]-.12,zz),(.018,.018,.018),'flower_yellow',7,4)

def house():
    old=assets.window;assets.window=window
    try:m=detail.house_main()
    finally:assets.window=old
    # Detailed timber lintels and ironwork on the entry.
    for z in [1.03,1.64]:
        m.box((-.95,-3.758,z),(1.04,.026,.058),'metal')
        for x in [-1.37,-.52]:m.sphere((x,-3.785,z),(.022,.014,.022),'brass',8,4)
    # Window-side masonry has a warm, deliberately irregular rhythm.
    rng=random.Random(825)
    for i in range(15):
        x=rng.uniform(-4.4,3.8);z=rng.uniform(.7,1.1)
        if -2.25<x<.15:continue
        m.box((x,-3.09,z),(.28+rng.random()*.19,.075,.12+rng.random()*.05),'wall_shade')
    garden=Mesh('house_crafted_garden')
    for x in [-4.6,-2.05,.45,3.25]:
        foliage(garden,[(x+.10*sin(j*.8),-3.14,.7+j*.37) for j in range(8)],int((x+6)*71))
    foliage(garden,[(1.75+1.39*cos(t),-3.20,1.36+2.26*sin(t)) for t in [i*pi/18 for i in range(19)]],55)
    # A small teal tiled eyebrow above the entry, echoed in the reference.
    eyebrow=Mesh('entry_eyebrow');detail.tiled_roof(eyebrow,-.95,-3.29,2.60,1.04,3.25,.51,33)
    detail.merge(m,eyebrow)
    return m,garden

def cafe():
    old_roof,old_umbrella=assets.roof,assets.umbrella
    def roof(m,cx,cy,w,d,e,r,seed=1):
        n=Mesh('cafe_roof');detail.tiled_roof(n,cx,cy,w,d,e,r*.79,seed)
        n.mats=[{'roof':'cafe_roof','roof_light':'cafe_roof_light','roof_dark':'cafe_roof_dark'}.get(mat,mat) for mat in n.mats]
        detail.merge(m,n)
    assets.roof,assets.umbrella=roof,umbrella
    try:m=assets.cafe_pavilion()
    finally:assets.roof,assets.umbrella=old_roof,old_umbrella
    for x in [-2.3,-.8,.8,2.3]:window(m,x,2.55,1.42,1.12,1.65,False)
    for x in [-2.85,-2.45,-2.05,-1.65,-1.25,-.85,-.45,-.05,.35,.75,1.15,1.55,1.95,2.35,2.75]:
        m.box((x,.19,1.51),(.045,.04,.96),'wood_light')
    # Folded napkins, saucers and handles make the terrace tables read as used.
    for x,y in [(-2.85,-1.63),(2.9,-1.43),(.15,-1.58)]:
        m.beam((x+.18,y,z:=1.84),(x+.18,y,z+.012),.11,'cream',n=20)
        pts=[(x+.245+.037*cos(a),y-.001,z+.072+.04*sin(a)) for a in [i*math.tau/18 for i in range(19)]]
        m.tube(pts,.012,'cream',6)
        m.box((x-.24,y-.11,1.86),(.19,.13,.016),'curtain_linen',rz=.22)
    # Replace the old anonymous chalk strokes with an inset menu field.
    m.box((1.58,-3.266,1.72),(.75,.012,.88),'board')
    for j in range(3):m.box((1.56,-3.278,1.71-j*.13),(.45-j*.04,.008,.017),'chalk')
    garden=Mesh('cafe_crafted_garden')
    for side in [-1,1]:foliage(garden,[(side*(3.21+.06*sin(j)),.03,1.02+j*.40) for j in range(8)],81+side)
    foliage(garden,[(x,2.78,3.67+.09*sin(x*2)) for x in [-3.2+i*.40 for i in range(17)]],84)
    for side in [-1,1]:foliage(garden,[(side*(3.2+.09*sin(j)),-.02+j*.29,3.62+.04*j) for j in range(10)],89+side)
    return m,garden
