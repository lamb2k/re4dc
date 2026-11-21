"""wepcheck.py <run> <addr> <SCENE>:<k> <ref run> <REFSCENE>:<k>: Leon's weapon found in the stills (lane eng-look1).

  <run>        a Flycast STILLS run folder: serial.txt and pic-<addr>-s<k>-NNNN.png (tools as hudcheck.py: the runner names
               each still by the image's m1_state address, k = that image's scene run on the disc, NNNN = the picture)
  <addr>       the image's m1_state address (sh-elf-nm <elf> | grep _m1_state)
  SCENE:k      the scene whose stills are checked (its name in SCENES.TXT, e.g. LEONS) and its k in the still names
  <ref run> REFSCENE:k   the same scene run with the weapon undrawn (boot file NOWEP: CNWLS, CNWHS, CNWFS in
               tools/engine/build_console_disc.sh); the same image, so the same address
Exit 0 PASS, 1 FAIL, 2 nothing to check.

The image says, for every still it hands over, what the hosted code decided and where the weapon is
("E1 WEPSTILL n tick t present p visible v drawn d box x0 y0 x1 y1", services/weapon_draw.inc: the box of the weapon's
own positions skinned on its skeleton palette and projected with the camera; -1 when not on screen). History: the first
run (commit 2a2233484, lane eng-look1 F2) gave the box of the part spheres, several times the weapon's silhouette; the
rule below failed LEONS 4 and FIGHTS 18 stills on the 8% share although every differing pixel lay in the box. The box
was made the positions' box; the rule's numbers were not changed. The rule, stated before the
first run (2026-11-21), per still of SCENE with the reference still of the same picture number:
  1. the image's own facts: drawn == visible (the weapon drawn exactly when the hosted code says);
  2. visible and on screen (box area at least 100 pixels after clipping to 640 x 480): the weapon's pixels are found in
     its box: at least 40 pixels and at least 8% of the box differ from the reference by more than 24 (sum of the
     absolute R, G, B differences), and at least 90% of all the picture's differing pixels lie in the box grown by 8;
  3. not visible: at most 0.05% of the picture's pixels differ from the reference (nothing drawn where nothing should be).
At least 3 stills must pass rule 2, else the verdict is "nothing to check" (exit 2). Any still failing 1, 2 or 3 fails.
The controls: the reference checked against itself (SCENE = REFSCENE: no weapon pixels, rule 1 fails on drawn 0), and the
NOWEP scene put in place of SCENE (the same).
The pixel rule's own control (lane eng-draw3, the gate's note): boot file WEPSHIFT (services/weapon_draw.inc) draws the
weapon from its palette moved 400 mm along world x while the box it reports stays the true one; the weapon is drawn and
counted as drawn (rule 1 holds), so rule 2 must fail on every still where it is on screen. Disc:
build_console_disc.sh --scenes LEONS,CNWLS --put E1LS/WEPSHIFT; check: wepcheck.py <run> <addr> LEONS:0 <run> CNWLS:1 (both scenes run the E1 image: k 0 and 1)."""
import re, sys
from pathlib import Path
import numpy as np
from PIL import Image

DIFF, MIN_PIX, MIN_FRAC, INSIDE, GROW, QUIET, MIN_AREA, MIN_STILLS = 24, 40, 0.08, 0.90, 8, 0.0005, 100, 3


def scene_lines(serial, name):
    """the E1 WEPSTILL facts of the scene NAME's run (between its CDISC RUN and CDISC RESULT lines), by picture"""
    out, on = {}, False
    for s in serial.splitlines():
        if re.match(r'^CDISC RUN \d+ %s ' % re.escape(name), s): on = True; out = {}; continue
        if on and re.match(r'^CDISC RESULT \d+ %s ' % re.escape(name), s): break
        m = on and re.match(r'^E1 WEPSTILL (\d+) tick (\d+) present (\d+) visible (\d+) drawn (\d+) box (-?\d+) (-?\d+) (-?\d+) (-?\d+)$', s.strip())
        if m:
            v = list(map(int, m.groups()))
            out[v[0]] = dict(tick=v[1], present=v[2], visible=v[3], drawn=v[4], box=v[5:9])
    return out


def stills(run, addr, k):
    return {int(f.stem.split('-')[3]): f for f in run.glob(f'pic-{addr}-s{k}-*.png')}


def main(a):
    if len(a) != 5: sys.exit(__doc__)
    run, addr, (name, k), ref, (rname, rk) = Path(a[0]), a[1].lower(), a[2].split(':'), Path(a[3]), a[4].split(':')
    facts = scene_lines((run / 'serial.txt').read_text(errors='replace'), name)
    rfacts = scene_lines((ref / 'serial.txt').read_text(errors='replace'), rname)
    pics, rpics = stills(run, addr, k), stills(ref, addr, rk)
    print(f'# wepcheck {run} {name}:s{k} against {ref} {rname}:s{rk}: {len(facts)} WEPSTILL lines, {len(pics)} stills, '
          f'reference {len(rpics)}; rule: diff>{DIFF}, in box >= {MIN_PIX} px and {MIN_FRAC:.0%}, inside >= {INSIDE:.0%} '
          f'(grown {GROW}), hidden <= {QUIET:.2%}')
    fails = found = 0
    for n in sorted(facts):
        f = facts[n]
        if n not in pics or n not in rpics:
            print(f'pic {n:4} tick {f["tick"]:4}: still missing (run {n in pics}, reference {n in rpics}): FAIL'); fails += 1; continue
        img = np.asarray(Image.open(pics[n]).convert('RGB')).astype(int)
        rimg = np.asarray(Image.open(rpics[n]).convert('RGB')).astype(int)
        diff = np.abs(img - rimg).sum(-1) > DIFF
        total = int(diff.sum())
        why = []
        if f['drawn'] != f['visible']: why.append(f'drawn {f["drawn"]} != visible {f["visible"]}')
        x0, y0, x1, y1 = f['box']
        cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(640, x1 + 1), min(480, y1 + 1)
        area = max(0, cx1 - cx0) * max(0, cy1 - cy0)
        note = ''
        if f['visible'] and x0 != -1 and area >= MIN_AREA:
            inbox = int(diff[cy0:cy1, cx0:cx1].sum())
            gx0, gy0, gx1, gy1 = max(0, cx0 - GROW), max(0, cy0 - GROW), min(640, cx1 + GROW), min(480, cy1 + GROW)
            inside = int(diff[gy0:gy1, gx0:gx1].sum())
            frac = inbox / area
            ok = inbox >= MIN_PIX and frac >= MIN_FRAC and (total == 0 or inside / total >= INSIDE)
            note = f'box {x0},{y0}-{x1},{y1} area {area}: in box {inbox} ({frac:.1%}), inside grown {inside} of {total}'
            if ok and not why: found += 1
            if not ok: why.append('weapon pixels not found in its box' if inbox < MIN_PIX or frac < MIN_FRAC else
                                  'differences outside the weapon box')
        elif not f['visible']:
            note = f'hidden: {total} pixels differ'
            if total > QUIET * 640 * 480: why.append('pixels differ while the weapon is hidden')
        else:
            note = f'visible, off screen or small (box {x0},{y0}-{x1},{y1}): not judged on pixels'
        print(f'pic {n:4} tick {f["tick"]:4} present {f["present"]} visible {f["visible"]} drawn {f["drawn"]}: {note}: '
              f'{"FAIL (" + "; ".join(why) + ")" if why else "ok"}')
        fails += bool(why)
    verdict = 'FAIL' if fails else 'PASS' if found >= MIN_STILLS else 'NOTHING TO CHECK'
    print(f'wepcheck {name}: {found} stills with the weapon found, {fails} failing: {verdict}')
    return 1 if fails else 0 if found >= MIN_STILLS else 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
