"""lane lod27: one room's PS2 world from its recorded recipe (the shipped lineage), optionally with the lod27 LOD
settings (3 m clusters, min gain 0.8, floor 60; no merge). Windows Python (numpy/PIL), like bakeall/conv_room.sh.
  python conv_lod.py <room> <recipe ps2-world.json (any path)> <out dir> base|lod27|scan1|dec:<decplan.json>|scan1+dec:<decplan.json>
Prints the mesh sha256 so a base run can be checked against the shipped package."""
import ast, hashlib, json, os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, '..', '..', 'ps2_room_r4im.py')
SKIP = {'room', 'src', 'out', 'bake_static', 'bake_rows', 'bake_cell', 'meshlet_vertices'}
LOD27 = ['--lod-cluster', '3000', '--lod-min-gain', '0.8', '--lod-floor', '60']
# scan1 (roomscan, user look call 11-03 "halving the detail of expensive rooms"): coarser levels on more geometry
# (UV guard 0.2, first level at 48 mm, floor 2) for roomscan's distance caps to switch to
SCAN1 = ['--lod-cluster', '3000', '--lod-min-gain', '0.8', '--lod-floor', '2', '--lod-uv-guard', '0.2',
         '--lod-eps', '48,96,192,384,768']
room, rec, out, arm = sys.argv[1:5]
a = json.load(open(rec))['args']
a = ast.literal_eval(a) if isinstance(a, str) else a
opts = []
for k, v in a.items():
    if k in SKIP or v in ('None', None, 'False'):
        continue
    opts += ['--' + k.replace('_', '-')] if v == 'True' else ['--' + k.replace('_', '-'), str(v)]
if a.get('bake_static') == 'True':
    opts.append('--bake-static')
cmd = [sys.executable, TOOL, room, a['src'], os.path.join(out, room)] + opts + ['--meshlet-vertices', str(a.get('meshlet_vertices', '64'))]
for part in arm.split('+'):   # e.g. scan1+dec:<plan>: the scan1 levels plus decimation in place
    if part == 'lod27':
        cmd += LOD27
    elif part == 'scan1':
        cmd += SCAN1
    elif part.startswith('dec:'):   # roomscan decimate in place (roomscan.py decplan output), no LOD records added
        cmd += ['--decimate', part[4:]]
os.makedirs(out, exist_ok=True)
r = subprocess.run(cmd, capture_output=True, text=True)
open(os.path.join(out, room + '.log'), 'w').write(' '.join(cmd) + '\n' + r.stdout[-2000:] + r.stderr[-3000:])
for sub in ('tex', 'textures-packed', 'textures-source'):
    shutil.rmtree(os.path.join(out, room, sub), ignore_errors=True)
m = os.path.join(out, room, 'ps2-world.re4mesh')
print(room, arm, r.returncode, hashlib.sha256(open(m, 'rb').read()).hexdigest()[:8] if os.path.exists(m) else '-',
      os.path.getsize(m) if os.path.exists(m) else 0)
