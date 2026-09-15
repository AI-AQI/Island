import bpy, math, random, json
from pathlib import Path
from mathutils import Vector
from geometry import *
from build import ROOT,reset,stage,triangles

def run():
    reset();rng=random.Random(20260915);sc=bpy.context.scene;templates={};counts={};placed=[]
    groups={}
    for n in ['01_terrain','02_architecture','03_farm','04_trees','05_gardens','06_paths','07_water','08_clouds','09_details']:
        c=bpy.data.collections.new(n);sc.collection.children.link(c);groups[n]=c
    def place(name,x,y,z=None,scale=1,rz=0,group='09_details'):
        if name not in templates:
            with bpy.data.libraries.load(str(ROOT/'assets/source'/f'{name}.blend'),link=False) as (a,b):b.objects=[name]
            templates[name]=b.objects[0]
            for i,mat in enumerate(templates[name].data.materials):
                key=mat.name.split('.')[0]
                if key in MATS:templates[name].data.materials[i]=MATS[key]
        obj=templates[name].copy();obj.data=templates[name].data
        counts[name]=counts.get(name,0)+1;obj.name=f'{name}_{counts[name]:03d}'
        groups[group].objects.link(obj);obj.location=(x,y,land_z(x,y)-.04 if z is None else z)
        obj.scale=(scale,)*3 if isinstance(scale,(int,float)) else scale;obj.rotation_euler[2]=rz
        placed.append(obj);return obj
    def attached(host,asset,point,scale=1,rz=0,group='05_gardens'):
        stats=json.loads((ROOT/'reports'/f"{host['asset_id']}.json").read_text());p=Vector(point)-Vector(stats['offset'])
        p=host.matrix_world@p if False else p+host.location
        return place(asset,*p,scale=scale,rz=rz,group=group)
    place('island_base',0,0,0,group='01_terrain')
    house=place('house_main',-8,5,land_z(-8,5)-.16,group='02_architecture')
    cafe=place('cafe_pavilion',18,-2.5,land_z(18,-2.5)-.16,group='02_architecture')
    by=-5.2;bx=river_x(by);bridge_level=(land_z(bx-3.4,by)+land_z(bx+3.4,by))/2-.47+.02
    bridge=place('stone_bridge',bx,by,bridge_level,group='02_architecture')
    # Gardens / vegetable beds, with openings along their paths.
    for bed,(cx,cy,typ) in enumerate([(-15,-3.7,'crop_pumpkin'),(-10.9,-3.7,'crop_generic_leaf'),(-6.8,-3.7,'crop_generic_radish')]):
        place('farm_soil',cx,cy,group='03_farm')
        for yy in [-1.02,1.02]:
            place(typ,cx,cy+yy,land_z(cx,cy)+.22,scale=.91,rz=.08*(bed-1),group='03_farm')
        for dx in [-2.02,2.02]:
            for yy in [-1.02,1.02]:place('farm_fence',cx+dx,cy+yy,rz=pi/2,group='03_farm')
        for xx in [-1.02,1.02]:
            for dy in [-2.28,2.28]:
                if dy<0 and xx>0:continue
                place('farm_fence',cx+xx,cy+dy,group='03_farm')
    place('scarecrow',-17.8,-1.4,rz=-.18,group='03_farm')
    for x,y,a in [(-16,.9,-.2),(-13.7,1.05,.25),(-18.1,2.1,-.55)]:place('sheep',x,y,scale=1.08,rz=a,group='03_farm')
    for i in range(5):place('farm_fence',-18.1+i*2,3.0,group='03_farm')
    # Six broadleaf trees and a smaller flowering tree beside the cottage.
    for i,(x,y,s) in enumerate([(-14.2,8.7,1.07),(-18.3,3.8,.89),(-2.8,9.3,.92),(10.9,6.4,1.05),(16.4,4.2,.96),(-19.8,-1.7,.67)]):
        place('tree_large_green' if i%2==0 else 'tree_large_gold',x,y,scale=s,rz=i*1.7,group='04_trees')
    place('tree_blossom',-2.5,5,scale=.83,rz=.4,group='04_trees')
    # Deliberately curved footpaths with two parallel courses of irregular slabs.
    paths=[ [(-9.6,.2),(-9.3,-.55),(-5,-.6),(-3,-2.8),(bx-3.7,by)],
            [(bx+3.7,by),(7,-6.4),(11,-7.9),(17.9,-7.3),(18,-6.8)],
            [(-17,-7),(-12,-7.3),(-8,-7.2),(-4.4,-6),(bx-3.7,by)],
            [(-17,1.8),(-15,.3),(-12,-.9),(-9.3,-.55)],
            [(7,-6.4),(7.7,-1.8),(8.2,2.3),(10.9,4.5)] ]
    path_points=[]
    for path in paths:
        for j in range(len(path)-1):
            a,b=Vector(path[j]),Vector(path[j+1]);d=(b-a);length=d.length;normal=Vector((-d.y,d.x)).normalized();angle=math.atan2(d.y,d.x)
            for i in range(max(1,int(length/.74))):
                p=a+d*(i+.35)/max(1,int(length/.74));path_points.append(p)
                for side in [-1,1]:
                    pp=p+normal*(side*.35+rng.uniform(-.045,.045))
                    place('stone_path_'+str(rng.randint(1,3)),pp.x,pp.y,land_z(pp.x,pp.y)+.015,scale=rng.uniform(.82,1.02),rz=angle+rng.uniform(-.2,.2),group='06_paths')
    # Water is a continuous strip in the carved river bed.
    water=Mesh('stream_surface');yy=[-13.35+26.1*i/110 for i in range(111)]
    for y in yy:
        for j in range(9):
            x=river_x(y)+(j/8-.5)*4.5;z=9.98+.02*sin(y*.7+j*.8)
            water.v.append((x,y,z))
    for i in range(110):
        for j in range(8):
            a=i*9+j;water.face((a,a+1,a+10,a+9),'water',True)
    wo=water.object(groups['07_water']);placed.append(wo)
    ripple=Mesh('stream_ripples')
    for i in range(145):
        y=rng.uniform(-13.2,12.6);x=river_x(y)+rng.uniform(-1.25,1.25);r=rng.uniform(.08,.33)
        if land_z(x,y)>10.04:continue
        pts=[(x+r*cos(t),y+.34*r*sin(t),10.043) for t in [j*pi/6 for j in range(5)]];ripple.tube(pts,.012 if i%2 else .018,'foam',4)
    placed.append(ripple.object(groups['07_water']))
    # Waterfall follows the lip, then drops clear of the cliff and dissolves into spray.
    fall=Mesh('waterfall_sheet');fx=river_x(-13.25);rows=32;cols=24
    for i in range(rows+1):
        t=i/rows;z=10.0-13*t;y=-13.2-1.5*(1-math.exp(-t*8))-.7*t
        for j in range(cols+1):
            u=j/cols;w=3.3*(1-.17*t);x=fx+(u-.5)*w+.07*sin(t*18+j*1.7)
            fall.v.append((x,y+.04*sin(j*2.4+t*12),z))
    for i in range(rows):
        for j in range(cols):
            a=i*(cols+1)+j;fall.face((a,a+1,a+cols+2,a+cols+1),'waterfall' if j%7 else 'foam',True)
    placed.append(fall.object(groups['07_water']))
    streak=Mesh('waterfall_foam')
    for j in range(28):
        t0=rng.uniform(0,.3);t1=rng.uniform(.55,.99);xx=fx+rng.uniform(-1.55,1.55)
        pts=[]
        for i in range(15):
            t=t0+(t1-t0)*i/14;pts.append((xx+.065*sin(t*19+j),-13.27-1.5*(1-math.exp(-t*8))-.7*t,10.02-13*t))
        streak.tube(pts,rng.uniform(.011,.026),'foam',4)
    for i in range(145):
        t=rng.uniform(.5,1.05);streak.sphere((fx+rng.uniform(-2,2)*t,-15.25+rng.uniform(-.6,.2),10-13*t),(.03,.035,.06),'foam',5,3)
    placed.append(streak.object(groups['07_water']))
    # River boulders and reed/flower tufts sit on banks, outside the water corridor.
    for side in [-1,1]:
        for i in range(24):
            y=-12.5+i*1.07
            if abs(y-by)<1.9:continue
            x=river_x(y)+side*rng.uniform(2.25,2.9)
            place('rock_deco_'+str(rng.choice([2,3])),x,y,land_z(x,y)-.25,scale=rng.uniform(.65,1.12),rz=rng.random()*pi,group='05_gardens')
            if i%2==0:place('bush_flower_'+rng.choice(['white','pink','yellow']),x+side*.55,y,scale=rng.uniform(.85,1.4),group='05_gardens')
    # Sparse clusters along path sides; never across a doorway or bridge entrance.
    for i,p in enumerate(path_points):
        if i%3:continue
        for side in [-1,1]:
            x=p.x+rng.uniform(-.3,.3);y=p.y+side*rng.uniform(1.0,1.5)
            if x<-5 and -6.2<y<-1.6:continue
            if abs(x-river_x(y))<3.1:continue
            place('bush_flower_'+rng.choice(['white','pink','yellow']),x,y,scale=rng.uniform(.9,1.6),rz=rng.random()*6.28,group='05_gardens')
    # Concentrated planting and hanging vines along the foreground rim.
    for i in range(54):
        t=pi+pi*i/53;x=20.65*cos(t);y=12.55*sin(t)
        if abs(x-river_x(y))<3.0:continue
        if x>13 and y>-8:continue
        place('bush_flower_'+['white','pink','yellow'][i%3],x,y,scale=rng.uniform(.9,1.55),rz=t,group='05_gardens')
        if i%2==0:
            s=rng.uniform(1.1,1.85);place('vine_hanging',x*1.15,y*1.19,land_z(x,y)-3.7*s-.22,scale=s,rz=t+pi/2,group='05_gardens')
            shoot=Mesh('vine_rim_root');shoot.beam((x,y,land_z(x,y)-.12),(x*1.15,y*1.19,land_z(x,y)-.15),.025,'wood',n=5)
            for q in [.3,.5,.7,.9]:shoot.leaf((x*(1+.15*q),y*(1+.19*q),land_z(x,y)-.06),.55,.29,t,.25,'leaf')
            placed.append(shoot.object(groups['05_gardens']))
        if i%4==0:place('rock_deco_3',x*.97,y*.96,scale=.8,group='05_gardens')
    for i in range(14):
        t=rng.uniform(0,pi);x=21*cos(t);y=12*sin(t)
        place('vine_hanging',x,y,land_z(x,y)-rng.uniform(3.1,4.2),rz=t+pi/2,group='05_gardens')
    # Pots, climbing ivy and sunflowers use attachment points in each building's local frame.
    for x,y,z in [(-3.4,-3.1,.75),(-.1,-3.5,.75),(3.45,-3.35,.76),(1.1,-3.32,1.55),(2.4,-3.32,1.55),(0,-3.15,4.75)]:
        attached(house,'flower_pot_'+str(1+int(abs(x))%2),(x,y,z),scale=.85 if z>1 else 1.2)
    for x in [-3.75,.4,3.65]:attached(house,'ivy_wall',(x,-3.03,.78),scale=1.6)
    for i in range(4):attached(house,'sunflower',(-3.9-i*.38,-3.7+i*.2,.13),scale=1+i*.06)
    for x,y,z in [(-4,-3,1),(4,-3,1),(-3.7,.2,1),(3.7,.2,1),(1.9,-3.9,.4)]:attached(cafe,'flower_pot_2',(x,y,z),scale=1.15)
    for x in [-3.1,3.05]:attached(cafe,'ivy_wall',(x,.03,1),scale=1.25)
    for x in [-4.5,-3,3,4.5]:attached(cafe,'vine_hanging',(x,-3.3,-2.4),scale=.95)
    # Lamps stand on paving. Emission belongs to each lantern's material slot.
    for x,y in [(-5.3,.4),(-3.5,-6.8),(6.1,-4.9),(11.9,-6.5),(7.25,3.1),(-17,-6.8),(16.2,-6.5)]:place('lamp_post',x,y,rz=pi if x>0 else 0)
    for x,y in [(-11,.2),(-6.5,1.1),(14.5,-6.8)]:place('lantern_stone',x,y)
    place('player_ref',-3.9,-1.6,rz=-.25)
    place('hanging_boat',20.7,-6.4,6.15)
    anchors=Mesh('boat_davit_anchors')
    for x in [19.4,22.0]:
        anchors.beam((x,-5.57,10.45),(19.1+(x-19.4)*.24,-3.6,10.6),.14,'wood_dark')
        anchors.beam((x,-5.57,8.4),(19.1+(x-19.4)*.24,-3.6,10.6),.1,'wood')
        anchors.box((19.1+(x-19.4)*.24,-3.6,10.65),(.55,.55,.25),'rock_dark')
    placed.append(anchors.object(groups['09_details']))
    # Clouds and two reused distant islands establish depth below and behind the stage.
    for i,(x,y,z,s) in enumerate([(-24,4,-1,2.7),(-23,-9,-4,2.7),(-16,-17,-6,2.5),(-5,-20,-7,2.4),(7,-19,-6,2.5),(19,-14,-4,2.6),(26,-3,-1,2.7),(23,12,0,2.5),(-12,20,1,2.7),(8,20,-1,2.9),(-30,21,-7,3.3),(24,30,-7,3.5),(-4,29,-8,3.7),(29,-23,-11,3.7)]):
        place('cloud_puff_'+str(1+i%3),x,y,z,scale=s,rz=rng.uniform(-.4,.4),group='08_clouds')
    place('distant_island',-29,12,6,scale=.5,group='08_clouds');place('distant_island',17,21,5,scale=.47,group='08_clouds')
    # Smoke is a quiet static chimney plume, omitted from the runtime animation system.
    smoke=Mesh('chimney_smoke')
    for i in range(5):smoke.sphere((-10.35+.19*sin(i),6.68,19.52+i*.55),(.25+i*.075,.25+i*.065,.39),'cloud_warm',9,5)
    placed.append(smoke.object(groups['09_details']))
    cam=stage((0,0,9),66,False);cam.location=(39,-65,47);look_at(cam,(0,0,8.0));cam.data.ortho_scale=64
    bpy.data.objects['sunset_key'].location=(35,-15,20);look_at(bpy.data.objects['sunset_key'],(0,0,10))
    # Dusk sky gradient in the world, separate from the portable PBR mesh.
    world=sc.world;nodes=world.node_tree.nodes;links=world.node_tree.links;bg=nodes.get('Background')
    tex=nodes.new('ShaderNodeTexCoord');sep=nodes.new('ShaderNodeSeparateXYZ');ramp=nodes.new('ShaderNodeValToRGB');mul=nodes.new('ShaderNodeMath');mul.operation='MULTIPLY_ADD';mul.inputs[1].default_value=.75;mul.inputs[2].default_value=.5
    links.new(tex.outputs['Normal'],sep.inputs[0]);links.new(sep.outputs['Z'],mul.inputs[0]);links.new(mul.outputs[0],ramp.inputs[0])
    ramp.color_ramp.elements[0].position=.15;ramp.color_ramp.elements[0].color=rgba('C8B0E0');ramp.color_ramp.elements[1].position=.83;ramp.color_ramp.elements[1].color=rgba('F5C8A8')
    links.new(ramp.outputs[0],bg.inputs[0]);bg.inputs[1].default_value=.6
    # A small static solar disc in the upper-right background of the acceptance camera.
    sun=Mesh('sun_disc');sun.sphere((15,23,16),(2.0,2.0,2.0),'sun',32,16);placed.append(sun.object(groups['08_clouds']))
    sc.cycles.samples=64;sc.render.resolution_x=2048;sc.render.resolution_y=1152
    # Light glows use compositor glare only for rendering; the GLB retains emissive surfaces.
    # Orthographic rays are parallel, so a world-direction gradient would appear flat.
    # A packed compositor sky supplies the requested image-space lavender-to-peach gradient.
    sc.render.film_transparent=True
    sky=bpy.data.images.new('dusk_sky_2048',width=2048,height=1152,alpha=True,float_buffer=True)
    sky.colorspace_settings.name='Linear Rec.709';pixels=[];low=rgba('F5C8A8');high=rgba('C8B0E0')
    for row in range(1152):
        t=row/1151
        for col in range(2048):
            u=col/2047;glow=.18*math.exp(-((u-.83)/.3)**2-((t-.68)/.4)**2)
            c=[(low[k]*(1-t)+high[k]*t)*1.35+glow*low[k] for k in range(3)]
            pixels.extend((*c,1))
    sky.pixels.foreach_set(pixels);sky.pack()
    nt=bpy.data.node_groups.new('dusk_compositing','CompositorNodeTree');sc.compositing_node_group=nt
    nt.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor')
    rl=nt.nodes.new('CompositorNodeRLayers');g=nt.nodes.new('CompositorNodeGlare');g.inputs['Type'].default_value='Fog Glow';g.inputs['Quality'].default_value='High';g.inputs['Threshold'].default_value=1.7;g.inputs['Strength'].default_value=.17;g.inputs['Size'].default_value=.32
    sky_node=nt.nodes.new('CompositorNodeImage');sky_node.image=sky
    over=nt.nodes.new('CompositorNodeAlphaOver');out=nt.nodes.new('NodeGroupOutput')
    nt.links.new(rl.outputs['Image'],g.inputs['Image']);nt.links.new(sky_node.outputs['Image'],over.inputs['Background']);nt.links.new(g.outputs['Image'],over.inputs['Foreground']);nt.links.new(over.outputs[0],out.inputs['Image'])
    bpy.context.view_layer.update()
    total=sum(triangles(o) for o in placed)
    sc['asset_count']=len(counts);sc['triangle_count']=total;sc['static_scene']=True;sc['reference_camera']='south_to_north_30_degrees'
    sc.render.filepath=str(ROOT/'renders/island_dusk_2048.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'island_dusk.blend'))
    report={'triangles':total,'asset_variants':len(counts),'instances':counts,'triangle_budget':600000,'texture_size_max':0,'coordinate_system':'Blender Z-up, -Y forward; glTF standard Y-up export','bridge':{'center':[bx,by,bridge_level],'span_m':6.8,'water_level_m':9.98,'end_deck_level_m':bridge_level+.47},'tripo':{'status':'device_authorization_service_unreachable','credits_consumed':0},'render':[2048,1152]}
    # Flatten by material for the browser: editable instances remain in the saved Blender source.
    bpy.ops.object.select_all(action='DESELECT')
    for o in placed:o.select_set(True)
    bpy.context.view_layer.objects.active=placed[0];bpy.ops.object.join();joined=bpy.context.object;joined.name='island_dusk_scene'
    bpy.ops.export_scene.gltf(filepath=str(ROOT/'island_dusk.glb'),export_format='GLB',use_selection=True,export_yup=True,export_animations=False,export_materials='EXPORT')
    report['glb_bytes']=(ROOT/'island_dusk.glb').stat().st_size;report['budget_pass']=total<=600000 and report['glb_bytes']<=25000000
    (ROOT/'reports/scene_report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    print('SCENE_REPORT '+json.dumps(report),flush=True)
    bpy.ops.render.render(write_still=True)
    # Additional genuine 3D camera views, useful for verifying hidden sides and layout.
    sc.cycles.samples=32;sc.render.resolution_x=1500;sc.render.resolution_y=1000
    for name,pos,target,size in [('house_detail',(-22,-17,24),(-8,3,13),21),('cafe_detail',(32,-21,24),(17,-1,13),19),('layout_top',(0,0,75),(0,0,5),56)]:
        cam.location=pos;look_at(cam,target);cam.data.ortho_scale=size;sc.render.filepath=str(ROOT/'renders'/f'{name}.png');bpy.ops.render.render(write_still=True)
