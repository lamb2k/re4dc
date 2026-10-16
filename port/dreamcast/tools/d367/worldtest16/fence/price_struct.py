"""price_struct.py OUT.json ROOM=MESH|R4PW|CLASS.json ...  (Windows Python): MODELLED world cost split into structure vs
terrain parts (class.json from ps2_world_vert_ladder.py --class-report), same view samples as price2.py (door arrivals +
enemy set positions, 16 yaws, + the sheet cameras). Structure ms = 1.1 ms per 1k on-screen structure TA vertices.
MODELLED, not measured. For the Blender-pass ranking (worldtest16, 10-16)."""
import sys, json, math, importlib.util
import numpy as np
sp = importlib.util.spec_from_file_location('p2', r'C:\Game Dev\Emulators\worldtest-20261016\scripts\price2.py')
src = open(sp.origin).read()
p2 = {}
exec(src.split('out = {}')[0], p2)   # CAMS, K, wp, rp
rp, CAMS, K, wp = p2['rp'], p2['CAMS'], p2['K'], p2['wp']
orig_flatten = rp.flatten


def flatten_skip(p, skip):
    import copy
    q = copy.copy(p)   # drop the skipped parts' clusters by giving them zero clusters
    q.plod = [(fc, 0) if i in skip else (fc, cc) for i, (fc, cc) in enumerate(p.plod)]
    return orig_flatten(q)


out = {}
esl = rp.esl_positions(); drs = rp.doors()
for spec_ in sys.argv[2:]:
    room, paths = spec_.split('=', 1)
    m, pw, cj = paths.split('|')
    p = rp.Pkg(wp(m), wp(pw))
    cls = json.load(open(wp(cj)))['parts']
    terr = {int(k) for k, v in cls.items() if v['cls'] == 'terrain'}
    FA = orig_flatten(p); FS = flatten_skip(p, terr)
    samples = [np.array(d['pos'], float) for d in drs.get(room, [])] + [np.array(e['pos'], float) * 10.0 for e in esl.get(room, [])]
    X = FA['X']
    def floored(P):
        mm = (np.abs(X[:, 0] - P[0]) < 4000) & (np.abs(X[:, 2] - P[2]) < 4000) & (X[:, 1] > P[1] - 3000) & (X[:, 1] < P[1] + 500)
        return bool(mm.any())
    eyes = []
    for P in samples:
        if not floored(P): continue
        for k in range(rp.NYAW):
            yaw = 2 * math.pi * k / rp.NYAW; fwd, right, _ = rp.basis(P, yaw, 0)
            eyes.append((P + np.array([0, rp.EYE_UP, 0]) - fwd * rp.EYE_BACK + right * rp.EYE_RIGHT, yaw))
    for x, y, z, yaw in CAMS.get(room, []):
        P = np.array([x, y, z], float); fwd, right, _ = rp.basis(P, yaw, 0)
        eyes.append((P + np.array([0, rp.EYE_UP, 0]) - fwd * rp.EYE_BACK + right * rp.EYE_RIGHT, yaw))
    ta = np.array([rp.view(FA, e, y)[0] for e, y in eyes], float); ts = np.array([rp.view(FS, e, y)[0] for e, y in eyes], float)
    i90 = int(np.argsort(ta)[int(0.9 * (len(ta) - 1))]); imax = int(ta.argmax())
    r = dict(room=room, views=len(ta), parts=len(cls), terrain_parts=len(terr),
             ms_p90=round(K * np.percentile(ta, 90) / 1000, 2), struct_ms_p90=round(K * np.percentile(ts, 90) / 1000, 2),
             ms_max=round(K * ta.max() / 1000, 2), struct_ms_at_max=round(K * ts[imax] / 1000, 2),
             struct_share_all=round(float(ts.sum() / max(ta.sum(), 1)), 3))
    out[room] = r
    print(json.dumps(r), flush=True)
json.dump(out, open(sys.argv[1], 'w'), indent=1)
