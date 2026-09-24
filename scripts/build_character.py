"""Local Blender character modeling, skinning, animation and glTF export.

No external model generation, paid APIs, or image projection on billboards.
The supplied portrait guides proportions, clothing, hair and accessories.
"""
import argparse
import json
import math
import random
import sys
import struct
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector, Quaternion

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from geometry import Mesh, MATS, material, rgba, look_at

OUT = ROOT / 'assets/character'
RENDERS = ROOT / 'renders/character'
RNG = random.Random(9171219)
PI = math.pi
sin, cos = math.sin, math.cos
PIECES = []


def smooth_path(points, steps=6):
    pp = [Vector(p) for p in points]
    result = []
    for i in range(len(pp)-1):
        a,b,c,d = pp[max(i-1,0)],pp[i],pp[i+1],pp[min(i+2,len(pp)-1)]
        for j in range(steps):
            t=j/steps
            result.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    return result+[pp[-1]]


def tube(m, points, radius, mat, sides=8, squash=1, taper=False):
    pp = [Vector(p) for p in points]
    vv=[];previous_u=None
    for i,p in enumerate(pp):
        t=i/(len(pp)-1)
        direction=(pp[min(i+1,len(pp)-1)]-pp[max(0,i-1)]).normalized()
        axis=Vector((0,1,0))
        if abs(direction.dot(axis))>.93:axis=Vector((1,0,0))
        if previous_u is None:u=direction.cross(axis).normalized()
        else:u=(previous_u-direction*previous_u.dot(direction)).normalized()
        v=direction.cross(u).normalized();previous_u=u
        r=radius(t) if callable(radius) else radius
        if taper:r*=max(.12,sin(PI*(.05+.9*t))**.55)
        for j in range(sides):
            a=2*PI*j/sides
            vv.append(p+u*cos(a)*r+v*sin(a)*r*squash)
    ff=[tuple(reversed(range(sides)))]
    for i in range(len(pp)-1):
        for j in range(sides):ff.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
    ff.append(tuple((len(pp)-1)*sides+j for j in range(sides)))
    m.poly(vv,ff,mat,True)


def curve(m, points, radius, mat, sides=8, steps=6, **kwargs):
    tube(m,smooth_path(points,steps),radius,mat,sides,**kwargs)


def surface(m, rows, mat, close=True, cap=False):
    n=len(rows[0]); vv=[v for row in rows for v in row];ff=[]
    for i in range(len(rows)-1):
        for j in range(n if close else n-1):
            k=(j+1)%n;ff.append((i*n+j,i*n+k,(i+1)*n+k,(i+1)*n+j))
    if cap:ff += [tuple(reversed(range(n))),tuple((len(rows)-1)*n+j for j in range(n))]
    m.poly(vv,ff,mat,True)


def loft(m, rings, mat, n=64, folds=0, amplitude=0, center=(0,0)):
    rows=[]
    for i,(z,rx,ry) in enumerate(rings):
        row=[]
        for j in range(n):
            a=2*PI*j/n;f=amplitude*sin(a*folds+.15*sin(i*.4)) if folds else 0
            row.append((center[0]+(rx+f)*cos(a),center[1]+(ry+f*.65)*sin(a),z))
        rows.append(row)
    surface(m,rows,mat)


def ribbon(m, points, width, mat):
    pp=smooth_path(points,6);rows=[]
    for i,p in enumerate(pp):
        t=i/(len(pp)-1)
        w=width(t) if callable(width) else width
        direction=(pp[min(i+1,len(pp)-1)]-pp[max(0,i-1)]).normalized()
        u=direction.cross(Vector((0,-1,0))).normalized()
        if u.length<.1:u=Vector((1,0,0))
        rows.append([p-u*w/2,p+u*w/2])
    surface(m,rows,mat,False)


def leaf(m, point, length, width, direction, normal, mat='sage_dark'):
    p=Vector(point);u=Vector(direction).normalized()*length;v=Vector(normal).normalized().cross(u).normalized()*width
    n=Vector(normal).normalized()
    m.poly([p,p+u*.45-v*.5,p+u,p+u*.45+v*.5,p+u*.48+n*width*.11],[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],mat,True)


def daisy(m, point, size, normal=(0,-1,0), petals=9):
    p=Vector(point);normal=Vector(normal).normalized();u=normal.cross(Vector((0,0,1))).normalized()
    if u.length<.1:u=Vector((1,0,0))
    v=normal.cross(u).normalized()
    for j in range(petals):
        a=j*2*PI/petals;direction=u*cos(a)+v*sin(a)
        q=p+direction*size*.57
        # A rounded raised petal, closed and thin like embroidered thread.
        rows=[]
        for k in range(9):
            theta=PI*k/8;r=sin(theta);center=q+direction*cos(theta)*size*.39
            across=normal.cross(direction)
            rows.append([center+across*cos(2*PI*l/6)*size*.18*r+normal*sin(2*PI*l/6)*size*.075*r for l in range(6)])
        surface(m,rows,'ivory',True)
    m.sphere(p+normal*size*.08,(size*.23,)*3,'pollen',12,6)


def rounded_box(m,c,s,mat,bevel=.008):
    # Apply a bevel locally, then append its real geometry to the part batch.
    bpy.ops.mesh.primitive_cube_add(size=1,location=c)
    o=bpy.context.object;o.scale=s;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    mod=o.modifiers.new('Rounded leather edges','BEVEL');mod.width=bevel;mod.segments=3
    bpy.ops.object.modifier_apply(modifier=mod.name)
    o.data.update();vv=[o.matrix_world@v.co for v in o.data.vertices]
    m.poly(vv,[tuple(p.vertices) for p in o.data.polygons],mat,True)
    bpy.data.objects.remove(o,do_unlink=True)


def palette():
    specs={
        'skin':('F1BE9F',.48),'skin_warm':('E3A48B',.54),'skin_lip':('CC8774',.48),
        'mouth':('9D6055',.6),'freckle':('B98165',.7),'ivory':('F5ECD9',.7),
        'linen':('E9DFCD',.8),'linen_shadow':('D4C6AC',.83),'sage':('909873',.83),
        'sage_dark':('596B48',.77),'sage_light':('B0B895',.8),'thread':('D5C5A4',.75),
        'hair':('5F3D2B',.46),'hair_dark':('4C3024',.48),'hair_light':('79543C',.48),
        'hair_gold':('916D4E',.52),'straw':('C99B5E',.79),'straw_light':('DFBA80',.83),
        'straw_dark':('AB7D49',.82),'leather':('855536',.48),'leather_light':('AA7953',.54),
        'sole':('4D3527',.71),'eye_white':('FFF3E4',.24),'iris':('925B2C',.25),
        'iris_light':('966639',.34),'iris_dark':('482719',.32),'pupil':('21130F',.18),
        'pollen':('E6B64C',.62),'gold':('B99751',.33),'glint':('FFFAF0',.17)}
    for name,(color,rough) in specs.items():
        m=material(name,color,rough,.7 if name=='gold' else 0)
        p=m.node_tree.nodes.get('Principled BSDF')
        if name.startswith('skin'):p.inputs['Subsurface Weight'].default_value=.075
    # Author tileable cloth color and tangent normals locally in Blender.
    for name in ['linen','sage','straw','leather']:
        mat=MATS[name];nodes=mat.node_tree.nodes;links=mat.node_tree.links;p=nodes.get('Principled BSDF')
        size=256;yy,xx=np.mgrid[0:size,0:size]/size
        field=.96+.035*np.sin(xx*PI*64)*np.cos(yy*PI*64)+.025*np.sin(yy*PI*32)
        rgb=np.array(p.inputs['Base Color'].default_value[:3])[None,None,:]*field[:,:,None]
        pix=np.ones((size,size,4),dtype=np.float32);pix[:,:,:3]=rgb
        im=bpy.data.images.new('character_'+name,width=size,height=size);im.colorspace_settings.name='Linear Rec.709';im.pixels.foreach_set(pix.ravel());im.filepath_raw=str(OUT/'textures'/f'{name}.png');im.file_format='PNG';im.save();im.pack()
        tex=nodes.new('ShaderNodeTexImage');tex.image=im;links.new(tex.outputs['Color'],p.inputs['Base Color'])
        norm=np.ones((size,size,4),dtype=np.float32);norm[:,:,0]=.5+.085*np.cos(xx*PI*64)*np.sin(yy*PI*64);norm[:,:,1]=.5+.085*np.sin(xx*PI*64)*np.cos(yy*PI*64);norm[:,:,2]=.99
        image=bpy.data.images.new('character_'+name+'_normal',width=size,height=size);image.colorspace_settings.name='Non-Color';image.pixels.foreach_set(norm.ravel());image.filepath_raw=str(OUT/'textures'/f'{name}_normal.png');image.file_format='PNG';image.save();image.pack()
        nt=nodes.new('ShaderNodeTexImage');nt.image=image;normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.22;links.new(nt.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],p.inputs['Normal'])


def face_width(z):
    t=(z-1.54)/.188
    return .151*math.sqrt(max(0,1-t*t))*(1-.20*max(0,-t))


def face_y(x,z):
    t=(z-1.54)/.188;rx=max(.0001,face_width(z));ry=.137*math.sqrt(max(0,1-t*t))
    y=.014-ry*math.sqrt(max(0,1-(x/rx)**2))
    y-=.043*math.exp(-(x/.025)**2-((z-1.490)/.027)**2)
    y-=.013*math.exp(-(x/.018)**2-((z-1.535)/.047)**2)
    y-=.005*math.exp(-(x/.052)**2-((z-1.434)/.024)**2)
    return y


def head():
    m=Mesh('Face');rows=[]
    for i in range(1,64):
        z=1.54-.188*cos(PI*i/64);rx=face_width(z);t=(z-1.54)/.188;ry=.137*math.sqrt(max(0,1-t*t));row=[]
        for j in range(96):
            a=2*PI*j/96;x=rx*cos(a)
            y=face_y(x,z) if sin(a)<0 else .014+ry*sin(a)*1.02
            row.append((x,y,z))
        rows.append(row)
    surface(m,rows,'skin');m.sphere((0,.014,1.728),(.007,.006,.003),'skin',12,6);m.sphere((0,.014,1.352),(.006,.006,.003),'skin',12,6)
    loft(m,[(1.235,.102,.046),(1.27,.081,.043),(1.304,.045,.037),(1.35,.037,.036),(1.39,.043,.039)],'skin',48,center=(0,.013))
    for side in [-1,1]:
        m.sphere((side*.140,.013,1.507),(.022,.017,.029),'skin',24,14)
        m.sphere((side*.150,-.002,1.507),(.011,.007,.019),'skin_warm',18,10)
        cx=side*.062;cz=1.552
        def eye_surface(x,z):
            d=((x-cx)/.043)**2+((z-cz)/(.030 if z>=cz else .024))**2
            return face_y(x,z)-.0015-.014*max(0,1-d)
        rows=[]
        for k in range(13):
            r=.001+.999*k/12
            rows.append([(cx+.043*r*cos(a),eye_surface(cx+.043*r*cos(a),cz+(.030 if sin(a)>0 else .024)*r*sin(a)),cz+(.030 if sin(a)>0 else .024)*r*sin(a)) for a in [j*2*PI/64 for j in range(64)]])
        surface(m,rows,'eye_white')
        # Iris cap follows the eye instead of a flat disk pasted on the face.
        for k in range(11):
            r0=.024*k/11;r1=.024*(k+1)/11
            for j in range(48):
                a=j*2*PI/48;b=(j+1)*2*PI/48
                vv=[(cx+r*cos(t),eye_surface(cx+r*cos(t),cz+r*sin(t))-.0005,cz+r*sin(t)) for r,t in [(r0,a),(r1,a),(r1,b),(r0,b)]]
                mat='iris_dark' if k>9 else ('pupil' if k<6 else ['iris','iris_light','iris','iris'][j%4])
                m.poly(vv,[(0,1,2,3)],mat,True)
        for dx,dz,r in [(-.007,.010,.005),(.009,-.010,.002)]:m.sphere((cx+dx,eye_surface(cx+dx,cz+dz)-.002,cz+dz),(r,.0015,r),'glint',14,8)
        upper=[(cx+.043*cos(a),eye_surface(cx+.043*cos(a),cz+.030*sin(a))-.001,cz+.030*sin(a)) for a in [j*PI/32 for j in range(33)]]
        lower=[(cx+.043*cos(a),eye_surface(cx+.043*cos(a),cz+.024*sin(a))-.001,cz+.024*sin(a)) for a in [PI+j*PI/32 for j in range(33)]]
        tube(m,upper,.0030,'skin_warm',8);tube(m,lower,.0019,'skin',8)
        tube(m,[(x,y-.0017,z-.0008) for x,y,z in upper],lambda t:.0006+.0014*sin(PI*t),'hair_dark',6)
        for j in range(3):
            x=cx+side*(.032+j*.003);z=cz+.019-j*.004;y=eye_surface(x,z)-.002
            curve(m,[(x,y,z),(x+side*.006,y-.003,z+.003),(x+side*.009,y-.002,z+.007)],lambda t:.0012*(1-t)+.0002,'hair_dark',5,3)
        brow=[(cx-.040,face_y(cx-.040,1.607)-.007,1.607),(cx-.016,face_y(cx-.016,1.620)-.007,1.620),(cx+.013,face_y(cx+.013,1.621)-.007,1.621),(cx+.039,face_y(cx+.039,1.609)-.007,1.609)]
        curve(m,brow,lambda t:.0015+.0035*sin(PI*t),'hair',8,7,squash=.5)
        for j in range(11):
            x=side*RNG.uniform(.052,.103);z=RNG.uniform(1.480,1.509);r=RNG.uniform(.0008,.0015)
            m.sphere((x,face_y(x,z)-.001,z),(r,.00045,r*.8),'freckle',8,4)
        x=side*.010;z=1.479;m.sphere((x,face_y(x,z)-.0002,z),(.0034,.0009,.0017),'skin_lip',10,6)
    curve(m,[(-.034,face_y(-.034,1.439)-.001,1.439),(-.014,face_y(-.014,1.433)-.002,1.433),(0,face_y(0,1.432)-.002,1.432),(.014,face_y(.014,1.433)-.002,1.433),(.034,face_y(.034,1.439)-.001,1.439)],.0018,'mouth',7,5)
    curve(m,[(-.027,face_y(-.027,1.436)-.002,1.432),(0,face_y(0,1.43)-.003,1.428),(.027,face_y(.027,1.436)-.002,1.432)],lambda t:.0008+.0021*sin(PI*t),'skin_lip',7,6)
    return m


def hair():
    m=Mesh('Wavy_Hair');rows=[]
    for i in range(28):
        row=[];t=(i+.05)/27.05
        for j in range(80):
            a=j*2*PI/80;front=max(0,-sin(a));end=2.08-1.10*front**2;p=t*end
            row.append((.159*sin(p)*cos(a),.025+.142*sin(p)*sin(a),1.545+.191*cos(p)))
        rows.append(row)
    surface(m,rows,'hair_dark')
    for j in range(42):
        a=-.10+(PI+.20)*j/41;length=.57+RNG.uniform(0,.17);phase=j*1.13;pts=[]
        for i in range(49):
            t=i/48;r=.068+.105*sin(min(1,t*3)*PI/2)
            x=r*cos(a)+.017*sin(t*PI*4+phase)*sin(PI*t*.86)
            y=.037+(r+.010)*sin(a)+.019*cos(t*PI*4+phase)*sin(PI*t)
            z=1.715-length*t
            pts.append((x,y,z))
        tube(m,pts,lambda t:.016*(.60+.40*sin(PI*(.12+.80*t)))*(1-.87*t**5),['hair','hair_light','hair','hair'][j%4],10,squash=.75)
        for offset in [-.004,.004]:
            tube(m,[(x+offset,y-.010,z) for x,y,z in pts],lambda t:.00065*(1-.8*t),'hair_gold' if j%3 else 'hair_dark',5)
    for side in [-1,1]:
        for j in range(5):
            a=j*.008
            pts=[(-.027+side*a,-.092,1.715-a*.3),(side*.063,-.132,1.691-a),(side*.124,-.115,1.625-a),(side*.154,-.077,1.561-a),(side*.150,-.058,1.493-a)]
            curve(m,pts,.010-j*.0008,'hair' if j%2 else 'hair_light',9,8,squash=.48,taper=True)
        for j in range(4):
            pts=[]
            for i in range(34):
                t=i/33;pts.append((side*(.146+j*.010+.019*sin(t*13+j)), -.008-.025*sin(t*10+j),1.55-.47*t))
            tube(m,pts,lambda t:.010*(1-.8*t*t),'hair_light' if j==1 else 'hair',8,squash=.7)
    return m


def hat():
    m=Mesh('Woven_Straw_Hat');rows=[]
    def point(r,a):
        return Vector((.32*r*cos(a),.275*r*sin(a),1.726+.055*r*r+.030*cos(a+.2)*r**3-.031*sin(a)*r))
    for i in range(18):rows.append([point(.42+.58*i/17,j*2*PI/112) for j in range(112)])
    surface(m,rows,'straw')
    # Concentric braided straw courses and interleaved radial strands.
    for j in range(34):
        r=.44+.56*j/33
        tube(m,[point(r,i*2*PI/112)+Vector((0,0,.0012*sin(i*PI/2+j))) for i in range(113)],.00095,'straw_light' if j%3 else 'straw_dark',4)
    for j in range(84):
        a=j*2*PI/84
        tube(m,[point(.43+.57*i/20,a)+Vector((0,0,.0011*cos(i*PI+j))) for i in range(21)],.00062,'straw_light',4)
    tube(m,[point(1,i*2*PI/128) for i in range(129)],.0032,'straw_dark',7)
    loft(m,[(1.735,.15,.126),(1.765,.151,.127),(1.806,.143,.119),(1.839,.124,.10),(1.852,.087,.071),(1.856,.003,.003)],'straw',80)
    for j in range(19):
        z=1.741+j*.0058;t=(z-1.735)/.12;rx=.151*(1-.36*t*t);ry=.127*(1-.36*t*t)
        tube(m,[(rx*cos(a),ry*sin(a),z) for a in [i*2*PI/80 for i in range(81)]],.0010,'straw_light',4)
    loft(m,[(1.749,.153,.129),(1.781,.153,.129)],'sage_dark',80)
    tube(m,[(.154*cos(a),.13*sin(a),1.752) for a in [i*2*PI/80 for i in range(81)]],.0009,'sage_light',5)
    for x,z,s in [(-.112,1.79,.022),(-.147,1.766,.020),(-.089,1.77,.017)]:daisy(m,(x,-.095,z),s,(0,-1,.3))
    for j in range(7):leaf(m,(-.115,-.095,1.77),.045,.017,(cos(j*.9),-.1,sin(j*.9)),(0,-1,.3))
    # Slight tilt is part of the reference silhouette and is local to the hat.
    pivot=Vector((0,0,1.73));q=Quaternion(Vector((0,1,0)),.17)@Quaternion(Vector((1,0,0)),.18)
    m.v=[pivot+q@(Vector(v)-pivot)-Vector((0,0,.035)) for v in m.v]
    return m


def torso():
    m=Mesh('Linen_Blouse');loft(m,[(.98,.088,.059),(1.04,.100,.070),(1.12,.118,.080),(1.21,.138,.072),(1.27,.126,.059)],'linen',64,folds=13,amplitude=.002)
    # Wide softly gathered neckline, leaving the neck visible.
    rows=[]
    for r in [.70,.83,1]:
        rows.append([(.126*r*cos(a),.06*r*sin(a),1.272-.035*max(0,-sin(a))+.003*sin(a*30)) for a in [j*2*PI/80 for j in range(80)]])
    surface(m,rows,'ivory')
    for r in [.72,1]:tube(m,[(.126*r*cos(a),.06*r*sin(a),1.273-.035*max(0,-sin(a))+.003*sin(a*30)) for a in [j*2*PI/100 for j in range(101)]],.002,'linen_shadow',5)
    for z in [1.135,1.172,1.209]:
        m.sphere((0,-.085,z),(.0048,.002,.0048),'gold',12,8)
        curve(m,[(-.007,-.084,z-.010),(-.007,-.084,z+.012)],.0005,'thread',4,3)
    return m


def sleeve(side):
    m=Mesh('Sleeve');rows=[]
    for i in range(36):
        t=i/35;x=side*(.125+.432*t)
        radius=.042+.027*sin(PI*t)**.7-.015*t**5
        row=[]
        for j in range(40):
            a=j*2*PI/40;r=radius+.0028*sin(a*12+t*7)
            row.append((x,r*cos(a),1.265+r*sin(a)-.006*t))
        rows.append(row)
    surface(m,rows,'linen')
    # Gathered cuff and a small scalloped ruffle.
    rows=[]
    for i in range(5):
        t=i/4;row=[]
        for j in range(48):
            a=j*2*PI/48;r=.032+.009*t+.003*sin(a*14)
            row.append((side*(.546+t*.023),r*cos(a),1.259+r*sin(a)))
        rows.append(row)
    surface(m,rows,'ivory')
    tube(m,[(side*.548,.031*cos(a),1.259+.031*sin(a)) for a in [i*2*PI/48 for i in range(49)]],.002,'linen_shadow',6)
    return m


def hand(side):
    m=Mesh('Hand');curve(m,[(side*.52,0,1.26),(side*.575,0,1.26),(side*.611,0,1.26)],lambda t:.026-.006*t,'skin',16,5,squash=.7)
    m.sphere((side*.610,0,1.259),(.040,.026,.018),'skin',24,16)
    fingers=[]
    for j,(y,length) in enumerate([(-.019,.057),(-.006,.065),(.008,.059),(.021,.048)]):
        x=.635;pts=[(side*x,y,1.26),(side*(x+length*.47),y*1.2,1.259),(side*(x+length*.86),y*1.3,1.255),(side*(x+length),y*1.3,1.251)]
        curve(m,pts,lambda t:.0062*(1-.48*t),'skin',10,5)
        m.sphere(pts[-1],(.0034,.0035,.0035),'skin',10,6)
        fingers.append((f'finger_{j}',pts[0],pts[2]))
        m.sphere((side*(x+length*.85),y*1.3,1.260),(.006,.0038,.0007),'ivory',10,5)
    pts=[(side*.601,-.019,1.257),(side*.611,-.037,1.25),(side*.635,-.045,1.245),(side*.647,-.042,1.243)]
    curve(m,pts,lambda t:.009*(1-.46*t),'skin',10,6);fingers.append(('thumb',pts[0],pts[-1]))
    return m,fingers


def skirt():
    m=Mesh('Sage_Embroidered_Dress');rings=[]
    for i in range(40):
        t=i/39;z=.526+.510*t;rx=.252-(.252-.103)*t**.76;ry=.174-(.174-.076)*t**.80
        rings.append((z,rx,ry))
    loft(m,rings,'sage',96,folds=17,amplitude=.0055)
    loft(m,[(1.017,.109,.081),(1.070,.117,.086),(1.112,.125,.087)],'sage',64,folds=14,amplitude=.0015)
    for side in [-1,1]:
        pts=[(side*.087,-.070,1.102),(side*.10,-.060,1.20),(side*.112,-.033,1.274),(side*.108,.029,1.285),(side*.09,.074,1.14),(side*.075,.078,1.03)]
        ribbon(m,pts,.024,'sage');curve(m,[(x+side*.010,y-.001,z) for x,y,z in pts],.001,'thread',5,5)
    for z in [1.035,1.067,1.098]:m.sphere((0,-.08,z),(.0045,.002,.0045),'gold',12,6)
    loft(m,[(1.006,.116,.088),(1.031,.116,.088)],'sage_dark',72)
    for side in [-1,1]:
        ribbon(m,[(0,-.093,1.021),(side*.045,-.110,1.051),(side*.066,-.102,1.026),(side*.030,-.104,1.008),(0,-.093,1.021)],lambda t:.016+.008*sin(PI*t),'sage')
        ribbon(m,[(side*.006,-.094,1.018),(side*.022,-.105,.977),(side*.033,-.131,.891),(side*.036,-.145,.849)],lambda t:.019-.004*t,'sage')
    m.sphere((0,-.105,1.024),(.014,.010,.012),'sage_dark',16,10)
    # The embroidered hem wraps around the full garment, including the back.
    for j in range(22):
        a=j*2*PI/22;z=.567+.017*sin(j*2.2);rx=.241;ry=.165
        p=Vector((rx*cos(a),ry*sin(a),z));n=Vector((cos(a),sin(a),.1))
        daisy(m,p,.012+(j%3)*.002,n,8)
        tangent=Vector((-sin(a),cos(a),0))
        curve(m,[p-tangent*.026-Vector((0,0,.025)),p-Vector((0,0,.018)),p+tangent*.023+Vector((0,0,.022))],.0011,'sage_dark',5,4)
        for side in [-1,1]:leaf(m,p+tangent*side*.018-Vector((0,0,.01)),.018,.007,tangent*side+Vector((0,0,.65)),n,'sage_light')
    for z,rx,ry in [(.535,.252,.174),(.609,.230,.158)]:
        for j in range(120):
            a=j*2*PI/120;b=a+.025
            tube(m,[(rx*cos(a),ry*sin(a),z),(rx*cos(b),ry*sin(b),z)],.00062,'thread',4)
    return m


def petticoat():
    m=Mesh('Layered_Petticoat')
    for layer in range(2):
        rows=[]
        for i in range(10):
            t=i/9;z=.456+layer*.028+t*.073;rx=.274-.060*t;ry=.19-.048*t
            rows.append([((rx+.007*sin(a*32))*cos(a),(ry+.006*sin(a*32))*sin(a),z+.006*cos(a*32)*(1-t)) for a in [j*2*PI/128 for j in range(128)]])
        surface(m,rows,'ivory' if layer==0 else 'linen')
    return m


def legs():
    m=Mesh('Legs')
    for side in [-1,1]:
        curve(m,[(side*.063,.015,.95),(side*.070,.012,.76),(side*.071,-.007,.57),(side*.069,.005,.43),(side*.067,.012,.23),(side*.067,.01,.13)],lambda t:.047-.021*t+.005*sin(PI*t),'skin',20,8)
    vv=[]
    for x,y,z in m.v:
        t=max(0,min(1,(.36-z)/.07));center=.067 if x>0 else -.067
        vv.append((center+(x-center)*(1-.22*t),.01+(y-.01)*(1-.27*t),z))
    m.v=vv
    return m


def boots():
    m=Mesh('Laced_Boots')
    for side in [-1,1]:
        x=side*.067
        vv=[(x+.055*cos(a),-.037+.117*sin(a),.015) for a in [i*2*PI/56 for i in range(56)]]
        m.poly(vv,[tuple(reversed(range(56)))],'sole')
        loft(m,[(.015,.055,.117),(.027,.061,.124),(.05,.061,.124),(.057,.056,.118)],'sole',56,center=(x,-.037))
        loft(m,[(.052,.055,.115),(.071,.057,.116),(.098,.051,.101),(.123,.043,.073),(.149,.036,.054)],'leather',56,center=(x,-.037))
        loft(m,[(.103,.047,.083),(.136,.041,.064),(.161,.041,.053),(.24,.042,.045),(.293,.045,.043)],'leather',48,center=(x,0))
        loft(m,[(.288,.044,.041),(.305,.043,.040)],'leather_light',48,center=(x,.009))
        # Rolled knit sock cuff and fine ribs.
        loft(m,[(.288,.041,.039),(.331,.043,.040),(.353,.046,.041),(.367,.044,.040)],'linen',48,center=(x,.009))
        for j in range(24):
            a=j*2*PI/24;curve(m,[(x+.035*cos(a),.009+.032*sin(a),.303),(x+.039*cos(a),.009+.034*sin(a),.352),(x+.038*cos(a),.009+.034*sin(a),.365)],.0009,'ivory',5,4)
        for row in range(7):
            z=.140+row*.022;y=-.050+row*.0023
            for sign in [-1,1]:
                c=Vector((x+sign*.026,y,z))
                tube(m,[c+Vector((.0035*cos(a),0,.0035*sin(a))) for a in [j*2*PI/12 for j in range(13)]],.001,'gold',5)
            if row<6:
                for sign in [-1,1]:curve(m,[(x+sign*.026,y-.003,z),(x,y-.009,z+.011),(x-sign*.026,y-.001,z+.022)],.0016,'straw_dark',5,5)
        for sign in [-1,1]:curve(m,[(x,-.040,.291),(x+sign*.029,-.046,.311),(x+sign*.032,-.048,.288),(x,-.040,.291),(x+sign*.020,-.045,.255)],.002,'leather_light',6,6)
        for j in range(64):
            a=j*2*PI/64;b=a+.06
            tube(m,[(x+.058*cos(a),-.037+.121*sin(a),.047),(x+.058*cos(b),-.037+.121*sin(b),.047)],.0007,'thread',4)
    m.v=[(x,y*.87,.115+(z-.115)*.70 if z>.115 else z) for x,y,z in m.v]
    return m


def bag():
    m=Mesh('Leather_Satchel');center=Vector((-.183,-.067,.924))
    rounded_box(m,center,(.135,.072,.158),'leather',.020)
    rounded_box(m,center+Vector((0,-.034,.036)),(.139,.016,.084),'leather_light',.015)
    for side in [-1,1]:
        x=center.x+side*.038
        rounded_box(m,(x,center.y-.047,.874),(.019,.008,.063),'leather_light',.004)
        pts=[(x-.009,-.12,.897),(x+.009,-.12,.897),(x+.009,-.12,.875),(x-.009,-.12,.875),(x-.009,-.12,.897)]
        tube(m,pts,.0018,'gold',6)
        curve(m,[(x,-.122,.875),(x,-.122,.89)],.001,'gold',5,3)
    for sign in [-1,1]:
        x=center.x+sign*.057
        for j in range(15):tube(m,[(x,-.106,.861+j*.009),(x,-.106,.865+j*.009)],.00065,'thread',4)
    daisy(m,(-.170,-.12,.958),.017,(0,-1,.1),9)
    leaf(m,(-.178,-.12,.950),.033,.014,(-.5,0,-1),(0,-1,0))
    return m


def strap():
    m=Mesh('Satchel_Strap')
    pp=[(-.179,-.087,.99),(-.150,-.10,1.10),(-.114,-.083,1.22),(-.104,-.026,1.293),(-.11,.047,1.271),(-.145,.088,1.12),(-.182,.043,.987)]
    ribbon(m,pp,.021,'leather');curve(m,[(x+.008,y-.0006,z) for x,y,z in pp],.0008,'thread',5,6)
    return m


def watering_can():
    m=Mesh('Watering_Can')
    loft(m,[(-.07,.058,.053),(-.062,.073,.064),(.056,.070,.063),(.073,.060,.054)],'sage_dark',40)
    m.sphere((0,0,-.065),(.064,.057,.006),'sage_dark',32,8)
    tube(m,[(.061*cos(a),.055*sin(a),.073) for a in [i*2*PI/48 for i in range(49)]],.003,'gold',6)
    curve(m,[(0,.045,.04),(0,.075,.09),(0,.048,.17),(0,-.034,.17),(0,-.050,.05)],.006,'leather',10,9)
    curve(m,[(0,-.050,-.030),(0,-.11,.005),(0,-.17,.055),(0,-.191,.060)],lambda t:.018-.010*t,'sage_dark',12,7)
    m.sphere((0,-.193,.061),(.025,.012,.022),'gold',24,12)
    for j in range(7):
        a=j*2*PI/7;m.sphere((.015*cos(a),-.204,.061+.013*sin(a)),(.0018,.001,.0018),'sole',8,4)
    daisy(m,(.066,-.018,.01),.018,(1,-.1,0))
    q=Vector((0,0,1)).rotation_difference(Vector((-1,0,0)))
    m.v=[q@Vector(v)+Vector((.81,0,1.26)) for v in m.v]
    return m


def emit(m, weight, tint=False):
    obj=m.object();obj['part']=m.name;obj['source']='Local Blender procedural modeling from supplied portrait'
    # Portable projected UVs for small repeating fabric textures.
    mesh=obj.data;uv=mesh.uv_layers.new(name='FabricUV')
    for p in mesh.polygons:
        normal=p.normal;axis=max(range(3),key=lambda i:abs(normal[i]));indices=[i for i in range(3) if i!=axis]
        for loop in p.loop_indices:
            v=mesh.vertices[mesh.loops[loop].vertex_index].co
            uv.data[loop].uv=(v[indices[0]]*4,v[indices[1]]*4)
    if tint:
        skin=MATS['skin'].copy();skin.name='Face_Skin_with_Blush';mesh.materials[mesh.materials.find('skin')]=skin
        color=mesh.color_attributes.new(name='SkinTint',type='FLOAT_COLOR',domain='POINT')
        base=np.array(rgba('F1BE9F')[:3]);blush=np.array(rgba('E69283')[:3])
        for v,item in zip(mesh.vertices,color.data):
            x,y,z=v.co;amount=.40*math.exp(-((abs(x)-.084)/.031)**2-((z-1.492)/.025)**2)*max(0,min(1,(-y-.015)/.065))
            item.color=(*(base*(1-amount)+blush*amount),1)
        nodes=skin.node_tree.nodes;attr=nodes.new('ShaderNodeVertexColor');attr.layer_name='SkinTint';skin.node_tree.links.new(attr.outputs['Color'],nodes.get('Principled BSDF').inputs['Base Color'])
    PIECES.append((obj,weight))
    return obj


def torso_weights(v):
    z=v.z
    if z<1.04:return {'pelvis':1}
    if z<1.17:
        t=(z-1.04)/.13;return {'spine':1-t,'chest':t}
    return {'chest':1}


def arm_weights(side):
    tag='L' if side>0 else 'R'
    def weight(v):
        x=abs(v.x)
        if x<.17:return {'chest':max(0,(.17-x)/.055),f'upper_arm.{tag}':min(1,(x-.115)/.055)}
        if x<.325:return {f'upper_arm.{tag}':1}
        if x<.405:
            t=(x-.325)/.08;return {f'upper_arm.{tag}':1-t,f'forearm.{tag}':t}
        if x<.555:return {f'forearm.{tag}':1}
        if x<.594:
            t=(x-.555)/.039;return {f'forearm.{tag}':1-t,f'hand.{tag}':t}
        return {f'hand.{tag}':1}
    return weight


def leg_weights(v):
    tag='L' if v.x>=0 else 'R'
    if v.z<.18:return {f'foot.{tag}':1}
    if v.z<.51:return {f'shin.{tag}':1}
    if v.z<.61:
        t=(v.z-.51)/.10;return {f'shin.{tag}':1-t,f'thigh.{tag}':t}
    return {f'thigh.{tag}':1}


def dress_weights(v):
    if v.z>1.04:return torso_weights(v)
    amount=max(0,min(.60,(.98-v.z)/.43*.60))
    axis=('front' if v.y<0 else 'back') if abs(v.y)*1.3>abs(v.x) else ('left' if v.x>0 else 'right')
    return {'pelvis':1-amount,'skirt_'+axis:amount}


def create_rig():
    data=bpy.data.armatures.new('Daisy_Character_Rig');rig=bpy.data.objects.new('Daisy_Rig',data);bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    specs={
        'root':((0,0,0),(0,0,.12),None),
        'pelvis':((0,0,.94),(0,0,1.025),'root'),
        'spine':((0,0,1.025),(0,0,1.17),'pelvis'),
        'chest':((0,0,1.17),(0,0,1.29),'spine'),
        'neck':((0,0,1.29),(0,0,1.38),'chest'),
        'head':((0,0,1.38),(0,0,1.70),'neck'),
        'hat':((0,0,1.72),(0,0,1.85),'head'),
        'hair_back':((0,.1,1.58),(0,.14,1.06),'head'),
        'hair_left':((.14,.03,1.58),(.17,.02,1.07),'head'),
        'hair_right':((-.14,.03,1.58),(-.17,.02,1.07),'head'),
        'bag':((-.183,-.05,1.01),(-.183,-.05,.845),'pelvis')}
    for name,(x,y) in {'front':(0,-.075),'back':(0,.075),'left':(.10,0),'right':(-.10,0)}.items():specs['skirt_'+name]=((x,y,.985),(x*2,y*2,.51),'pelvis')
    for side,tag in [(-1,'R'),(1,'L')]:
        specs.update({
            f'upper_arm.{tag}':((side*.14,0,1.265),(side*.37,0,1.26),'chest'),
            f'forearm.{tag}':((side*.37,0,1.26),(side*.58,0,1.26),f'upper_arm.{tag}'),
            f'hand.{tag}':((side*.58,0,1.26),(side*.69,0,1.26),f'forearm.{tag}'),
            f'thigh.{tag}':((side*.063,.015,.94),(side*.071,-.007,.57),'pelvis'),
            f'shin.{tag}':((side*.071,-.007,.57),(side*.067,.012,.16),f'thigh.{tag}'),
            f'foot.{tag}':((side*.067,.012,.16),(side*.067,-.10,.055),f'shin.{tag}')})
    for name,(h,t,parent) in specs.items():
        bone=data.edit_bones.new(name);bone.head=h;bone.tail=t
        if parent:bone.parent=data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True
    for obj,weight in PIECES:
        obj.parent=rig
        groups={name:obj.vertex_groups.new(name=name) for name in specs}
        for v in obj.data.vertices:
            weights=weight(v.co) if callable(weight) else {weight:1}
            weights={n:max(0,w) for n,w in weights.items() if w>0}
            total=sum(weights.values())
            for name,value in weights.items():groups[name].add([v.index],value/total,'REPLACE')
        mod=obj.modifiers.new('Character skin','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=True
    return rig


def rotate_world(rig,name,axis,angle):
    pb=rig.pose.bones[name];basis=pb.bone.matrix_local.to_quaternion();q=Quaternion(Vector(axis),angle)
    pb.rotation_quaternion=basis.inverted()@q@basis


def pose_arm(rig,side,tag,swing=0,bend=.11):
    # Aim upper arm and forearm in the chest coordinate system. A rest-bone
    # local-X rotation alone would twist these T-pose arms instead of reaching.
    down=Vector((side*.27,-.015,-.963)).normalized()
    directions=[Quaternion((1,0,0),swing)@down,Quaternion((1,0,0),swing-bend)@down]
    parent_q=Quaternion()
    for name,direction in zip([f'upper_arm.{tag}',f'forearm.{tag}'],directions):
        pb=rig.pose.bones[name];bone=pb.bone;basis=bone.matrix_local.to_quaternion()
        absolute=(bone.tail_local-bone.head_local).normalized().rotation_difference(direction)
        relative=parent_q.inverted()@absolute
        pb.rotation_quaternion=basis.inverted()@relative@basis
        parent_q=absolute


def animate(rig,ground_mesh=None,ground_height=.015):
    rig.animation_data_create();clips={}
    for name,frames in [('Idle',72),('Walk',32),('Plant',52),('Water',72),('Harvest',56)]:
        action=bpy.data.actions.new(name);rig.animation_data.action=action
        for frame in range(1,frames+2,2):
            t=(frame-1)/frames;phase=t*2*PI;gesture=sin(PI*t)**2
            for pb in rig.pose.bones:pb.rotation_mode='QUATERNION';pb.rotation_quaternion=Quaternion();pb.location=(0,0,0)
            for side,tag in [(-1,'R'),(1,'L')]:
                pose_arm(rig,side,tag)
            if name=='Idle':
                rotate_world(rig,'chest',(1,0,0),sin(phase)*.012)
                rotate_world(rig,'head',(0,0,1),sin(phase)*.025)
            elif name=='Walk':
                for side,tag in [(-1,'R'),(1,'L')]:
                    swing=sin(phase)*side
                    rotate_world(rig,f'thigh.{tag}',(1,0,0),swing*.18)
                    rotate_world(rig,f'shin.{tag}',(1,0,0),max(0,swing)*.22)
                    rotate_world(rig,f'foot.{tag}',(1,0,0),-swing*.10)
                    pose_arm(rig,side,tag,-swing*.24,.11+max(0,swing)*.10)
                rig.pose.bones['pelvis'].location.y=abs(sin(phase))*.010
                rotate_world(rig,'pelvis',(0,0,1),sin(phase)*.025)
            else:
                depth=.25 if name=='Water' else .43
                rotate_world(rig,'spine',(1,0,0),gesture*depth)
                rotate_world(rig,'head',(1,0,0),gesture*.16)
                for side,tag in [(-1,'R'),(1,'L')]:
                    pose_arm(rig,side,tag,-gesture*(.72 if name=='Water' else .48),.11+gesture*(.63 if name=='Harvest' else .44))
            for part,scale in [('hair_back',.018),('hair_left',.023),('hair_right',-.023),('bag',.025),('skirt_front',.022),('skirt_back',-.020),('skirt_left',.014),('skirt_right',-.014)]:
                rig.pose.bones[part].rotation_quaternion=Quaternion(Vector((1,0,0)),sin(phase)*scale)
            if name=='Walk':
                bpy.context.view_layer.update()
                obj=(ground_mesh or bpy.data.objects['Laced_Boots']).evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=obj.to_mesh()
                lowest=min(v.co.z for v in mesh.vertices);obj.to_mesh_clear()
                rig.pose.bones['pelvis'].location.y-=lowest-ground_height
            for pb in rig.pose.bones:
                pb.keyframe_insert('rotation_quaternion',frame=frame,group=pb.name)
                if pb.name=='pelvis':pb.keyframe_insert('location',frame=frame,group=pb.name)
        action.use_fake_user=True;clips[name]=action
    rig.animation_data.action=clips['Idle'];bpy.context.scene.frame_set(1)
    return clips


def setup_stage(width,samples):
    sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=samples;sc.cycles.use_denoising=True
    sc.cycles.device='GPU'
    prefs=bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type='METAL';prefs.get_devices()
        for d in prefs.devices:d.use=d.type=='METAL'
    except Exception:sc.cycles.device='CPU'
    sc.world.color=(.35,.35,.35);sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs['Color'].default_value=rgba('DCD7D1');sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
    sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.view_settings.exposure=.3
    for name,pos,power,size,color in [('Softbox',(-3,-4,5),420,4,'FFF0DB'),('Fill',(3,-2,3),230,3,'E4ECFA'),('Rim',(1,3,4),500,3,'FFDCA9')]:
        data=bpy.data.lights.new(name,'AREA');o=bpy.data.objects.new(name,data);sc.collection.objects.link(o);o.location=pos;data.energy=power;data.shape='DISK';data.size=size;data.color=rgba(color)[:3];look_at(o,(0,0,1))
    ground=material('studio_ground','D9D3C5',.92)
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,.002));o=bpy.context.object;o.name='Studio_Ground';o.data.materials.append(ground)
    data=bpy.data.cameras.new('Character_Camera');cam=bpy.data.objects.new('Character_Camera',data);sc.collection.objects.link(cam);sc.camera=cam;cam.location=(2.5,-7,2.6);look_at(cam,(0,0,.94));data.type='ORTHO';data.ortho_scale=2.12;data.lens=60
    sc.render.resolution_x=width;sc.render.resolution_y=round(width*1.25);sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
    return cam


def repair_degenerate_tangents(filepath):
    # Collapsed UV corners can produce a zero tangent in Blender. Choose an
    # orthogonal unit vector only for those corners; retain every valid tangent.
    raw=bytearray(filepath.read_bytes());length=struct.unpack_from('<I',raw,12)[0]
    data=json.loads(raw[20:20+length]);start=28+length;count=0
    for mesh in data['meshes']:
        for primitive in mesh['primitives']:
            attrs=primitive['attributes']
            if 'TANGENT' not in attrs:continue
            ta=data['accessors'][attrs['TANGENT']];na=data['accessors'][attrs['NORMAL']]
            tv=data['bufferViews'][ta['bufferView']];nv=data['bufferViews'][na['bufferView']]
            for i in range(ta['count']):
                tp=start+tv.get('byteOffset',0)+ta.get('byteOffset',0)+i*tv.get('byteStride',16)
                t=struct.unpack_from('<4f',raw,tp)
                if sum(v*v for v in t[:3])>.5:continue
                np_=start+nv.get('byteOffset',0)+na.get('byteOffset',0)+i*nv.get('byteStride',12)
                n=Vector(struct.unpack_from('<3f',raw,np_));axis=Vector((1,0,0)) if abs(n.x)<.8 else Vector((0,1,0));u=(axis-n*axis.dot(n)).normalized()
                struct.pack_into('<4f',raw,tp,*u,1);count+=1
    filepath.write_bytes(raw);return count


def main(args):
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'textures').mkdir(exist_ok=True);RENDERS.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);MATS.clear();palette()
    emit(head(),'head',True);emit(hair(),lambda v:{'head':1-max(0,min(.65,(1.52-v.z)*1.5)),('hair_left' if v.x>.07 else 'hair_right' if v.x<-.07 else 'hair_back'):max(0,min(.65,(1.52-v.z)*1.5))});emit(hat(),'hat')
    emit(torso(),torso_weights);emit(skirt(),dress_weights);emit(petticoat(),dress_weights);emit(legs(),leg_weights);emit(boots(),leg_weights);emit(bag(),'bag');emit(strap(),torso_weights)
    for side in [-1,1]:emit(sleeve(side),arm_weights(side));m,_=hand(side);emit(m,arm_weights(side))
    can=emit(watering_can(),'hand.L');can.hide_render=True
    rig=create_rig();clips=animate(rig);cam=setup_stage(args.width,args.samples);sc=bpy.context.scene;sc.render.fps=24
    sc.frame_end=73
    for obj,_ in PIECES:obj.data.validate(verbose=False);obj.data.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'daisy_character.blend'),compress=True)
    if not args.no_render:
        sc.render.filepath=str(RENDERS/'character_hero.png');bpy.ops.render.render(write_still=True)
        if args.details:
            cam.location=(.35,-5,1.64);look_at(cam,(0,0,1.56));cam.data.ortho_scale=.59;sc.render.resolution_y=args.width;sc.render.filepath=str(RENDERS/'face_detail.png');bpy.ops.render.render(write_still=True)
            for name,p in [('character_back',(2,6,2.3)),('character_side',(6,-.5,2.3))]:
                cam.location=p;look_at(cam,(0,0,.94));cam.data.ortho_scale=2.12;sc.render.resolution_y=round(args.width*1.25);sc.render.filepath=str(RENDERS/(name+'.png'));bpy.ops.render.render(write_still=True)
            cam.location=(2.5,-7,2.6);look_at(cam,(0,0,.94))
            for name,frame in [('Walk',9),('Plant',27),('Water',37),('Harvest',29)]:
                can.hide_render=name!='Water';rig.animation_data.action=clips[name];sc.frame_set(frame);sc.render.filepath=str(RENDERS/('action_'+name.lower()+'.png'));bpy.ops.render.render(write_still=True)
            can.hide_render=True;rig.animation_data.action=clips['Idle'];sc.frame_set(1)
    source_triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o,_ in PIECES)
    if args.export:
        # Save the full authoring mesh above; simplify only the exported copy.
        # Applying before the skin modifier interpolates existing weight groups.
        bpy.ops.object.select_all(action='DESELECT')
        for obj,_ in PIECES:
            obj.select_set(True);bpy.context.view_layer.objects.active=obj
            mod=obj.modifiers.new('Realtime detail reduction','DECIMATE')
            mod.ratio=.34 if obj.name in ['Wavy_Hair','Woven_Straw_Hat'] else (.80 if obj.name in ['Face','Hand','Hand.001'] else .65)
            bpy.ops.object.modifier_move_up(modifier=mod.name)
            bpy.ops.object.modifier_apply(modifier=mod.name)
            tri=obj.modifiers.new('Portable triangulation','TRIANGULATE')
            bpy.ops.object.modifier_move_up(modifier=tri.name);bpy.ops.object.modifier_apply(modifier=tri.name)
            obj.select_set(False)
        bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
        for obj,_ in PIECES:obj.select_set(True)
        bpy.context.view_layer.objects.active=rig
        # ACTIONS exports every compatible action on this one armature.
        bpy.ops.export_scene.gltf(filepath=str(OUT/'daisy_character.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_frame_range=False,export_force_sampling=True,export_tangents=True,export_armature_object_remove=True,export_yup=True,export_extras=True,export_cameras=False,export_lights=False)
        print('REPAIRED_DEGENERATE_TANGENTS='+str(repair_degenerate_tangents(OUT/'daisy_character.glb')))
    report=dict(method='Local Blender only',source_reference='reference/character/original.png',height=1.87,mesh_objects=len(PIECES),bones=len(rig.data.bones),source_triangles=source_triangles,web_triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o,_ in PIECES),clips=list(clips),parts=[o.name for o,_ in PIECES],pixel_identical=False)
    (ROOT/'reports/character_model.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('CHARACTER_REPORT='+json.dumps(report))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--width',type=int,default=960);parser.add_argument('--samples',type=int,default=40);parser.add_argument('--export',action='store_true');parser.add_argument('--details',action='store_true');parser.add_argument('--no-render',action='store_true')
    main(parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []))
