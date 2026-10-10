#!/usr/bin/env python3
"""job.json for bl_render.py: today / A / B / GC, flat + lit + wire, six views.

  mk_render_job.py <job.json> [labels, e.g. A,B]      (meshes from $PS2LEON_WORK/arms, renders to $PS2LEON_WORK/renders)
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import leon_sources as ls  # noqa
R = ls.WORK
CB = ls.PRIV / 'charbake-20261010/src'
models = [dict(label='today', mesh=str(ls.LEON_MESH)), dict(label='A', mesh=str(R / 'arms/a/mesh.json')),
          dict(label='B', mesh=str(R / 'arms/b/mesh.json')), dict(label='GC', mesh=str(R / 'arms/gc/mesh.json'))]
if len(sys.argv) > 2:
    models = [m for m in models if m['label'] in sys.argv[2].split(',')]
views = [
    dict(name='front', aim='body', cam=[0, -2.95, 0.15], lens=50, size=[400, 720], wire=0.0042),
    dict(name='back', aim='body', cam=[0, 2.95, 0.15], lens=50, size=[400, 720], wire=0.0042),
    dict(name='side', aim='body', cam=[2.95, 0, 0.15], lens=50, size=[400, 720], wire=0.0042),
    # RE4's over-the-shoulder play camera: behind and right of Leon, looking ahead (Leon on the left of the frame)
    dict(name='game', relative=False, aim=[0.40, -3.0, 1.30], cam=[0.50, 1.05, 1.74], lens=30, size=[640, 480], wire=0.0026),
    dict(name='hair', aim='head', aim_offset=[0, 0, 0.07], cam=[0.42, 0.62, 0.10], lens=50, size=[480, 480], wire=0.0012, hide_roles=[2]),
    dict(name='face', aim='head', aim_offset=[0, 0, 0.07], cam=[-0.22, -0.70, 0.04], lens=50, size=[480, 480], wire=0.0012, hide_roles=[2]),
]
job = dict(models=models, atlas=str(CB / 'ec255e66-76812316.png'), hair={'1': str(CB / 'fc24a99c-03d13534.png'), '2': str(CB / '9cf7f055-d40aae38.png')},
           tiles=json.loads((ls.PROTO / 'deliverables/leon-4k/asset-report.json').read_text())['source_uv_tiles'],
           modes=['flat', 'clay', 'wire'], views=views, out=str(R / 'renders'))
Path(sys.argv[1]).write_text(json.dumps(job, indent=1))
print('models', [m['label'] for m in models])
