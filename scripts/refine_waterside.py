"""Reference-led river, bridge and waterfall pass, built only with local Blender."""
import json,math,random,subprocess,sys
from pathlib import Path
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from geometry import Mesh,MATS,material,rgba,look_at
from refine import planar_uv,rounded_edges,triangles
from refined_assets import petal
from layout_spec import RIVER,closest
from landscape_spec import ground,edge_y,WATER_HEIGHTS

OUT=ROOT/'assets/waterside';RNG=random.Random(92026);COLS=32

def emit(m,keep=False):
    obj=m.object();obj['waterside_asset']=True
    if keep:obj['keep_water_detail']=True
    return obj

def color_layer(obj,colors,name='WaterColor'):
    layer=obj.data.color_attributes.new(name=name,type='FLOAT_COLOR',domain='CORNER')
    for loop in obj.data.loops:layer.data[loop.index].color=colors[loop.vertex_index]

def colored_material(name,color,rough=.28,alpha=1):
    mat=material(name,color,rough,alpha=alpha);nodes=mat.node_tree.nodes;p=nodes.get('Principled BSDF');links=mat.node_tree.links
    vc=nodes.new('ShaderNodeVertexColor');vc.layer_name='WaterColor';links.new(vc.outputs['Color'],p.inputs['Base Color'])
    if alpha<1:links.new(vc.outputs['Alpha'],p.inputs['Alpha'])
    return mat

def setup_materials():
    for mat in bpy.data.materials:MATS[mat.name]=mat
    for key,source in [('bridge_stone','rock_light_crafted'),('bridge_stone_shade','rock_crafted'),('bridge_wood','wood_crafted'),('bridge_wood_light','wood_light_crafted'),('bridge_wood_dark','wood_dark_crafted')]:MATS[key]=bpy.data.materials[source]
    material('rock_river_sand','AFA994',.76);material('rock_river_cool','879B96',.68);material('rock_river_warm','ADA08C',.8);material('rock_river_wet','687F7B',.42)
    material('moss_river','81925B',.94);material('moss_river_light','A2AA70',.96)
    colored_material('water_stream_crafted','FFFFFF',.23)
    colored_material('waterfall_crafted','FFFFFF',.22,.96)
    colored_material('waterfall_foam_crafted','FFFFFF',.38,.96)
    colored_material('river_foam_crafted','FFFFFF',.48,.92)
    colored_material('shore_transition','FFFFFF',.90)
    # Real geometry and vertex colors export; fine offline ripples use bump only.
    mat=MATS['water_stream_crafted'];nodes=mat.node_tree.nodes;links=mat.node_tree.links;p=nodes.get('Principled BSDF')
    noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=4.5;noise.inputs['Detail'].default_value=2.1;noise.inputs['Roughness'].default_value=.65
    bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.23;bump.inputs['Distance'].default_value=.09
    links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],p.inputs['Normal'])

def section(i,u):
    x,y,w=RIVER[i];a=RIVER[max(0,i-1)];b=RIVER[min(len(RIVER)-1,i+1)];dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
    return x-dy/length*w*u,y+dx/length*w*u

def surface_point(t,u):
    f=max(0,min(1,t))*(len(RIVER)-1);i=min(len(RIVER)-2,int(f));q=f-i
    def pos(i):
        px,py=section(i,u)
        if i<8:
            mix=i/8;py=py*mix+(edge_y(px,True)-.06)*(1-mix)
        if i>len(RIVER)-25:
            mix=(i-(len(RIVER)-25))/24;ax,ay=section(len(RIVER)-25,u);ex,_=section(len(RIVER)-1,u)
            px=ax+(ex-ax)*mix;py=ay+(edge_y(ex)+.03-ay)*mix
        return px,py,WATER_HEIGHTS[i]
    a,b=pos(i),pos(i+1);return tuple(a[k]+q*(b[k]-a[k]) for k in range(3))

def river():
    m=Mesh('stream_surface');colors=[];deep=rgba('438F9C');shallow=rgba('9CC9BB')
    for i in range(len(RIVER)):
        t=i/(len(RIVER)-1)
        for j in range(COLS+1):
            u=j/COLS*2-1;x,y,z=surface_point(t,u);m.v.append((x,y,z))
            edge=abs(u)**3;variation=.035*math.sin(t*61+u*7)+.018*math.cos(t*117-u*11)
            q=max(0,min(1,.13+edge*.76+variation));colors.append(tuple(deep[k]*(1-q)+shallow[k]*q for k in range(3))+(1,))
    for i in range(len(RIVER)-1):
        for j in range(COLS):
            a=i*(COLS+1)+j;m.face((a,a+COLS+1,a+COLS+2,a+1),'water_stream_crafted',True)
    obj=emit(m,True);color_layer(obj,colors)
    uv=obj.data.uv_layers.new(name='RiverFlow')
    for loop in obj.data.loops:
        i,j=divmod(loop.vertex_index,COLS+1);uv.data[loop.index].uv=(j/COLS,i/(len(RIVER)-1))
    return [list(p) for p in m.v[-COLS-1:]]

def shoreline():
    # Locally refine the actual ground, then overlay the gradual shore colors.
    # Keep the underlying surface closed, including the curved waterfall mouth.
    land=bpy.data.objects['island_land'];bm=bmesh.new();bm.from_mesh(land.data);edges=set()
    for face in bm.faces:
        if any(v.co.z<9 for v in face.verts):continue
        c=face.calc_center_median();d,w,_,_=closest(c.x,c.y)
        if d<w+1.6:edges.update(face.edges)
    bmesh.ops.subdivide_edges(bm,edges=list(edges),cuts=2,use_grid_fill=True)
    for v in bm.verts:
        if v.co.z<9:continue
        d,w,_,_=closest(v.co.x,v.co.y)
        if d<w+2.2:v.co.z=ground(v.co.x,v.co.y)
    bm.to_mesh(land.data);bm.free();land.data.update()
    for i,mat in enumerate(land.data.materials):
        if mat.name=='bank_sand':land.data.materials[i]=MATS['grass']
    m=Mesh('river_shore_transition');colors=[];wet,sand,green=rgba('8BADA1'),rgba('B5B494'),rgba('819B58');steps=12
    for side in [-1,1]:
        start=len(m.v)
        for i in range(len(RIVER)):
            t=i/(len(RIVER)-1);w=RIVER[i][2]
            for j in range(steps+1):
                q=j/steps;offset=-.06+q*1.4;p=surface_point(t,side*(1+offset/w));x,y,z=p
                z=max(z-.035,ground(x,y))+.012
                m.v.append((x,y,z))
                blend=min(1,max(0,(q-.14)/.66));blend=blend*blend*(3-2*blend)
                edge=tuple(wet[k]*(1-min(1,q*4))+sand[k]*min(1,q*4) for k in range(3))
                colors.append(tuple(edge[k]*(1-blend)+green[k]*blend for k in range(3))+(1,))
        for i in range(len(RIVER)-1):
            for j in range(steps):
                a=start+i*(steps+1)+j;face=(a,a+steps+1,a+steps+2,a+1)
                m.face(face if side>0 else tuple(reversed(face)),'shore_transition',True)
    obj=emit(m,True);color_layer(obj,colors)

def ribbon(m,colors,points,width,color='E2F1E5',opacity=.85):
    rgb=rgba(color);start=len(m.v)
    for j,p in enumerate(points):
        a=Vector(points[max(0,j-1)]);b=Vector(points[min(len(points)-1,j+1)]);d=b-a;n=Vector((-d.y,d.x,0)).normalized()
        q=j/(len(points)-1);w=width*math.sin(math.pi*q)**.65
        m.v.extend([tuple(Vector(p)-n*w),tuple(Vector(p)+n*w)]);fade=opacity*math.sin(math.pi*q)**.55
        colors.extend([(*rgb[:3],fade)]*2)
    for j in range(len(points)-1):
        a=start+j*2;m.face((a,a+2,a+3,a+1),'river_foam_crafted',True)

def surface_foam(eddies):
    m=Mesh('river_foam');colors=[]
    # Sparse, long strokes follow the bend; avoid an evenly scattered dot pattern.
    for k in range(94):
        t=RNG.uniform(.08,.99);u=RNG.uniform(-.85,.85);length=RNG.uniform(.007,.022)
        pts=[]
        for j in range(12):
            q=j/11;p=surface_point(t+(q-.5)*length,u+.035*math.sin(q*math.pi+k));pts.append((p[0],p[1],p[2]+.025))
        ribbon(m,colors,pts,RNG.uniform(.008,.027),opacity=RNG.uniform(.38,.68))
    for rock in eddies:
        x,y,z,rx,ry,tx,ty=rock
        for side in [-1,1]:
            pts=[]
            for j in range(15):
                q=j/14;along=-ry*.7+q*ry*3.5;across=side*rx*(.92+.4*math.sin(math.pi*q))
                pts.append((x+tx*along-ty*across,y+ty*along+tx*across,z+.028))
            ribbon(m,colors,pts,.016,opacity=.8)
    # Aerated streaks at the two upper cascades.
    for center in [.031,.114,.254]:
        for k in range(10):
            u=(k+.5)/10*1.86-.93;pts=[];start=center+RNG.uniform(-.008,.008);length=RNG.uniform(.012,.031)
            for j in range(12):
                p=surface_point(start+j/11*length,u+.02*math.sin(j*.8+k));pts.append((p[0],p[1],p[2]+.035))
            ribbon(m,colors,pts,RNG.uniform(.009,.024),opacity=.66)
    obj=emit(m,True);color_layer(obj,colors)

def bridge(meta):
    old=bpy.data.objects.get('stone_bridge_001')
    if old:bpy.data.objects.remove(old,do_unlink=True)
    spec=meta['bridge'];half=spec['halfLength'];base=spec['deckBase'];m=Mesh('stone_bridge_001')
    co,si=math.cos(spec['angle']),math.sin(spec['angle']);bx,by=spec['position'][:2]
    def height(x,y=0):return max(base+.95*math.cos(math.pi*min(half,abs(x))/(half*2)),ground(bx+co*x-si*y,by+si*x+co*y))
    # Separate, slightly irregular wearing stones follow the actual walk surface.
    for i in range(26):
        x0=-half+2*half*i/26+.013;x1=-half+2*half*(i+1)/26-.013
        for j in range(4):
            y0=-1.28+j*.64+.012;y1=y0+.614;z0=height(x0)-.018;z1=height(x1)-.018
            vv=[(x0,y0,height(x0,y0)-.018),(x1,y0,height(x1,y0)-.018),(x1,y1,height(x1,y1)-.018),(x0,y1,height(x0,y1)-.018)]
            vv += [(x,y,z-.22) for x,y,z in vv]
            m.poly(vv,[(0,1,2,3),(0,4,5,1),(3,2,6,7),(0,3,7,4),(1,5,6,2),(7,6,5,4)],'bridge_stone' if RNG.random()>.25 else 'bridge_stone_shade')
    # Voussoirs are individually shaped wedges with a visible arch underneath.
    for side in [-1,1]:
        for i in range(21):
            x0=-half+i*2*half/21+.009;x1=-half+(i+1)*2*half/21-.009
            z0,z1=height(x0)-.16,height(x1)-.16;thick=.40+.30*(abs((x0+x1)/(2*half))**3)
            vv=[(x0,side*1.29,z0),(x1,side*1.29,z1),(x1,side*1.29,z1-thick),(x0,side*1.29,z0-thick)]
            vv += [(x,y-side*.28,z) for x,y,z in vv]
            m.poly(vv,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],'bridge_stone' if i%4 else 'bridge_stone_shade')
        for i in range(7):
            x=-half+.12+i*(2*half-.24)/6;z=height(x)
            m.box((x,side*1.40,z+.48),(.18,.18,.98),'bridge_wood')
            m.sphere((x,side*1.40,z+1.0),(.145,.145,.125),'bridge_wood_light',12,6)
            for dz in [.29,.76]:m.sphere((x,side*1.505,z+dz),(.026,.016,.026),'metal',8,4)
        for dz,r in [(.27,.045),(.72,.075)]:
            pts=[(-half+.10+j*(2*half-.20)/64,side*1.4,height(-half+.10+j*(2*half-.20)/64)+dz) for j in range(65)]
            m.tube(pts,r,'bridge_wood_light',8)
    # Solid abutments only at the bank ends, leaving the waterway open.
    for side in [-1,1]:
        for row in range(2):
            for j in range(5):m.box((side*(half-.24),-.99+j*.49,height(half)-.39-row*.25),(.72,.46,.24),'bridge_stone_shade' if j%3 else 'bridge_stone')
    obj=emit(m,True);rounded_edges(obj,.025);planar_uv(obj)
    obj.location=(spec['position'][0],spec['position'][1],0);obj.rotation_euler.z=spec['angle'];obj['asset_id']='stone_bridge'
    return obj

def banks(meta):
    stones=Mesh('river_boulders');wet=Mesh('river_wet_stones');moss=Mesh('river_moss_gardens');grass=Mesh('river_edge_plants');eddies=[];obstacles=[]
    b=meta['bridge'];bx,by=b['position'][:2];co,si=math.cos(b['angle']),math.sin(b['angle'])
    def blocked_bridge(x,y,r):
        u=(x-bx)*co+(y-by)*si;v=-(x-bx)*si+(y-by)*co
        return abs(u)<b['walkHalfLength']+r+.35 and abs(v)<1.15+r
    for side in [-1,1]:
        for i in range(9,len(RIVER)-9,5):
            x,y,w=RIVER[i];a,bp=RIVER[i-1],RIVER[i+1];dx,dy=bp[0]-a[0],bp[1]-a[1];length=math.hypot(dx,dy);nx,ny=-dy/length,dx/length
            # Stagger clusters, avoiding a continuous ornamental wall.
            if RNG.random()<.2:continue
            rad=RNG.uniform(.28,.65);px=x+nx*side*(w-.02);py=y+ny*side*(w-.02)
            if blocked_bridge(px,py,rad):continue
            z=WATER_HEIGHTS[i];rz=rad*RNG.uniform(.7,1.1)
            stones.sphere((px,py,z+.08),(rad*1.25,rad*.86,rz),RNG.choice(['rock_river_sand','rock_river_cool','rock_river_warm']),12,8,False,.075,i+side)
            wet.sphere((px,py,z-.08),(rad*1.29,rad*.9,rz*.49),'rock_river_wet',12,6,True,.04,i)
            if i%3:
                moss.sphere((px-.06,py+.025,z+rz*.85),(.72*rad,.62*rad,.08),'moss_river',10,5,True,.06,i)
            if rad>.45:obstacles.append(dict(position=[px,py],radius=rad*.95))
            for j in range(3):
                xx=px+nx*side*.20+RNG.uniform(-.35,.35);yy=py+ny*side*.20+RNG.uniform(-.35,.35);zz=max(z+.01,ground(xx,yy))
                rr=RNG.uniform(.07,.16);wet.sphere((xx,yy,zz),(rr*1.4,rr,rr*.5),'rock_river_sand',8,4,True,.07,i+j)
            if i%4==1:
                xx=px+nx*side*rad*.3;yy=py+ny*side*rad*.3;zz=max(ground(xx,yy),z+.2)
                for j in range(7):petal(grass,(xx+RNG.uniform(-.16,.16),yy+RNG.uniform(-.16,.16),zz+.06),RNG.uniform(.25,.44),.055,RNG.random()*math.tau,1.1,'leaf_light' if j%3 else 'leaf_dark')
            if i%3==0:eddies.append([px,py,z,rad*1.18,rad,dx/length,dy/length])
    # In-stream stones establish depth and create local, directional wakes.
    for i,u,rad in [(47,-.28,.40),(75,.47,.34),(98,-.42,.36),(121,.36,.39),(161,-.60,.50),(174,.61,.48)]:
        x,y,z=surface_point(i/(len(RIVER)-1),u)
        if blocked_bridge(x,y,rad):continue
        stones.sphere((x,y,z-.14),(rad,rad*.73,rad*.65),'rock_river_cool',12,7,True,.08,i)
        a,bp=RIVER[i-1],RIVER[i+1];length=math.dist(a[:2],bp[:2]);eddies.append([x,y,z,rad,rad*.73,(bp[0]-a[0])/length,(bp[1]-a[1])/length])
    # Larger shoulders conceal the raw cut where river becomes waterfall.
    for u in [-1.10,1.10]:
        x,y,z=surface_point(.987,u)
        for j in range(3):
            xx=x+(j-1)*.45;yy=y+.22+j*.28;zz=max(z-.15,ground(xx,yy)-.32);r=.72-j*.10
            stones.sphere((xx,yy,zz),(r,r*.8,r*.82),'rock_river_warm',12,8,False,.09,81+j)
            moss.sphere((xx-.12,yy+.08,zz+r*.72),(.52,.45,.12),'moss_river_light',10,5,True,.05,j)
            obstacles.append(dict(position=[xx,yy],radius=r*.65))
    for m in [stones,wet,moss,grass]:emit(m)
    meta['terrainObstacles']+=obstacles
    return eddies,obstacles

def waterfall(lip):
    sheet=Mesh('waterfall_ribbons');colors=[];steps=52;strips=104
    def at(u):
        f=u*(len(lip)-1);i=min(len(lip)-2,int(f));q=f-i;a,b=lip[i],lip[i+1];return tuple(a[k]+(b[k]-a[k])*q for k in range(3))
    teal,white=rgba('83BEC7'),rgba('E3F4F0')
    for k in range(strips+1):
        u=k/strips;x,y,z=at(u);length=15.7+.8*math.sin(u*13)+.55*math.sin(u*29)
        for j in range(steps+1):
            t=j/steps;xx=x+.12*math.sin(t*15+u*17)*t+(u-.5)*.42*t*t;yy=y-1.38*(1-math.exp(-t*9))-.32*t+.045*math.sin(u*39+t*10)*t
            sheet.v.append((xx,yy,z-length*t))
            stream=(.5+.5*math.sin(u*89+math.sin(t*18)*2.4))**2
            broken=(.5+.5*math.sin(u*137+t*53))*(.5+.5*math.cos(u*47-t*69));mix=.15+stream*.43+broken*.39
            fade=min(1,max(0,(1-t)/.27));fade=fade*fade*(3-2*fade)
            colors.append(tuple(teal[c]*(1-mix)+white[c]*mix for c in range(3))+(fade,))
    for k in range(strips):
        for j in range(steps):
            a=k*(steps+1)+j;sheet.face((a,a+1,a+steps+2,a+steps+1),'waterfall_crafted',True)
    # Varying, wandering ribbons replace straight wire-like lines.
    for k in range(53):
        u=(k+.4+RNG.uniform(-.25,.25))/53;x,y,z=at(u);length=RNG.uniform(13.9,17);width=RNG.uniform(.014,.045);start=len(sheet.v)
        for j in range(steps+1):
            t=j/steps;xx=x+.11*math.sin(t*14+k)*t;yy=y-1.38*(1-math.exp(-t*9))-.32*t-.035
            w=width*(.7+.3*math.sin(t*16+k));sheet.v.extend([(xx-w,yy,z-length*t+.015),(xx+w,yy,z-length*t+.015)])
            fade=min(1,max(0,(1-t)/.30));fade=fade*fade*(3-2*fade);colors.extend([(*white[:3],fade)]*2)
        for j in range(steps):
            a=start+j*2;sheet.face((a,a+2,a+3,a+1),'waterfall_foam_crafted',True)
    # Short irregular aerated ribbons break up the otherwise continuous strands.
    for k in range(165):
        u=RNG.uniform(.015,.985);x,y,z=at(u);a=RNG.uniform(.005,.92);length=RNG.uniform(.025,.11);start=len(sheet.v)
        for j in range(9):
            q=j/8;t=a+q*length;xx=x+.11*math.sin(t*14+k)*t;yy=y-1.38*(1-math.exp(-t*9))-.32*t-.06
            w=RNG.uniform(.025,.05)*math.sin(q*math.pi);sheet.v.extend([(xx-w,yy,z-15.7*t),(xx+w,yy,z-15.7*t)])
            fade=math.sin(q*math.pi)*min(1,max(0,(1-t)/.23));colors.extend([(*white[:3],fade)]*2)
        for j in range(8):
            a0=start+j*2;sheet.face((a0,a0+2,a0+3,a0+1),'waterfall_foam_crafted',True)
    obj=emit(sheet,True);color_layer(obj,colors)
    # Thin irregular crest streaks rather than a row of identical white beads.
    crest=Mesh('waterfall_lip_foam');cc=[]
    for k in range(42):
        u=(k+.4)/42*1.92-.96;pts=[]
        for j in range(10):
            p=surface_point(.974+j/9*.026,u+.008*math.sin(j));pts.append((p[0],p[1],p[2]+.032))
        ribbon(crest,cc,pts,RNG.uniform(.017,.048),opacity=.93)
    obj=emit(crest,True);color_layer(obj,cc)

def preview_mist(lip):
    # Offline equivalent of the runtime's soft moving mist particles.
    size=64;image=bpy.data.images.new('waterside_soft_mist',width=size,height=size,alpha=True)
    pixels=[]
    for y in range(size):
        for x in range(size):
            r=math.hypot((x+.5)/size*2-1,(y+.5)/size*2-1);a=max(0,1-r*r)**3*.20;pixels.extend([.86,.94,.95,a])
    image.pixels.foreach_set(pixels);image.pack()
    mat=material('waterfall_preview_mist','E5F3F3',1,alpha=.2);nodes=mat.node_tree.nodes;p=nodes.get('Principled BSDF');tex=nodes.new('ShaderNodeTexImage');tex.image=image;mat.node_tree.links.new(tex.outputs['Alpha'],p.inputs['Alpha'])
    for i in range(15):
        u=(i+.5)/15;f=u*(len(lip)-1);k=min(len(lip)-2,int(f));a,b=lip[k],lip[k+1];q=f-k
        x=a[0]+q*(b[0]-a[0]);y=a[1]+q*(b[1]-a[1])-1.9;z=-2.8-RNG.random()*2.5;s=RNG.uniform(1,1.7)
        m=Mesh('waterfall_mist_preview');m.poly([(-s,-s,0),(s,-s,0),(s,s,0),(-s,s,0)],[(0,1,2,3)],'waterfall_preview_mist')
        obj=emit(m);obj.location=(x,y,z);obj.rotation_euler=(Vector((16,-94,69))-obj.location).to_track_quat('Z','Y').to_euler();uv=obj.data.uv_layers.new(name='MistUV')
        for loop,coord in zip(obj.data.loops,[(0,0),(1,0),(1,1),(0,1)]):uv.data[loop.index].uv=coord

def export(sc,meta):
    player=bpy.data.objects['player'];preserved=[];static=[]
    for o in list(sc.objects):
        if o.type!='MESH':continue
        if o.name=='chimney_smoke_refined' or o.name.startswith('waterfall_mist_preview'):bpy.data.objects.remove(o,do_unlink=True);continue
        if o.get('architecture_asset') or o.get('keep_water_detail') or o.parent==player or o.name.startswith('crop_') or o.name in ['boat_hull','garden_cat','tree_blossom_hero'] or o.get('asset_id')=='sheep':preserved.append(o)
        else:static.append(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in static:o.select_set(True)
    bpy.context.view_layer.objects.active=static[0];bpy.ops.object.join();scenery=bpy.context.object;scenery.name='island_scenery'
    count=triangles(scenery)
    if count>450000:
        mod=scenery.modifiers.new('Scenery budget','DECIMATE');mod.ratio=450000/count;mod.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    scenery.data.validate();scenery.data.update()
    for obj in preserved:
        bpy.context.view_layer.objects.active=obj
        crafted=obj.get('architecture_asset') or obj.get('asset_id')=='stone_bridge'
        if crafted:
            budget=90000 if obj.name=='house_main_001' else 72000 if obj.name=='cafe_pavilion_001' else 18000
            if triangles(obj)>budget:
                mod=obj.modifiers.new('Detail web budget','DECIMATE');mod.ratio=budget/triangles(obj);mod.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=mod.name)
        mod=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
        if crafted:
            bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.dissolve_degenerate(bm,dist=1e-7,edges=list(bm.edges));bm.to_mesh(obj.data);bm.free();obj.data.update()
            for layer in list(obj.data.uv_layers):obj.data.uv_layers.remove(layer)
            planar_uv(obj)
    for mat in bpy.data.materials:
        if mat.use_nodes and not mat.get('architecture_material'):
            p=mat.node_tree.nodes.get('Principled BSDF')
            if p:
                for link in list(p.inputs['Normal'].links):mat.node_tree.links.remove(link)
    for o in preserved+[scenery,player]:o.select_set(True)
    glb=OUT/'island_waterside.glb'
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_animations=False,export_yup=True,export_cameras=False,export_lights=False,export_extras=True,export_tangents=True)
    subprocess.run(['node','-e',"console.log(require('./scripts/optimize_glb.cjs').optimize('assets/waterside/island_waterside.glb',{preserveNormalMaps:true}))"],cwd=ROOT,check=True)
    meta['webTriangles']=sum(triangles(o) for o in preserved+[scenery]);meta['independentNodes']=[o.name for o in preserved]+['player']
    (OUT/'scene.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
    print('WATERSIDE_REPORT',json.dumps(dict(triangles=meta['webTriangles'],bytes=glb.stat().st_size,independentNodes=len(meta['independentNodes']),water=meta['waterDetails'])))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/architecture/island_architecture.blend'));bpy.context.preferences.filepaths.save_version=0;sc=bpy.context.scene
    setup_materials();meta=json.loads((ROOT/'assets/architecture/scene.json').read_text());meta['source']='assets/architecture/island_architecture.blend';meta['waterRevision']=1
    for name in ['stream_surface','waterfall_ribbons','waterfall_lip_foam','river_rocks_and_shallows','bank_moss','river_eddies']:
        obj=bpy.data.objects.get(name)
        if obj:bpy.data.objects.remove(obj,do_unlink=True)
    bridge(meta);lip=river();shoreline();eddies,obstacles=banks(meta);surface_foam(eddies);waterfall(lip);preview_mist(lip)
    meta['waterfallLip']=lip;meta['waterDetails']=dict(eddies=eddies,newBankObstacles=obstacles,bridgeNode='stone_bridge_001',surfaceNode='stream_surface',foamNode='river_foam',fallNode='waterfall_ribbons')
    for o in sc.objects:
        if o.type=='MESH' and o.get('waterside_asset') and not o.data.uv_layers:planar_uv(o)
    sc['art_revision']='waterside_v1';bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'island_waterside.blend'),compress=True)
    export(sc,meta)

if __name__=='__main__':main()
