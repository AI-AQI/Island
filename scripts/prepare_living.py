"""Build the living-island revision from the existing refined Blender file.

Native objects remain editable. Runtime export batches only static scenery;
the player, crops, water and hanging hull keep independently addressable nodes.
All movement and game state are implemented in viewer/, not baked into a video.
"""
import argparse
import json
import math
import random
import subprocess
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from geometry import look_at


def bend(y):
    return 1.25 * math.sin((y + 5.2) * .21)


def mapped(v):
    x, y, z = v
    return Vector((x + bend(y), y, 10.1 + (z - 10.1) * .73 if z < 10.1 else z))


def bounds(o):
    vv = [o.matrix_world @ Vector(v) for v in o.bound_box]
    return [[min(v[k] for v in vv) for k in range(3)], [max(v[k] for v in vv) for k in range(3)]]


def part(src, name, faces, pivot):
    """Copy selected polygons, keeping loop UVs and material identities."""
    used = sorted({i for p in faces for i in p.vertices})
    indices = {v: i for i, v in enumerate(used)}
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([src.data.vertices[i].co - pivot for i in used], [],
                     [[indices[i] for i in p.vertices] for p in faces])
    for mat in src.data.materials:
        mesh.materials.append(mat)
    for dst, source in zip(mesh.polygons, faces):
        dst.material_index = source.material_index
        dst.use_smooth = source.use_smooth
    for uv in src.data.uv_layers:
        target = mesh.uv_layers.new(name=uv.name)
        for dst, source in zip(mesh.polygons, faces):
            for di, si in zip(dst.loop_indices, source.loop_indices):
                target.data[di].uv = uv.data[si].uv
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = pivot
    return obj


def split_player(src):
    # Each original sphere / beam is a connected component. Assign whole pieces,
    # so the face, hat, skirt and shoes never tear across an animation joint.
    parent = list(range(len(src.data.vertices)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for edge in src.data.edges:
        a, b = map(find, edge.vertices)
        parent[a] = b
    groups = {}
    for p in src.data.polygons:
        groups.setdefault(find(p.vertices[0]), []).append(p)
    assigned = {n: [] for n in ['body', 'leg_l', 'leg_r', 'arm_l', 'arm_r']}
    for faces in groups.values():
        vv = [src.data.vertices[i].co for i in {i for p in faces for i in p.vertices}]
        center = sum(vv, Vector()) / len(vv)
        top = max(v.z for v in vv)
        name = 'body'
        if top < .52:
            name = 'leg_l' if center.x < 0 else 'leg_r'
        elif .59 < center.z < .85 and abs(center.x) > .19 and center.y < -.035:
            name = 'arm_l' if center.x < 0 else 'arm_r'
        assigned[name].extend(faces)
    root = bpy.data.objects.new('player', None)
    bpy.context.scene.collection.objects.link(root)
    root.matrix_world = src.matrix_world.copy()
    for name, faces in assigned.items():
        pivot = Vector((0, 0, 0))
        if name.startswith('leg'):
            pivot = Vector((-.13 if name.endswith('l') else .13, 0, .49))
        if name.startswith('arm'):
            pivot = Vector((-.16 if name.endswith('l') else .16, 0, .93))
        obj = part(src, 'player_' + name, faces, pivot)
        obj.parent = root
    bpy.data.objects.remove(src, do_unlink=True)
    return root


def main(args):
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'island_dusk_refined.blend'))
    sc = bpy.context.scene
    bpy.context.view_layer.update()
    rng = random.Random(91726)
    house_eave = 10.375858 + 1.12 * 3.9
    old_boat = bpy.data.objects['hanging_boat_001']
    boat_pivot = mapped(old_boat.matrix_world @ Vector((0, -.435, 4.29)))
    boat_matrix = old_boat.matrix_world.copy()
    hull_faces, support_faces = [], []
    for p in old_boat.data.polygons:
        vv = [old_boat.data.vertices[i].co for i in p.vertices]
        center = sum(vv, Vector()) / len(vv)
        if max(v.z for v in vv) < 1.12:
            hull_faces.append(p)
        elif abs(center.y + .435) < .045 and max(v.x for v in vv) - min(v.x for v in vv) < .055:
            continue  # Suspension ropes are redrawn between fixed and moving anchors.
        else:
            support_faces.append(p)
    for name, faces in [('boat_hull', hull_faces), ('boat_support', support_faces)]:
        o = part(old_boat, name, faces, Vector())
        o.matrix_world = boat_matrix
    bpy.data.objects.remove(old_boat, do_unlink=True)

    for o in list(sc.objects):
        if o.type != 'MESH':
            continue
        # The runtime replaces the solid smoke and static spray with particles.
        o.data = o.data.copy()
        aid = o.get('asset_id', '')
        if aid.startswith('bush_flower'):
            o.location.x += rng.uniform(-.30, .30)
            o.location.y += rng.uniform(-.22, .22)
            o.scale *= rng.uniform(.78, 1.18)
        mat = o.matrix_world.copy()
        if aid.startswith('bush_flower'):
            bpy.context.view_layer.update()
            mat = o.matrix_world.copy()
        inv = mat.inverted()
        rigid = aid in ['house_main', 'cafe_pavilion', 'farm_soil', 'stone_bridge', 'sheep'] or aid.startswith(('tree', 'crop')) or o.name in ['garden_wanderer', 'garden_cat']
        offset = bend(mat.translation.y)
        for v in o.data.vertices:
            world = mat @ v.co
            new = mapped(world)
            if rigid:
                new.x = world.x + offset
            if aid == 'house_main' or o.name in ['house_climbing_flowers', 'chimney_smoke_refined']:
                if new.z > house_eave:
                    new.z = house_eave + (new.z - house_eave) * .69
            v.co = inv @ new
        # Shift object origins with rigid content, without changing the result.
        if rigid:
            shift = Vector((offset, 0, 0))
            local_shift = mat.to_3x3().inverted() @ shift
            for v in o.data.vertices:
                v.co -= local_shift
            o.location += shift
        o.data.update()

    bpy.context.view_layer.update()
    player = split_player(bpy.data.objects['garden_wanderer'])
    player['role'] = 'controllable_player'
    boat = bpy.data.objects['boat_hull']
    # Bake world vertices around a suspension pivot, ready for pendulum rotation.
    matrix = boat.matrix_world.copy()
    for v in boat.data.vertices:
        v.co = matrix @ v.co - boat_pivot
    boat.matrix_world = Matrix.Translation(boat_pivot)
    boat['role'] = 'pendulum_hull'

    # Collect collider bounds before batching. Coordinates here are Blender Z-up.
    house = bpy.data.objects['house_main_001']
    cafe = bpy.data.objects['cafe_pavilion_001']
    bridge = bpy.data.objects['stone_bridge_001']
    plots = []
    for index, o in enumerate(sorted([o for o in sc.objects if o.get('asset_id') == 'farm_soil'], key=lambda o: o.name)):
        x, y, z = o.location
        crops = [c for c in sc.objects if c.get('asset_id', '').startswith('crop') and abs(c.location.x - x) < 1.7]
        for j, crop in enumerate(crops):
            crop.name = f'crop_{index}_{j}'
            crop['plot_id'] = index
        plots.append(dict(id=index, name=['南瓜田', '生菜田', '萝卜田'][index], position=[x,y,z], cropNodes=[c.name for c in crops], approach=[x+.65, -6.75]))
    smoke = bpy.data.objects['chimney_smoke_refined']
    smoke_bounds = bounds(smoke)
    metadata = dict(version=1, source='island_dusk_refined.blend', coordinateSystem='blender-z-up',
        house=bounds(house), cafe=bounds(cafe), bridge=dict(position=list(bridge.location), halfLength=3.4, halfWidth=1.08, deckBase=bridge.location.z+.27+.2),
        plots=plots, spawn=list(player.location), smokeOrigin=[sum(a)/2 for a in zip(*smoke_bounds)][:2]+[smoke_bounds[0][2]+.18],
        boatPivot=list(boat_pivot), trees=[dict(position=list(o.location), radius=.5*o.scale.x+.25) for o in sc.objects if o.get('asset_id','').startswith('tree')],
        fences=[bounds(o) for o in sc.objects if o.get('asset_id')=='farm_fence'],
        riverBend=1.25, cliffCompression=.73)

    # Lower the main camera and leave breathing room around the complete island.
    sc.camera.location=(22,-73,47)
    look_at(sc.camera,(0,0,9))
    sc.camera.data.ortho_scale=55.5
    sc.render.resolution_x=args.width
    sc.render.resolution_y=round(args.width*.75)
    sc.render.resolution_percentage=100
    sc.cycles.samples=args.samples
    sc.cycles.use_denoising=True
    sc.render.image_settings.file_format='PNG'
    sc['art_revision']='living_island_v3'
    out=ROOT/'renders/living'
    out.mkdir(parents=True,exist_ok=True)
    (ROOT/'assets/living').mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'island_dusk_living.blend'),compress=True)
    if args.render:
        sc.render.filepath=str(out/'island_living.png')
        bpy.ops.render.render(write_still=True)

    # Export a web copy, keeping only the nodes that need runtime control.
    preserved = []
    static = []
    for o in list(sc.objects):
        if o.type!='MESH':continue
        if o.name in ['chimney_smoke_refined','waterfall_spray','flowing_ripples_and_eddies']:
            bpy.data.objects.remove(o,do_unlink=True)
            continue
        if o.parent == player or o.name.startswith('crop_') or o.name in ['boat_hull','stream_surface','waterfall_ribbons','garden_cat'] or o.get('asset_id')=='sheep':
            preserved.append(o)
        else:static.append(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in static:o.select_set(True)
    bpy.context.view_layer.objects.active=static[0]
    bpy.ops.object.join()
    scenery=bpy.context.object
    scenery.name='island_scenery'
    source_tris=sum(len(p.vertices)-2 for p in scenery.data.polygons)
    if source_tris>400000:
        mod=scenery.modifiers.new('Realtime scenery budget','DECIMATE')
        mod.ratio=400000/source_tris
        mod.use_collapse_triangulate=True
        bpy.ops.object.modifier_apply(modifier=mod.name)
    scenery.data.validate(verbose=False)
    scenery.data.update()
    # Bump-only procedural normals are retained in the native file. glTF uses the
    # portable color textures and geometry normals without unused image channels.
    for mat in bpy.data.materials:
        if mat.use_nodes:
            p=mat.node_tree.nodes.get('Principled BSDF')
            if p:
                for link in list(p.inputs['Normal'].links):mat.node_tree.links.remove(link)
    for o in preserved+[scenery,player]:o.select_set(True)
    glb=ROOT/'island_dusk_living.glb'
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,
        export_animations=False,export_yup=True,export_cameras=False,export_lights=False,export_extras=True)
    subprocess.run(['node','-e',"console.log(require('./scripts/optimize_glb.cjs').optimize('island_dusk_living.glb'))"],cwd=ROOT,check=True)
    metadata['webTriangles']=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in preserved+[scenery])
    metadata['independentNodes']=[o.name for o in preserved]+['player']
    (ROOT/'assets/living/scene.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2))
    print('LIVING_REPORT='+json.dumps(dict(triangles=metadata['webTriangles'],bytes=glb.stat().st_size,nodes=len(preserved)+2)))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--render',action='store_true')
    parser.add_argument('--width',type=int,default=1440)
    parser.add_argument('--samples',type=int,default=40)
    main(parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []))
