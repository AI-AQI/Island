import math, random
from math import sin,cos,pi
from geometry import Mesh, river_x, land_z, rock

def island_base():
    m=Mesh('island_base'); rng=random.Random(11); n=128; nr=32
    m.v=[(0,0,land_z(0,0))]
    def radius(t):return 1+.022*sin(5*t)+.018*sin(9*t+.7)
    for j in range(1,nr+1):
        r=j/nr
        for i in range(n):
            t=2*pi*i/n; x=22.2*cos(t)*r*radius(t); y=13.7*sin(t)*r*radius(t)
            m.v.append((x,y,land_z(x,y)))
    for i in range(n):m.face((0,1+i,1+(i+1)%n),'grass',True)
    for j in range(nr-1):
        for i in range(n):
            a=1+j*n+i; b=1+j*n+(i+1)%n
            x,y,_=m.v[a]; mat='soil_light' if abs(x-river_x(y))<1.85 else 'grass'
            m.face((a,a+n,b+n,b),mat,True)
    previous=[1+(nr-1)*n+i for i in range(n)]
    for j,(r,z) in enumerate([(1,9.9),(.98,8.8),(.91,6.5),(.76,3.8),(.58,1.8),(.33,.65),(.07,.08)]):
        ids=[]
        for i in range(n):
            t=i*2*pi/n; q=radius(t)*(1+.025*sin(19*t+j*1.7)); ids.append(len(m.v))
            zz=z+.32*sin(7*t+j)*min(z,.9)
            if j==0:zz=min(land_z(22.2*cos(t),13.7*sin(t))-.2,zz)
            m.v.append((22.2*cos(t)*r*q,13.7*sin(t)*r*q,zz))
        for i in range(n):m.face((previous[i],ids[i],ids[(i+1)%n],previous[(i+1)%n]),rng.choice(['rock','rock_dark','rock_warm']),False)
        previous=ids
    b=len(m.v);m.v.append((0,0,0))
    for i in range(n):m.face((previous[i],b,previous[(i+1)%n]),'rock_dark')
    for row,(r,z,sz) in enumerate([(1,8.8,1.9),(.94,6.4,2.4),(.79,3.8,2.0),(.57,1.7,1.6)]):
        for i in range(60 if row<2 else 42):
            count=60 if row<2 else 42; t=(i+.4*(row%2))*2*pi/count
            x=22.2*r*cos(t)*radius(t);y=13.7*r*sin(t)*radius(t)
            # A deep open notch underneath the waterfall, rather than rock through water.
            if y<-10 and abs(x-river_x(y))<2.6:continue
            rock(m,(x,y,z+rng.uniform(-.25,.25)),(rng.uniform(1,1.9),rng.uniform(.8,1.55),sz*rng.uniform(.75,1.15)),i+row*90)
    return m

def distant_island():
    m=Mesh('distant_island');m.sphere((0,0,2.6),(4,2.6,.7),'grass_dark',12,4,False)
    for i in range(8):
        t=i*2*pi/8;rock(m,(2*cos(t),1.3*sin(t),1.7),(1.7,1.3,1.6),i)
    rock(m,(0,0,.9),(1.8,1.6,.9),90);return m

def window(m,x,y,z,w=1.4,h=1.65,arched=True):
    if arched:
        m.arch((x,y,z),w+.23,h+.18,.2,'wood_dark');m.arch((x,y-.12,z+.09),w,h,.09,'glow')
    else:
        m.box((x,y,z+h/2),(w+.24,.21,h+.24),'wood_dark');m.box((x,y-.12,z+h/2),(w,.06,h),'glow')
    for dx in [-w/2,0,w/2]:m.box((x+dx,y-.18,z+h*.46),(.07,.1,h*.88),'wood_light')
    for zz in [z+.1,z+h*.45]:m.box((x,y-.18,zz),(w+.1,.13,.09),'wood_light')
    m.box((x,y-.25,z-.04),(w+.38,.55,.15),'rock_light')

def roof(m,cx,cy,width,depth,eave,rise,seed=1):
    rng=random.Random(seed); hw=width/2; cols=int(depth/.39); rows=12
    def height(u):return eave+rise*max(0,1-u)**1.45+.24*(u**10)
    # Curved continuous roof underlay, individual overlapping shingles on both sides.
    for side in [-1,1]:
        for j in range(rows):
            u0=j/rows;u1=min((j+1.16)/rows,1.025)
            for i in range(cols):
                y0=cy-depth/2+i*depth/cols; y1=y0+depth/cols-.026
                if j%2:y0-=.12;y1-=.12
                x0=cx+side*hw*u0;x1=cx+side*hw*u1
                zz=.035*rng.random()
                verts=[(x0,y0,height(u0)+zz),(x1,y0,height(u1)+zz),(x1,y1,height(u1)+zz),(x0,y1,height(u0)+zz)]
                verts += [(x,y,z-.09) for x,y,z in verts]
                m.poly(verts,[(0,1,2,3),(3,2,6,7),(0,4,5,1),(1,5,6,2),(0,3,7,4)],rng.choices(['roof','roof_light','roof_dark'],[5,2,2])[0])
        for y in [cy-depth/2-.08,cy+depth/2+.02]:
            m.tube([(cx+side*hw*j/20,y,height(j/20)+.1) for j in range(21)],.115,'wood_light',8)
        m.beam((cx+side*hw,cy-depth/2,eave+.18),(cx+side*hw,cy+depth/2,eave+.18),.11,'wood_dark')
    m.beam((cx,cy-depth/2-.17,eave+rise+.09),(cx,cy+depth/2+.17,eave+rise+.09),.16,'roof_light',n=10)

def lantern(m,c,scale=1):
    x,y,z=c;s=scale
    m.box((x,y,z+.28*s),(.32*s,.32*s,.48*s),'glow')
    for xx in [-.19,.19]:
        for yy in [-.19,.19]:m.beam((x+xx*s,y+yy*s,z),(x+xx*s,y+yy*s,z+.59*s),.026*s,'metal',n=5)
    m.box((x,y,z),(.45*s,.45*s,.08*s),'wood_dark')
    m.sphere((x,y,z+.62*s),(.32*s,.32*s,.15*s),'wood_dark',4,2,False)
    m.beam((x,y,z+.72*s),(x,y,z+.85*s),.026*s,'metal')

def house_main():
    m=Mesh('house_main');rng=random.Random(12)
    m.box((0,0,.4),(8.8,6.5,.8),'rock_dark')
    for row in range(2):
        for i in range(12):m.box((-4.08+i*.74,-3.29,.2+row*.32),(.69,.17,.29),'rock_light' if i%3 else 'rock')
    m.box((0,0,2.36),(8.15,5.85,3.22),'wall')
    profile=[(-4.075,3.85),(4.075,3.85)]
    for i in range(33):
        x=4.075-8.15*i/32;u=abs(x)/4.75
        profile.append((x,3.83+3.4*(1-u)**1.45+.24*u**10-.1))
    vv=[(x,y,z) for y in [-2.925,2.925] for x,z in profile];nn=len(profile)
    m.poly(vv,[tuple(range(nn)),tuple(reversed(range(nn,2*nn)))]+[(i,(i+1)%nn,(i+1)%nn+nn,i+nn) for i in range(nn)],'wall')
    roof(m,0,0,9.5,7.05,3.83,3.4)
    # Front porch gable and rounded oak door, with three connected stone steps.
    m.box((-1.6,-3.19,1.95),(2.55,1.0,2.45),'wall_shade')
    m.poly([(-2.87,-3.71,3.17),(-.33,-3.71,3.17),(-1.6,-3.71,4.38)],[(0,1,2)],'wall')
    roof(m,-1.6,-3.13,3.25,1.55,3.0,1.4,7)
    m.arch((-1.6,-3.73,.75),1.68,2.24,.19,'rock_light')
    m.arch((-1.6,-3.85,.76),1.38,2.03,.13,'wood_dark')
    for i in range(6):m.box((-2.19+i*.236,-3.935,1.48),(.216,.04,1.44),'wood')
    m.arch((-1.6,-3.94,2.16),1.08,.55,.035,'glow',12)
    for dx in [-.28,0,.28]:m.box((-1.6+dx,-3.97,2.42),(.045,.03,.42),'wood_light')
    m.sphere((-1.14,-4,1.58),(.064,.042,.064),'metal',8,4)
    for i in range(3):
        m.box((-1.6,-4.7+i*.31,.125+i*.25),(2.85-i*.14,1.5-i*.35,.25),'rock_light')
    window(m,1.85,-2.965,1.45,2.15,1.9)
    window(m,0,-2.98,4.8,1.2,1.55)
    # Side windows face the visible west wall.
    tmp=Mesh('side');window(tmp,0,0,1.5,1.4,1.7)
    for off in [-1.6,1.25]:
        start=len(m.v);m.v.extend((-4.1+y,off-x,z) for x,y,z in tmp.v)
        for f,mi,sm in zip(tmp.f,tmp.mi,tmp.sm):m.face([start+i for i in f],tmp.mats[mi],sm)
        start=len(m.v);m.v.extend((4.1-y,off+x,z) for x,y,z in tmp.v)
        for f,mi,sm in zip(tmp.f,tmp.mi,tmp.sm):m.face([start+i for i in f],tmp.mats[mi],sm)
    for x in [-4.08,4.08]:m.box((x,-2.99,2.42),(.14,.18,3.14),'wood_light')
    # Stone chimney with alternating blocks and a proper cap.
    m.box((-2.35,.8,6.55),(1.03,1.16,3.9),'rock')
    for row in range(12):
        for i in range(3):
            xx=-2.77+i*.35+(row%2)*.09
            m.box((xx,.196,4.8+row*.29),(.31,.095,.26),rng.choice(['rock_light','wall_shade','rock']))
    m.box((-2.35,.8,8.58),(1.26,1.37,.25),'rock_light')
    m.box((-2.35,.8,8.74),(.73,.88,.08),'wood_dark')
    for x in [-2.83,-.34]:
        m.beam((x,-3.78,2.9),(x,-4.03,2.9),.046,'wood_dark');m.beam((x,-4.03,2.9),(x,-4.03,2.78),.022,'metal')
        lantern(m,(x,-4.03,2.18),.65)
    # Flower boxes: leaves and flowers are separate reusable assets in assembly.
    m.box((1.85,-3.32,1.26),(2.38,.58,.42),'wood')
    for i in range(9):m.box((.83+i*.255,-3.63,1.28),(.2,.04,.45),'wood_light')
    return m

def player_ref():
    m=Mesh('player_ref')
    for x in [-.13,.13]:m.beam((x,0,0),(x,0,.51),.075,'wood_dark')
    m.sphere((0,0,.73),(.26,.18,.35),'cream',10,6)
    m.sphere((0,-.025,1.15),(.16,.15,.18),'skin',10,6)
    m.sphere((0,0,1.33),(.29,.23,.055),'wood_light',12,4)
    m.sphere((0,0,1.36),(.17,.16,.04),'wood',10,4)
    for s in [-1,1]:m.beam((s*.2,0,.94),(s*.31,-.02,.62),.062,'skin')
    return m

BUILDERS={'island_base':island_base,'distant_island':distant_island,'house_main':house_main,'player_ref':player_ref}

def umbrella(m,x,y,z,r=1.7):
    m.beam((x,y,z),(x,y,z+2.8),.045,'wood_light');m.sphere((x,y,z+.04),(.4,.4,.08),'rock',10,3)
    for i in range(12):
        t0=i*2*pi/12;t1=(i+1)*2*pi/12;tm=(t0+t1)/2;mat='pink' if i%2 else 'cream'
        a=(x,y,z+2.9);b=(x+r*.57*cos(t0),y+r*.57*sin(t0),z+2.63);c=(x+r*.57*cos(t1),y+r*.57*sin(t1),z+2.63)
        d=(x+r*cos(t0),y+r*sin(t0),z+2.27);e=(x+r*cos(t1),y+r*sin(t1),z+2.27)
        f=(x+r*cos(tm),y+r*sin(tm),z+2.13)
        m.poly([a,b,c,d,e,f],[(0,1,2),(1,3,4,2),(3,5,4)],mat)
        m.beam((x,y,z+2.85),d,.018,'wood_light',n=5)
    m.sphere((x,y,z+2.98),(.07,.07,.13),'wood',8,4)

def table(m,x,y,z):
    m.beam((x,y,z+.76),(x,y,z+.85),.57,'wood_light',n=16)
    m.beam((x,y,z+.05),(x,y,z+.78),.1,'wood');
    for i in range(3):
        a=2*pi*i/3;m.beam((x,y,z+.23),(x+.43*cos(a),y+.43*sin(a),z+.05),.052,'wood')
    m.beam((x+.18,y,z+.86),(x+.18,y,z+.97),.064,'cream',n=10)
    m.beam((x-.17,y+.04,z+.85),(x-.17,y+.04,z+.97),.07,'terracotta',n=10)
    for angle in [0,2.2,4.25]:
        cx=x+cos(angle)*.92;cy=y+sin(angle)*.92
        m.beam((cx,cy,z+.43),(cx,cy,z+.52),.27,'wood_light',n=10)
        for a in [pi/4,3*pi/4,5*pi/4,7*pi/4]:
            dx=.21*cos(a);dy=.21*sin(a);m.beam((cx+dx,cy+dy,z+.03),(cx+dx*.9,cy+dy*.9,z+.48),.037,'wood')
        tx,ty=-sin(angle),cos(angle)
        for s in [-1,1]:m.beam((cx+cos(angle)*.18+tx*.22*s,cy+sin(angle)*.18+ty*.22*s,z+.45),(cx+cos(angle)*.25+tx*.22*s,cy+sin(angle)*.25+ty*.22*s,z+1.02),.039,'wood')
        m.beam((cx+cos(angle)*.25+tx*.22,cy+sin(angle)*.25+ty*.22,z+.94),(cx+cos(angle)*.25-tx*.22,cy+sin(angle)*.25-ty*.22,z+.94),.062,'wood_light')

def cafe_pavilion():
    m=Mesh('cafe_pavilion')
    # Load-bearing beams and diagonal brackets below a projecting deck.
    for x in [-4.25,0,4.25]:
        m.box((x,0,.44),(.22,6.5,.38),'wood_dark')
        for y in [-2.7,2.6]:
            m.box((x,y,.5),(.3,.3,1),'wood');m.beam((x,y,.05),(x,y-1.0 if y<0 else y+1,.78),.1,'wood')
    for i in range(38):m.box((-4.55+i*.245,0,.9),(.222,6.6,.18),'wood_light' if i%5 else 'wood')
    for x in [-4.6,4.6]:
        for y in [-3.25,-1.6,0,1.65,3.25]:m.box((x,y,1.44),(.16,.16,1.15),'wood')
        for z in [1.21,1.94]:m.beam((x,-3.25,z),(x,3.25,z),.065,'wood_light')
    for x0,x1 in [(-4.6,-1.1),(1.1,4.6)]:
        for z in [1.21,1.94]:m.beam((x0,-3.25,z),(x1,-3.25,z),.065,'wood_light')
        for x in [x0,x1]:m.box((x,-3.25,1.44),(.17,.17,1.15),'wood')
    for i in range(3):m.box((0,-3.95+i*.27,.15+i*.28),(2.15,1.35-i*.3,.3),'rock_light')
    # Half-open timber tea house at the back.
    m.box((0,2.87,2.05),(6.35,.22,2.2),'wood')
    for i in range(25):m.box((-3+i*.25,2.73,2.05),(.05,.045,2.2),'wood_light')
    for x in [-3.18,3.18]:
        for y in [.15,2.9]:m.box((x,y,2.27),(.23,.23,2.7),'wood_dark')
        m.beam((x,.15,3.5),(x,2.9,3.5),.12,'wood_light')
    m.box((0,.53,1.51),(5.15,.65,1.05),'wood');m.box((0,.47,2.08),(5.4,.85,.14),'wood_dark')
    for z in [1.75,2.55,3.04]:
        m.box((0,2.64,z),(4.8,.45,.09),'wood_dark')
        for i in range(11):
            x=-2.1+i*.4;m.beam((x,2.62,z+.06),(x,2.62,z+.34),.09,'terracotta' if i%3 else 'cream',n=8)
    roof(m,0,1.63,7.2,3.9,3.45,1.38,5)
    for x,y in [(-2.9,-1.5),(2.85,-1.3)]:
        umbrella(m,x,y,.99,1.62);table(m,x+.05,y-.13,.99)
    table(m,.15,-1.58,.99)
    # Catenary string: every lantern is attached to a continuous cable.
    pts=[(-3.15+6.3*i/24,-.1,3.35-.38*sin(pi*i/24)) for i in range(25)];m.tube(pts,.017,'wood_dark',5)
    for i in [2,6,10,14,18,22]:
        x,y,z=pts[i];m.beam((x,y,z),(x,y,z-.1),.015,'metal',n=5);lantern(m,(x,y,z-.49),.48)
    # Menu board, legs and chalk marks; readable detail remains geometry.
    m.box((1.58,-3.15,1.71),(.92,.11,1.08),'wood_dark');m.box((1.58,-3.223,1.71),(.76,.026,.88),'board')
    for x in [1.16,2.0]:m.beam((x,-3.3,1.01),(x,-3.05,2.28),.055,'wood_light')
    for j in range(5):m.box((1.55,-3.24,2.01-j*.13),(.47-j*.035,.01,.021),'chalk')
    return m

def stone_bridge():
    m=Mesh('stone_bridge');n=22;length=6.8;width=2.7
    def z(x):return .2+.95*cos(pi*x/length)
    for i in range(n):
        x0=-length/2+i*length/n;x1=x0+length/n-.025
        for j in range(5):
            y0=-width/2+j*width/5+.014;y1=y0+width/5-.03
            v=[(x0,y0,z(x0)),(x1,y0,z(x1)),(x1,y1,z(x1)),(x0,y1,z(x0))]
            v += [(x,y,zz-.47) for x,y,zz in v]
            m.poly(v,[(0,1,2,3),(0,4,5,1),(3,2,6,7),(0,3,7,4),(1,5,6,2)],'rock_light' if (i+j)%3 else 'rock')
    for y in [-1.42,1.42]:
        for x in [-3.4,-2.25,-1.12,0,1.12,2.25,3.4]:
            m.box((x,y,z(x)+.43),(.17,.17,.97),'wood');m.sphere((x,y,z(x)+.95),(.14,.14,.12),'wood_light',8,4)
        for dz in [.43,.86]:m.tube([(x,y,z(x)+dz) for x in [-3.4+6.8*i/24 for i in range(25)]],.067,'wood_light')
    for x in [-3.24,3.24]:m.box((x,0,-.02),(.52,3.02,.48),'rock')
    return m

def farm_fence():
    m=Mesh('farm_fence')
    for x in [-.96,.96]:
        m.beam((x,0,.02),(x+.04,.02,1.1),.09,'wood',r2=.07,n=5)
        m.sphere((x+.04,.02,1.11),(.095,.095,.085),'wood_light',5,2,False)
    for z in [.4,.86]:m.box((0,0,z),(2,.10,.14),'wood_light')
    m.beam((-.85,.03,.39),(.85,.03,.85),.035,'wood');return m

def farm_soil():
    m=Mesh('farm_soil');m.box((0,0,.09),(3,4,.18),'soil')
    for i in range(5):m.sphere((-1.18+i*.59,0,.19),(.2,1.9,.14),'soil_light',8,4)
    return m

def crop_pumpkin():
    m=Mesh('crop_pumpkin');rng=random.Random(4)
    for x,y,s in [(-.4,-.25,.35),(.25,-.2,.42),(.53,.36,.28),(-.38,.4,.25)]:
        m.sphere((x,y,s*.85),(s,s,s*.83),'pumpkin',12,7)
        for i in range(8):
            t=i*2*pi/8;m.sphere((x+s*.62*cos(t),y+s*.62*sin(t),s*.86),(s*.36,s*.36,s*.78),'pumpkin_light' if i%3==0 else 'pumpkin',6,5)
        m.beam((x,y,s*1.55),(x+.05,y,s*1.93),.044,'wood',r2=.025,n=6)
    for i in range(18):
        t=rng.random()*2*pi;r=rng.uniform(.5,1.02);m.leaf((cos(t)*r,sin(t)*r,.12),.53,.42,t,.5,'leaf' if i%3 else 'leaf_light')
    m.tube([(-1+i*.15,.8*sin(i*.6),.07) for i in range(14)],.026,'leaf_dark');return m

def crop_generic(radish=False):
    m=Mesh('crop_generic_radish' if radish else 'crop_generic_leaf');rng=random.Random(6)
    for x in [-.48,0,.48]:
        for y in [-.65,0,.65]:
            if radish:m.sphere((x,y,.13),(.13,.13,.17),'radish',8,5)
            else:m.sphere((x,y,.18),(.18,.19,.16),'leaf_light',8,4)
            for i in range(7):
                a=i*2*pi/7;m.leaf((x+.12*cos(a),y+.12*sin(a),.24),.49 if radish else .4,.13 if radish else .26,a,.8,'leaf' if i%2 else 'leaf_light')
    return m

def scarecrow():
    m=Mesh('scarecrow');m.beam((0,0,0),(0,0,1.95),.07,'wood');m.beam((-.75,0,1.38),(.75,0,1.43),.055,'wood')
    m.sphere((0,0,1.26),(.31,.17,.35),'cloth',8,4,False)
    for s in [-1,1]:m.beam((s*.2,0,1.4),(s*.59,0,1.42),.15,'cloth',r2=.1)
    m.sphere((0,0,1.76),(.21,.17,.22),'skin',8,5)
    m.sphere((0,0,1.94),(.41,.34,.045),'wood_light',12,4);m.sphere((0,0,2.04),(.21,.2,.16),'wood_light',9,4)
    for x in [-.085,.085]:m.sphere((x,-.16,1.78),(.021,.016,.027),'wood_dark',6,3)
    for x in [-.15,.15]:m.beam((x,0,1.02),(x,-.01,.66),.11,'soil_light')
    for s in [-1,1]:
        for i in range(5):m.beam((s*.57,0,1.41),(s*(.76+i*.022),.025*sin(i),1.36+i*.022),.011,'flower_yellow',n=4)
    return m

def sheep():
    m=Mesh('sheep');rng=random.Random(41)
    for x in [-.22,.22]:
        for y in [-.37,.37]:m.beam((x,y,0),(x,y,.46),.064,'face',n=7)
    m.sphere((0,.05,.6),(.43,.64,.38),'wool',12,7)
    for i in range(30):
        t=rng.uniform(0,2*pi);q=rng.uniform(-.9,.9);r=math.sqrt(1-q*q)
        m.sphere((.38*r*cos(t),.05+.56*r*sin(t),.6+.33*q),(.13,.16,.14),'wool',7,4)
    m.sphere((0,-.52,.79),(.2,.27,.25),'face',10,6)
    for x in [-.2,.2]:m.sphere((x,-.52,.9),(.16,.055,.08),'face',7,4)
    for x in [-.11,.11]:
        m.sphere((x,-.735,.85),(.035,.025,.037),'cream',7,4);m.sphere((x,-.757,.85),(.017,.01,.024),'wood_dark',6,3)
    m.sphere((0,-.47,1),(.19,.18,.11),'wool',8,4);return m

BUILDERS.update({'cafe_pavilion':cafe_pavilion,'stone_bridge':stone_bridge,'farm_fence':farm_fence,'farm_soil':farm_soil,'crop_pumpkin':crop_pumpkin,'crop_generic_leaf':lambda:crop_generic(False),'crop_generic_radish':lambda:crop_generic(True),'scarecrow':scarecrow,'sheep':sheep})

def tree(variant=0,blossom=False):
    name='tree_blossom' if blossom else ['tree_large_green','tree_large_gold'][variant]
    m=Mesh(name);rng=random.Random(201+variant+20*blossom);k=.8 if blossom else 1
    cols=['flower_pink','flower_white','flower_hot'] if blossom else (['leaf_light','leaf_gold','leaf'] if variant else ['leaf','leaf_dark','leaf_light'])
    spine=[(0,0,0),(.12,.08,1.5),(-.1,.04,3),(.15,0,4.4),(.35,.1,5.8)]
    for i in range(4):m.beam(tuple(v*k for v in spine[i]),tuple(v*k for v in spine[i+1]),(.39-i*.073)*k,'wood',r2=(.31-i*.067)*k,n=9)
    for i in range(6):
        a=i*2*pi/6;m.beam((.12*cos(a),.12*sin(a),.55*k),(1.02*k*cos(a),.85*k*sin(a),.02),.17*k,'wood',r2=.025,n=7)
    crowns=[]
    for layer in range(4):
        for i in range(3):
            a=i*2*pi/3+layer*.9;r=(1.75-layer*.25)*k;cx=r*cos(a);cy=r*sin(a);cz=(4.7+layer*.67)*k
            crowns.append((cx,cy,cz,(1.55-layer*.12)*k))
            m.beam((0,0,(2.6+layer*.62)*k),(cx,cy,cz-.35*k),.14*k,'wood',r2=.025,n=7)
            m.sphere((cx,cy,cz),(1.22*k,1.03*k,.68*k),cols[0],8,4,True)
    for cx,cy,cz,r in crowns:
        for i in range(89):
            a=rng.uniform(0,2*pi);u=rng.uniform(-1,1);s=math.sqrt(1-u*u)*rng.uniform(.7,1)
            x=cx+r*s*cos(a);y=cy+r*s*sin(a);z=cz+.83*k*u
            m.leaf((x,y,z),rng.uniform(.52,.85)*k,rng.uniform(.27,.48)*k,a,rng.uniform(-.8,.8),rng.choices(cols,[5,2,3])[0])
    return m

def flower_patch(m,c=(0,0,0),color='flower_white',seed=1,scale=1,flowers=15):
    rng=random.Random(seed);x,y,z=c;s=scale
    for i in range(23):
        t=rng.uniform(0,2*pi);r=rng.uniform(.05,.62)*s
        m.leaf((x+r*cos(t),y+r*sin(t),z+.1*s),.54*s,.18*s,t,.65,'leaf' if i%3 else 'leaf_light')
    for i in range(flowers):
        a=rng.uniform(0,2*pi);r=rng.uniform(.07,.5)*s;xx=x+r*cos(a);yy=y+r*sin(a);h=rng.uniform(.22,.55)*s
        m.beam((xx,yy,z+.07*s),(xx,yy,z+h),.009*s,'leaf_dark',n=4)
        if i%4==0:
            for j in range(4):
                m.sphere((xx+.035*s*sin(j),yy,z+h+j*.064*s),(.06*s,.055*s,.065*s),color,5,3)
        else:
            for j in range(5):
                t=j*2*pi/5;rr=.075*s;m.leaf((xx+rr*cos(t),yy+rr*sin(t),z+h),.15*s,.08*s,t,.05,color)
            m.sphere((xx,yy,z+h+.025*s),(.035*s,.035*s,.022*s),'flower_yellow',6,3)

def bush_flower(color='white'):
    m=Mesh('bush_flower_'+color);flower_patch(m,color='flower_'+color,seed={'white':5,'pink':7,'yellow':9}[color]);return m

def vine_hanging():
    m=Mesh('vine_hanging');pts=[(.14*sin(i*.66),.065*cos(i*.7),3.7-i*.145) for i in range(26)];m.tube(pts,.017,'wood',5)
    for i,p in enumerate(pts):
        if i>23:continue
        x,y,z=p
        for s in [-1,1]:m.leaf((x+s*.11,y-.05,z-.07),.33,.22,s*.75,-.8,'leaf' if i%3 else 'leaf_light')
    return m

def ivy_wall():
    m=Mesh('ivy_wall')
    for branch in range(3):
        pts=[((branch-1)*.28+.09*sin(i*.8+branch),0,i*.15) for i in range(14-branch*2)];m.tube(pts,.014,'wood',5)
        for i,(x,y,z) in enumerate(pts):m.leaf((x+.1*(-1)**i,-.06,z),.32,.25,(-1)**i*.7,1.5,'leaf' if i%3 else 'leaf_light')
    return m

def stone_path(variant=0):
    m=Mesh('stone_path_'+str(variant+1));n=7+variant; rng=random.Random(variant+37);r=[rng.uniform(.84,1.08) for i in range(n)]
    vv=[(cos(i*2*pi/n)*r[i]*.52,sin(i*2*pi/n)*r[i]*.4,z) for z in [.02,.13] for i in range(n)]
    m.poly(vv,[tuple(range(n,2*n)),tuple(reversed(range(n)))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],'rock_light' if variant!=1 else 'wall_shade')
    return m

def rock_deco(variant=0):
    m=Mesh('rock_deco_'+str(variant+1));s=[.4,.75,1.15][variant]
    rock(m,(0,0,s*.6),(s,s*.8,s*.6),variant+38)
    for i in range(4):m.sphere((.32*s*cos(i*1.4),.32*s*sin(i*1.4),s*1.04),(.35*s,.26*s,.1*s),'moss',7,3)
    return m

def lamp_post():
    m=Mesh('lamp_post');m.box((0,0,.15),(.45,.45,.3),'rock')
    m.beam((0,0,.2),(0,0,2.85),.105,'wood',r2=.068,n=8)
    m.beam((0,0,2.85),(.67,0,2.85),.072,'wood_light');m.beam((0,0,2.28),(.47,0,2.84),.035,'wood')
    m.beam((.62,0,2.85),(.62,0,2.61),.021,'metal');lantern(m,(.62,0,1.9),.86);return m

def lantern_stone():
    m=Mesh('lantern_stone');m.box((0,0,.1),(.6,.6,.2),'rock');m.beam((0,0,.16),(0,0,.61),.13,'rock',n=6)
    m.box((0,0,.64),(.47,.47,.13),'rock_light');lantern(m,(0,0,.72),.85);return m

def flower_pot(variant=0):
    m=Mesh('flower_pot_'+str(variant+1));m.beam((0,0,.035),(0,0,.41),.2,'terracotta',r2=.31,n=12)
    m.beam((0,0,.39),(0,0,.48),.34,'terracotta',n=12);m.beam((0,0,.48),(0,0,.484),.28,'soil',n=12)
    flower_patch(m,(0,0,.48),'flower_pink' if variant else 'flower_yellow',variant+13,.66,10);return m

def sunflower():
    m=Mesh('sunflower');m.beam((0,0,0),(0,0,1.45),.025,'leaf_dark',n=6)
    for i in range(4):m.leaf((.13*(-1)**i,0,.35+i*.22),.5,.28,0 if i%2 else pi,.4,'leaf')
    for i in range(15):
        t=i*2*pi/15
        # flower disc faces -Y
        x=.235*cos(t);z=1.45+.235*sin(t);r=.13
        m.poly([(x+r*cos(t),-.04,z+r*sin(t)),(x-.065*sin(t),-.055,z+.065*cos(t)),(x-r*cos(t),-.025,z-r*sin(t)),(x+.065*sin(t),-.055,z-.065*cos(t))],[(0,1,2,3)],'flower_yellow')
    m.sphere((0,-.02,1.45),(.19,.085,.19),'soil',12,6);return m

def cloud_puff(variant=0):
    m=Mesh('cloud_puff_'+str(variant+1));rng=random.Random(87+variant)
    for i,(x,y,z,r) in enumerate([(-1.65,0,.72,.85),(-.9,.14,.98,1.03),(0,.15,1.27,1.23),(.9,0,.95,1.04),(1.65,0,.62,.78),(.1,-.6,.65,.84)]):
        x+=rng.uniform(-.15,.15);y+=rng.uniform(-.1,.1)
        m.sphere((x,y,z),(.95*r,.84*r,.86*r),'cloud_warm' if variant==1 else 'cloud',12,6,True)
    return m

def hanging_boat():
    m=Mesh('hanging_boat');n=16;vv=[]
    for sx,sy,z in [(1.23,.43,.4),(1.65,.65,.94),(1.51,.53,.94),(1.06,.29,.52)]:
        vv += [(sx*cos(2*pi*i/n),sy*sin(2*pi*i/n),z) for i in range(n)]
    faces=[]
    for j in range(3):faces += [(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for i in range(n)]
    faces.append(tuple(range(3*n,4*n)));m.poly(vv,faces,'wood')
    for x in [-.85,0,.85]:m.box((x,0,.83),(.19,1.03,.09),'wood_light')
    for side in [-1,1]:
        x=1.3*side;m.box((x,1.1,2.45),(.2,.2,4.9),'wood_dark');m.beam((x,1.1,4.83),(x,-.15,4.83),.12,'wood')
        m.beam((x,1.1,3.72),(x,0,4.8),.075,'wood_light');m.beam((x,-.16,4.52),(x,-.16,4.86),.16,'metal',n=12)
        m.beam((x,-.16,.95),(x,-.16,4.69),.022,'wood_light',n=6)
        m.beam((x,-.16,4.69),(x,1.16,3.6),.022,'wood_light',n=6)
        for y in [-.35,.35]:m.beam((x,-.16,1.45),(x*.84,y,.83),.022,'wood_light',n=6)
    return m

BUILDERS.update({'tree_large_green':lambda:tree(0),'tree_large_gold':lambda:tree(1),'tree_blossom':lambda:tree(0,True),'vine_hanging':vine_hanging,'ivy_wall':ivy_wall,'lamp_post':lamp_post,'lantern_stone':lantern_stone,'sunflower':sunflower,'hanging_boat':hanging_boat})
for col in ['white','pink','yellow']:BUILDERS['bush_flower_'+col]=lambda c=col:bush_flower(c)
for i in range(3):
    BUILDERS['stone_path_'+str(i+1)]=lambda v=i:stone_path(v)
    BUILDERS['rock_deco_'+str(i+1)]=lambda v=i:rock_deco(v)
    BUILDERS['cloud_puff_'+str(i+1)]=lambda v=i:cloud_puff(v)
for i in range(2):BUILDERS['flower_pot_'+str(i+1)]=lambda v=i:flower_pot(v)
