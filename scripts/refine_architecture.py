"""Locally crafted architectural revision; the accepted landscape is immutable."""
import json,math,struct,subprocess,sys,zlib
from pathlib import Path
import bpy,bmesh
import numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from geometry import MATS,material
from refine import noise_field,planar_uv,rounded_edges,triangles
from prepare_living import bounds
import crafted_architecture as craft
OUT=ROOT/'assets/architecture'

def png(name,rgb):
    a=np.uint8(np.clip(rgb,0,1)*255+.5);h,w,c=a.shape
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    data=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(b'\x00'+row.tobytes() for row in a),9))+chunk(b'IEND',b'')
    path=OUT/'textures'/f'{name}.png';path.write_bytes(data)
    image=bpy.data.images.load(str(path),check_existing=False);image.pack();return image

def materials():
    for mat in bpy.data.materials:
        key=mat.name.split('.')[0]
        if key not in MATS:MATS[key]=mat
    palette={
      'wood':('A07751','wood'),'wood_light':('C39A6B','wood'),'wood_dark':('705038','wood'),
      'wall':('F2DEC0','plaster'),'wall_shade':('D9C3A5','plaster'),
      'roof':('628B82','slate'),'roof_light':('779B8B','slate'),'roof_dark':('547A74','slate'),
      'cafe_roof':('927656','wood'),'cafe_roof_light':('A08762','wood'),'cafe_roof_dark':('846B51','wood'),
      'rock':('B2A392','stone'),'rock_light':('CCBDA7','stone'),'rock_dark':('978D82','stone'),
      'cream':('F7E8CD','canvas'),'pink':('DCA3A0','canvas'),'curtain_linen':('F9EAD1','canvas')}
    size=512;yy,xx=np.mgrid[:size,:size]/size;maps={}
    for index,family in enumerate(['wood','plaster','slate','stone','canvas']):
        f=noise_field(size,913+index);micro=noise_field(size,121+index)
        if family=='wood':
            grain=np.sin(math.tau*(xx*42+.8*np.sin(yy*math.tau)+f*2.2));height=f*.45+grain*.08
            tone=.91+.15*f+.025*grain;strength=.23
        elif family=='canvas':
            weave=np.sin(xx*math.tau*128)*np.sin(yy*math.tau*128)
            height=.04*weave+.08*f;tone=.96+.06*f+.015*weave;strength=.12
        else:
            height=f*.65+micro*.18;tone=.89+.19*f;strength=.5 if family=='stone' else .27
        dx=(np.roll(height,-1,1)-np.roll(height,1,1))*strength*size*.035
        dy=(np.roll(height,-1,0)-np.roll(height,1,0))*strength*size*.035
        normal=np.stack([-dx,-dy,np.ones_like(dx)],2);normal/=np.linalg.norm(normal,axis=2,keepdims=True)
        ni=png(f'{family}_normal',normal*.5+.5);ni.colorspace_settings.name='Non-Color'
        rough=np.clip(.77+f*.12,0,1);ri=png(f'{family}_roughness',np.repeat(rough[:,:,None],3,2));ri.colorspace_settings.name='Non-Color'
        maps[family]=(tone,ni,ri)
    for key,(color,family) in palette.items():
        # Prefixes retain the world's existing rain response.
        name=('roof_cafe_'+key.removeprefix('cafe_roof') if key.startswith('cafe_roof') else key)+'_crafted'
        mat=material(name,color,.83);mat['architecture_material']=True;MATS[key]=mat
        tone,normal,rough=maps[family];rgb=np.array([int(color[i:i+2],16)/255 for i in [0,2,4]])
        albedo=png(key+'_color',rgb[None,None,:]*tone[:,:,None])
        nodes=mat.node_tree.nodes;links=mat.node_tree.links;p=nodes.get('Principled BSDF')
        for image,socket in [(albedo,'Base Color'),(rough,'Roughness')]:
            tex=nodes.new('ShaderNodeTexImage');tex.image=image;tex.extension='REPEAT';links.new(tex.outputs['Color'],p.inputs[socket])
        tex=nodes.new('ShaderNodeTexImage');tex.image=normal;tex.extension='REPEAT'
        norm=nodes.new('ShaderNodeNormalMap');norm.inputs['Strength'].default_value=.4
        links.new(tex.outputs['Color'],norm.inputs['Color']);links.new(norm.outputs['Normal'],p.inputs['Normal'])
    MATS['glow']=material('glow_crafted','FFD898',.36,emission=.8)

def replace(name,builder):
    old=bpy.data.objects[name];original_bounds=bounds(old)
    target_lo=[min(p[k] for p in old.bound_box) for k in range(3)]
    target_hi=[max(p[k] for p in old.bound_box) for k in range(3)]
    mesh,garden=builder();lo=[min(v[k] for v in mesh.v) for k in range(3)];hi=[max(v[k] for v in mesh.v) for k in range(3)]
    def remap(v):
        xy=[target_lo[k]+(v[k]-lo[k])/(hi[k]-lo[k])*(target_hi[k]-target_lo[k]) for k in range(2)]
        z=v[2]-lo[2]
        # Keep the door and downstairs windows upright, shorten only the upper roof.
        if name.startswith('house'):
            knee=3.9;z=z if z<=knee else knee+(z-knee)*(target_hi[2]-knee)/(hi[2]-lo[2]-knee)
        return (*xy,z+target_lo[2])
    objects=[]
    for part in [mesh,garden]:
        part.v=[remap(v) for v in part.v];obj=part.object();obj.matrix_world=old.matrix_world.copy()
        obj['architecture_asset']=True;obj['art_revision']='crafted_architecture_v1'
        if part==mesh:
            for key,value in old.items():obj[key]=value
            obj['art_revision']='crafted_architecture_v1';rounded_edges(obj,.017)
        planar_uv(obj);objects.append(obj)
    bpy.data.objects.remove(old,do_unlink=True);objects[0].name=name
    bpy.context.view_layer.update()
    return objects,dict(before=original_bounds,after=bounds(objects[0]),triangles=sum(triangles(o) for o in objects))

def main():
    (OUT/'textures').mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/landscape/island_landscape.blend'))
    bpy.context.preferences.filepaths.save_version=0;sc=bpy.context.scene;materials()
    for o in list(sc.objects):
        if o.get('asset_id')=='ivy_wall' or o.name in ['flowering_window_climber','cafe_glazed_back']:bpy.data.objects.remove(o,do_unlink=True)
    home,home_report=replace('house_main_001',craft.house)
    cafe,cafe_report=replace('cafe_pavilion_001',craft.cafe)
    crafted=home+cafe
    meta=json.loads((ROOT/'assets/landscape/scene.json').read_text());meta['source']='assets/landscape/island_landscape.blend'
    meta['architectureRevision']=1;meta['house']=bounds(home[0]);meta['cafe']=bounds(cafe[0])
    meta['architecture']=dict(house=home_report,cafe=cafe_report,source='scripts/crafted_architecture.py',materials='Local procedural albedo, roughness and tangent-space normal maps; 512px')
    sc['art_revision']='crafted_architecture_v1'
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'island_architecture.blend'),compress=True)
    player=bpy.data.objects['player'];preserved=[];static=[]
    for o in list(sc.objects):
        if o.type!='MESH':continue
        if o.name=='chimney_smoke_refined':bpy.data.objects.remove(o,do_unlink=True);continue
        if o in crafted or o.parent==player or o.name.startswith('crop_') or o.name in ['boat_hull','stream_surface','waterfall_ribbons','garden_cat','tree_blossom_hero'] or o.get('asset_id')=='sheep':preserved.append(o)
        else:static.append(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in static:o.select_set(True)
    bpy.context.view_layer.objects.active=static[0];bpy.ops.object.join();scenery=bpy.context.object;scenery.name='island_scenery'
    count=triangles(scenery)
    if count>470000:
        mod=scenery.modifiers.new('Scenery budget','DECIMATE');mod.ratio=470000/count;mod.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    scenery.data.validate();scenery.data.update()
    for obj in preserved:
        bpy.context.view_layer.objects.active=obj
        if obj in crafted:
            budget=90000 if obj==home[0] else 72000 if obj==cafe[0] else 16000
            if triangles(obj)>budget:
                mod=obj.modifiers.new('Architecture web budget','DECIMATE');mod.ratio=budget/triangles(obj);mod.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=mod.name)
        # Tangent-space normal maps require triangles, including capped beams.
        mod=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
        if obj in crafted:
            bm=bmesh.new();bm.from_mesh(obj.data)
            bmesh.ops.dissolve_degenerate(bm,dist=1e-7,edges=list(bm.edges));bm.to_mesh(obj.data);bm.free();obj.data.update()
            # Decimation can collapse UV triangles while retaining geometry.
            # Reproject only these procedural architectural materials afterward.
            for layer in list(obj.data.uv_layers):obj.data.uv_layers.remove(layer)
            planar_uv(obj)
    for mat in bpy.data.materials:
        if mat.use_nodes and not mat.get('architecture_material'):
            p=mat.node_tree.nodes.get('Principled BSDF')
            if p:
                for link in list(p.inputs['Normal'].links):mat.node_tree.links.remove(link)
    for o in preserved+[scenery,player]:o.select_set(True)
    glb=OUT/'island_architecture.glb'
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_animations=False,export_yup=True,export_cameras=False,export_lights=False,export_extras=True,export_tangents=True)
    subprocess.run(['node','-e',"console.log(require('./scripts/optimize_glb.cjs').optimize('assets/architecture/island_architecture.glb',{preserveNormalMaps:true}))"],cwd=ROOT,check=True)
    meta['webTriangles']=sum(triangles(o) for o in preserved+[scenery]);meta['independentNodes']=[o.name for o in preserved]+['player']
    (OUT/'scene.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
    print('ARCHITECTURE_REPORT',json.dumps(dict(triangles=meta['webTriangles'],bytes=glb.stat().st_size,house=home_report,cafe=cafe_report)))

if __name__=='__main__':main()
