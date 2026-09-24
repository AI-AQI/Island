"""Inspect the original Tripo mesh in Blender without changing its source file."""
import argparse
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from geometry import rgba,look_at

def stage(width):
    sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=40;sc.cycles.use_denoising=True
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='METAL';prefs.get_devices()
        for device in prefs.devices:device.use=device.type=='METAL'
        sc.cycles.device='GPU'
    except Exception:sc.cycles.device='CPU'
    sc.world=bpy.data.worlds.new('Warm studio');sc.world.use_nodes=True
    bg=sc.world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=rgba('E3DED3');bg.inputs['Strength'].default_value=.4
    sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast'
    for name,pos,power,size,color in [('Key',(-3,-4,5),380,4,'FFF3E4'),('Fill',(3,-2,3),170,3,'E5EEFF'),('Rim',(1,3,4),380,3,'FFEAC8')]:
        data=bpy.data.lights.new(name,'AREA');obj=bpy.data.objects.new(name,data);sc.collection.objects.link(obj);obj.location=pos;data.energy=power;data.shape='DISK';data.size=size;data.color=rgba(color)[:3];look_at(obj,(0,0,1))
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.008));ground=bpy.context.object;ground.name='Studio_Ground'
    mat=bpy.data.materials.new('Studio taupe');mat.diffuse_color=rgba('D8D0C1');ground.data.materials.append(mat)
    data=bpy.data.cameras.new('Review Camera');cam=bpy.data.objects.new('Review Camera',data);sc.collection.objects.link(cam);sc.camera=cam;data.type='ORTHO';data.ortho_scale=2.3
    sc.render.resolution_x=width;sc.render.resolution_y=width;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
    return cam

def main(args):
    output=ROOT/args.output;output.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str((ROOT/args.input).resolve()))
    imported=list(bpy.context.scene.objects);meshes=[o for o in imported if o.type=='MESH' and len(o.data.polygons)>1000]
    bounds=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
    lo=Vector(tuple(min(v[i] for v in bounds) for i in range(3)));hi=Vector(tuple(max(v[i] for v in bounds) for i in range(3)))
    root=bpy.data.objects.new('Reference model orientation',None);bpy.context.scene.collection.objects.link(root)
    for obj in imported:
        if obj.parent is None:obj.parent=root
    # Tripo's default forward is +X. Match the existing Blender character's -Y.
    scale=1.86/(hi.z-lo.z);root.scale=(scale,)*3;root.rotation_euler.z=-math.pi/2
    center=(lo+hi)*.5;root.location=(-center.y*scale,center.x*scale,-lo.z*scale)
    for im in bpy.data.images:
        if im.type=='IMAGE' and im.has_data:im.pack()
    cam=stage(args.width);sc=bpy.context.scene
    bpy.context.view_layer.update()
    report={'input':args.input,'mesh_objects':len(meshes),'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes),'original_bounds':[list(lo),list(hi)],'textures':[{'name':im.name,'size':list(im.size)} for im in bpy.data.images if im.type=='IMAGE'],'bones':{o.name:[{'name':b.name,'head':list(o.matrix_world@b.head_local),'tail':list(o.matrix_world@b.tail_local),'parent':b.parent.name if b.parent else None} for b in o.data.bones] for o in imported if o.type=='ARMATURE'}}
    (output/'inspection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    views=[('front',(0,-6,1.18),(0,0,.93),2.18),('back',(0,6,1.18),(0,0,.93),2.18),('side',(6,0,1.18),(0,0,.93),2.18),('face',(.20,-5,1.62),(0,0,1.53),.62)]
    for name,pos,target,span in views:
        cam.location=pos;look_at(cam,target);cam.data.ortho_scale=span;sc.render.filepath=str(output/(name+'.png'));bpy.ops.render.render(write_still=True)
    cam.location=(.6,-6,1.5);look_at(cam,(0,0,.93));cam.data.ortho_scale=2.2
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'daisy_tripo_source.blend'),compress=True)
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',default='assets/character_tripo/source');p.add_argument('--width',type=int,default=1024)
    main(p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []))
