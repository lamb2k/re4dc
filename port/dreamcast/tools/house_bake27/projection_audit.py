import bpy,json,sys
from pathlib import Path
from mathutils.bvhtree import BVHTree
root=Path(sys.argv[sys.argv.index('--')+1]);assert not bpy.app.online_access
bpy.ops.wm.open_mainfile(filepath=str(root/'house-bake.blend'))
src=bpy.data.objects['roof_source'];target=bpy.data.objects['roof_BAKED_TARGET']
bvh=BVHTree.FromPolygons([v.co for v in src.data.vertices],[list(p.vertices) for p in src.data.polygons],all_triangles=True)
rows=[]
for p in target.data.polygons:
 hits=[]
 for offset in (.25,.5,1.,2.):
  h=bvh.ray_cast(p.center+p.normal*offset,-p.normal,4.)
  hits.append(dict(offset_m=offset,hit=h[0] is not None,distance_m=h[3] if h[0] is not None else None))
 near=bvh.find_nearest(p.center)
 rows.append(dict(triangle=p.index,hits=hits,nearest_distance_m=near[3]))
(root/'PROJECTION-AUDIT.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps([r for r in rows if not r['hits'][0]['hit']],indent=2))
