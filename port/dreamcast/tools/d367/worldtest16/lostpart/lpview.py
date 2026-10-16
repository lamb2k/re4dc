"""lpview.py NAME ORIG_MESH ORIG_R4PW RED_MESH RED_R4PW ROOM N OUT.png: original | reduced renders (colour = texture,
flat shaded by normal) from the walk cameras where NAME's flagged pieces lose the most pixels; flagged pieces outlined."""
import sys, json, importlib.util, numpy as np
from PIL import Image, ImageDraw
sp = importlib.util.spec_from_file_location('lp', r'C:\Game Dev\Emulators\worldtest-20261016\scripts\lostpart.py')
lp = importlib.util.module_from_spec(sp); sys_argv = sys.argv; sys.argv = ['x']; sp.loader.exec_module(lp); sys.argv = sys_argv
name, om, op, rm, rpw, room, N, out = sys.argv[1:9]; N = int(N)
po, ko, TO, KO, PC, recs = lp.load(om, op, pieces=True)
pr, kr, TR, KR, _, _ = lp.load(rm, rpw)
kmap = {v: ko.get(k, -1) for k, v in kr.items()}; KR = np.array([kmap[k] for k in KR])
d = json.load(open(r'C:\Game Dev\Emulators\worldtest-20261016\lostpart\%s.json' % name))['pieces']
cams = lp.cameras(room)
score = {}
for i, r in enumerate(d):
    for c in r.get('cam_fail', []):
        if r['ortho_fail']:
            score.setdefault(c['cam'], []).append((c['px'] - c['kept'], i))
best = sorted(score, key=lambda c: -sum(x[0] for x in score[c]))[:N]
rng = np.random.default_rng(1); pal = rng.integers(60, 230, (len(ko) + 2, 3))
def shade(T, K, cam, W=480, H=360):
    n, eye, fwd, right, up, yaw = cam
    ids = np.arange(len(T))
    im = lp.render_ids(T, ids, eye, fwd, right, up, W, H) - 1
    nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-9
    lit = 0.45 + 0.55 * np.abs(nrm @ np.array([0.3, 0.8, 0.5]) / np.linalg.norm([0.3, 0.8, 0.5]))
    img = np.zeros((H, W, 3), np.uint8); m = im >= 0
    img[m] = (pal[K[im[m]]] * lit[im[m]][:, None]).astype(np.uint8)
    return img
rows = []
for c in best:
    cam = cams[c]
    a = shade(TO, KO, cam); b = shade(TR, KR, cam)
    # outline flagged pieces (original pixels)
    pid = lp.render_ids(TO, PC, *cam[1:5], 480, 360) - 1
    fl = np.zeros(pid.shape, bool)
    for _, i in score[c]:
        fl |= pid == i
    edge = fl & ~lp.erode(fl)
    for img in (a, b):
        img[edge] = (255, 0, 255)
    row = Image.new('RGB', (970, 380), (20, 20, 20)); row.paste(Image.fromarray(a), (0, 20)); row.paste(Image.fromarray(b), (490, 20))
    ImageDraw.Draw(row).text((4, 4), '%s cam %d %s yaw %.2f eye %s: %d flagged pieces lose %d px (magenta = flagged, left original, right reduced)' % (
        name, c, cam[0], cam[5], [int(v) for v in cam[1]], len(score[c]), sum(x[0] for x in score[c])), fill=(255, 255, 255))
    rows.append(row)
sheet = Image.new('RGB', (970, 380 * len(rows)), (0, 0, 0))
for k, r in enumerate(rows):
    sheet.paste(r, (0, 380 * k))
sheet.save(out); print('saved', out, best)
