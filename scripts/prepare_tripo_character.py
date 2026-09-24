"""Turn the reviewed Tripo source into an editable, animated island character.

Tripo authors the shape, 4K PBR textures and initial skin. This script performs
local normalization, simplification, naming, clothing weight repairs and clips.
The original service artifacts are never overwritten.
"""
import argparse
import json
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix,Vector

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from geometry import look_at
from review_tripo_character import stage
from build_character import animate,repair_degenerate_tangents

OUT=ROOT/'assets/character_tripo/runtime'
RENDERS=ROOT/'renders/character_tripo'

def normalize(mesh,rig):
    bounds=[mesh.matrix_world@Vector(c) for c in mesh.bound_box]
    lo=Vector([min(p[i] for p in bounds) for i in range(3)]);hi=Vector([max(p[i] for p in bounds) for i in range(3)])
    s=1.86/(hi.z-lo.z);center=(lo+hi)*.5
    transform=Matrix.Translation((0,0,0))@Matrix.Rotation(-math.pi/2,4,'Z')@Matrix.Scale(s,4)@Matrix.Translation((-center.x,-center.y,-lo.z))
    worlds={o:o.matrix_world.copy() for o in [mesh,rig]}
    # Bake matching transforms into rest vertices and rest bones, preserving the skin.
    for o in [mesh,rig]:o.parent=None;o.matrix_world=Matrix.Identity(4)
    mesh.data.transform(transform@worlds[mesh]);rig.data.transform(transform@worlds[rig])
    for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update()
    return {'original_bounds':[list(lo),list(hi)],'scale':s}

def rename_bones(rig):
    mapping={
      'tripo::Root':'root','tripo::Spine_0':'pelvis','tripo::Spine_1':'spine','tripo::Spine_2':'chest','tripo::Head_0':'neck','tripo::Head_1':'head',
      'bone_6':'clavicle.L','bone_7':'upper_arm.L','tripo::0_Right_Limb_0':'forearm.L','tripo::0_Right_Limb_1':'hand.L',
      'bone_13':'clavicle.R','tripo::0_Left_Limb_0':'upper_arm.R','tripo::0_Left_Limb_1':'forearm.R','tripo::0_Left_Limb_2':'hand.R',
    }
    for source,side in [('Right','L'),('Left','R')]:
        for i,name in enumerate(['thigh','shin','foot','toe']):mapping[f'tripo::1_{source}_Limb_{i}']=f'{name}.{side}'
    for b in list(rig.data.bones):
        if b.name in mapping:b.name=mapping[b.name]
    # Keep API auxiliary hand bones intact; the service did not return named fingers.
    bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    eb=rig.data.edit_bones
    for side in ['L','R']:
        thigh,shin,foot=[eb[f'{name}.{side}'] for name in ['thigh','shin','foot']]
        thigh.parent=eb['pelvis'];thigh.use_connect=False;shin.use_connect=False;foot.use_connect=False
        # The long dress confused the automatic hip/knee estimate. Place joints
        # inside the actual legs before authoring clips, leaving rest geometry intact.
        thigh.head.z=.85;thigh.tail.z=.39;shin.head=thigh.tail.copy()
        shin.tail.z=.145;foot.head=shin.tail.copy()
    new_bones={
      'hat':((0,0,1.70),(0,0,1.83),'head'),
      'hair_back':((0,.09,1.49),(0,.11,1.14),'head'),
      'hair_left':((.17,.06,1.48),(.19,.065,1.14),'head'),
      'hair_right':((-.17,.06,1.48),(-.19,.065,1.14),'head'),
      'bag':((-.23,-.035,1.065),(-.23,-.035,.89),'pelvis'),
    }
    for name,(x,y) in {'front':(0,-.08),'back':(0,.08),'left':(.11,0),'right':(-.11,0)}.items():new_bones['skirt_'+name]=((x,y,1.14),(x*2,y*2,.50),'pelvis')
    for name,(h,t,parent) in new_bones.items():
        b=eb.new(name);b.head=h;b.tail=t;b.parent=eb[parent]
    bpy.ops.object.mode_set(mode='OBJECT');rig.name='Daisy_Tripo_Rig';rig.show_in_front=True
    return mapping

def vertex_colors(mesh):
    # Texture-guided brown hair selection avoids accidentally weighting cream
    # shoulder fabric to the head where the hair and sleeve share the same height.
    image=next(im for im in bpy.data.images if im.name.startswith('Color_'))
    pixels=np.empty(len(image.pixels),dtype=np.float32);image.pixels.foreach_get(pixels);pixels=pixels.reshape(image.size[1],image.size[0],4)
    colors=np.zeros((len(mesh.data.vertices),3),dtype=np.float32);uv=mesh.data.uv_layers.active.data
    for loop in mesh.data.loops:
        u,v=uv[loop.index].uv;x=min(image.size[0]-1,int((u%1)*image.size[0]));y=min(image.size[1]-1,int((v%1)*image.size[1]));colors[loop.vertex_index]=pixels[y,x,:3]
    return colors

def repair_weights(mesh,rig):
    groups={b.name:mesh.vertex_groups.get(b.name) or mesh.vertex_groups.new(name=b.name) for b in rig.data.bones}
    colors=vertex_colors(mesh);fixed={'hair':0,'skirt':0,'bag':0,'head':0,'legs':0}
    # Below the hem, identify the two leg surfaces by connectivity. Join only
    # coincident UV seam vertices virtually; retain all authored mesh/UV data.
    parent={v.index:v.index for v in mesh.data.vertices if v.co.z<.555}
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for edge in mesh.data.edges:
        a,b=edge.vertices
        if a in parent and b in parent:parent[root(a)]=root(b)
    seams={}
    for i in parent:
        key=tuple(round(x,4) for x in mesh.data.vertices[i].co)
        if key in seams:parent[root(i)]=root(seams[key])
        else:seams[key]=i
    leg_roots={root(i) for i in parent if mesh.data.vertices[i].co.z<.1}
    lower_legs={i for i in parent if root(i) in leg_roots}
    def smooth(a,b,t):
        t=max(0,min(1,(t-a)/(b-a)));return t*t*(3-2*t)
    for v in mesh.data.vertices:
        x,y,z=v.co;r,g,b=colors[v.index];brown=(r>g*1.16 and g>b*1.17 and r<.80)
        weights=None;kind=None
        if z<.65:
            side='L' if x>0 else 'R';knee=smooth(.305,.475,z);ankle=smooth(.13,.24,z)
            weights={f'thigh.{side}':knee,f'shin.{side}':(1-knee)*ankle,f'foot.{side}':(1-knee)*(1-ankle)};kind='legs'
        if z>1.45:
            weights={'head':1};kind='head'
        elif brown and y>.008 and z>1.12 and abs(x)<.265:
            amount=min(.38,max(0,(1.46-z)*1.2));name='hair_left' if x>.10 else 'hair_right' if x<-.10 else 'hair_back'
            weights={'head':1-amount,name:amount};kind='hair'
        elif .79<z<1.10 and x<-.16 and brown:
            weights={'bag':1};kind='bag'
        elif .46<z<1.14 and v.index not in lower_legs:
            leg_weights=weights
            amount=min(.44,max(0,(1.12-z)*.7));wx=abs(x)/.27;wy=abs(y)/.19;total=max(.0001,wx+wy)
            weights={'pelvis':1-amount,('skirt_left' if x>0 else 'skirt_right'):amount*wx/total,('skirt_front' if y<0 else 'skirt_back'):amount*wy/total};kind='skirt'
            if .555<=z<.65:
                skin=smooth(1.10,1.18,r/max(g,.001))*(1-smooth(.60,.65,z)) if .035<abs(x)<.17 and abs(y)<.085 else 0
                influence=1-skin
                weights={n:w*influence for n,w in weights.items()}
                for name,w in leg_weights.items():weights[name]=weights.get(name,0)+w*(1-influence)
        if weights:
            for index in [g.group for g in v.groups]:mesh.vertex_groups[index].remove([v.index])
            for name,w in weights.items():
                if w>0:groups[name].add([v.index],w,'REPLACE')
            fixed[kind]+=1
    # Match native deformation to WebGL's four-influence skinning budget.
    for v in mesh.data.vertices:
        weights=sorted([(g.group,g.weight) for g in v.groups if g.weight>1e-5],key=lambda x:x[1],reverse=True)[:4]
        total=sum(w for _,w in weights)
        if not total:weights=[(groups['pelvis'].index,1)];total=1
        for index in [g.group for g in v.groups]:mesh.vertex_groups[index].remove([v.index])
        for index,w in weights:mesh.vertex_groups[index].add([v.index],w/total,'REPLACE')
    assert all(len(v.groups)<=4 and abs(sum(g.weight for g in v.groups)-1)<1e-5 for v in mesh.data.vertices)
    return fixed

def add_can(rig):
    with bpy.data.libraries.load(str(ROOT/'assets/character/daisy_character.blend'),link=False) as (src,dst):dst.objects=['Watering_Can']
    can=dst.objects[0];bpy.context.scene.collection.objects.link(can);can.name='Watering_Can';can.parent=None;can.matrix_world=Matrix.Identity(4)
    wrist=rig.data.bones['hand.L'].head_local
    offset=wrist+Vector((.065,0,0))-Vector((.663,0,1.26))
    for v in can.data.vertices:v.co+=offset
    can.modifiers.clear();can.vertex_groups.clear();group=can.vertex_groups.new(name='hand.L');group.add(list(range(len(can.data.vertices))),1,'REPLACE')
    mod=can.modifiers.new('Hand attachment','ARMATURE');mod.object=rig;can.hide_render=True
    return can

def main(args):
    OUT.mkdir(parents=True,exist_ok=True);RENDERS.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/args.input));bpy.context.view_layer.update()
    mesh=max((o for o in bpy.context.scene.objects if o.type=='MESH'),key=lambda o:len(o.data.polygons));rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    normalized=normalize(mesh,rig);mesh.name='Daisy_Detailed';rig.animation_data_clear()
    bpy.context.view_layer.objects.active=mesh;bpy.ops.object.select_all(action='DESELECT');mesh.select_set(True)
    source_triangles=sum(len(p.vertices)-2 for p in mesh.data.polygons)
    mod=mesh.modifiers.new('Web geometry budget','DECIMATE');mod.ratio=args.triangles/source_triangles
    while mesh.modifiers.find(mod.name)>0:bpy.ops.object.modifier_move_up(modifier=mod.name)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    mapping=rename_bones(rig);fixes=repair_weights(mesh,rig);can=add_can(rig)
    # The service's shape gizmo is not a renderable part of the character.
    for o in list(bpy.context.scene.objects):
        if o not in [mesh,rig,can]:bpy.data.objects.remove(o,do_unlink=True)
    for o in [mesh,can]:
        for mod in o.modifiers:
            if mod.type=='ARMATURE':mod.use_deform_preserve_volume=False
    for action in list(bpy.data.actions):bpy.data.actions.remove(action)
    for o in [mesh,can]:o.parent=rig
    clips=animate(rig,ground_mesh=mesh,ground_height=0)
    for im in bpy.data.images:
        if im.type=='IMAGE' and im.has_data:im.pack()
    cam=stage(args.width);sc=bpy.context.scene;sc.render.fps=24;sc.frame_end=73
    cam.location=(.65,-6,1.5);look_at(cam,(0,0,.94));cam.data.ortho_scale=2.13
    sc.render.resolution_y=round(args.width*1.2)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'daisy_tripo.blend'),compress=True)
    if not args.no_render:
        sc.render.filepath=str(RENDERS/'hero.png');bpy.ops.render.render(write_still=True)
        for name,pos,target,span in [('face',(.1,-5,1.61),(0,0,1.54),.60),('back',(0,6,1.5),(0,0,.94),2.13)]:
            cam.location=pos;look_at(cam,target);cam.data.ortho_scale=span;sc.render.filepath=str(RENDERS/(name+'.png'));bpy.ops.render.render(write_still=True)
        cam.location=(.65,-6,1.5);look_at(cam,(0,0,.94));cam.data.ortho_scale=2.13
        for name,frame in [('Walk',9),('Plant',27),('Water',37),('Harvest',29)]:
            can.hide_render=name!='Water';rig.animation_data.action=clips[name];sc.frame_set(frame);sc.render.filepath=str(RENDERS/(name.lower()+'.png'));bpy.ops.render.render(write_still=True)
    rig.animation_data.action=clips['Idle'];sc.frame_set(1);can.hide_render=True
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
    for o in [mesh,can]:
        bpy.context.view_layer.objects.active=o;o.select_set(True)
        tri=o.modifiers.new('Portable triangles','TRIANGULATE')
        while o.modifiers.find(tri.name)>0:bpy.ops.object.modifier_move_up(modifier=tri.name)
        bpy.ops.object.modifier_apply(modifier=tri.name)
    bpy.ops.export_scene.gltf(filepath=str(OUT/'daisy_tripo.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_frame_range=False,export_force_sampling=True,export_tangents=True,export_armature_object_remove=True,export_yup=True,export_extras=True,export_cameras=False,export_lights=False)
    tangents=repair_degenerate_tangents(OUT/'daisy_tripo.glb')
    report={'source_task':'a7bd67e9-c3c8-4ab2-a4cb-701c54a7c994','rig_task':'3dbebed3-0676-4779-9df7-e5fc50a89a0a','credits_consumed':85,'source_triangles':source_triangles,'web_triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in [mesh,can]),'bones':len(rig.data.bones),'clips':list(clips),'normalization':normalized,'weight_repairs':fixes,'degenerate_tangent_repairs':tangents,'bone_map':mapping,'bone_positions':{b.name:{'head':list(b.head_local),'tail':list(b.tail_local)} for b in rig.data.bones}}
    (ROOT/'reports/tripo_character_model.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ['bone_map','bone_positions']},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',default='assets/character_tripo/tripo-out/daisy-rigged-3dbebed3/model.glb');p.add_argument('--triangles',type=int,default=150000);p.add_argument('--width',type=int,default=960);p.add_argument('--no-render',action='store_true')
    main(p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []))
