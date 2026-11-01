"""mkcfg.py <pkg dir> <out json> <room int> <comment> <spec json>: a build_cell.py config from hand-authored boxes.
spec: {"hull": [[lo,hi],...], "eye_boxes": [[lo,hi],...]}; outer = hull union bbox, occluder box = outer + 1.5 m."""
import hashlib, json, sys
from pathlib import Path
pkg, out, room, comment, spec = sys.argv[1], sys.argv[2], int(sys.argv[3], 0), sys.argv[4], json.loads(Path(sys.argv[5]).read_text())
sha = lambda f: hashlib.sha256((Path(pkg) / f).read_bytes()).hexdigest()
H = spec['hull']
lo = [min(h[0][a] for h in H) for a in range(3)]; hi = [max(h[1][a] for h in H) for a in range(3)]
cfg = dict(comment=comment, room=room,
           package=dict(mesh='ps2-world.re4mesh', sidecar='ps2-world.r4pw', mesh_sha256=sha('ps2-world.re4mesh'),
                        sidecar_sha256=sha('ps2-world.r4pw')),
           exclude_dynamic=True,
           occluder_box=[[x - 1500 for x in lo], [x + 1500 for x in hi]], outer=[lo, hi], eye_boxes=spec['eye_boxes'], hull=H,
           near_max=150, subcell_size=1500, camera_step=350, target_step=150, exit_cell=100, dilate_cells=2, margin=200,
           edge_step=40, edge_eps=2.0)
Path(out).write_text(json.dumps(cfg, indent=1) + '\n', newline='\n')
print(out, 'outer', lo, hi)
