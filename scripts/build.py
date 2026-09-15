import bpy, sys, os, json, math, argparse, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from geometry import *
import assets

ROOT=Path(__file__).resolve().parent.parent

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True); MATS.clear(); palette()
    bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1

def stage(target=(0,0,0),size=8,preview=True):
    sc=bpy.context.scene; sc.render.engine='CYCLES';sc.cycles.samples=24 if preview else 80
    sc.cycles.use_denoising=True;sc.cycles.device='GPU'
    pref=bpy.context.preferences.addons['cycles'].preferences;pref.compute_device_type='METAL';pref.get_devices()
    for d in pref.devices:d.use=d.type=='METAL'
    sc.render.resolution_x=900 if preview else 2048;sc.render.resolution_y=750 if preview else 1152;sc.render.resolution_percentage=100
    sc.world=bpy.data.worlds.new('dusk_environment');sc.world.use_nodes=True
    sc.world.node_tree.nodes['Background'].inputs[0].default_value=rgba('B8A8D8');sc.world.node_tree.nodes['Background'].inputs[1].default_value=.6
    sc.view_settings.view_transform='AgX';sc.view_settings.exposure=.5
    light=bpy.data.lights.new('sunset_key','SUN');light.energy=2.7;light.color=rgba('FFD9A0')[:3];light.angle=.16
    obj=bpy.data.objects.new('sunset_key',light);sc.collection.objects.link(obj);obj.location=(30,-18,18);look_at(obj,(-10,4,8))
    ar=bpy.data.lights.new('lavender_fill','AREA');ar.energy=3*size*size if preview else 4200;ar.shape='DISK';ar.size=size*.65;ar.color=rgba('CFD9F8')[:3]
    ao=bpy.data.objects.new('lavender_fill',ar);sc.collection.objects.link(ao);ao.location=(-size*.7,-size*.2,size*1.1);look_at(ao,target)
    camd=bpy.data.cameras.new('camera');cam=bpy.data.objects.new('camera',camd);sc.collection.objects.link(cam)
    cam.location=Vector(target)+Vector((.78,-1.25,.83))*size;look_at(cam,target);camd.type='ORTHO';camd.ortho_scale=size
    camd.lens=45;sc.camera=cam
    if preview:
        ground=Mesh('preview_ground');ground.box((0,0,-.16),(size*200,size*200,.2),'cloud');ground.object()
    sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
    return cam

def triangles(obj):return sum(len(p.vertices)-2 for p in obj.data.polygons)

def asset(name):
    reset();m=assets.BUILDERS[name]();obj=m.object()
    # Origin at the centre of the bottom bounding rectangle; all asset geometry in metres.
    lo=Vector(tuple(min(v[i] for v in m.v) for i in range(3)));hi=Vector(tuple(max(v[i] for v in m.v) for i in range(3)))
    offset=Vector(((hi.x+lo.x)/2,(hi.y+lo.y)/2,lo.z)) if name!='island_base' else Vector((0,0,0))
    for v in obj.data.vertices:v.co-=offset
    obj['asset_id']=name;obj['forward']='-Y';obj['units']='metres';obj['origin']='bottom_center';obj['source']='Blender procedural modeling'
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(ROOT/'assets/glb'/f'{name}.glb'),export_format='GLB',use_selection=True,export_yup=True,export_animations=False)
    dims=hi-lo;stats={'id':name,'triangles':triangles(obj),'dimensions_m':list(dims),'offset':list(offset),'glb_bytes':(ROOT/'assets/glb'/f'{name}.glb').stat().st_size}
    (ROOT/'reports'/f'{name}.json').write_text(json.dumps(stats,indent=2))
    size=max(dims.x*1.38,dims.y*1.55,dims.z*1.8,1.5)
    stage((0,0,dims.z*.42),size)
    if name=='island_base':
        pm=assets.player_ref();po=pm.object();po.location=(-6,-4,land_z(-6,-4));po.name='preview_player_ref_1_4m'
    # Lighting/camera are kept with each source; GLB includes only the asset.
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'assets/source'/f'{name}.blend'))
    bpy.context.scene.render.filepath=str(ROOT/'assets/previews'/f'{name}.png');bpy.ops.render.render(write_still=True)
    print('ASSET_COMPLETE '+json.dumps(stats),flush=True)

if __name__=='__main__':
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    p=argparse.ArgumentParser();p.add_argument('--asset');p.add_argument('--assemble',action='store_true');args=p.parse_args(argv)
    if args.asset:
        for name in (list(assets.BUILDERS) if args.asset=='all' else args.asset.split(',')):asset(name)
    elif args.assemble:
        import assemble;assemble.run()
