"""Editable low-cost silhouettes for the surrounding archipelago. Local only."""
import sys,math,random,json
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from geometry import Mesh,material,MATS,look_at
OUT=ROOT/'assets/world'

def build():
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    for name,color in {'far_rock':'A6A69A','far_rock_dark':'818F8F','far_rock_light':'C2BBA5','far_grass':'8EA17C','far_moss':'718E78','far_leaf':'739079','far_leaf_light':'A4B48B','far_bark':'847A6B','far_wall':'DCD9C7','far_roof':'7C9B97','far_window':'F9DDAA','far_water':'ABD3D7'}.items():material(name,color)
    rng=random.Random(9182026);objects=[]
    placements=[(-39,-38,-6,1.05,'village'),(31,-52,0,.93,'ruin'),(-9,-72,-10,.56,'forest'),(59,-22,-12,.57,'forest'),(-59,12,-13,.55,'ruin'),(42,40,-22,.48,'village'),(-31,52,-25,.56,'forest'),(5,69,-32,.39,'ruin'),(-71,-56,-13,.44,'forest'),(70,-73,-3,.48,'village'),(-8,-110,-24,.35,'forest'),(93,15,-26,.34,'forest')]
    def tree(m,x,y,s,seed):
        rr=random.Random(seed);m.beam((x,y,.6),(x+.15*s,y,2.4*s),.17*s,'far_bark',r2=.09*s,n=6)
        for k in range(7):
            a=rr.random()*math.tau;r=rr.random()*1.15*s
            m.sphere((x+math.cos(a)*r,y+math.sin(a)*r,2.7*s+rr.random()*.75*s),(1.0*s,.85*s,.85*s),rr.choice(['far_leaf','far_leaf_light']),n=9,rings=5,noise=.08,seed=seed+k)
    def house(m,x,y,s):
        m.box((x,y,.55+1.15*s),(2.7*s,2.3*s,2.3*s),'far_wall')
        v=[(x+a*s,y+b*s,.55+c*s) for a,b,c in [(-1.6,-1.35,2.3),(1.6,-1.35,2.3),(0,-1.35,3.8),(-1.6,1.35,2.3),(1.6,1.35,2.3),(0,1.35,3.8)]]
        m.poly(v,[(0,1,2),(3,5,4),(0,2,5,3),(2,1,4,5)],'far_roof')
        m.box((x+.55*s,y-1.17*s,.55+1.3*s),(.55*s,.04,.72*s),'far_window')
        m.box((x-.6*s,y-1.17*s,.55+.7*s),(.48*s,.04,1.4*s),'far_bark')
    for index,(x,y,z,scale,kind) in enumerate(placements):
        m=Mesh('distant_island_%02d_%s'%(index,kind));n=17;verts=[]
        rings=[(1,.4),(.98,-.6),(.72,-3.3),(.34,-6.2),(.07,-8.8)]
        radii=[1+rng.uniform(-.17,.17) for _ in range(n)]
        for row,(radius,height) in enumerate(rings):
            for i in range(n):
                a=i*math.tau/n;v=radii[i]*radius
                verts.append((math.cos(a)*5.4*v+row*.22,math.sin(a)*4.4*v,height+rng.uniform(-.28,.28)))
        m.poly(verts,[tuple(range(n))],'far_grass')
        for r in range(len(rings)-1):
            for i in range(n):
                a=r*n+i;b=r*n+(i+1)%n;c=b+n;d=a+n
                m.poly([verts[a],verts[b],verts[c],verts[d]],[(0,1,2),(0,2,3)],rng.choice(['far_rock','far_rock_dark','far_rock_light']))
        m.poly(verts,[tuple(reversed(range((len(rings)-1)*n,len(rings)*n)))],'far_rock_dark')
        for k in range(16):
            a=rng.random()*math.tau;r=rng.uniform(2,4.5)
            m.sphere((math.cos(a)*r,math.sin(a)*r*.8,.5),(.9,.7,.35),rng.choice(['far_grass','far_moss']),n=7,rings=4)
        for k in range(5 if kind=='forest' else 3):
            a=k*2.4+index;tree(m,math.cos(a)*3.3,math.sin(a)*2.5,rng.uniform(.65,1.0),index*33+k)
        if kind=='village':house(m,-.8,-.2,.9);house(m,2,1,.55)
        elif kind=='ruin':
            for k in range(3):
                h=2.8+k*.7;m.box((k*1.2-1,0,.6+h/2),(.7,.8,h),'far_wall')
            m.box((.2,0,3.15),(3.6,.85,.5),'far_rock_light')
            m.box((1.35,0,4.2),(1.0,.95,.4),'far_wall')
        # Waterfall strips are retained as distinct material regions for runtime flow.
        path=[(1.5,-1,.64),(2.3,-2.7,.65),(2.2,-4.05,.35),(2.3,-4.6,-2),(2.5,-4.7,-6),(2.7,-4.8,-13)]
        for k in range(len(path)-1):
            a,b=path[k],path[k+1];w=.48 if k<3 else .28
            m.poly([(a[0]-w,a[1],a[2]),(a[0]+w,a[1],a[2]),(b[0]+w*.8,b[1],b[2]),(b[0]-w*.8,b[1],b[2])],[(0,1,2,3)],'far_water')
        obj=m.object();obj.location=(x,-y,z);obj.scale=(scale,)*3;obj.rotation_euler.z=rng.uniform(-.3,.3);objects.append(obj)
    OUT.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'distant_islands.blend'),compress=True)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(OUT/'distant_islands.glb'),export_format='GLB',use_selection=True,export_animations=False,export_yup=True,export_cameras=False,export_lights=False)
    report={'seed':9182026,'islands':len(objects),'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in objects),'bytes':(OUT/'distant_islands.glb').stat().st_size,'description':'Three-dimensional distant scenery; no travel or collision.'}
    (ROOT/'reports/world_islands.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

build()
