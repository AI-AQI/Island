"""Render the authored composition for visual review, without modifying source."""
from pathlib import Path
import sys
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from geometry import look_at
architecture='--architecture' in sys.argv
waterside='--waterside' in sys.argv
landscape='--landscape' in sys.argv or architecture or waterside
if landscape:from landscape_spec import ground
else:from layout_spec import ground
edition='waterside' if waterside else 'architecture' if architecture else 'landscape' if landscape else 'layout'

bpy.ops.wm.open_mainfile(filepath=str(ROOT/f'assets/{edition}/island_{edition}.blend'))
sc=bpy.context.scene
old=bpy.data.objects.get('player')
if old:
    for o in old.children:o.hide_render=True
before=set(sc.objects)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'assets/character_tripo/runtime/daisy_tripo.glb'))
added=set(sc.objects)-before
root=bpy.data.objects.new('Daisy_preview',None);sc.collection.objects.link(root)
for o in added:
    if o.parent not in added:o.parent=root
    if o.name.startswith('Watering_Can'):o.hide_render=True
root.location=(-1,-4,ground(-1,-4)+.10);root.scale=(1.35,)*3
sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=24;sc.cycles.use_denoising=True
sc.render.resolution_x=1200;sc.render.resolution_y=900;sc.render.resolution_percentage=100
out=ROOT/f'renders/{edition}';out.mkdir(parents=True,exist_ok=True)
sc.render.image_settings.file_format='PNG';sc.render.filepath=str(out/'hero.png')
sc.camera.location=(16,-94,69);look_at(sc.camera,(0,0,8.5));sc.camera.data.ortho_scale=66
bpy.ops.render.render(write_still=True)
sc.camera.location=(0,-.01,90);look_at(sc.camera,(0,0,9));sc.camera.data.ortho_scale=68
sc.render.resolution_x=1100;sc.render.resolution_y=1000;sc.cycles.samples=16
sc.render.filepath=str(out/'top.png');bpy.ops.render.render(write_still=True)
if architecture:
    sc.render.resolution_x=1200;sc.render.resolution_y=1000;sc.cycles.samples=32
    for name,position,target,span in [('house',(-22,-15,26),(-12,10,15.5),16),('cafe',(28,-12,23),(18,9,13.8),15)]:
        sc.camera.location=position;look_at(sc.camera,target);sc.camera.data.ortho_scale=span
        sc.render.filepath=str(out/f'{name}_detail.png');bpy.ops.render.render(write_still=True)
if waterside:
    sc.render.resolution_x=1200;sc.render.resolution_y=1000;sc.cycles.samples=32
    for name,position,target,span in [('bridge',(27,-36,28),(15,-11,10.8),18),('river',(21,-19,37),(8,3,10.6),23),('waterfall',(26,-42,18),(11,-20,3.5),20)]:
        sc.camera.location=position;look_at(sc.camera,target);sc.camera.data.ortho_scale=span
        sc.render.filepath=str(out/f'{name}_detail.png');bpy.ops.render.render(write_still=True)
