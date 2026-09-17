"""Reference-led second art pass. Run with Blender --background --python scripts/refine.py.

The previous island_dusk.blend is the immutable input. New assets, complete editable
scene, portable textured GLB, previews and measured reports are written separately.
"""
import argparse
import json
import math
import random
import sys
import subprocess
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0,str(Path(__file__).parent))
from geometry import Mesh, MATS, material, palette, rgba, land_z, river_x, look_at
import assets
import refined_assets as detail

ROOT=Path(__file__).resolve().parent.parent
RNG=random.Random(91542)
FALLBACKS={}


def triangles(obj):
    return sum(len(p.vertices)-2 for p in obj.data.polygons)


def collection(name):
    c=bpy.data.collections.get(name)
    if c is None:
        c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c)
    return c


def emit(mesh, group='10_refined_gardens'):
    return mesh.object(collection(group))


def remove(obj):
    bpy.data.objects.remove(obj,do_unlink=True)


def rounded_edges(obj,width=.035):
    bpy.context.view_layer.objects.active=obj
    mod=obj.modifiers.new('Soft worn edges','BEVEL');mod.width=width;mod.segments=2
    mod.limit_method='ANGLE';mod.angle_limit=.7
    bpy.ops.object.modifier_apply(modifier=mod.name)


def planar_uv(obj):
    """Real exported UVs, with consistent world-scale grain on every face."""
    me=obj.data
    if me.uv_layers:return
    uv=me.uv_layers.new(name='SurfaceUV')
    pos=np.empty(len(me.vertices)*3,dtype=np.float32);me.vertices.foreach_get('co',pos);pos=pos.reshape(-1,3)
    vi=np.empty(len(me.loops),dtype=np.int32);me.loops.foreach_get('vertex_index',vi)
    normal=np.empty(len(me.polygons)*3,dtype=np.float32);me.polygons.foreach_get('normal',normal);normal=normal.reshape(-1,3)
    sizes=np.empty(len(me.polygons),dtype=np.int32);me.polygons.foreach_get('loop_total',sizes)
    axis=np.repeat(np.argmax(np.abs(normal),axis=1),sizes)
    coords=pos[vi];out=np.empty((len(vi),2),dtype=np.float32)
    for a,ij in [(0,(1,2)),(1,(0,2)),(2,(0,1))]:out[axis==a]=coords[axis==a][:,ij]/1.7
    uv.data.foreach_set('uv',out.ravel())


def noise_field(size,seed):
    rng=np.random.default_rng(seed);result=np.zeros((size,size),dtype=np.float32)
    for grid,weight in [(4,.32),(8,.21),(16,.17),(32,.13),(64,.10),(128,.07)]:
        v=rng.random((grid,grid));u=np.arange(size)*grid/size;i=u.astype(int);f=u-i;f=f*f*(3-2*f)
        low=v[i[:,None]%grid,i[None,:]%grid]*(1-f[None,:])+v[i[:,None]%grid,(i[None,:]+1)%grid]*f[None,:]
        hi=v[(i[:,None]+1)%grid,i[None,:]%grid]*(1-f[None,:])+v[(i[:,None]+1)%grid,(i[None,:]+1)%grid]*f[None,:]
        result+=(low*(1-f[:,None])+hi*f[:,None])*weight
    return result


def materials():
    MATS.clear()
    for mat in bpy.data.materials:
        key=mat.name.split('.')[0]
        if key not in MATS:MATS[key]=mat
    palette()
    material('brass','B68B43',.34,.65)
    material('lavender','A889CD');material('leaf_sage','8B9F5B')
    material('water_shine','C8EFF1',.21,emission=.18)
    material('water_edge','80D1D4',.16)
    colors={'leaf':'588044','leaf_dark':'355E42','leaf_light':'99AF5F','leaf_gold':'CFBE69',
            'grass':'88AA5B','grass_light':'ADC574','grass_dark':'6C914C',
            'roof':'557F7D','roof_light':'739B90','roof_dark':'42676C',
            'rock':'AA9B8F','rock_light':'C4B3A1','rock_dark':'817D7C','rock_warm':'AC9584',
            'wood':'8F603C','wood_light':'BA8B58','wood_dark':'593D2C',
            'water':'4BAEBD','water_deep':'399AAB','glow':'FFB948','wall':'F4DCB9','water_edge':'68BAC5'}
    for name,col in colors.items():
        mat=MATS[name];p=mat.node_tree.nodes.get('Principled BSDF')
        p.inputs['Base Color'].default_value=rgba(col);mat.diffuse_color=rgba(col)
        if name=='glow':p.inputs['Emission Color'].default_value=rgba(col);p.inputs['Emission Strength'].default_value=1.65
    for name in ['leaf','leaf_light','leaf_gold']:
        p=MATS[name].node_tree.nodes.get('Principled BSDF');p.inputs['Subsurface Weight'].default_value=.075
    # Small packed, tileable material textures survive glTF export.
    textures=[]
    for name,mat in list(MATS.items()):
        family=name.split('_')[0]
        if family not in ['rock','wood','grass','wall','roof','soil','moss']:continue
        p=mat.node_tree.nodes.get('Principled BSDF')
        if p is None:continue
        size=256;seed=sum(ord(c) for c in name);f=noise_field(size,seed)
        yy,xx=np.mgrid[:size,:size]/size
        if family=='wood':
            grain=np.sin(2*math.pi*(xx*30+f*2+.12*np.sin(yy*2*math.pi)))
            fac=.74+.37*f+.09*grain
        elif family=='rock':fac=.72+.50*f+.06*np.sin((xx+yy)*120+f*30)
        elif family=='grass':fac=.68+.52*f
        else:fac=.81+.30*f
        col=np.array(p.inputs['Base Color'].default_value[:3]);rgb=np.clip(col[None,None,:]*fac[:,:,None],0,1)
        pixels=np.ones((size,size,4),dtype=np.float32);pixels[:,:,:3]=rgb
        img=bpy.data.images.new('surface_'+name,width=size,height=size,alpha=False,float_buffer=False)
        img.colorspace_settings.name='Linear Rec.709';img.pixels.foreach_set(pixels.ravel())
        img.filepath_raw=str(ROOT/'assets/textures'/('surface_'+name+'.png'));img.file_format='PNG';img.save();img.pack()
        nodes=mat.node_tree.nodes;links=mat.node_tree.links
        tex=nodes.new('ShaderNodeTexImage');tex.image=img;tex.label='Portable color and grain';tex.extension='REPEAT'
        links.new(tex.outputs['Color'],p.inputs['Base Color'])
        bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.22 if family=='rock' else .15
        bump.inputs['Distance'].default_value=.065 if family=='rock' else .028
        links.new(tex.outputs['Color'],bump.inputs['Height']);links.new(bump.outputs['Normal'],p.inputs['Normal'])
        textures.append(img.name)
    return textures


def replace_assets():
    changed={}
    # Warm timber cafe roof, scalloped separate shingles, original load-bearing deck.
    old_roof=assets.roof
    def cafe_roof(m,cx,cy,w,d,e,r,seed=1):
        n=Mesh('cafe_roof');detail.tiled_roof(n,cx,cy,w,d,e,r,seed)
        n.mats=[{'roof':'wood','roof_dark':'wood_dark','roof_light':'wood_light'}.get(x,x) for x in n.mats]
        detail.merge(m,n)
    assets.roof=cafe_roof
    builders={**detail.BUILDERS,'cafe_pavilion':assets.cafe_pavilion}
    for name,builder in builders.items():
        mesh=builder();obj=mesh.object()
        lo=Vector(tuple(min(v[k] for v in mesh.v) for k in range(3)))
        hi=Vector(tuple(max(v[k] for v in mesh.v) for k in range(3)))
        offset=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
        for v in obj.data.vertices:v.co-=offset
        if name.startswith('rock_deco'):rounded_edges(obj,.045)
        obj['asset_id']=name;obj['origin']='bottom_center';obj['forward']='-Y';obj['units']='metres';obj['raw_offset']=list(offset)
        planar_uv(obj)
        for placed in list(bpy.context.scene.objects):
            if placed==obj or placed.type!='MESH':continue
            if placed.get('asset_id')==name:
                placed.data=obj.data
        changed[name]={'template':obj,'offset':offset}
    assets.roof=old_roof
    return changed


def place(changed,name,x,y,z=None,scale=1,rz=0,group='10_refined_gardens'):
    if name in changed:base=changed[name]['template']
    else:
        base=next((o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('asset_id')==name),None)
        if base is None:
            if name not in FALLBACKS:
                with bpy.data.libraries.load(str(ROOT/'assets/source'/f'{name}.blend'),link=False) as (src,dst):dst.objects=[name]
                FALLBACKS[name]=dst.objects[0]
                for i,mat in enumerate(FALLBACKS[name].data.materials):FALLBACKS[name].data.materials[i]=MATS[mat.name.split('.')[0]]
            base=FALLBACKS[name]
    obj=base.copy();obj.data=base.data;collection(group).objects.link(obj)
    obj.name=name+'_refined';obj.location=(x,y,land_z(x,y)-.02 if z is None else z)
    obj.scale=(scale,)*3 if isinstance(scale,(int,float)) else scale;obj.rotation_euler[2]=rz
    return obj


def terrain():
    # Preserve the carved grass surface, reconstruct a deeper, irregular cliff.
    old=bpy.data.objects.get('island_base_001');base=assets.island_base();core=Mesh('island_base')
    core.v=base.v[:4994]
    for f,mi,sm in zip(base.f[:5120],base.mi[:5120],base.sm[:5120]):core.face(f,base.mats[mi],sm)
    for i,(x,y,z) in enumerate(core.v):
        if z<10.1:core.v[i]=(x,y,10.1+(z-10.1)*1.42)
    for row,(radius,height,count,vertical) in enumerate([(1,8.7,51,1.9),(.93,6.2,46,2.0),(.78,3.6,38,2.2),(.55,1.6,26,1.7),(.29,.45,13,1.1)]):
        for i in range(count):
            t=(i+.47*(row%2)+RNG.uniform(-.18,.18))*2*pi/count
            x=22.2*radius*cos(t);y=13.65*radius*sin(t)
            if y<-9.5 and abs(x-river_x(y))<2.3:continue
            z=10.1+(height-10.1)*1.42+RNG.uniform(-.4,.4)
            start=len(core.v)
            core.sphere((x,y,z),(RNG.uniform(.9,1.8),RNG.uniform(.85,1.5),vertical*RNG.uniform(.8,1.3)),RNG.choice(['rock','rock_light','rock_warm','rock_dark']),11,7,False,.10,900+row*60+i)
            # Unequal leaning strata break the repeated vertical block pattern.
            tilt=RNG.uniform(-.3,.3)
            for v in range(start,len(core.v)):
                xx,yy,zz=core.v[v];core.v[v]=(xx+(zz-z)*tilt,yy+.08*sin(zz),zz)
    new=core.object(collection('01_terrain'));new['asset_id']='island_base';new['origin']='bottom_center';new['forward']='-Y';new['units']='metres'
    remove(old);new.name='island_base_001';rounded_edges(new,.055)
    rockmesh=Mesh('rim_boulders');roots=Mesh('exposed_twisting_roots');crevices=Mesh('stone_seams')
    for i in range(61):
        t=math.pi+math.pi*i/60;x=21.9*math.cos(t);y=13.3*math.sin(t)
        if abs(x-river_x(y))<2.7:continue
        if x>16 and y>-7:continue
        z=land_z(x,y)
        if i%2==0:
            rockmesh.sphere((x,y,z-.31),(RNG.uniform(.55,1.2),RNG.uniform(.6,.95),RNG.uniform(.5,.92)),RNG.choice(['rock','rock_light','rock_warm']),11,6,False,.12,i)
        if i%3==0:
            for strand in range(2):
                length=RNG.uniform(3.4,8.5);pts=[]
                for j in range(13):
                    q=j/12;rad=1-.07*q*q
                    pts.append((x*rad+.23*sin(q*6+strand),y*rad-.24*cos(q*5+strand),z-length*q))
                for j in range(12):roots.beam(pts[j],pts[j+1],(.13-.008*j)*(1-.25*strand),'wood',r2=max(.013,.12-.009*j),n=6)
        for j in range(2):
            zz=z-1.9-j*3.2;px=x*(.98-.05*j);py=y*(.99-.04*j)
            pts=[(px+.7*q,py-.09*cos(q*5),zz-.55*q+.10*sin(q*7)) for q in [k/5 for k in range(6)]]
            crevices.tube(pts,.018,'rock_dark',4)
    obj=emit(rockmesh,'01_terrain');rounded_edges(obj,.045)
    emit(roots,'01_terrain');emit(crevices,'01_terrain')


def gardens(changed):
    # Remove uniform old rim chains, keep their useful rooting positions.
    for obj in list(bpy.context.scene.objects):
        if obj.get('asset_id')=='vine_hanging':
            obj.scale.x*=.8;obj.scale.y*=.8
        if obj.get('asset_id','').startswith('bush_flower'):
            obj.scale*=.83
    for i in range(115):
        t=pi+pi*(i+.25)/115;x=20.8*cos(t);y=12.55*sin(t)
        if abs(x-river_x(y))<2.65 or (x>15 and y>-6.5):continue
        x+=RNG.uniform(-.55,.55);y+=RNG.uniform(-.35,.35)
        place(changed,'bush_flower_'+RNG.choice(['white','white','pink','yellow']),x,y,scale=RNG.uniform(.72,1.14),rz=RNG.random()*6.28)
    ground=Mesh('wild_grass_and_clover');lav=Mesh('foxgloves_and_lavender');shrubs=Mesh('rim_leaf_mounds')
    for i in range(10000):
        x=RNG.uniform(-21.5,21.5);y=RNG.uniform(-12.7,12.7)
        if (x/21.5)**2+(y/13.2)**2>.98 or abs(x-river_x(y))<2.8:continue
        if -18<x<-4 and -6.1<y<-1.6:continue
        if -14<x<-1 and 0<y<9:continue
        if x>12 and -5<y<5:continue
        if RNG.random()>.55:continue
        z=land_z(x,y)+.035;a=RNG.random()*2*pi;h=RNG.uniform(.055,.19);w=.025
        ground.poly([(x-w*cos(a),y-w*sin(a),z),(x+w*cos(a),y+w*sin(a),z),(x+.08*cos(a),y+.08*sin(a),z+h)],[(0,1,2)],RNG.choice(['grass_light','leaf_light','grass_dark']))
    # Dense planting has an intentional hierarchy: low rim beds and taller flower spires.
    for i in range(33):
        t=pi+pi*(i+.5)/33;x=21.15*cos(t);y=12.8*sin(t)
        if abs(x-river_x(y))<3 or (x>16 and y>-7):continue
        z=land_z(x,y)
        for j in range(165):
            a=RNG.uniform(0,2*pi);r=RNG.uniform(.1,1.42);zz=z+.77*(1-r/1.65)+RNG.uniform(-.15,.15)
            detail.petal(shrubs,(x+r*cos(a),y+r*.7*sin(a),zz),RNG.uniform(.32,.63),.25,a,RNG.uniform(-.6,.8),RNG.choice(['leaf','leaf_light','leaf_sage']))
    for x,y in [(-4,-8),(-3,-3),(7,-8),(10,-7),(7,0),(-17,-8),(-11,-8.6),(12,-8.2)]:
        z=land_z(x,y)
        for j in range(9):
            xx=x+RNG.uniform(-.6,.6);yy=y+RNG.uniform(-.45,.45);h=RNG.uniform(.5,1.15)
            lav.beam((xx,yy,z),(xx,yy,z+h),.017,'leaf_dark',n=4)
            for k in range(6):
                a=k*2.4;lav.sphere((xx+.055*cos(a),yy+.055*sin(a),z+h-k*.075),(.06,.06,.083),'lavender' if j%2 else 'flower_hot',6,3,True)
            detail.petal(lav,(xx,yy,z+.19),.47,.16,j,1,'leaf')
    emit(ground);emit(shrubs);emit(lav)


def buildings(changed):
    house=bpy.data.objects['house_main_001'];house.location=(-8.3,4.45,land_z(-8.3,4.45)-.12);house.scale=(1.12,)*3
    # Existing pots/vines belonged to the old facade. Re-seat them at actual new ledges.
    for obj in list(bpy.context.scene.objects):
        aid=obj.get('asset_id','')
        if aid in ['ivy_wall','flower_pot_1','flower_pot_2','sunflower'] and obj.location.x<0:remove(obj)
    offset=changed['house_main']['offset'];bpy.context.view_layer.update()
    def attach(name,p,s=1):
        w=house.matrix_world@(Vector(p)-offset)
        return place(changed,name,*w,scale=s*1.12)
    for x,y,z,s in [(-3.9,-3.15,.62,1.25),(-2.5,-3.7,.65,1.12),(.40,-3.55,.64,1.2),(3.85,-3.3,.6,1.12),(.75,-3.4,1.23,.7),(1.7,-3.4,1.23,.7),(2.65,-3.4,1.23,.7),(1.7,-3.2,4.88,.66)]:attach('flower_pot_2',(x,y,z),s)
    for x in [-4.6,-2.18,.45,3.3]:attach('ivy_wall',(x,-3.04,.63),1.8)
    for i in range(5):attach('sunflower',(-4.45+.30*i,-3.82-.16*sin(i),.63),1.1+.15*sin(i))
    climbing=Mesh('flowering_window_climber')
    for i in range(65):
        a=RNG.uniform(0,pi);x=1.75+1.5*cos(a);z=1.35+2.25*sin(a)
        y=-3.1-RNG.random()*.19
        detail.petal(climbing,(x,y,z),.34,.23,a,1.4,RNG.choice(['leaf','leaf_light']))
        if i%3==0:
            for j in range(5):
                t=j*2*pi/5;climbing.sphere((x+.052*cos(t),y-.04,z+.05*sin(t)),(.048,.03,.046),RNG.choice(['flower_white','flower_pink']),6,3)
    for v in range(len(climbing.v)):climbing.v[v]=house.matrix_world@(Vector(climbing.v[v])-offset)
    emit(climbing,'02_architecture')
    # Match the wide silhouettes of the large trees framing each building.
    trees=sorted([o for o in bpy.context.scene.objects if o.get('asset_id','').startswith('tree_large') and o not in [v['template'] for v in changed.values()]],key=lambda o:o.name)
    positions=[(-16.3,7.3,.97),(-19.0,1.9,.47),(-1.4,8.6,.61),(12.7,5.8,.96),(18,5,.56),(-19.4,-1.9,.42)]
    # Sort spatially, so the tallest trunk actually stands behind the cottage.
    trees.sort(key=lambda o:o.location.x)
    positions=[(-19.4,-1.9,.42),(-19,2.8,.5),(-15.5,7.3,1.43),(-1.7,8,.83),(12.7,8.6,1.4),(17,7.8,.50)]
    for o,(x,y,s) in zip(trees,positions):o.location=(x,y,land_z(x,y));o.scale=(s,s,s)
    blossom=bpy.data.objects.get('tree_blossom_001')
    if blossom:blossom.location=(-1,6.8,land_z(-1,6.8));blossom.scale=(.58,)*3
    cafe=bpy.data.objects['cafe_pavilion_001'];delta=Vector((-1.7,2.8,0));old=cafe.location.copy()
    cafe.location+=delta;cafe.scale=(1.12,)*3
    for obj in list(bpy.context.scene.objects):
        if obj.get('asset_id') in ['flower_pot_1','flower_pot_2','ivy_wall','vine_hanging'] and obj.location.x>13 and (obj.location-old).length<9 and obj not in [v['template'] for v in changed.values()]:obj.location+=delta
    # Connected stone approach to the relocated terrace.
    steps=Mesh('cafe_garden_approach')
    for row in range(6):
        x=16.3;y=-5.1+row*.42
        for col in range(4):steps.box((x+(col-1.5)*.56,y,land_z(x,y)+.07+max(0,row-3)*.12),(.52,.50,.16),'rock_light')
    emit(steps,'06_paths')
    # Warm cafe glazed panels set behind the open bar.
    glazing=Mesh('cafe_glazed_back')
    for x in [-2.3,-.8,.8,2.3]:
        assets.window(glazing,x,2.56,1.45,1.1,1.35,False)
    co=changed['cafe_pavilion']['offset'];bpy.context.view_layer.update()
    for i,v in enumerate(glazing.v):glazing.v[i]=cafe.matrix_world@(Vector(v)-co)
    emit(glazing,'02_architecture')
    # Low branch-supported lantern strings on the tree beside the cafe.
    garland=Mesh('tree_lantern_garland')
    points=[(9.7+9*i/40,4.25,14.95-.76*sin(pi*i/40)) for i in range(41)]
    garland.beam((12.7,8.6,14.2),points[0],.15,'wood',r2=.05,n=8)
    garland.beam((17,7.8,13.4),points[-1],.09,'wood',r2=.035,n=7)
    garland.tube(points,.025,'wood_dark',5)
    for i in [3,10,17,24,31,38]:
        x,y,z=points[i];garland.beam((x,y,z),(x,y,z-.15),.016,'metal',n=4);assets.lantern(garland,(x,y,z-.79),.76)
    emit(garland,'09_details')
    # Correct chimney plume location.
    smoke=bpy.data.objects.get('chimney_smoke')
    if smoke:remove(smoke)
    smoke=Mesh('chimney_smoke_refined');base=house.matrix_world@(Vector((-1.22,1.24,8.75))-offset)
    for i in range(9):smoke.sphere(base+Vector((.12*sin(i*.7)+i*.09,0,i*.31)),(.19+i*.014,.16+i*.018,.29),'cloud_warm',12,7,True)
    emit(smoke,'09_details')


def water():
    for name in ['stream_ripples','waterfall_sheet','waterfall_foam']:
        o=bpy.data.objects.get(name)
        if o:remove(o)
    sc=bpy.context.scene
    # Faceted watercolor variations live in geometry and survive GLB export.
    stream=bpy.data.objects.get('stream_surface');stream.data.materials.clear()
    names=['water','water_deep','water_edge']
    for n in names:stream.data.materials.append(MATS[n])
    for p in stream.data.polygons:p.material_index=RNG.choices([0,1,2],[8,1,2])[0]
    for v in stream.data.vertices:v.co.z=9.98+.035*sin(v.co.x*3+v.co.y*1.7)+.016*sin(v.co.y*5.1)
    ripple=Mesh('flowing_ripples_and_eddies')
    for i in range(220):
        y=RNG.uniform(-13.2,12.3);x=river_x(y)+RNG.uniform(-1.6,1.6)
        if land_z(x,y)>10.05:continue
        angle=RNG.random()*pi;rx=RNG.uniform(.12,.50);ry=RNG.uniform(.05,.15)
        pts=[(x+rx*cos(t),y+ry*sin(t),10.05+.006*sin(t*3)) for t in [angle+j*pi/12 for j in range(10)]]
        ripple.tube(pts,RNG.uniform(.008,.018),'water_shine' if i%3 else 'foam',4)
    emit(ripple,'07_water')
    fx=river_x(-13.25);fall=Mesh('waterfall_ribbons');foam=Mesh('waterfall_spray')
    for j in range(52):
        u=(j+.5)/52;xx=fx+(u-.5)*4.05;length=RNG.uniform(12.4,14.2)
        width=RNG.uniform(.065,.13)
        for i in range(52):
            t=i/51;t1=(i+1)/51
            def p(q,dx):
                return (xx+dx+.08*sin(q*14+j*.7)+.25*(u-.5)*q,
                        -13.23-1.7*(1-math.exp(-q*8))-.32*q+.07*sin(j*1.91),
                        10.01-length*q)
            fall.poly([p(t,-width),p(t,width),p(t1,width),p(t1,-width)],[(0,1,2,3)],'foam' if j%9==0 else ('water_edge' if j%3 else 'water_shine'),True)
        if j%2==0:
            pts=[]
            for i in range(22):
                t=i/22;pts.append((xx+.1*sin(t*12+j),-13.37-1.7*(1-math.exp(-t*8))-.32*t,10-length*t))
            foam.tube(pts,.013,'foam',4)
    for i in range(900):
        t=RNG.uniform(.04,1.08);s=RNG.uniform(.01,.044)
        foam.sphere((fx+RNG.uniform(-2.1,2.1)*(1+.22*t),-13.5-1.65*(1-math.exp(-t*8))+RNG.uniform(-.3,.22),10-13.8*t),(s,s,s*1.7),'foam',5,3)
    for i in range(45):
        x=fx+RNG.uniform(-1.7,1.7);y=RNG.uniform(-13.48,-12.7)
        foam.sphere((x,y,10.02),(RNG.uniform(.045,.13),.08,.045),'foam',7,3)
    emit(fall,'07_water');emit(foam,'07_water')


def storytelling(changed):
    old=bpy.data.objects.get('player_ref_001')
    if old:remove(old)
    person=Mesh('garden_wanderer')
    for x in [-.13,.13]:
        person.beam((x,0,.14),(x,0,.49),.069,'skin',n=8)
        person.sphere((x,-.075,.12),(.105,.19,.10),'wood_dark',10,5)
    # An actual flared dress, shawl, hair, straw hat and shoulder bag.
    person.beam((0,0,.39),(0,0,.82),.33,'cream',r2=.15,n=18)
    person.sphere((0,0,.84),(.18,.135,.22),'cloth',12,7)
    person.sphere((0,.05,1.14),(.22,.15,.25),'wood_dark',12,8)
    person.sphere((0,-.06,1.14),(.17,.15,.21),'skin',12,8)
    for x in [-.065,.065]:person.sphere((x,-.203,1.17),(.019,.017,.023),'wood_dark',8,4)
    person.sphere((-.18,.005,1),(.063,.105,.26),'wood',9,6)
    person.sphere((.18,.005,1),(.063,.105,.26),'wood',9,6)
    person.sphere((0,0,1.36),(.39,.33,.056),'wood_light',24,6)
    person.sphere((0,0,1.40),(.205,.19,.115),'wood_light',18,6)
    person.beam((0,0,1.39),(0,0,1.43),.208,'wood',n=24)
    for side in [-1,1]:
        person.beam((side*.16,0,.93),(side*.26,-.07,.71),.066,'cream',r2=.05,n=8)
        person.beam((side*.26,-.07,.71),(side*.24,-.14,.62),.045,'skin',n=8)
    person.sphere((.27,0,.54),(.15,.10,.17),'terracotta',12,6)
    person.beam((-.15,-.145,.97),(.27,-.10,.60),.018,'wood',n=5)
    obj=emit(person,'09_details');obj.location=(-3.7,-2.15,land_z(-3.7,-2.15));obj.scale=(1.25,)*3;obj.rotation_euler.z=.2
    cat=Mesh('garden_cat')
    cat.sphere((0,0,.22),(.14,.24,.21),'cream',10,6)
    cat.sphere((0,-.18,.41),(.14,.13,.13),'cream',10,6)
    for side in [-1,1]:
        cat.poly([(side*.06,-.24,.47),(side*.14,-.17,.47),(side*.11,-.18,.64)],[(0,1,2)],'pumpkin_light')
        cat.sphere((side*.06,-.297,.44),(.018,.012,.018),'wood_dark',6,3)
        cat.sphere((side*.1,-.13,.06),(.06,.09,.05),'cream',8,4)
    cat.tube([(.06,.18,.25),(.21,.28,.3),(.27,.29,.44),(.25,.24,.54)],.04,'pumpkin_light',7)
    co=emit(cat,'09_details');co.location=(-2.86,-2.4,land_z(-2.86,-2.4));co.scale=(1.1,)*3
    # Small supported lights tucked into the cliff vegetation.
    edge=Mesh('cliff_lanterns')
    for x,y,length in [(-20,-5.2,3.9),(-13,-11,5.3),(-6,-12.4,4.3),(8,-12.1,4.9),(14,-10.4,3.7),(20.5,-6.2,3.1)]:
        z=land_z(x,y)+.12
        edge.beam((x*.96,y*.96,z),(x*1.045,y*1.045,z+.06),.057,'wood_dark',n=6)
        edge.beam((x*1.045,y*1.045,z+.06),(x*1.045,y*1.045,z-length+.73),.017,'metal',n=5)
        assets.lantern(edge,(x*1.045,y*1.045,z-length),.86)
    emit(edge,'09_details')


def lights_and_camera(args):
    sc=bpy.context.scene
    for obj in list(sc.objects):
        if obj.get('asset_id','').startswith(('cloud_puff','distant_island')) or obj.name=='sun_disc':remove(obj)
    sun=bpy.data.objects['sunset_key'];sun.location=(30,4,23);look_at(sun,(0,0,10));sun.data.energy=3.1;sun.data.color=rgba('FFE0A4')[:3];sun.data.angle=.12
    fill=bpy.data.objects['lavender_fill'];fill.location=(-22,-26,30);fill.data.energy=11000;fill.data.size=30;fill.data.color=rgba('BBCBE9')[:3];look_at(fill,(0,0,9))
    sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.55
    cam=sc.camera;cam.location=(23,-67,53);look_at(cam,(0,0,8.3));cam.data.ortho_scale=54.2
    sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.view_settings.exposure=.4
    sc.cycles.samples=args.samples;sc.cycles.use_denoising=True;sc.cycles.device='GPU'
    pref=bpy.context.preferences.addons['cycles'].preferences
    try:
        pref.compute_device_type='METAL';pref.get_devices()
        for d in pref.devices:d.use=d.type=='METAL'
    except Exception:sc.cycles.device='CPU'
    sc.render.resolution_x=args.width;sc.render.resolution_y=round(args.width*.75);sc.render.resolution_percentage=100
    sc.render.film_transparent=True
    sky=bpy.data.images.load(str(ROOT/'assets/textures/dusk_cloudscape.png'),check_existing=True);sky.pack()
    nt=bpy.data.node_groups.new('Reference sunset compositing','CompositorNodeTree');sc.compositing_node_group=nt
    nt.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor')
    rl=nt.nodes.new('CompositorNodeRLayers');bg=nt.nodes.new('CompositorNodeImage');bg.image=sky
    scale=nt.nodes.new('CompositorNodeScale');scale.inputs['Type'].default_value='Render Size';scale.inputs['Frame Type'].default_value='Crop'
    glare=nt.nodes.new('CompositorNodeGlare');glare.inputs['Type'].default_value='Fog Glow';glare.inputs['Quality'].default_value='High';glare.inputs['Threshold'].default_value=2.3;glare.inputs['Strength'].default_value=.12;glare.inputs['Size'].default_value=.24
    over=nt.nodes.new('CompositorNodeAlphaOver');out=nt.nodes.new('NodeGroupOutput')
    nt.links.new(bg.outputs['Image'],scale.inputs['Image']);nt.links.new(scale.outputs['Image'],over.inputs['Background'])
    nt.links.new(rl.outputs['Image'],glare.inputs['Image']);nt.links.new(glare.outputs['Image'],over.inputs['Foreground']);nt.links.new(over.outputs[0],out.inputs['Image'])
    for a in bpy.data.screens:
        for area in a.areas:
            if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'


def run(args):
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'island_dusk.blend'))
    sc=bpy.context.scene;bpy.ops.object.select_all(action='DESELECT')
    textures=materials();changed=replace_assets()
    terrain();gardens(changed);buildings(changed);water();storytelling(changed);lights_and_camera(args)
    template_ids={v['template'] for v in changed.values()}
    meshes=[o for o in sc.objects if o.type=='MESH' and o not in template_ids]
    seen=set()
    for o in meshes:
        if o.data.name not in seen:planar_uv(o);seen.add(o.data.name)
    # Export each newly built standalone asset; previews use the real scene later.
    if args.export:
        for name,entry in changed.items():
            obj=entry['template'];bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
            bpy.ops.export_scene.gltf(filepath=str(ROOT/'assets/refined/glb'/f'{name}.glb'),export_format='GLB',use_selection=True,export_animations=False,export_yup=True)
            bpy.data.libraries.write(str(ROOT/'assets/refined/source'/f'{name}.blend'),{obj},fake_user=True,compress=True)
    for obj in template_ids:remove(obj)
    for o in meshes:
        if o.type=='MESH' and o.get('asset_id') in changed:o['art_revision']='reference_refinement_v2'
    bpy.context.view_layer.update()
    total=sum(triangles(o) for o in meshes)
    report={'revision':'reference_refinement_v2','triangles':total,'mesh_objects':len(meshes),'unique_meshes':len(seen),'material_textures':len(textures),'material_texture_size':256,'sky_backdrop':'assets/textures/dusk_cloudscape.png','sky_is_2d':True,'render':[args.width,round(args.width*.75)],'camera_position':list(sc.camera.location),'camera_target':[0,0,8.3],'ortho_scale':sc.camera.data.ortho_scale,'changed_assets':list(changed),'pixel_identical':False,'source':'island_dusk.blend','largest_meshes':sorted([{'name':o.name,'triangles':triangles(o)} for o in meshes],key=lambda x:x['triangles'],reverse=True)[:15]}
    sc['art_revision']='reference_refinement_v2';sc['triangle_count']=total
    sc.render.filepath=str(ROOT/'renders/refined'/('island_preview.png' if not args.export else 'island_dusk_refined.png'))
    if args.export:
        # Keep independent, named and editable objects in the native scene.
        bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'island_dusk_refined.blend'),compress=True)
        bpy.ops.object.select_all(action='DESELECT')
        water_meshes=[o for o in meshes if any(c.name=='07_water' for c in o.users_collection)]
        land_meshes=[o for o in meshes if o not in water_meshes]
        water_total=sum(triangles(o) for o in water_meshes)
        for o in land_meshes:o.select_set(True)
        bpy.context.view_layer.objects.active=land_meshes[0];bpy.ops.object.join();joined=bpy.context.object;joined.name='island_dusk_refined'
        # Native scene keeps every leaf. The web copy meets the original triangle cap.
        if total>580000:
            mod=joined.modifiers.new('Web geometry budget','DECIMATE');mod.ratio=(575000-water_total)/(total-water_total)
            mod.use_collapse_triangulate=True
            bpy.ops.object.modifier_apply(modifier=mod.name)
        joined.data.validate(verbose=False);joined.data.update()
        for o in water_meshes:o.select_set(True)
        bpy.context.view_layer.objects.active=joined;bpy.ops.object.join()
        report['web_triangles']=triangles(joined)
        bpy.ops.export_scene.gltf(filepath=str(ROOT/'island_dusk_refined.glb'),export_format='GLB',use_selection=True,export_animations=False,export_yup=True,export_cameras=False,export_lights=False)
        report['glb_bytes']=(ROOT/'island_dusk_refined.glb').stat().st_size
        report['original_budget_pass']=report['web_triangles']<=600000 and report['glb_bytes']<=25000000
    (ROOT/'reports'/('refined_scene.json' if args.export else 'refined_preview.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2))
    if args.export:
        subprocess.run(['node',str(ROOT/'scripts/optimize_glb.cjs')],check=True)
        report=json.loads((ROOT/'reports/refined_scene.json').read_text())
    print('REFINED_REPORT '+json.dumps(report),flush=True)
    if args.export:bpy.ops.wm.open_mainfile(filepath=str(ROOT/'island_dusk_refined.blend'))
    bpy.ops.render.render(write_still=True)
    if args.export:
        # Reopen the editable scene for genuine alternate views and final validation.
        bpy.ops.wm.open_mainfile(filepath=str(ROOT/'island_dusk_refined.blend'));sc=bpy.context.scene;cam=sc.camera
        sc.cycles.samples=48;sc.render.resolution_x=1440;sc.render.resolution_y=1080
        for name,pos,target,size in [('house_detail',(-15,-22,24),(-8,3,14),20),('cafe_detail',(28,-18,23),(16,1,13),18),('layout_top',(0,0,75),(0,0,6),53)]:
            cam.location=pos;look_at(cam,target);cam.data.ortho_scale=size
            sc.render.filepath=str(ROOT/'renders/refined'/f'{name}.png');bpy.ops.render.render(write_still=True)


if __name__=='__main__':
    from math import sin,cos,pi
    parser=argparse.ArgumentParser();parser.add_argument('--width',type=int,default=1100);parser.add_argument('--samples',type=int,default=24);parser.add_argument('--export',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    run(args)
