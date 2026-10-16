"""price2.py OUT.json ROOM:ARM=MESH|R4PW ...  (Windows Python, numpy): MODELLED world cost per arm (worldtest16).
Same camera samples as room-budget-20261015/roomproj.py (door arrivals + enemy set positions, 16 yaws, Leon's rig,
25 m far) plus the two still cameras per room. Modelled world ms = K_WORLD 1.1 x K_W 1.0 ms per 1k on-screen world
TA vertices (budget.py console fit). MODELLED, not measured."""
import sys, json, math, os, importlib.util
import numpy as np
spec = importlib.util.spec_from_file_location('rp', r'C:\Game Dev\Emulators\room-budget-20261015\roomproj.py')
rp = importlib.util.module_from_spec(spec); spec.loader.exec_module(rp)
CAMS = {'r101': [(-7914, 0, 2000, 1.5708)],
        'r100': [(96524, -6771, -8536, 5.498), (-83950, 830, -32960, 0.393)],
        'r102': [(-19691, 0, -19088, 0.785), (-12210, -8720, 38420, 2.749)],
        'r103': [(-47609, 12, 7084, 2.356), (-27380, 40, -18290, 1.178)],
        'r104': [(-3443, 0, 12338, 2.749), (-6040, 1010, 8570, 2.356)],
        'r105': [(-33040, 0, -1792, 1.963), (32440, 2840, -7090, 5.498)],
        'r106': [(11141, -893, -120, 1.178), (113010, -8260, -33390, 1.178)],
        'r107': [(29683, -13, -28512, 1.963), (74980, 180, -34790, 3.927)],
        'r108': [(-43905, -38, -14737, 1.963), (-1390, 10000, -19250, 1.963)],
        'r109': [],
        'r10a': [(-58327, 7346, 69786, 1.178), (41850, -10000, 89330, 1.178)]}
K = 1.1  # ms per 1k projected world TA vertices (K_WORLD x K_W)


def wp(p):
    return r'\\wsl.localhost\Ubuntu-24.04' + p.replace('/', '\\') if p.startswith('/root/') else rp.hp(p)


out = {}
esl = rp.esl_positions(); drs = rp.doors()
for spec_ in sys.argv[2:]:
    ra, paths = spec_.split('=', 1)
    room, arm = ra.split(':')
    m, pw = paths.split('|')
    p = rp.Pkg(wp(m), wp(pw)); F = rp.flatten(p)
    samples = [('door<' + d['src'], np.array(d['pos'], float)) for d in drs.get(room, [])]
    samples += [('em%02x' % e['id'], np.array(e['pos'], float) * 10.0) for e in esl.get(room, [])]
    X = F['X']

    def floored(P):
        mm = (np.abs(X[:, 0] - P[0]) < 4000) & (np.abs(X[:, 2] - P[2]) < 4000) & (X[:, 1] > P[1] - 3000) & (X[:, 1] < P[1] + 500)
        return bool(mm.any())
    tas = []
    for n, P in samples:
        if not floored(P):
            continue
        for k in range(rp.NYAW):
            yaw = 2 * math.pi * k / rp.NYAW
            fwd, right, _ = rp.basis(P, yaw, 0)
            eye = P + np.array([0, rp.EYE_UP, 0]) - fwd * rp.EYE_BACK + right * rp.EYE_RIGHT
            tas.append(rp.view(F, eye, yaw)[0])
    cams = []
    for x, y, z, yaw in CAMS.get(room, []):
        P = np.array([x, y, z], float)
        fwd, right, _ = rp.basis(P, yaw, 0)
        eye = P + np.array([0, rp.EYE_UP, 0]) - fwd * rp.EYE_BACK + right * rp.EYE_RIGHT
        cams.append(rp.view(F, eye, yaw)[0])
    t = np.array(tas, float)
    r = dict(room=room, arm=arm, mesh=m, corners=int(F['lvc'].sum()), ta_total=int(F['slen'].sum()), views=len(tas),
             ta_p50=float(np.percentile(t, 50)), ta_p90=float(np.percentile(t, 90)), ta_max=float(t.max()), cams=cams)
    r.update(ms_p90=round(K * r['ta_p90'] / 1000, 2), ms_max=round(K * r['ta_max'] / 1000, 2),
             ms_cams=[round(K * c / 1000, 2) for c in cams])
    out[ra] = r
    print('%s %-4s corners %6d  TA p50 %6.0f p90 %6.0f max %6.0f | MODELLED world ms p90 %5.2f max %5.2f cams %s TA %s' % (
        room, arm, r['corners'], r['ta_p50'], r['ta_p90'], r['ta_max'], r['ms_p90'], r['ms_max'], r['ms_cams'], cams), flush=True)
json.dump(out, open(sys.argv[1], 'w'), indent=1)
