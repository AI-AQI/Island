"""Deterministic, editable geometry for the reference-led second art pass."""
import math
import random
from math import sin, cos, pi
from mathutils import Vector
from geometry import Mesh
import assets


def merge(dst, src, offset=(0, 0, 0), scale=1):
    start = len(dst.v)
    dst.v.extend(tuple(v[k] * scale + offset[k] for k in range(3)) for v in src.v)
    for f, mi, smooth in zip(src.f, src.mi, src.sm):
        dst.face([i + start for i in f], src.mats[mi], smooth)


def petal(m, center, length, width, angle, tilt, material):
    """Rounded six-sided folded leaf, with a visible central vein ridge."""
    c = Vector(center)
    u = Vector((cos(angle), sin(angle), tilt)).normalized() * length
    v = Vector((-sin(angle), cos(angle), .12)) * width
    verts = [c-u*.5, c-u*.24+v*.44, c+u*.22+v*.5,
             c+u*.5, c+u*.22-v*.5, c-u*.24-v*.44, c+Vector((0,0,width*.13))]
    m.poly(verts, [(i, (i+1)%6, 6) for i in range(6)], material, True)


def roof_height(u, eave, rise):
    return eave + rise * (1-u)**1.48 + .39*u**9


def tiled_roof(m, cx, cy, width, depth, eave, rise, seed):
    rng = random.Random(seed)
    half = width/2
    rows = max(8, round(half/.35))
    cols = max(5, round(depth/.39))
    for side in [-1, 1]:
        for row in range(rows):
            u0 = row/rows
            u1 = min((row+1.2)/rows, 1.015)
            for col in range(cols):
                yc = cy-depth/2+(col+.5)*depth/cols + (.18 if row%2 else 0)
                w = depth/cols-.022
                # Rounded scalloped hanging ends and overlapping thickness.
                outline = [(u0,-w*.48),(u1-.045,-w*.5),(u1,-w*.32),
                           (u1+.006,0),(u1,w*.32),(u1-.045,w*.5),(u0,w*.48)]
                zoff = rng.uniform(.012,.04)
                vv = [(cx+side*half*u, yc+dy, roof_height(min(u,1),eave,rise)+zoff) for u,dy in outline]
                vv += [(x,y,z-.065) for x,y,z in vv]
                faces=[tuple(range(7)),tuple(reversed(range(7,14)))]
                faces += [(i,(i+1)%7,(i+1)%7+7,i+7) for i in range(7)]
                m.poly(vv,faces,rng.choices(['roof','roof_light','roof_dark'],[7,2,2])[0],False)
        for y in [cy-depth/2-.13,cy+depth/2+.18]:
            pts=[(cx+side*half*j/24,y,roof_height(j/24,eave,rise)+.08) for j in range(25)]
            m.tube(pts,.135,'wood_dark',8)
            m.tube([(x,y-.035,z+.048) for x,y,z in pts],.084,'wood_light',7)
        m.beam((cx+side*half,cy-depth/2,eave+.27),(cx+side*half,cy+depth/2,eave+.27),.12,'wood_dark')
    for i in range(cols+1):
        y=cy-depth/2+i*depth/cols
        m.beam((cx,y,eave+rise+.08),(cx,y+.35,eave+rise+.08),.19,'roof_light',n=10)
    # Curl at each gable tip.
    for y in [cy-depth/2-.22,cy+depth/2+.26]:
        pts=[(cx+.27*sin(t),y,eave+rise+.04+.26*(1-cos(t))) for t in [i*pi/14 for i in range(15)]]
        m.tube(pts,.10,'wood_light',7)


def gabled_wall(m,cx,cy,width,depth,eave,rise):
    m.box((cx,cy,(eave+.68)/2),(width,depth,eave-.68),'wall')
    half=width/2
    profile=[(cx-half,eave-.02),(cx+half,eave-.02)]
    for i in range(31):
        x=half-2*half*i/30
        profile.append((cx+x,roof_height(abs(x)/(half+.38),eave,rise)-.16))
    n=len(profile)
    vv=[(x,cy+dy,z) for dy in [-depth/2,depth/2] for x,z in profile]
    m.poly(vv,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],'wall')


def house_main():
    m=Mesh('house_main');rng=random.Random(42)
    m.box((0,0,.32),(9.8,6.0,.64),'rock_dark')
    # Two unequal front gables give the reference cottage its silhouette.
    gabled_wall(m,-2.75,0,4.25,5.7,3.9,2.35)
    gabled_wall(m,1.7,.16,4.9,6.0,3.9,3.25)
    tiled_roof(m,-2.75,0,5.15,6.5,3.88,2.38,10)
    tiled_roof(m,1.7,.16,5.85,6.85,3.88,3.28,11)
    for row in range(3):
        for i in range(15):
            m.box((-4.58+i*.65+(row%2)*.15,-3.05,.12+row*.20),(.59,.23,.18),rng.choice(['rock','rock_light','wall_shade']))
    # Slightly rounded entry arch between the gables.
    m.arch((-.95,-3.2,.62),2.15,3.10,.58,'wall_shade',24)
    m.arch((-.95,-3.52,.63),1.57,2.44,.16,'rock_light',24)
    m.arch((-.95,-3.63,.66),1.29,2.19,.13,'wood_dark',24)
    m.arch((-.95,-3.71,.70),1.13,2.0,.05,'wood',24)
    for j in range(6):m.box((-1.43+j*.19,-3.75,1.39),(.012,.025,1.35),'wood_dark')
    m.arch((-.95,-3.77,2.03),.95,.59,.025,'glow',18)
    for x in [-1.23,-.95,-.67]:m.box((x,-3.80,2.31),(.045,.045,.42),'wood_light')
    m.sphere((-.51,-3.82,1.45),(.07,.044,.07),'brass',10,5)
    for j in range(3):
        for i in range(4):m.box((-2.2+i*.76,-4.12-j*.34,.59-j*.2),(.72,.6,.2),'rock_light' if (i+j)%3 else 'rock')
    # Large bay, small gable lights and side windows.
    assets.window(m,1.75,-2.94,1.24,2.12,2.15)
    assets.window(m,1.7,-2.94,4.91,1.0,1.45)
    assets.window(m,-3.18,-2.91,1.24,1.07,1.78)
    assets.window(m,-2.75,-2.92,4.33,.69,1.18)
    for side in [-1,1]:
        for y in [-1.7,.95]:
            tmp=Mesh('window');assets.window(tmp,0,0,1.35,1.16,1.75)
            start=len(m.v)
            m.v.extend((side*(4.2 if side>0 else 4.88)-side*yy,y+side*x,z) for x,yy,z in tmp.v)
            for f,mi,sm in zip(tmp.f,tmp.mi,tmp.sm):m.face([start+i for i in f],tmp.mats[mi],sm)
    m.box((1.75,-3.29,1.03),(2.54,.7,.42),'wood')
    for i in range(12):m.box((.56+i*.21,-3.66,1.05),(.17,.04,.46),'wood_light')
    m.box((1.7,-3.19,4.75),(1.45,.55,.25),'wood_light')
    # Individual pale stones on all chimney sides.
    m.box((-1.22,1.24,6.62),(.94,.99,3.64),'rock_dark')
    for row in range(12):
        z=4.93+row*.30
        for side in [-1,1]:
            for i in range(3):
                mat=rng.choice(['rock_light','wall_shade','rock','wall'])
                m.box((-1.53+i*.32,1.24+side*.515,z),(.29,.11,.27),mat)
                m.box((-1.22+side*.49,.90+i*.34,z),(.11,.31,.27),mat)
    m.box((-1.22,1.24,8.58),(1.18,1.28,.22),'rock_light')
    m.box((-1.22,1.24,8.72),(.64,.72,.07),'wood_dark')
    # Face quoins, exposed stone patches and warm entry fixtures.
    for x in [-4.83,4.08]:
        for j in range(9):m.box((x,-2.96,.85+j*.33),(.34 if j%2 else .50,.18,.26),'wall_shade')
    for x in [-2.02,.09]:
        m.beam((x,-3.31,2.99),(x,-3.65,2.99),.035,'metal')
        m.beam((x,-3.65,2.99),(x,-3.65,2.81),.026,'metal')
        assets.lantern(m,(x,-3.65,2.20),.69)
    m.sphere((-.95,-3.56,3.17),(.14,.06,.14),'glow',12,6)
    return m


def broad_tree(variant=0):
    m=Mesh(['tree_large_green','tree_large_gold'][variant]);rng=random.Random(472+variant)
    cols=['leaf','leaf_dark','leaf_light','leaf_gold']
    spine=[(0,0,0),(.18,.08,1.2),(-.17,.1,2.5),(.18,.15,3.55),(.55,.12,4.6)]
    for i in range(4):m.beam(spine[i],spine[i+1],.48-i*.087,'wood',r2=.39-i*.08,n=10)
    for j in range(8):
        a=j*2*pi/8;pts=[(.2*cos(a),.2*sin(a),.7),(.64*cos(a+.12),.64*sin(a+.12),.25),(1.65*cos(a),1.15*sin(a),.04)]
        m.beam(pts[0],pts[1],.23,'wood',r2=.15,n=7);m.beam(pts[1],pts[2],.15,'wood',r2=.035,n=7)
    crowns=[]
    for i in range(11):
        a=i*2.399+variant*.7
        radius=2.7 if i<7 else 1.2
        c=Vector((radius*cos(a),radius*.8*sin(a),4.8+(i%3)*.55+(1 if i>6 else 0)))
        root=Vector((.04,.05,2.2+(i%3)*.45))
        mid=root.lerp(c,.52)+Vector((0,0,.20))
        m.beam(root,mid,.23,'wood',r2=.15,n=8);m.beam(mid,c,.15,'wood',r2=.025,n=7)
        for k in range(3):
            t=a+k*2.1;tip=c+Vector((.9*cos(t),.8*sin(t),.46))
            m.beam(mid.lerp(c,.72),tip,.065,'wood_light',r2=.012,n=5)
        crowns.append((c,1.55 if i<7 else 1.7))
    for c,r in crowns:
        # Shaded small inner leaf masses avoid empty holes without a ball silhouette.
        for k in range(4):
            a=k*pi/2
            m.sphere(c+Vector((.6*cos(a),.5*sin(a),.12)),(.53,.46,.35),'leaf_dark',9,5,True)
        for j in range(280):
            a=rng.uniform(0,2*pi);z=rng.uniform(-.8,1);q=math.sqrt(1-z*z)*rng.uniform(.62,1)
            p=c+Vector((r*q*cos(a),r*q*.84*sin(a),.95*z))
            mat=rng.choices(cols,[5,2,5,1] if variant==0 else [4,1,6,3])[0]
            petal(m,p,rng.uniform(.22,.43),rng.uniform(.12,.21),a,rng.uniform(-1.3,.9),mat)
    return m


def flower_patch(variant):
    m=Mesh('bush_flower_'+variant);rng=random.Random(600+len(variant))
    for j in range(44):
        a=rng.uniform(0,2*pi);r=rng.uniform(.1,.74)
        petal(m,(r*cos(a),r*sin(a),rng.uniform(.08,.26)),rng.uniform(.25,.49),.16,a,rng.uniform(.3,1.2),'leaf' if j%3 else 'leaf_light')
    for j in range(21):
        a=rng.uniform(0,2*pi);r=rng.uniform(.12,.7);x=r*cos(a);y=r*sin(a);h=rng.uniform(.22,.57)
        m.beam((x,y,.03),(x,y,h),.012,'leaf_dark',n=4)
        for k in range(7):
            t=k*2*pi/7;petal(m,(x+.10*cos(t),y+.10*sin(t),h),.20,.085,t,.18,'flower_'+variant)
        m.sphere((x,y,h+.035),(.05,.05,.035),'flower_yellow',7,3)
    return m


def vine(seed=3):
    m=Mesh('vine_hanging');rng=random.Random(seed)
    for branch in range(3):
        length=3.9-branch*.63;ox=(branch-1)*.29
        pts=[(ox+.12*sin(i*.62+branch),.065*cos(i*.5),3.95-length*i/23) for i in range(24)]
        m.tube(pts,.015,'wood',5)
        for i,(x,y,z) in enumerate(pts):
            for side in [-1,1]:
                petal(m,(x+side*.10,y-.06,z-.06),rng.uniform(.21,.37),.21,side*.83,-1.8,'leaf' if (i+branch)%3 else 'leaf_light')
    return m


def stone_variant(i):
    m=Mesh('rock_deco_'+str(i+1));s=[.43,.78,1.17][i]
    m.sphere((0,0,s*.6),(s,s*.8,s*.66),['rock','rock_light','rock_warm'][i],11,6,False,.14,19+i)
    for j in range(7):
        a=j*2.399
        m.sphere((.36*s*cos(a),.36*s*sin(a),s*1.14),(.29*s,.21*s,.055*s),'moss',8,3,True)
    return m


BUILDERS={'house_main':house_main,'tree_large_green':lambda:broad_tree(0),'tree_large_gold':lambda:broad_tree(1),'vine_hanging':vine}
for col in ['white','pink','yellow']:BUILDERS['bush_flower_'+col]=lambda c=col:flower_patch(c)
for i in range(3):BUILDERS['rock_deco_'+str(i+1)]=lambda n=i:stone_variant(n)
