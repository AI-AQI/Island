"""Expand the living scene without scaling its buildings or character.

Landscape coordinates grow by 1.28 x 1.38; architectural attachments move as
groups. The previous living source is read-only. Outputs keep editable objects.
"""
import json
import math
import random
import subprocess
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from geometry import Mesh, MATS, material, look_at, land_z
from prepare_living import bounds, bend
from refined_assets import broad_tree

SX, SY = 1.28, 1.38
RNG = random.Random(91827)
OUT = ROOT / 'assets/expanded'


def ground(x, y):
    oy = y / SY
    return land_z(x / SX - bend(oy), oy)


def expand(p):
    return Vector((p[0] * SX, p[1] * SY, p[2]))


def emit(mesh, x=0, y=0, rotation=0):
    o = mesh.object()
    o.location = (x, y, ground(x, y))
    o.rotation_euler.z = rotation
    o['expansion_asset'] = True
    return o


def bench(name, x, y, rotation=0):
    m = Mesh(name)
    for yy in [-.25, 0, .25]:
        m.box((0, yy, .57), (2.3, .21, .11), 'wood_light')
    for xx in [-.87, .87]:
        for yy in [-.25, .25]:
            m.beam((xx, yy, .04), (xx, yy, .54), .065, 'wood_dark')
        m.beam((xx, .31, .45), (xx, .4, 1.36), .065, 'wood')
    for zz in [.95, 1.19]:
        m.box((0, .37, zz), (2.3, .09, .17), 'wood_light')
    return emit(m, x, y, rotation)


def planter(name, x, y, width=2.2):
    m = Mesh(name)
    m.box((0, 0, .25), (width, .72, .48), 'wood')
    m.box((0, 0, .50), (width-.12, .6, .05), 'soil')
    for i in range(18):
        xx=RNG.uniform(-width*.43, width*.43); yy=RNG.uniform(-.24,.24)
        h=RNG.uniform(.22,.52)
        m.beam((xx,yy,.5),(xx,yy,.5+h),.015,'leaf_dark',n=5)
        for j in range(3):
            m.leaf((xx,yy,.60+h*.35),.34,.14,j*2.1,.4,'leaf')
        for j in range(5):
            a=j*math.tau/5
            m.sphere((xx+.06*math.cos(a),yy+.06*math.sin(a),.5+h),(.064,.055,.035),'flower_white' if i%3 else 'flower_pink',6,3)
        m.sphere((xx,yy,.53+h),(.035,.035,.025),'flower_yellow',6,3)
    return emit(m,x,y)


def path(name, points, width=.70):
    m = Mesh(name)
    for a,b in zip(points,points[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1]; length=math.hypot(dx,dy)
        angle=math.atan2(dy,dx)
        for i in range(max(1,math.ceil(length/.63))):
            t=(i+.5)/max(1,math.ceil(length/.63))
            for side in [-1,1]:
                x=a[0]+dx*t-side*math.sin(angle)*width*.4
                y=a[1]+dy*t+side*math.cos(angle)*width*.4
                m.sphere((x,y,ground(x,y)+.035),(.35,.26,.07),RNG.choice(['rock','rock_light','rock_warm']),7,3,False,.13,RNG.randrange(100000))
    o=m.object();o['expansion_asset']=True
    return o


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'island_dusk_living.blend'))
    bpy.context.preferences.filepaths.save_version=0
    sc=bpy.context.scene
    for mat in bpy.data.materials: MATS[mat.name]=mat
    material('fruit_apple','C95F44',.65)
    material('fruit_pear','D4BB66',.75)
    house=bpy.data.objects['house_main_001']; cafe=bpy.data.objects['cafe_pavilion_001']
    house_delta=expand(house.location)-house.location
    cafe_delta=expand(cafe.location)-cafe.location
    boat=bpy.data.objects['boat_hull'];boat_delta=expand(boat.location)-boat.location
    original=json.loads((ROOT/'assets/living/scene.json').read_text())
    terrain_names={'rim_boulders','exposed_twisting_roots','stone_seams','wild_grass_and_clover','rim_leaf_mounds','foxgloves_and_lavender','stream_surface','flowing_ripples_and_eddies','waterfall_ribbons','waterfall_spray','tree_lantern_garland','cliff_lanterns'}
    house_names={'flowering_window_climber','chimney_smoke_refined'}
    cafe_names={'cafe_glazed_back','cafe_garden_approach'}
    boat_names={'boat_hull','boat_support','boat_davit_anchors'}
    for o in list(sc.objects):
        if o.parent or o.type not in ['MESH','EMPTY']: continue
        aid=o.get('asset_id','')
        if o.name in house_names or aid=='house_main' or (aid in ['flower_pot_1','flower_pot_2','ivy_wall','sunflower'] and o.location.x<0):
            o.location+=house_delta
        elif o.name in cafe_names or aid=='cafe_pavilion' or (aid in ['flower_pot_1','flower_pot_2','ivy_wall'] and o.location.x>10):
            o.location+=cafe_delta
        elif o.name in boat_names:
            o.location+=boat_delta
        elif o.type=='MESH' and (o.name in terrain_names or o.name.startswith('vine_rim_root') or aid in ['island_base','farm_soil','farm_fence','stone_bridge'] or aid.startswith('stone_path')):
            matrix=o.matrix_world.copy();inv=matrix.inverted();o.data=o.data.copy()
            for v in o.data.vertices:v.co=inv@expand(matrix@v.co)
            o.data.update()
        else:
            o.location=expand(o.location)
    bpy.context.view_layer.update()
    # The bridge and soil origins need to follow their already deformed geometry.
    for o in sc.objects:
        if o.type=='MESH' and o.get('asset_id') in ['farm_soil','stone_bridge']:
            old=o.location.copy();delta=expand(old)-old;local=o.matrix_world.to_3x3().inverted()@delta
            for v in o.data.vertices:v.co-=local
            o.location+=delta

    # Small orchard: each crown is a reduced version of the established tree art.
    orchard=[]
    for i,(x,y,s) in enumerate([(9.2,6.5,.47),(12.8,8.6,.43),(12.0,2.0,.42),(15.4,5.3,.40)]):
        m=broad_tree(i%2);m.name=f'orchard_tree_{i}'
        for j in range(25):
            a=j*2.399; r=RNG.uniform(1.25,3.0);z=RNG.uniform(4.7,5.9)
            m.sphere((r*math.cos(a),r*.8*math.sin(a),z),(.20,.19,.22),'fruit_apple' if i%2==0 else 'fruit_pear',8,5)
        o=emit(m,x,y);o.scale=(s,)*3
        orchard.append(dict(position=list(o.location),radius=.5))

    # A roofed porch beside the house gives rain shelter a real visible location.
    hx,hy=house.location.x,-1.2
    porch=Mesh('home_garden_porch')
    for x in [-1.75,1.75]:
        for y in [-1.45,1.05]:porch.beam((x,y,0),(x,y,3.1),.095,'wood',n=8)
    for y in [-1.45,1.05]:porch.box((0,y,2.90),(3.85,.16,.2),'wood_dark')
    for i in range(13):
        x=-1.92+i*.32
        porch.box((x,-.22,3.03),( .34,3.1,.14),'roof' if i%3 else 'roof_light')
    emit(porch,hx,hy)
    bench('porch_bench',hx,hy+.75)
    planter('porch_flower_box',hx-2.75,hy+.3,1.7)
    planter('courtyard_herbs',-4.5,1.1,2.6)
    bench('riverside_bench',10.6,-11.4,math.pi*.86)
    planter('riverside_flowers',13.0,-11.4,2.3)
    bench('orchard_bench',17.0,3.5,math.pi/2)

    # Potting bench, crates and a small barrel make the courtyard feel occupied.
    work=Mesh('garden_potting_table')
    work.box((0,0,1.0),(2.3,.8,.14),'wood_light')
    for x in [-.94,.94]:
        for y in [-.28,.28]:work.box((x,y,.47),(.11,.11,.94),'wood')
    work.box((0,.38,1.65),(2.3,.1,.9),'wood')
    for x in [-.7,0,.7]:
        work.beam((x,0,1.05),(x,0,1.32),.17,'terracotta',r2=.23,n=10)
        work.sphere((x,0,1.43),(.22,.18,.17),'leaf',8,5)
    emit(work,-19.7,-1.6)
    crates=Mesh('orchard_crates')
    for x,y in [(0,0),(.78,.12)]:
        crates.box((x,y,.27),(.67,.55,.5),'wood_light')
        for j in range(6):crates.sphere((x+RNG.uniform(-.22,.22),y+RNG.uniform(-.17,.17),.54),(.10,.10,.1),'fruit_apple',7,4)
    emit(crates,15.5,1.2)
    barrel=Mesh('courtyard_rain_barrel')
    barrel.beam((0,0,.05),(0,0,.95),.44,'wood_dark',r2=.40,n=14)
    for z in [.14,.77]:barrel.beam((0,0,z),(0,0,z+.06),.455,'metal',n=14)
    emit(barrel,-19.1,-2.5)

    cafe_x=(bounds(cafe)[0][0]+bounds(cafe)[1][0])/2
    awning=Mesh('cafe_rain_awning')
    for x in [-1.8,1.8]:awning.beam((x,-1.1,0),(x,-1.1,3.05),.065,'wood',n=8)
    for i in range(12):awning.box((-1.98+i*.36,0,3.12),(.37,3.2,.10),'cream' if i%2 else 'cloth')
    emit(awning,cafe_x,-5.6)

    # New spurs join the existing paths and leave open meadow for later buildings.
    path('orchard_walk',[(8.6,-6.6),(10.4,-3.8),(9.2,-.2),(9.8,3.6),(11,5.2),(14.5,3.5),(18.8,1.4)])
    path('river_walk',[(8.6,-6.6),(10.2,-8.1),(10.6,-10.3),(15.0,-9.5),(20.4,-7.0),(22.3,-6.5)])
    path('courtyard_walk',[(-3.8,-3.0),(-5.5,-1.8),(hx,-2.25),(-14.1,-1.6),(-18.5,-2.5)])
    path('garden_front_walk',[(-18.0,-9.3),(-13.3,-11.3),(-8.6,-10.0),(-4.8,-7.7)])

    bpy.context.view_layer.update()
    meta=json.loads(json.dumps(original));meta.update(version=2,source='island_dusk_living.blend',layoutRevision=2,terrainScale=[SX,SY])
    meta['house']=bounds(house);meta['cafe']=bounds(cafe)
    meta['bridge']['position']=list(expand(original['bridge']['position']))
    meta['bridge']['halfLength']=3.4*SX;meta['bridge']['halfWidth']=1.08*SY
    meta['bridge']['walkHalfLength']=3.8*SX;meta['bridge']['walkHalfWidth']=.92*SY
    meta['spawn']=list(expand(original['spawn']))
    meta['smokeOrigin']=list(Vector(original['smokeOrigin'])+house_delta)
    meta['boatPivot']=list(Vector(original['boatPivot'])+boat_delta)
    meta['trees']=[dict(position=list(expand(t['position'])),radius=t['radius']) for t in original['trees']]+orchard
    meta['fences']=[bounds(o) for o in sc.objects if o.get('asset_id')=='farm_fence']
    for p in meta['plots']:
        p['position']=list(expand(p['position']));p['approach']=[p['approach'][0]*SX,p['approach'][1]*SY]
        p['halfSize']=[2.22*SX,2.52*SY]
    cafe_x=(meta['cafe'][0][0]+meta['cafe'][1][0])/2
    meta['cafeApproach']=[cafe_x,6.1-cafe_delta.y]
    meta['obstacles']=[bounds(o) for o in sc.objects if o.get('expansion_asset') and any(k in o.name for k in ['bench','flower_box','flowers','herbs','potting_table','crates','barrel'])]
    for x,y in [(hx+dx,hy+dy) for dx in [-1.75,1.75] for dy in [-1.45,1.05]]+[(cafe_x+dx,-6.7) for dx in [-1.8,1.8]]:
        meta['obstacles'].append([[x-.10,y-.10,ground(x,y)],[x+.10,y+.10,ground(x,y)+3.1]])
    meta['shelters']=[dict(position=[hx,-hy],roofHeight=ground(hx,hy)+3.2,halfSize=[1.8,1.5]),dict(position=[cafe_x,5.6],roofHeight=ground(cafe_x,-5.6)+3.25,halfSize=[2.1,1.6])]
    meta['lifeSites']=[
        dict(id='home',label='小院廊下',position=[hx,1.55],lookAt=[hx,3.5],shelter=True,duration=50),
        dict(id='garden',label='菜园',position=[meta['plots'][1]['approach'][0],-meta['plots'][1]['approach'][1]],lookAt=[meta['plots'][1]['position'][0],-meta['plots'][1]['position'][1]],action='Water',duration=24),
        dict(id='flowers',label='院边花草',position=[-4.5,.1],lookAt=[-4.5,-1.1],action='Water',duration=22),
        dict(id='orchard',label='果树林',position=[10.2,-3.8],lookAt=[12,-2],action='Harvest',duration=26),
        dict(id='cafe',label='咖啡馆檐下',position=meta['cafeApproach'],lookAt=[cafe_x,1.0],shelter=True,duration=32),
        dict(id='overlook',label='溪边长椅',position=[10.4,10.15],lookAt=[5,13],duration=35),
        dict(id='yard',label='花园工作台',position=[-18.2,1.0],lookAt=[-19.7,1.6],action='Plant',duration=22),
    ]
    meta['districts']=[dict(id=i,label=l,position=p) for i,l,p in [('home','生活小院',[-9,1.55]),('orchard','果树林',[10.2,-3.8]),('overlook','溪边散步',[10.4,10.15]),('garden','花园菜田',[-13.2,9.315])]]

    sc.camera.location=(29,-94,58);look_at(sc.camera,(0,0,8.8));sc.camera.data.ortho_scale=69
    sc['art_revision']='expanded_life_v4';sc['terrain_area_multiplier']=SX*SY
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'island_expanded.blend'),compress=True)

    preserved=[];static=[];player=bpy.data.objects['player']
    for o in list(sc.objects):
        if o.type!='MESH':continue
        if o.name in ['chimney_smoke_refined','waterfall_spray','flowing_ripples_and_eddies']:
            bpy.data.objects.remove(o,do_unlink=True);continue
        if o.parent==player or o.name.startswith('crop_') or o.name in ['boat_hull','stream_surface','waterfall_ribbons','garden_cat'] or o.get('asset_id')=='sheep':preserved.append(o)
        else:static.append(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in static:o.select_set(True)
    bpy.context.view_layer.objects.active=static[0];bpy.ops.object.join();scenery=bpy.context.object;scenery.name='island_scenery'
    source_tris=sum(len(p.vertices)-2 for p in scenery.data.polygons)
    if source_tris>475000:
        mod=scenery.modifiers.new('Expanded scene budget','DECIMATE');mod.ratio=475000/source_tris;mod.use_collapse_triangulate=True
        bpy.ops.object.modifier_apply(modifier=mod.name)
    scenery.data.validate();scenery.data.update()
    for mat in bpy.data.materials:
        if mat.use_nodes:
            p=mat.node_tree.nodes.get('Principled BSDF')
            if p:
                for link in list(p.inputs['Normal'].links):mat.node_tree.links.remove(link)
    for o in preserved+[scenery,player]:o.select_set(True)
    glb=OUT/'island_expanded.glb'
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_animations=False,export_yup=True,export_cameras=False,export_lights=False,export_extras=True)
    subprocess.run(['node','-e',"console.log(require('./scripts/optimize_glb.cjs').optimize('assets/expanded/island_expanded.glb'))"],cwd=ROOT,check=True)
    meta['webTriangles']=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in preserved+[scenery])
    meta['independentNodes']=[o.name for o in preserved]+['player']
    (OUT/'scene.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
    report=dict(terrainScale=[SX,SY],areaMultiplier=SX*SY,triangles=meta['webTriangles'],bytes=glb.stat().st_size,lifeSites=len(meta['lifeSites']))
    (ROOT/'reports/expansion_model.json').write_text(json.dumps(report,indent=2))
    print('EXPANSION_REPORT='+json.dumps(report))


if __name__=='__main__':main()
