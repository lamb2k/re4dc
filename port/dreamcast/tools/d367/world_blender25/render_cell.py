# world-blender25: render a hot-spot cell OBJ (from cellobj.py) solid (vertex colour) + wireframe, fixed camera.
# blender --background --factory-startup --python render_cell.py -- <in.obj> <out-prefix> <label>
import sys, math
import bpy, bmesh

a = sys.argv[sys.argv.index('--') + 1:]
src, outp, label = a[0], a[1], a[2]
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
V, C, F = [], [], []
for line in open(src):
    s = line.split()
    if s[0] == 'v':
        V.append(tuple(map(float, s[1:4]))); C.append(tuple(map(float, s[4:7])))
    elif s[0] == 'f':
        F.append(tuple(int(x) - 1 for x in s[1:4]))
me = bpy.data.meshes.new('cell'); me.from_pydata(V, [], F); me.update()
attr = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
for i, c in enumerate(C):
    attr.data[i].color = (*c, 1.0)
ob = bpy.data.objects.new('cell', me); bpy.context.scene.collection.objects.link(ob)
sc = bpy.context.scene
cam = bpy.data.cameras.new('cam'); co = bpy.data.objects.new('cam', cam); sc.collection.objects.link(co); sc.camera = co
co.location = (0.0, -26.0, 22.0); co.rotation_euler = (math.radians(50), 0, 0); cam.lens = 24
sc.render.engine = 'BLENDER_WORKBENCH'; sc.render.resolution_x = 1280; sc.render.resolution_y = 800
sh = sc.display.shading
sh.light = 'FLAT'; sh.color_type = 'VERTEX'; sh.background_type = 'WORLD'
sc.render.film_transparent = False
bpy.context.scene.world = bpy.data.worlds.new('w'); bpy.context.scene.world.color = (0.1, 0.1, 0.12)
# label as a text object in view
def text(msg):
    cu = bpy.data.curves.new('t', 'FONT'); cu.body = msg; t = bpy.data.objects.new('t', cu)
    sc.collection.objects.link(t); t.parent = co; t.location = (-0.95, 0.52, -2.0); t.scale = (0.045,)*3
    return t
t = text(label + '  (Blender, LOD0 pieces whose centre is in the 25 m box)')
sc.render.filepath = outp + '-solid.png'; bpy.ops.render.render(write_still=True)
md = ob.modifiers.new('wf', 'WIREFRAME'); md.thickness = 0.02; md.use_replace = True
sh.color_type = 'SINGLE'; sh.single_color = (0.9, 0.9, 0.9)
sc.render.filepath = outp + '-wire.png'; bpy.ops.render.render(write_still=True)
print('RENDERED', outp)
