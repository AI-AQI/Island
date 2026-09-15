import bpy, math, random
from mathutils import Vector
from math import sin, cos, pi

def linear(v):
    return v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4

def rgba(h):
    h=h.lstrip('#'); return tuple(linear(int(h[i:i+2],16)/255) for i in (0,2,4))+(1,)

MATS={}
def material(name, color, rough=.78, metallic=0, emission=0, alpha=1):
    if name in MATS: return MATS[name]
    m=bpy.data.materials.new(name); m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF'); c=rgba(color)
    p.inputs['Base Color'].default_value=c; p.inputs['Roughness'].default_value=rough
    p.inputs['Metallic'].default_value=metallic
    if emission:
        p.inputs['Emission Color'].default_value=c; p.inputs['Emission Strength'].default_value=emission
    p.inputs['Alpha'].default_value=alpha
    m.diffuse_color=(*c[:3],alpha)
    if alpha<1: m.surface_render_method='DITHERED'
    MATS[name]=m; return m

def palette():
    colors={
      'grass':'8FBF6A','grass_light':'99C374','grass_dark':'7AA358','moss':'769151',
      'rock':'B8A898','rock_light':'C8B6A2','rock_dark':'958D86','rock_warm':'AE9986',
      'soil':'65503E','soil_light':'7B6048','wood':'976C44','wood_light':'BE9463','wood_dark':'594632',
      'wall':'F4DFC0','wall_shade':'E4CBAC','roof':'6A9E8F','roof_light':'83AE9B','roof_dark':'547F79',
      'leaf':'638C48','leaf_dark':'45694A','leaf_light':'98AF58','leaf_gold':'BDBB65',
      'flower_white':'FFF1DA','flower_pink':'E8A6B5','flower_hot':'C77294','flower_yellow':'F5CE60',
      'pumpkin':'E99536','pumpkin_light':'F5B64F','terracotta':'BF8160','cream':'F9EDD7',
      'pink':'E6A6A8','cloth':'71958C','wool':'F0EADC','face':'665E55','metal':'5A5D4D',
      'water':'7ECDE0','water_deep':'53AABF','foam':'E5F7ED','cloud':'E8D4E6','cloud_warm':'F4DCD7',
      'radish':'D97E86','chalk':'F0DDB5','board':'3D5A51','skin':'EEC69B'}
    for n,c in colors.items(): material(n,c,rough=.32 if n.startswith('water') else .8)
    material('glow','FFDF9E',.3,emission=3.0)
    material('waterfall','92D8E5',.2,alpha=.73)
    material('sun','FFF1BA',1,emission=1.8)

class Mesh:
    def __init__(self,name): self.name=name; self.v=[]; self.f=[]; self.mi=[]; self.sm=[]; self.mats=[]
    def face(self, ids, mat, smooth=False):
        if mat not in self.mats: self.mats.append(mat)
        self.f.append(tuple(ids)); self.mi.append(self.mats.index(mat)); self.sm.append(smooth)
    def poly(self,verts,faces,mat,smooth=False):
        o=len(self.v); self.v.extend(tuple(v) for v in verts)
        for f in faces:self.face([i+o for i in f],mat,smooth)
    def box(self,c,s,mat,rz=0):
        x,y,z=c; a,b,d=[q/2 for q in s]; cs,sn=cos(rz),sin(rz)
        verts=[(x+u*cs-v*sn,y+u*sn+v*cs,z+w) for u,v,w in [(-a,-b,-d),(a,-b,-d),(a,b,-d),(-a,b,-d),(-a,-b,d),(a,-b,d),(a,b,d),(-a,b,d)]]
        self.poly(verts,[(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],mat)
    def beam(self,a,b,r,mat,r2=None,n=8):
        a,b=Vector(a),Vector(b); axis=(b-a).normalized()
        u=axis.cross(Vector((0,0,1)))
        if u.length<.01:u=axis.cross(Vector((0,1,0)))
        u.normalize(); v=axis.cross(u).normalized(); r2=r if r2 is None else r2
        verts=[a+u*cos(i*2*pi/n)*r+v*sin(i*2*pi/n)*r for i in range(n)]
        verts += [b+u*cos(i*2*pi/n)*r2+v*sin(i*2*pi/n)*r2 for i in range(n)]
        faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        self.poly(verts,faces,mat,True)
    def sphere(self,c,s,mat,n=10,rings=6,smooth=True,noise=0,seed=0):
        rng=random.Random(seed); x,y,z=c; a,b,d=s; verts=[(x,y,z-d)]
        for j in range(1,rings):
            lat=-pi/2+pi*j/rings
            for i in range(n):
                t=i*2*pi/n; q=1+rng.uniform(-noise,noise)
                verts.append((x+a*cos(lat)*cos(t)*q,y+b*cos(lat)*sin(t)*q,z+d*sin(lat)*q))
        verts.append((x,y,z+d)); top=len(verts)-1
        faces=[(0,1+(i+1)%n,1+i) for i in range(n)]
        for j in range(rings-2):
            for i in range(n):
                a0=1+j*n+i; a1=1+j*n+(i+1)%n
                faces.append((a0,a1,a1+n,a0+n))
        faces += [(top,top-n+i,top-n+(i+1)%n) for i in range(n)]
        self.poly(verts,faces,mat,smooth)
    def tube(self,points,r,mat,n=6):
        for i in range(len(points)-1):self.beam(points[i],points[i+1],r,mat,n=n)
    def leaf(self,c,length,width,rz,tilt,mat):
        c=Vector(c); u=Vector((cos(rz),sin(rz),tilt)).normalized()*length
        v=Vector((-sin(rz),cos(rz),.1))*width
        self.poly([c-u*.5,c+v*.5,c+u*.5,c-v*.5,c+Vector((0,0,.06))],[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],mat)
    def arch(self,c,w,h,depth,mat,n=16):
        x,y,z=c; r=w/2; pts=[(x-r,z),(x+r,z)]
        pts += [(x+r*cos(i*pi/n),z+h-r+r*sin(i*pi/n)) for i in range(n+1)]
        verts=[(a,y-depth/2,b) for a,b in pts]+[(a,y+depth/2,b) for a,b in pts]; l=len(pts)
        self.poly(verts,[tuple(reversed(range(l))),tuple(range(l,2*l))]+[(i,(i+1)%l,(i+1)%l+l,i+l) for i in range(l)],mat)
    def object(self,collection=None):
        data=bpy.data.meshes.new(self.name+'_mesh'); data.from_pydata(self.v,[],self.f); data.update()
        for m in self.mats:data.materials.append(MATS[m])
        for i,p in enumerate(data.polygons):p.material_index=self.mi[i]; p.use_smooth=self.sm[i]
        obj=bpy.data.objects.new(self.name,data); (collection or bpy.context.scene.collection).objects.link(obj)
        return obj

def river_x(y): return 1.7+1.6*sin((y+4)*.13)+.35*sin(y*.43)
def land_z(x,y):
    d=abs(x-river_x(y)); depression=1.05*math.exp(-(d/2.7)**4)
    return 10.65+.3*sin(x*.11)+.16*cos(y*.23)-depression

def rock(mesh,c,s,seed=0):
    rng=random.Random(seed)
    mesh.sphere(c,s,rng.choice(['rock','rock_light','rock_dark','rock_warm']),n=7,rings=4,smooth=False,noise=.13,seed=seed)

def look_at(obj,target):obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
