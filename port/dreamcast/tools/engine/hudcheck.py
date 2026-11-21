"""hudcheck.py <pack> <run folder> <m1_state address> [--run N] [--min R]: the HUD ammo check, read from the stills
(lane eng-e1i; docs/engine/SERVICES.md 45).

  <pack>        the pack the scene drew, after bake/hud_fix.py (its digit widgets link the PS2 digit pictures; a pack
                without it is refused: "no linked digit widgets")
  <run folder>  a Flycast STILLS run: serial.txt and pic-<addr>-s<k>-NNNN.png (the runner names each still by the image's
                m1_state address, k = that image's scene run on the disc, NNNN = the picture)
  <addr>        the image's m1_state address (sh-elf-nm <elf> | grep _m1_state)
  --run N       the scene run, counted over the whole disc, of this image's first scene: serial.txt's STILL lines are
                numbered over every scene on the disc. Disc LEON, HILL, FIGHT: LEON and HILL --run 0 (e1.elf), FIGHT
                --run 2 (fight.elf)
  --min R       the least correlation a read digit needs (default 0.5)


For every still the E1 image handed over (pic-<addr>-s<k>-NNNN.png) and its serial line "E1 STILL n tick t magazine m
digits drawn ...", the two digit cells (ones, tens; laid out from the pack's widget records as the renderer lays them
out: degrees, group parents) are read from the picture: each cell's cyan (blue minus red) is correlated with the lit
segments of each of the ten PS2 digit pictures, cut to the glyph rows as the bake cuts them (v 5/32..29/32), and the
best digit is taken when its correlation is at least --min (0.5). The cells must read as the magazine: ones = m % 10,
tens = m // 10 % 10. Exit 0 PASS, 1 FAIL (a cell unread or another digit), 2 nothing to check.
The control: the same scene from a pack baked with --control-cut (the digits drawn over the whole 16 x 32 canvas):
its cells do not read as the magazine."""
import math, re, struct, sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hudana, dctex
a = sys.argv[1:]
pack, run, addr = a[0], Path(a[1]), a[2].lower()
RUN0 = int(a[a.index('--run') + 1]) if '--run' in a else 0   # the scene run of this image's first still (several scenes on one disc)
MIN = float(a[a.index('--min') + 1]) if '--min' in a else 0.5
p = hudana.load(pack)
ws = hudana.widgets(p, 1)[1]
X, Y, A, G = {}, {}, {}, {}
for lv in range(12):
    for q in ws:
        if (q['tree'] >> 8 & 255) != lv: continue
        par = q['tree'] & 255; i = q['identity'] & 255; G[i] = q['tree'] >> 16 == 1
        inh = par != 255 and G.get(par, False); an = A[par] if inh else 0.
        X[i] = (X[par] if inh else 0) + math.cos(an) * q['pos'][0] - math.sin(an) * q['pos'][1]
        Y[i] = (Y[par] if inh else 0) + math.sin(an) * q['pos'][0] + math.cos(an) * q['pos'][1]
        A[i] = an + math.radians(q['rot'][2])
cells = {}
for q in ws:
    mk = q['identity'] >> 16 & 255
    if (q['identity'] >> 8 & 255) == 0x21 and mk in (0x0B, 0x0A) and q['mask'][1]:
        cells[{0x0B: 0, 0x0A: 1}[mk]] = (320 + X[q['identity'] & 255], 240 - Y[q['identity'] & 255], q['w'], q['h'], q['mask'][1] - 1)
if len(cells) != 2: sys.exit('hudcheck: the pack has no linked digit widgets (bake/hud_fix.py)')
first = cells[0][4]
masks = []
for d in range(10):
    t = dctex.decode(hudana.texinfo(p, first + d)['pkg']).astype(float)
    masks.append(t[..., :3].mean(-1) / 255. * t[..., 3] / 255.)   # lit segments bright, unlit dark
V0, V1 = 5 / 32, 29 / 32
def read(img, cell):
    cx, cy, w, h, _ = cell
    ys = np.arange(int(cy - h / 2), int(math.ceil(cy + h / 2))); xs = np.arange(int(cx - w / 2), int(math.ceil(cx + w / 2)))
    sub = img[ys][:, xs].astype(float); cyan = sub[..., 2] - sub[..., 0]
    u = np.clip(((xs + .5 - (cx - w / 2)) / w * 16).astype(int), 0, 15)
    v = np.clip(((V0 + (ys + .5 - (cy - h / 2)) / h * (V1 - V0)) * 32).astype(int), 0, 31)
    scores = []
    for m in masks:
        t = m[v][:, u]
        scores.append(np.corrcoef(t.ravel(), cyan.ravel())[0, 1] if t.std() > 0 and cyan.std() > 0 else 0.)
    best = int(np.argmax(scores))
    return (best if scores[best] >= MIN else None), scores[best]
serial = (run / 'serial.txt').read_text(errors='replace')
facts = re.findall(r'E1 STILL (\d+) tick (\d+) magazine (\d+) digits drawn (-?\d+) (-?\d+) (-?\d+)', serial)
pics = sorted(run.glob(f'pic-{addr}-s*-*.png'))
# serial STILL lines in order; pictures by scene run then number
order = sorted(pics, key=lambda f: (int(f.stem.split('-')[2][1:]), int(f.stem.split('-')[3])))
fails = checked = 0
print(f'# hudcheck {pack} {run} {addr}: {len(order)} stills, {len(facts)} STILL lines, min r {MIN}')
facts_by = {}
k = -1; prev = 10 ** 9
for n, tick, mag, h, t, o in facts:
    if int(n) < prev: k += 1
    prev = int(n); facts_by.setdefault((k, int(n)), (int(tick), int(mag), (int(h), int(t), int(o))))
for f in order:
    s, n = int(f.stem.split('-')[2][1:]), int(f.stem.split('-')[3])
    fact = facts_by.get((s + RUN0, n))
    if fact is None: print(f'{f.name}: no STILL line'); continue
    tick, mag, drawn = fact
    img = np.asarray(Image.open(f).convert('RGB'))
    got = [read(img, cells[c]) for c in (0, 1)]
    want = [mag % 10, mag // 10 % 10]
    ok = all(g[0] == w for g, w in zip(got, want))
    checked += 1; fails += not ok
    print(f'{f.name}: tick {tick} magazine {mag} drawn {drawn} read tens {got[1][0]} (r {got[1][1]:.2f}) ones {got[0][0]} (r {got[0][1]:.2f}): {"ok" if ok else "WRONG"}')
print(f'checked {checked}, wrong {fails}: {"PASS" if checked and not fails else "FAIL" if checked else "NOTHING"}')
sys.exit(2 if not checked else 1 if fails else 0)
