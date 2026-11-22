#!/usr/bin/env python3
"""lvlcheck.py <base run> <levels run> [<base run 2>] [--pad N]: a still of the levels run may differ from the same
still of the base run only inside the screen box of a character drawn at another level (lane eng-draw6, item 3).

Each run folder holds serial.txt, m1_state.txt and the stills pic-<m1_state address>-s<k>-<picture>.png that
s/fly_cmp1_copy.py saves (k counts the stills scenes of one image in disc order). On a still picture of a STILLS run
the E1 actor pass logs one line a drawn character (services/actor_e1.inc e1_lvl_box):
    E1 LVLBOX f <picture> c <index> base <base model> asked <level> drawn <level> model <model drawn> box x0 y0 x1 y1
Characters of the two runs are matched by base model and order among that base model's lines in the picture. A
character "changed level" when its drawn level differs from its match's (or is not 0 without a match). The allowed
region of a still is the union of the changed characters' boxes in both runs, grown by --pad pixels (default 2: the
box is the projected positions, a strip's edge pixels lie up to a pixel outside it). With a second base run, stills
where the two base runs differ (the run-to-run floor) are left out and counted.
PASS: every compared still has 0 differing pixels outside its allowed region (any of R, G, B; the RGB565 frame widened).
Exit 1 on FAIL, also when a run has no LVLBOX lines or no still is compared.
Control: a base disc with PIXCTL (one blue step on every character colour, levels off) against the base must FAIL
(no character changed level, every character's pixels differ)."""
import re, sys, collections
from pathlib import Path
import numpy as np
from PIL import Image

args = [a for a in sys.argv[1:] if not a.startswith('--')]
pad = 2
for a in sys.argv[1:]:
    if a.startswith('--pad='): pad = int(a.split('=')[1])
if len(args) < 2: sys.exit(__doc__)
RUN_RE = re.compile(r'CDISC RUN \d+ (\S+) PROG/(\S+)\.BIN')
BOX_RE = re.compile(r'E1 LVLBOX f (\d+) c (\d+) base (\d+) asked (\d+) drawn (\d+) model (\d+) box (-?\d+) (-?\d+) (-?\d+) (-?\d+)')


def boxes(run):
    """{(image index, k, picture): [(base, drawn level, box)]} from the serial (image 0 E1, 1 FIGHT)"""
    out = collections.defaultdict(list); scene = None; prog = None; seen = {}; counted = set()
    for line in (Path(run) / 'serial.txt').read_text(errors='replace').splitlines():
        m = RUN_RE.search(line)
        if m: scene, prog = m.group(1), m.group(2); continue
        m = BOX_RE.search(line)
        if not m or prog is None: continue
        img = {'E1': 0, 'FIGHT': 1}.get(prog)
        if img is None: continue
        if (scene, img) not in counted:
            counted.add((scene, img)); seen[img] = seen.get(img, -1) + 1
        f, c, base, asked, drawn, model, x0, y0, x1, y1 = map(int, m.groups())
        out[(img, seen[img], f)].append((base, drawn, (x0, y0, x1, y1)))
    return out


def stills(run):
    run = Path(run)
    addrs = [a.lower() for a in (run / 'm1_state.txt').read_text().strip().split(',')]
    out = {}
    for p in run.glob('pic-*.png'):
        m = re.match(r'pic-([0-9a-f]+)-s(\d+)-(\d+)\.png', p.name)
        if m and m.group(1) in addrs: out[(addrs.index(m.group(1)), int(m.group(2)), int(m.group(3)))] = p
    return out


def px(p): return np.asarray(Image.open(p).convert('RGB')).astype(np.int16)


def matched(a, b):
    """pairs (entry of a, entry of b or None), by base model and order among that base's entries"""
    byb = collections.defaultdict(list)
    for e in b: byb[e[0]].append(e)
    used = collections.Counter(); out = []
    for e in a:
        lst = byb.get(e[0], []); k = used[e[0]]; used[e[0]] += 1
        out.append((e, lst[k] if k < len(lst) else None))
    return out


B, L = stills(args[0]), stills(args[1])
B2 = stills(args[2]) if len(args) > 2 else None
BB, LB = boxes(args[0]), boxes(args[1])
fail = 0
if not BB or not LB:
    print('FAIL: no LVLBOX lines in', 'base' if not BB else 'levels', 'run'); fail = 1
keys = sorted(set(B) & set(L) & (set(B2) if B2 is not None else set(B)))
floor = compared = changed_stills = 0; total_in = total_out = 0; worst = (0, None)
for k in keys:
    a, b = px(B[k]), px(L[k])
    if B2 is not None and (np.abs(a - px(B2[k])).max(axis=2) > 0).any(): floor += 1; continue
    compared += 1
    diff = np.abs(a - b).max(axis=2) > 0
    allow = np.zeros(diff.shape, bool); h, w = diff.shape; nchanged = 0
    for e, f in matched(LB.get(k, []), BB.get(k, [])):
        if e[1] == (f[1] if f else 0): continue
        nchanged += 1
        for bx in [e[2]] + ([f[2]] if f else []):
            x0, y0, x1, y1 = bx
            if x1 < x0: continue
            x0, y0 = max(0, x0 - pad), max(0, y0 - pad); x1, y1 = min(w - 1, x1 + pad), min(h - 1, y1 + pad)
            if x1 >= x0 and y1 >= y0: allow[y0:y1 + 1, x0:x1 + 1] = True
    changed_stills += nchanged > 0
    n_in = int((diff & allow).sum()); n_out = int((diff & ~allow).sum())
    total_in += n_in; total_out += n_out
    if n_out > worst[0]: worst = (n_out, k)
    print('still %s: characters %d (changed level %d), differing pixels %d inside changed boxes, %d outside%s'
          % (k, len(LB.get(k, [])), nchanged, n_in, n_out, '  <- FAIL' if n_out else ''))
    fail |= n_out > 0
if not compared: print('FAIL: no still compared'); fail = 1
print('stills in both %d, left out on the floor %d, compared %d (with a level change %d): differing pixels inside %d, '
      'outside %d (worst %d at %s)' % (len(keys), floor, compared, changed_stills, total_in, total_out, worst[0], worst[1]))
print('RESULT', 'FAIL' if fail else 'PASS', '(a still differs outside the boxes of the characters drawn at another level)' if fail
      else '(every differing pixel lies in the box of a character drawn at another level)')
sys.exit(fail)
