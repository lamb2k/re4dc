#!/usr/bin/env python3
"""ps2leon in-game sheet: Flycast stills of the knob-off control (today's Leon), arm A and arm B from the look
gallery's look.sh (warp + freeze; the same frame in every column), beside the GameCube reference frame (look gallery
gc/, Dolphin 1x). Rows: r100start (full frame and the "leon" close-up crop) and r101F (full frame and the
"leon-r101F" crop), crops as tools/d367/look/shots.json, scaled 2x (nearest) for the close-ups.

  make_dc_sheet.py <gallery dir with dc/<column>/<shot>.png> <look gallery dir (gc/)> <out.png>
Column labels read $PS2LEON_WORK/counts.json (counts.py).
"""
import json, os, sys, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

g, lg, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
counts = json.loads((Path(os.environ.get('PS2LEON_WORK', 'C:/Game Dev/Emulators/ps2leon-20261010')) / 'counts.json').read_text())
F = os.environ.get('PS2LEON_FONT', 'C:/Windows/Fonts/segoeui.ttf')
FB = os.environ.get('PS2LEON_FONT_BOLD', 'C:/Windows/Fonts/segoeuib.ttf')
font = lambda s, b=False: ImageFont.truetype(FB if b else F, s)
COLS = [('gc', 'GameCube (Dolphin 1x)', 'reference frame', None),
        ('today', "Today's Leon", 'PS2_LEON=0 (play build)', 'today'),
        ('A', 'A: full PS2 Leon', 'PS2_LEON=1', 'a'),
        ('B', 'B: hybrid, PS2 budget', 'PS2_LEON=2', 'b')]
ROWS = [('r100start', None, 'r100 first outdoor view (after the call)'),
        ('r100start', (140, 150, 300, 300), 'Leon close-up (r100start crop)'),
        ('r101F', None, 'r101 square view F (DC: Ganados on; GC: villagers off)'),
        ('r101F', (130, 160, 370, 420), 'Leon close-up (r101F crop)')]
BAND = (0, 60, 640, 420)
TW = 480


def load640(p):
    im = Image.open(p).convert('RGB')
    return im if im.size == (640, 480) else im.resize((640, 480), Image.BILINEAR)


def cell(col, shot, crop):
    p = (lg / 'gc' / (shot + '.png')) if col == 'gc' else (g / 'dc' / col / (shot + '.png'))
    if not p.exists():
        return None
    im = load640(p).crop(crop or BAND)
    h = round(TW * im.height / im.width)
    return im.resize((TW, h), Image.NEAREST if crop else Image.LANCZOS)


cells = [[cell(c, s, cr) for c, _, _, _ in COLS] for s, cr, _ in ROWS]
heights = [max(x.height for x in row if x is not None) for row in cells]
LW, TOP, GAP = 250, 120, 8
W = LW + (TW + GAP) * len(COLS)
H = TOP + sum(h + GAP for h in heights) + 70
S = Image.new('RGB', (W, H), (22, 23, 26))
d = ImageDraw.Draw(S)
d.text((16, 10), 'ps2leon: in-game stills (Flycast framebuffer, same frozen frame per row)', font=font(28, True), fill=(240, 240, 240))
for k, (c, title, knob, key) in enumerate(COLS):
    x = LW + k * (TW + GAP)
    d.text((x + 6, 52), title, font=font(20, True), fill=(230, 230, 230))
    sub = knob
    if key:
        cc = counts[key]
        sub += '   %s triangles, %d draw runs' % (format(cc['triangles'], ','), cc['work']['draw_runs'])
    d.text((x + 6, 80), sub, font=font(15), fill=(190, 192, 196))
y = TOP
for (s, cr, title), row, h in zip(ROWS, cells, heights):
    for i, line in enumerate(textwrap.wrap(title, 24)):
        d.text((14, y + 8 + 24 * i), line, font=font(17, True), fill=(225, 225, 225))
    for k, im in enumerate(row):
        x = LW + k * (TW + GAP)
        if im is None:
            d.text((x + 10, y + h // 2), 'missing', font=font(18), fill=(255, 90, 90))
        else:
            S.paste(im, (x, y))
    y += h + GAP
d.text((16, y + 8), 'Builds: route-build.sh twin of the play recipe at ad67e568 (look gallery play knobs, DBG_WARP=1); stills by tools/d367/look/look.sh '
       '(warp, freeze, one Flycast). Close-ups 2x nearest.', font=font(15), fill=(190, 192, 196))
d.text((16, y + 32), 'GameCube frames: re4-assets-private/look-gallery-20261010/gc (the GC r101F has the villagers off; Leon framing matches).',
       font=font(15), fill=(190, 192, 196))
S.save(out)
print(out, S.size)
