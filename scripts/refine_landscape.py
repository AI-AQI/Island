"""Refine the accepted layout locally; preserve the layout version as a source."""
import json,math,random,subprocess,sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from geometry import Mesh,MATS,material
from refined_assets import petal
from prepare_living import bounds
from layout_spec import ground as old_ground,closest,RADIUS,RIVER
from landscape_spec import ground,outline,edge_y,WATER_HEIGHTS,terrain_metadata

OUT=ROOT/'assets/landscape';RNG=random.Random(180926);OBSTACLES=[]
def emit(m):
    o=m.object();o['landscape_asset']=True;return o
def polar(a,r=1):return RADIUS[0]*r*outline(a)*math.cos(a),RADIUS[1]*r*outline(a)*math.sin(a)

def terrain():
    m=Mesh('island_land');n=192;nr=64;m.v=[(0,0,ground(0,0))]
    for j in range(1,nr+1):
        for i in range(n):
            x,y=polar(i*math.tau/n,j/nr);m.v.append((x,y,ground(x,y)))
    for i in range(n):m.face((0,1+i,1+(i+1)%n),'grass',True)
    for j in range(nr-1):
        for i in range(n):
            a=1+j*n+i;b=1+j*n+(i+1)%n;x,y,z=m.v[a];d,w,_,_=closest(x,y)
            mat='bank_sand' if d<w+.22 else 'grass'
            m.face((a,a+n,b+n,b),mat,True)
    prev=[1+(nr-1)*n+i for i in range(n)]
    for row,(r,z) in enumerate([(1,8.8),(.97,6),(.83,2.8),(.64,-.9),(.37,-4.5),(.04,-7.2)]):
        ids=[]
        for i in range(n):
            a=i*math.tau/n;rr=r*(1+.045*math.sin(a*5+row*.5));x,y=polar(a,rr)
            zz=z+.8*math.sin(a*3+.7)+.5*math.sin(a*8+row*.4)
            ids.append(len(m.v));m.v.append((x,y,zz))
        for i in range(n):m.face((prev[i],ids[i],ids[(i+1)%n],prev[(i+1)%n]),['rock','rock_warm','rock_dark'][(i//8+row//2)%3])
        prev=ids
    m.face(tuple(reversed(prev)),'rock_dark');emit(m)
    cliff=Mesh('weathered_cliff_buttresses');moss=Mesh('cliff_moss_shelves')
    for i in range(43):
        a=math.tau*(i+RNG.uniform(-.2,.2))/43;x,y=polar(a,RNG.uniform(.98,1.02));d,w,_,_=closest(x,y)
        if d<w+.25:continue
        h=RNG.uniform(1.6,3.5);top=ground(x,y)-RNG.uniform(.15,.65);rx=RNG.uniform(1.35,2.45);ry=RNG.uniform(1.0,1.8)
        cliff.sphere((x,y,top-h),(rx,ry,h),RNG.choice(['rock','rock_warm','rock_light']),8,6,False,.17,i)
        if i%3:
            moss.sphere((x-.2*math.cos(a),y-.2*math.sin(a),top-.13),(rx*.85,ry*.78,.25),'moss',9,4,True,.10,i)
        # Offset, unequal lower fragments avoid a repeated ring of identical rocks.
        for k in range(1+(i%3==0)):
            xx=x*.83+.3*math.cos(a+1);yy=y*.83+.3*math.sin(a+1)
            cliff.sphere((xx,yy,top-h*1.4-2-k*2),(rx*RNG.uniform(.75,1.15),ry*.9,h*RNG.uniform(.75,1.15)),RNG.choice(['rock_dark','rock_warm','rock']),7,5,False,.20,i*4+k)
    emit(cliff);emit(moss)

def river():
    m=Mesh('stream_surface');cols=16
    def section(i,u):
        x,y,w=RIVER[i];a=RIVER[max(0,i-1)];b=RIVER[min(len(RIVER)-1,i+1)];dx,dy=b[0]-a[0],b[1]-a[1];l=math.hypot(dx,dy)
        return x-dy/l*w*u,y+dx/l*w*u
    for i,(x,y,w) in enumerate(RIVER):
        for j in range(cols+1):
            u=j/cols*2-1;px,py=section(i,u)
            if i<8:
                t=i/8;py=py*t+(edge_y(px,True)-.06)*(1-t)
            if i>len(RIVER)-25:
                t=(i-(len(RIVER)-25))/24;ax,ay=section(len(RIVER)-25,u);ex,_=section(len(RIVER)-1,u)
                px=ax+(ex-ax)*t;py=ay+(edge_y(ex)+.03-ay)*t
            m.v.append((px,py,WATER_HEIGHTS[i]))
    for i in range(len(RIVER)-1):
        for j in range(cols):
            a=i*(cols+1)+j;m.face((a,a+cols+1,a+cols+2,a+1),'water',True)
    emit(m);lip=m.v[-cols-1:];fall=Mesh('waterfall_ribbons')
    # A connected translucent sheet under separate foam strands.
    strips=80;steps=36
    for k in range(strips+1):
        f=k/strips*cols;i=min(cols-1,int(f));q=f-i;a=lip[i];b=lip[i+1];x=a[0]+(b[0]-a[0])*q;y=a[1]+(b[1]-a[1])*q
        for j in range(steps+1):
            t=j/steps;xx=x+.075*math.sin(t*13+k*.16)*t
            fall.v.append((xx,y-1.35*(1-math.exp(-t*6))-.5*t,10.055-15.8*t+.08*math.sin(k*.35)*t))
    for k in range(strips):
        for j in range(steps):
            a=k*(steps+1)+j;fall.face((a,a+1,a+steps+2,a+steps+1),'waterfall',True)
    for k in range(69):
        f=k/68*cols;i=min(cols-1,int(f));q=f-i;a=lip[i];b=lip[i+1];x=a[0]+(b[0]-a[0])*q;y=a[1]+(b[1]-a[1])*q
        start=len(fall.v);width=RNG.uniform(.008,.022);length=RNG.uniform(11.8,16.1)
        for j in range(37):
            t=j/36;xx=x+.07*math.sin(t*13+k*.17)*t;yy=y-1.35*(1-math.exp(-t*6))-.5*t-.018
            fall.v.extend([(xx-width,yy,10.065-length*t),(xx+width,yy,10.065-length*t)])
        for j in range(36):
            a=start+j*2;fall.face((a,a+2,a+3,a+1),'fall_foam',True)
    fall_obj=emit(fall)
    # Exported vertex alpha also gives the offline preview a soft misty end.
    colors=fall_obj.data.color_attributes.new(name='FallFade',type='FLOAT_COLOR',domain='CORNER')
    for polygon in fall_obj.data.polygons:
        mat=fall_obj.data.materials[polygon.material_index];rgb=mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value[:3]
        for index in polygon.loop_indices:
            loop=fall_obj.data.loops[index];z=fall_obj.data.vertices[loop.vertex_index].co.z;t=max(0,min(1,(z+5.8)/5.8));fade=t*t*(3-2*t)
            colors.data[index].color=(*rgb,fade)
    for name in ['waterfall','fall_foam']:
        mat=MATS[name];nodes=mat.node_tree.nodes;vc=nodes.new('ShaderNodeVertexColor');vc.layer_name='FallFade'
        mat.node_tree.links.new(vc.outputs['Color'],nodes.get('Principled BSDF').inputs['Base Color'])
        alpha=nodes.new('ShaderNodeMath');alpha.operation='MULTIPLY';alpha.inputs[1].default_value=.72 if name=='waterfall' else .92
        mat.node_tree.links.new(vc.outputs['Alpha'],alpha.inputs[0]);mat.node_tree.links.new(alpha.outputs[0],nodes.get('Principled BSDF').inputs['Alpha'])
    froth=Mesh('waterfall_lip_foam')
    for k in range(70):
        f=RNG.random()*cols;i=min(cols-1,int(f));q=f-i;a=lip[i];b=lip[i+1]
        froth.sphere((a[0]+(b[0]-a[0])*q,a[1]+(b[1]-a[1])*q+RNG.uniform(0,.25),10.08),(.11,.19,.027),'foam',6,3)
    emit(froth)
    return [list(p) for p in lip]

def banks():
    rocks=Mesh('river_rocks_and_shallows');moss=Mesh('bank_moss');reeds=Mesh('riverbank_reeds');foam=Mesh('river_eddies')
    for side in [-1,1]:
        for i in range(3,len(RIVER)-8,4):
            if 137<i<165:continue # Leave both bridge approaches free.
            x,y,w=RIVER[i];a=RIVER[i-1];b=RIVER[i+1];dx,dy=b[0]-a[0],b[1]-a[1];l=math.hypot(dx,dy);nx,ny=-dy/l,dx/l
            offset=w+RNG.uniform(.1,.8);px=x+nx*side*offset;py=y+ny*side*offset
            if math.hypot(px/RADIUS[0],py/RADIUS[1])>.97:continue
            size=RNG.uniform(.28,.72)*(1.8 if y>11 else 1)
            z=ground(px,py);rocks.sphere((px,py,z-.20),(size*1.25,size*.85,size*.64),RNG.choice(['rock','rock_light','rock_warm']),9,5,False,.16,i+side*4)
            if size>.65:OBSTACLES.append(dict(position=[px,py],radius=size*.7))
            if i%3:moss.sphere((px,py,z+size*.36),(size*.76,size*.61,.10),'moss',8,4,True,.10,i)
            if i%4==3:
                for j in range(8):
                    xx=px+nx*side*.45+RNG.uniform(-.28,.28);yy=py+ny*side*.45+RNG.uniform(-.28,.28);zz=ground(xx,yy);h=RNG.uniform(.28,.68)
                    reeds.beam((xx,yy,zz),(xx+.09,yy,zz+h),.012,'leaf_dark',n=4)
                    petal(reeds,(xx+.08,yy,zz+h*.6),h*.75,.055,RNG.random()*6.28,.9,'leaf_light')
            # Sparse shoal stones and foam arcs inside the water, away from paths.
            if i%3==0 and y<13:
                xx=x+nx*side*w*.65;yy=y+ny*side*w*.65;z=WATER_HEIGHTS[i]
                rocks.sphere((xx,yy,z-.12),(.28,.23,.19),'river_stone',8,5,True,.12,i)
                pts=[(xx+.42*math.cos(t),yy+.28*math.sin(t),z+.022) for t in [j*.18 for j in range(13)]]
                foam.tube(pts,.012,'foam',4)
    for m in [rocks,moss,reeds,foam]:emit(m)
    # Outcrops frame the spring and hide its abrupt back-edge origin.
    spring=Mesh('spring_outcrops');green=Mesh('spring_moss')
    for i,(x,y,rx,ry,rz) in enumerate([(-6.6,18.7,1.7,1.6,1.6),(-.9,20,1.8,1.4,1.35),(-.9,16.6,1.2,1.0,.85),(5.4,17.5,2.2,1.5,1.45),(8.7,16.1,1.7,1.0,1.0),(-8.0,16.4,1.5,1.1,.9)]):
        z=ground(x,y);spring.sphere((x,y,z-.30),(rx,ry,rz),'rock_warm',9,5,False,.12,i)
        green.sphere((x,y,z+rz*.62),(rx*.76,ry*.74,.22),'moss',9,4,True,.14,i)
        OBSTACLES.append(dict(position=[x,y],radius=min(rx,ry)*.75))
    emit(spring);emit(green)

def vines():
    m=Mesh('trailing_cliff_gardens')
    for k in range(49):
        a=math.pi+(k+.25)*math.pi/49;x,y=polar(a,1.023);d,w,_,_=closest(x,y)
        if d<w+.65:continue
        z=ground(x,y)-.1;length=RNG.uniform(3.3,8.7)
        for branch in range(2+(k%3==0)):
            pts=[]
            for j in range(26):
                t=j/25;out=.38*math.sin(t*math.pi)+.20*t;sway=.23*math.sin(t*9+branch)+branch*.20
                p=(x+math.cos(a)*out-math.sin(a)*sway,y+math.sin(a)*out+math.cos(a)*sway,z-length*t)
                pts.append(p)
                if j>1:
                    for side in [-1,1]:
                        petal(m,(p[0]-math.sin(a)*side*.13,p[1]+math.cos(a)*side*.13,p[2]),RNG.uniform(.3,.48),.19,a+side*.8,-.85,RNG.choice(['leaf','leaf_light','leaf_dark']))
            m.tube(pts,.018,'wood',5)
    emit(m)

def rim_gardens(sc):
    rocks=Mesh('broken_shore_rocks');moss=Mesh('shore_groundcover')
    flowers=[next(o for o in sc.objects if o.get('asset_id')=='bush_flower_'+c) for c in ['white','pink','yellow']]
    for k in range(65):
        a=math.pi+(k+.35)*math.pi/65;x,y=polar(a,RNG.uniform(.97,1.01));d,w,_,_=closest(x,y)
        if d<w+.45:continue
        z=ground(x,y);r=RNG.uniform(.45,1.15)
        if k%3:rocks.sphere((x,y,z-.26),(r*1.2,r*.85,r*.55),RNG.choice(['rock','rock_light','rock_warm']),9,5,False,.15,k)
        moss.sphere((x-.3*math.cos(a),y-.3*math.sin(a),z-.05),(r*1.3,r,.16),'moss',8,4,True,.14,k)
        for j in range(1+k%3):
            xx=x-RNG.uniform(.1,.9)*math.cos(a)+RNG.uniform(-.35,.35);yy=y-RNG.uniform(.1,.9)*math.sin(a)+RNG.uniform(-.35,.35)
            o=flowers[(k+j)%3].copy();o.data=flowers[(k+j)%3].data;sc.collection.objects.link(o);o.name=f'shore_bloom_{k}_{j}'
            o.location=(xx,yy,ground(xx,yy));size=RNG.uniform(.6,1.05);o.scale=(size,)*3;o.rotation_euler.z=RNG.random()*6.28
    emit(rocks);emit(moss)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/layout/island_layout.blend'))
    bpy.context.preferences.filepaths.save_version=0;sc=bpy.context.scene
    for mat in bpy.data.materials:MATS[mat.name]=mat
    material('bank_sand','AF9C77',.93);material('river_stone','8E9C94',.64);material('fall_foam','E5F7ED',.35,alpha=.92)
    meta=json.loads((ROOT/'assets/layout/scene.json').read_text());meta['source']='assets/layout/island_layout.blend'
    remove=('island_land','island_cliff_strata','stream_surface','waterfall_ribbons','waterfall_lip_foam','river_bank_rock_','rim_boulder_','rim_bloom_','rim_vine_')
    for o in list(sc.objects):
        if o.name.startswith(remove):bpy.data.objects.remove(o,do_unlink=True);continue
        if o.type not in ['MESH','EMPTY'] or o.parent:continue
        x,y=o.location[:2]
        if abs(x)+abs(y)>.001:o.location.z+=ground(x,y)-old_ground(x,y)
        elif o.type=='MESH':
            o.data=o.data.copy()
            for v in o.data.vertices:
                x,y=v.co[:2];v.co.z+=ground(x,y)-old_ground(x,y)
    terrain();lip=river();banks();vines();rim_gardens(sc)
    template=bpy.data.objects['landmark_tree_0']
    added=[(-23,12,.62),(-18,17.2,.75),(-12.8,18.3,.68),(-8.6,19.1,.57),(1.8,19.1,.75),(7,19,.66),(12.6,17.3,.76),(16.7,16,.64),(-24,-7,.48),(-20.5,-14.6,.48),(-12.2,-18.1,.43),(-2.6,-15.5,.52),(21,-10.7,.50),(1.7,5.0,.57)]
    for i,(x,y,size) in enumerate(added):
        o=template.copy();o.data=template.data;sc.collection.objects.link(o);o.name=f'grove_tree_{i:02}';o.location=(x,y,ground(x,y));o.scale=(size,size*RNG.uniform(.9,1.08),size*RNG.uniform(.96,1.1));o.rotation_euler.z=RNG.random()*6.28
    # Recover the exact pink tree mesh used in the original version.
    with bpy.data.libraries.load(str(ROOT/'assets/source/tree_blossom.blend'),link=False) as (data_from,data_to):
        data_to.objects=[n for n in data_from.objects if n=='tree_blossom']
    blossom=next(o for o in data_to.objects if o is not None);sc.collection.objects.link(blossom)
    blossom.name='tree_blossom_hero';blossom.location=(-2.8,8.0,ground(-2.8,8.0));blossom.scale=(1.12,1.12,1.12);blossom.rotation_euler.z=.4;blossom['asset_id']='tree_blossom'
    petals=Mesh('blossom_petals_on_grass')
    for i in range(150):
        a=RNG.random()*math.tau;r=RNG.uniform(.4,3);x=-2.8+r*math.cos(a);y=8+r*.8*math.sin(a)
        petal(petals,(x,y,ground(x,y)+.025),.10,.065,a,.03,'flower_pink' if i%3 else 'flower_white')
    emit(petals)
    bpy.context.view_layer.update()
    # Rebuild height-sensitive metadata from the final scene; horizontal save
    # coordinates remain valid, and placePlayer rescues newly blocked positions.
    meta['terrain']=terrain_metadata();meta['waterfallLip']=lip;meta['landscapeRevision']=1
    meta['terrainObstacles']=OBSTACLES
    meta['trees']=[dict(position=list(o.location),radius=.5*o.scale.x+.25,name=o.name) for o in sc.objects if o.name.startswith(('landmark_tree_','orchard_tree_','grove_tree_','tree_blossom_'))]
    for key,name in [('house','house_main_001'),('cafe','cafe_pavilion_001')]:meta[key]=bounds(bpy.data.objects[name])
    meta['fences']=[bounds(bpy.data.objects[o]) for o in [o.name for o in sc.objects if o.get('asset_id')=='farm_fence']]+meta['fences'][-5:]
    for p in meta['plots']:
        x,y=p['position'][:2];p['position'][2]+=ground(x,y)-old_ground(x,y)
    for roof in meta['shelters']:
        x,z=roof['position'];roof['roofHeight']+=ground(x,-z)-old_ground(x,-z)
    for p in meta['lampPositions']:p[1]+=ground(p[0],-p[2])-old_ground(p[0],-p[2])
    meta['spawn'][2]=ground(*meta['spawn'][:2])
    bx,by=meta['bridge']['position'][:2];bridge_delta=ground(bx,by)-old_ground(bx,by)
    meta['bridge']['position'][2]+=bridge_delta;meta['bridge']['deckBase']+=bridge_delta
    meta['boatPivot']=list(bpy.data.objects['boat_hull'].location)
    meta['smokeOrigin'][2]+=ground(-12,10)-old_ground(-12,10)
    meta['blossomTree']=dict(name=blossom.name,position=list(blossom.location),source='assets/source/tree_blossom.blend')
    meta['heightSamples']=[dict(position=[x,-y],height=ground(x,y)) for x,y in [(-12,10),(-2.8,8),(-4,20),(4,16),(18,9),(-1,-4),(8,-4),(15,-14),(-20,-9),(23,0)]]
    for o in sc.objects:
        if o.type=='MESH' and o.get('landscape_asset') and not o.data.uv_layers:
            uv=o.data.uv_layers.new(name='SurfaceUV')
            for loop in o.data.loops:
                p=o.data.vertices[loop.vertex_index].co;uv.data[loop.index].uv=(p.x*.18,p.y*.18)
    sc['art_revision']='landscape_groves_v1'
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'island_landscape.blend'),compress=True)
    player=bpy.data.objects['player'];preserved=[];static=[]
    for o in list(sc.objects):
        if o.type!='MESH':continue
        if o.name=='chimney_smoke_refined':bpy.data.objects.remove(o,do_unlink=True);continue
        if o.parent==player or o.name.startswith('crop_') or o.name in ['boat_hull','stream_surface','waterfall_ribbons','garden_cat','tree_blossom_hero'] or o.get('asset_id')=='sheep':preserved.append(o)
        else:static.append(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in static:o.select_set(True)
    bpy.context.view_layer.objects.active=static[0];bpy.ops.object.join();scenery=bpy.context.object;scenery.name='island_scenery'
    tris=sum(len(p.vertices)-2 for p in scenery.data.polygons)
    if tris>550000:
        mod=scenery.modifiers.new('Landscape scene budget','DECIMATE');mod.ratio=550000/tris;mod.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    scenery.data.validate();scenery.data.update()
    for mat in bpy.data.materials:
        if mat.use_nodes:
            p=mat.node_tree.nodes.get('Principled BSDF')
            if p:
                for link in list(p.inputs['Normal'].links):mat.node_tree.links.remove(link)
    for o in preserved+[scenery,player]:o.select_set(True)
    glb=OUT/'island_landscape.glb'
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_animations=False,export_yup=True,export_cameras=False,export_lights=False,export_extras=True)
    subprocess.run(['node','-e',"console.log(require('./scripts/optimize_glb.cjs').optimize('assets/landscape/island_landscape.glb'))"],cwd=ROOT,check=True)
    meta['webTriangles']=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in preserved+[scenery]);meta['independentNodes']=[o.name for o in preserved]+['player']
    (OUT/'scene.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
    print('LANDSCAPE_REPORT',json.dumps(dict(triangles=meta['webTriangles'],bytes=glb.stat().st_size,trees=len(meta['trees']),blossom=meta['blossomTree'])))

if __name__=='__main__':main()
