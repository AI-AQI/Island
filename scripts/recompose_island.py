"""Rebuild the main island's composition around a broad central common.

Read the editable living source, keep its architecture/character/prop assets,
author terrain and a variable-width meandering river, and relocate districts.
"""
import json
import math
import random
import subprocess
import sys
from pathlib import Path
import bpy
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from geometry import Mesh,MATS,material,look_at
from prepare_living import bounds,bend
from geometry import land_z
from layout_spec import RADIUS,RIVER,ground,closest,bridge_pose
import expand_island as props
props.ground=ground

OUT=ROOT/'assets/layout'
RNG=random.Random(91926)

def old_ground(x,y):return land_z(x-bend(y),y)
def emit(m):
    o=m.object();o['layout_asset']=True;return o

def garden_path(name,points,width):
    m=Mesh(name)
    for a,b in zip(points,points[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy);n=max(1,math.ceil(length/.62))
        for i in range(n):
            t=(i+.5)/n
            for j in [-1,0,1]:
                side=j*.48*width
                x=a[0]+dx*t-dy/length*side+RNG.uniform(-.07,.07);y=a[1]+dy*t+dx/length*side+RNG.uniform(-.07,.07)
                m.sphere((x,y,ground(x,y)+.04),(.38,.34,.075),RNG.choice(['rock','rock_light','rock_warm']),7,3,False,.11,RNG.randrange(100000))
    return emit(m)
def relocate(o,x,y):
    old=o.location.copy();o.location+=(Vector((x,y,ground(x,y)))-Vector((old.x,old.y,old_ground(old.x,old.y))))
    return o.location-old
def build_terrain():
    m=Mesh('island_land');n=192;nr=60
    m.v=[(0,0,ground(0,0))]
    for j in range(1,nr+1):
        r=j/nr
        for i in range(n):
            a=i*math.tau/n;q=1+.009*math.sin(a*7)+.005*math.sin(a*13)
            x=RADIUS[0]*math.cos(a)*r*q;y=RADIUS[1]*math.sin(a)*r*q
            m.v.append((x,y,ground(x,y)))
    for i in range(n):m.face((0,1+i,1+(i+1)%n),'grass',True)
    for j in range(nr-1):
        for i in range(n):
            a=1+j*n+i;b=1+j*n+(i+1)%n
            x,y,_=m.v[a];dist,width,_,_=closest(x,y)
            mat='soil_light' if dist<width+.25 else 'grass'
            m.face((a,a+n,b+n,b),mat,True)
    prev=[1+(nr-1)*n+i for i in range(n)]
    for r,z in [(1,9.6),(.98,7.5),(.86,4.5),(.66,1.4),(.39,-1.6),(.08,-3.7)]:
        ids=[]
        for i in range(n):
            a=i*math.tau/n;ids.append(len(m.v));m.v.append((RADIUS[0]*r*math.cos(a),RADIUS[1]*r*math.sin(a),z+.22*math.sin(a*9)))
        for i in range(n):m.face((prev[i],ids[i],ids[(i+1)%n],prev[(i+1)%n]),RNG.choice(['rock','rock_warm','rock_dark']))
        prev=ids
    m.face(tuple(reversed(prev)),'rock_dark')
    emit(m)
    cliff=Mesh('island_cliff_strata')
    for row,(r,z,h,count) in enumerate([(1,8.4,1.8,65),(.96,5.8,2.0,60),(.83,3,2.0,52),(.63,.3,1.7,40),(.36,-2.1,1.3,24)]):
        for i in range(count):
            a=(i+.4*(row%2))*math.tau/count;x=RADIUS[0]*r*math.cos(a);y=RADIUS[1]*r*math.sin(a)
            if y<-16 and 6<x<16:continue
            cliff.sphere((x,y,z+RNG.uniform(-.25,.25)),(RNG.uniform(.85,1.55),RNG.uniform(.80,1.35),h),RNG.choice(['rock','rock_light','rock_warm','rock_dark']),9,5,False,.13,i+row*70)
    emit(cliff)

def build_river():
    m=Mesh('stream_surface');cols=12
    def section(i,u):
        x,y,w=RIVER[i];a=RIVER[max(0,i-1)];b=RIVER[min(len(RIVER)-1,i+1)]
        dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
        return x-dy/length*w*u,y+dx/length*w*u
    for i,(x,y,w) in enumerate(RIVER):
        a=RIVER[max(0,i-1)];b=RIVER[min(len(RIVER)-1,i+1)]
        dx,dy=b[0]-a[0],b[1]-a[1];l=math.hypot(dx,dy);nx,ny=-dy/l,dx/l
        for j in range(cols+1):
            u=j/cols*2-1;px=x+nx*w*u;py=y+ny*w*u
            if i<8:
                t=i/8;edge=RADIUS[1]*math.sqrt(max(0,1-(px/RADIUS[0])**2))-.05
                py=py*t+edge*(1-t)
            if i>len(RIVER)-25:
                # Interpolate complete cross-sections to the shore. Clamping
                # only Y at the end folds the outside bank back over itself.
                t=(i-(len(RIVER)-25))/24;ax,ay=section(len(RIVER)-25,u);ex,_=section(len(RIVER)-1,u)
                ey=-RADIUS[1]*math.sqrt(max(0,1-(ex/RADIUS[0])**2))+.08
                px=ax+(ex-ax)*t;py=ay+(ey-ay)*t
            m.v.append((px,py,10.055))
    for i in range(len(RIVER)-1):
        for j in range(cols):
            a=i*(cols+1)+j;m.face((a,a+cols+1,a+cols+2,a+1),'water',True)
    emit(m)
    lip=m.v[-(cols+1):];fall=Mesh('waterfall_ribbons')
    # Ribbons begin exactly at the curved shore, with distinct widths and lengths.
    for k in range(57):
        u=k/56;f=u*cols;i=min(cols-1,int(f));q=f-i;a=lip[i];b=lip[i+1];x=a[0]*(1-q)+b[0]*q;y=a[1]*(1-q)+b[1]*q
        start=len(fall.v);length=RNG.uniform(12.5,15.3);width=RNG.uniform(.045,.095)
        for j in range(29):
            t=j/28;yy=y-1.55*(1-math.exp(-t*7))-.40*t;z=10.055-length*t
            xx=x+.055*math.sin(t*18+k)
            fall.v.extend([(xx-width,yy,z),(xx+width,yy,z)])
        for j in range(28):
            a=start+j*2;fall.face((a,a+2,a+3,a+1),'foam' if k%7==0 else 'waterfall',True)
    emit(fall)
    foam=Mesh('waterfall_lip_foam')
    for i in range(len(lip)-1):
        a=lip[i];b=lip[i+1]
        foam.beam((a[0],a[1],10.09),(b[0],b[1],10.09),.045,'foam',n=6)
    emit(foam)
    return [list(p) for p in lip]

def fence(m,a,b,gap=False):
    length=math.dist(a,b);count=max(1,math.ceil(length/1.8))
    for i in range(count+1):
        t=i/count;x=a[0]+(b[0]-a[0])*t;y=a[1]+(b[1]-a[1])*t;z=ground(x,y)
        m.beam((x,y,z),(x,y,z+1.08),.075,'wood',n=7)
    for i in range(count):
        if gap and i==count//2:continue
        p=[a[k]+(b[k]-a[k])*i/count for k in range(2)];q=[a[k]+(b[k]-a[k])*(i+1)/count for k in range(2)]
        for h in [.42,.83]:m.beam((*p,ground(*p)+h),(*q,ground(*q)+h),.047,'wood_light',n=6)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'island_dusk_living.blend'))
    bpy.context.preferences.filepaths.save_version=0
    sc=bpy.context.scene
    for mat in bpy.data.materials:MATS[mat.name]=mat
    material('fruit_apple','C95F44',.7)
    material('waterfall','92D8E5',.24,alpha=.78)
    old=json.loads((ROOT/'assets/living/scene.json').read_text())
    house=bpy.data.objects['house_main_001'];cafe=bpy.data.objects['cafe_pavilion_001'];bridge=bpy.data.objects['stone_bridge_001'];player=bpy.data.objects['player'];boat=bpy.data.objects['boat_hull']
    flower_templates={c:next(o for o in sc.objects if o.get('asset_id')=='bush_flower_'+c).copy() for c in ['white','pink','yellow']}
    tree_templates=[o.copy() for o in sc.objects if o.get('asset_id','').startswith('tree_large')]
    lamp_template=next(o for o in sc.objects if o.get('asset_id')=='lamp_post').copy()
    rock_template=next(o for o in sc.objects if o.get('asset_id')=='rock_deco_3').copy()
    vine_template=next(o for o in sc.objects if o.get('asset_id')=='vine_hanging').copy()
    tree_metadata=[];fence_objects=[]
    house_delta=Vector((-12,10,house.location.z+ground(-12,10)-old_ground(*house.location[:2])))-house.location
    cafe_delta=Vector((18,9,cafe.location.z+ground(18,9)-old_ground(*cafe.location[:2])))-cafe.location
    boat_delta=Vector((29.4,4,boat.location.z))-boat.location
    farm_targets=[(-20,-9),(-15.1,-9),(-10.2,-9)]
    farm_deltas=[Vector((x,y,p['position'][2]+ground(x,y)-old_ground(*p['position'][:2])))-Vector(p['position']) for (x,y),p in zip(farm_targets,old['plots'])]
    keep=set()
    for o in list(sc.objects):
        if o.type not in ['MESH','EMPTY'] or o.parent:continue
        aid=o.get('asset_id','');name=o.name
        if o==house or name in ['flowering_window_climber','chimney_smoke_refined'] or (aid in ['flower_pot_1','flower_pot_2','ivy_wall','sunflower'] and o.location.x<0):o.location+=house_delta
        elif o==cafe or name in ['cafe_glazed_back','cafe_garden_approach'] or (aid in ['flower_pot_1','flower_pot_2','ivy_wall'] and o.location.x>10):o.location+=cafe_delta
        elif name in ['boat_hull','boat_support','boat_davit_anchors']:o.location+=boat_delta
        elif o==player:relocate(o,-1,-4)
        elif name=='garden_cat':relocate(o,1,-4.5)
        elif o==bridge:
            pose,angle=bridge_pose();o.location=pose;o.rotation_euler.z=angle;o.scale.x*=1.35
        elif aid=='farm_soil' or name.startswith('crop_'):
            index=int(name.split('_')[1]) if name.startswith('crop_') else min(range(3),key=lambda i:abs(o.location.x-old['plots'][i]['position'][0]))
            o.location+=farm_deltas[index]
        elif aid=='farm_fence':
            index=int(name.rsplit('_',1)[1])-1
            if index<21:o.location+=farm_deltas[index//7];fence_objects.append(o)
            else:bpy.data.objects.remove(o,do_unlink=True);continue
        elif aid=='sheep':
            i=int(name.rsplit('_',1)[1])-1;relocate(o,*[(-23.3,1.0),(-20.5,1.9),(-21.8,-.8)][i])
        elif aid=='scarecrow':relocate(o,-23.5,-5)
        else:
            if o.type=='MESH':bpy.data.objects.remove(o,do_unlink=True)
            continue
        keep.add(o.name)

    build_terrain();lip=build_river()
    def instance(template,name,x,y,scale=1,rz=0,z=None):
        o=template.copy();o.data=template.data;sc.collection.objects.link(o);o.name=name;o.location=(x,y,ground(x,y) if z is None else z);o.scale*=scale;o.rotation_euler.z=rz;return o
    for i,(x,y,size) in enumerate([(-18,14,1.6),(-25,6,.78),(-25,-3,.52),(-3,14,.53),(20,14,1.3),(25,7,.63),(10.5,15,.57),(-23,10,.48)]):
        # Use the same source tree each time so size has a predictable meaning.
        o=instance(tree_templates[0],f'landmark_tree_{i}',x,y);o.scale=(size,)*3;tree_metadata.append(dict(position=list(o.location),radius=.5*size+.25))
    for i,(x,y) in enumerate([(22.5,1),(25,3.8),(22.8,-2.8)]):
        o=instance(tree_templates[0],f'orchard_tree_{i}',x,y);o.scale=(.42,)*3;tree_metadata.append(dict(position=list(o.location),radius=.48))
        apples=Mesh(f'orchard_apples_{i}')
        for j in range(20):
            a=j*2.399;r=RNG.uniform(.55,1.2);apples.sphere((x+r*math.cos(a),y+.8*r*math.sin(a),ground(x,y)+RNG.uniform(1.9,2.55)),(.09,.08,.1),'fruit_apple',7,4)
        emit(apples)
    # A real sheep enclosure in the lower-left district, separate from the house.
    pen=Mesh('sheep_enclosure')
    for a,b,gap in [((-25.4,-2),(-17.8,-2),False),((-25.4,-2),(-25.4,4.3),False),((-25.4,4.3),(-17.8,4.3),False),((-17.8,4.3),(-17.8,-2),True)]:fence(pen,a,b,gap)
    pen_obj=emit(pen)
    # Open common: two curving routes and modest side furniture, no central wall.
    routes=[('home_to_common',[(-12,4.8),(-10,3.0),(-5,1.4),(-1,-2.7),(2,-5.8),(7,-8.5),(11.4,-10.0)],1.3),
            ('garden_to_common',[(-19.4,-12.1),(-14.4,-12.1),(-9.5,-12.1),(-5.7,-10.7),(-3.4,-7.7),(2,-5.8)],1.15),
            ('meadow_loop',[(-14.8,3),(-15.6,.3),(-15.7,-3.7),(-11.8,-4.5),(-7.4,-4.6),(-5,1.4)],.95),
            ('east_bank_walk',[(20.2,-11.5),(24,-8),(25.3,-4.5),(20.5,-1),(18,2.8)],1.15)]
    for name,points,width in routes:garden_path(name,points,width)
    # A small stone gathering circle leaves broad walkable grass between routes.
    plaza=Mesh('common_gathering_stones')
    for i in range(130):
        a=i*2.399;r=3.3*math.sqrt((i+.5)/130);x=-2+r*math.cos(a);y=-3.8+r*.78*math.sin(a)
        plaza.sphere((x,y,ground(x,y)+.025),(.34,.28,.055),RNG.choice(['rock_light','rock','rock_warm']),7,3,False,.1,i)
    emit(plaza)
    props.bench('common_bench',-6.3,-2.5,.18)
    props.bench('creek_bench',3.6,-10.6,math.pi*.9)
    props.planter('common_flowers',-6.6,-1.5,2.2)
    props.planter('yard_herbs',-15,3.5,2.1)
    # Side porch and cafe awning provide daily-life rain destinations.
    shelters=[];post_boxes=[]
    for name,x,y,w,d in [('home',-10.9,3.1,1.8,1.3),('cafe',18,2.9,1.9,1.3)]:
        m=Mesh(name+'_shelter')
        for dx in [-w,w]:
            for dy in [-d,d]:
                m.beam((x+dx,y+dy,ground(x,y)),(x+dx,y+dy,ground(x,y)+3),.07,'wood',n=6)
                post_boxes.append([[x+dx-.08,y+dy-.08,10],[x+dx+.08,y+dy+.08,14]])
        for i in range(12):m.box((x-w-.12+i*(2*w+.24)/11,y,ground(x,y)+3.05),((2*w+.24)/11+.025,d*2+.3,.11),'roof' if name=='home' else 'cream' if i%2 else 'cloth')
        emit(m);shelters.append(dict(position=[x,-y],halfSize=[w+ .1,d+.1],roofHeight=ground(x,y)+3.15))
    props.bench('porch_bench',-10.9,3.85)
    props.bench('orchard_bench',25.2,-.5,math.pi/2)
    props.planter('orchard_flower_box',24.2,-1.7,1.6)
    # Move the potting table from the previous expansion recipe, keeping its scale.
    work=Mesh('garden_potting_table')
    work.box((-18,3,ground(-18,3)+1),(2,.7,.12),'wood_light')
    for dx in [-.85,.85]:
        for dy in [-.25,.25]:work.box((-18+dx,3+dy,ground(-18,3)+.5),(.11,.11,1),'wood')
    emit(work)
    # Banks vary in density. Flower groups sit beside paths and rocks, not across them.
    for side in [-1,1]:
        for i in range(5,len(RIVER)-3,5):
            x,y,w=RIVER[i];a=RIVER[i-1];b=RIVER[i+1];dx,dy=b[0]-a[0],b[1]-a[1];l=math.hypot(dx,dy)
            px=x-dy/l*side*(w+.60);py=y+dx/l*side*(w+.60)
            if (px/RADIUS[0])**2+(py/RADIUS[1])**2>.96 or math.dist((px,py),bridge_pose()[0][:2])<5:continue
            instance(rock_template,f'river_bank_rock_{side}_{i}',px,py,RNG.uniform(.55,.95),RNG.random()*6.28,z=ground(px,py)-.25)
            if i%3:instance(flower_templates[RNG.choice(['white','pink','yellow'])],f'river_bank_bloom_{side}_{i}',px-dy/l*side*.65,py+dx/l*side*.65,RNG.uniform(.6,.95),RNG.random()*6.28)
    clusters=[(-14,4.5),(-6,3),(-7,-7),(-3,-10),(-7,-15),(-17,-14),(-23,-12),(-25,-6),(1,-8),(5,-12),(5,1),(20,-4),(23,-9),(25,0),(15,3),(12,11)]
    clusters += [(-23,8),(-21,10),(-7,15),(-8,17),(0,17),(7,15),(12,14),(15,14),(-22,-15),(-17,-17),(-10,-17),(-2,-17),(2,-14),(3,3),(-8,1.5)]
    for i,(x,y) in enumerate(clusters):
        for j in range(5):instance(flower_templates[['white','pink','yellow'][(i+j)%3]],f'garden_bloom_{i}_{j}',x+RNG.uniform(-1.0,1.0),y+RNG.uniform(-.7,.7),RNG.uniform(.85,1.45),RNG.random()*6.28)
    shrubs=Mesh('layered_garden_shrubs')
    for i,(x,y) in enumerate(clusters):
        for j in range(7):
            a=j*2.399;r=RNG.uniform(.3,1.0);px=x+math.cos(a)*r;py=y+math.sin(a)*r
            shrubs.sphere((px,py,ground(px,py)+.30),(.48,.42,.36),RNG.choice(['leaf_dark','leaf','leaf_light']),8,5,True,.09,i*7+j)
            for k in range(9):shrubs.leaf((px+.4*math.cos(k),py+.4*math.sin(k),ground(px,py)+.60),.26,.14,k,.2,'leaf_light')
    emit(shrubs)
    # Larger rim boulders break the regular outline and ground the flower beds.
    for i in range(48):
        a=math.pi+math.pi*i/47;x=RADIUS[0]*.98*math.cos(a);y=RADIUS[1]*.98*math.sin(a)
        dist,w,_,_=closest(x,y)
        if dist>w+1.1:instance(rock_template,f'rim_boulder_{i}',x,y,RNG.uniform(.65,1.05),a,z=ground(x,y)-.4)
    for i in range(88):
        a=math.pi+math.pi*i/87;x=RADIUS[0]*.96*math.cos(a);y=RADIUS[1]*.96*math.sin(a)
        dist,w,_,_=closest(x,y)
        if dist<w+1:continue
        instance(flower_templates[['white','pink','yellow'][i%3]],f'rim_bloom_{i}',x,y,RNG.uniform(.65,1.05),a)
        if i%3==0:instance(vine_template,f'rim_vine_{i}',x*1.025,y*1.025,RNG.uniform(.85,1.35),a+math.pi/2,z=ground(x,y)-4)
    lamp_positions=[]
    for i,(x,y) in enumerate([(-12,3),(-3,0),(7,-8),(-7,-12),(21,-9),(19,3),(3,6)]):
        o=instance(lamp_template,f'path_lamp_{i}',x,y,.95,0);lamp_positions.append([x,ground(x,y)+2,-y])
    # Light grass detail across the common avoids a blank uniform green slab.
    grass=Mesh('common_grass')
    for i in range(4800):
        x=RNG.uniform(-28,28);y=RNG.uniform(-21,21)
        if (x/29)**2+(y/22)**2>1:continue
        dist,w,_,_=closest(x,y)
        if dist<w+1 or (-18<x<-6 and 4<y<16) or (12<x<24 and 3<y<15) or (-23<x<-7 and -12<y<-6):continue
        z=ground(x,y);h=RNG.uniform(.04,.13);grass.poly([(x-.025,y,z),(x+.025,y,z),(x+.03,y,z+h)],[(0,1,2)],RNG.choice(['grass_light','grass_dark','leaf_light']))
    emit(grass)

    bpy.context.view_layer.update()
    for o in sc.objects:
        if o.name.startswith('rim_vine_'):
            o.location.z+=ground(o.location.x,o.location.y)-.12-bounds(o)[1][2]
        if o.type=='MESH' and (o.get('layout_asset') or o.get('expansion_asset')) and not o.data.uv_layers:
            uv=o.data.uv_layers.new(name='SurfaceUV')
            for loop in o.data.loops:
                p=o.data.vertices[loop.vertex_index].co;uv.data[loop.index].uv=(p.x*.18,p.y*.18)
    bpy.context.view_layer.update()
    meta=json.loads(json.dumps(old));pose,angle=bridge_pose()
    meta.update(version=3,layoutRevision=3,source='island_dusk_living.blend',terrainScale=[1,1],terrain=dict(radius=list(RADIUS),walkRadius=[27.1,20.6],river=RIVER),waterfallLip=lip)
    meta['house']=bounds(house);meta['cafe']=bounds(cafe);meta['bridge']=dict(position=pose,halfLength=3.4*1.35,halfWidth=1.08,walkHalfLength=3.8*1.35,walkHalfWidth=.92,angle=angle,deckBase=pose[2]+.47)
    meta['spawn']=[-1,-4,ground(-1,-4)];meta['smokeOrigin']=list(Vector(old['smokeOrigin'])+house_delta);meta['boatPivot']=list(boat.location)
    meta['trees']=tree_metadata;meta['fences']=[bounds(o) for o in fence_objects]
    # Four sheep-fence runs; the east gate stays open.
    for a,b in [((-25.4,-2),(-17.8,-2)),((-25.4,4.3),(-17.8,4.3)),((-25.4,-2),(-25.4,4.3)),((-17.8,-2),(-17.8,.3)),((-17.8,2.2),(-17.8,4.3))]:
        meta['fences'].append([[min(a[0],b[0])-.08,min(a[1],b[1])-.08,10],[max(a[0],b[0])+.08,max(a[1],b[1])+.08,12]])
    meta['obstacles']=[bounds(o) for o in sc.objects if o.get('expansion_asset') and any(k in o.name for k in ['bench','flowers','herbs','flower_box'])]+post_boxes
    meta['obstacles'].append(bounds(bpy.data.objects['garden_potting_table']))
    for i,p in enumerate(meta['plots']):
        p['position']=list(Vector(p['position'])+farm_deltas[i]);p['approach']=[farm_targets[i][0]+.65,-12.1];p['halfSize']=[2.22,2.52]
    meta['cafeApproach']=[18,-2.9];meta['shelters']=shelters;meta['lampPositions']=lamp_positions
    meta['lifeSites']=[
        dict(id='home',label='小院廊下',position=[-10.9,-2.75],lookAt=[-10.9,-.5],shelter=True,duration=45),
        dict(id='garden',label='菜园',position=[-14.45,12.1],lookAt=[-15.1,9],action='Water',duration=24),
        dict(id='flowers',label='广场花草',position=[-6.3,3.8],lookAt=[-6.6,1.5],action='Water',duration=24),
        dict(id='orchard',label='果树林',position=[23.3,.6],lookAt=[22.5,-1],action='Harvest',duration=26),
        dict(id='cafe',label='咖啡馆檐下',position=meta['cafeApproach'],lookAt=[18,-8],shelter=True,duration=30),
        dict(id='overlook',label='溪边长椅',position=[3.6,9.2],lookAt=[8,7],duration=35),
        dict(id='yard',label='花园工作台',position=[-16.45,-3],lookAt=[-18,-3],action='Plant',duration=22)]
    meta['districts']=[dict(id=i,label=l,position=p) for i,l,p in [('home','左上住宅',[-12,-10]),('garden','左下菜园',[-15.1,9]),('sheep','左侧羊圈',[-21.5,-1]),('common','中央休闲区',[-2,3.8]),('bridge','右下石桥',[pose[0],-pose[1]]),('cafe','右上咖啡馆',[18,-9])]]
    meta['commonBounds']=[[-7,-7],[5,3]]
    sc.camera.location=(16,-94,69);look_at(sc.camera,(0,0,8.5));sc.camera.data.ortho_scale=66
    sc['art_revision']='reference_layout_v5'
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'island_layout.blend'),compress=True)
    preserved=[];static=[]
    for o in list(sc.objects):
        if o.type!='MESH':continue
        if o.name=='chimney_smoke_refined':bpy.data.objects.remove(o,do_unlink=True);continue
        if o.parent==player or o.name.startswith('crop_') or o.name in ['boat_hull','stream_surface','waterfall_ribbons','garden_cat'] or o.get('asset_id')=='sheep':preserved.append(o)
        else:static.append(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in static:o.select_set(True)
    bpy.context.view_layer.objects.active=static[0];bpy.ops.object.join();scenery=bpy.context.object;scenery.name='island_scenery'
    tris=sum(len(p.vertices)-2 for p in scenery.data.polygons)
    if tris>490000:
        mod=scenery.modifiers.new('Layout scene budget','DECIMATE');mod.ratio=490000/tris;mod.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    scenery.data.validate();scenery.data.update()
    for mat in bpy.data.materials:
        if mat.use_nodes:
            p=mat.node_tree.nodes.get('Principled BSDF')
            if p:
                for link in list(p.inputs['Normal'].links):mat.node_tree.links.remove(link)
    for o in preserved+[scenery,player]:o.select_set(True)
    glb=OUT/'island_layout.glb'
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_animations=False,export_yup=True,export_cameras=False,export_lights=False,export_extras=True)
    subprocess.run(['node','-e',"console.log(require('./scripts/optimize_glb.cjs').optimize('assets/layout/island_layout.glb'))"],cwd=ROOT,check=True)
    meta['webTriangles']=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in preserved+[scenery]);meta['independentNodes']=[o.name for o in preserved]+['player']
    (OUT/'scene.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
    print('LAYOUT_REPORT',json.dumps(dict(triangles=meta['webTriangles'],bytes=glb.stat().st_size,bridge=pose,angle=angle)))

if __name__=='__main__':main()
