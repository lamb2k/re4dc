#!/usr/bin/env python3
"""ps2leon contact sheets from bl_render.py's renders and counts.json:
  sheet-ingame.png  today / A / B / GC in the in-game shading model (texture only, unlit), six views
  sheet-shape.png   the same four lit, and with their triangle edges (where each spends its triangles)
Reads and writes $PS2LEON_WORK (leon_sources.py); fonts: $PS2LEON_FONT / $PS2LEON_FONT_BOLD (default Segoe UI).
"""
import json, os, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

R = Path(os.environ.get('PS2LEON_WORK', 'C:/Game Dev/Emulators/ps2leon-20261010'))
REN = R / 'renders'
counts = json.loads((R / 'counts.json').read_text())
F = os.environ.get('PS2LEON_FONT', 'C:/Windows/Fonts/segoeui.ttf')
FB = os.environ.get('PS2LEON_FONT_BOLD', 'C:/Windows/Fonts/segoeuib.ttf')
font = lambda s, b=False: ImageFont.truetype(FB if b else F, s)
ROWS = [('today', 'today'), ('A', 'a'), ('B', 'b'), ('GC', 'gc')]
TITLES = {'today': "Today's Leon (leon4k)", 'a': 'A: full PS2 Leon', 'b': 'B: hybrid, PS2 budget', 'gc': 'GameCube Leon'}
KNOB = {'today': 'play build (PS2_LEON=0)', 'a': 'PS2_LEON=1', 'b': 'PS2_LEON=2', 'gc': 'source data (reference)'}
H = 360
LABEL_W = 300


def tile(name, label):
    im = Image.open(REN / ('%s-%s.png' % (name, label))).convert('RGB')
    return im.resize((round(im.width * H / im.height), H), Image.LANCZOS)


def row_label(key):
    c = counts[key]
    p = c['parts']
    lines = [(TITLES[key], 26, True), (KNOB[key], 17, False), ('%s triangles' % format(c['triangles'], ','), 22, True),
             ('head/face/hair %s' % format(p['head'], ','), 18, False), ('torso/back/shoulders %s' % format(p['torso'], ','), 18, False),
             ('arms/hands %s' % format(p['arms'], ','), 18, False), ('legs/feet %s' % format(p['legs'], ','), 18, False)]
    w = c.get('work', {})
    if key == 'gc':
        lines.append(('%s vertices, %d GX batches' % (format(c['vertices'], ','), w['draw_batches']), 16, False))
    else:
        lines.append(('%s vertices, %d draw runs' % (format(w['positions'], ','), w['draw_runs']), 16, False))
        lines.append(('%s palette matrices' % w['palette_entries'], 16, False))
    im = Image.new('RGB', (LABEL_W, H), (34, 36, 40))
    d = ImageDraw.Draw(im)
    y = 18
    for text, size, bold in lines:
        d.text((16, y), text, font=font(size, bold), fill=(235, 235, 235) if bold else (200, 202, 206))
        y += size + (10 if size >= 22 else 6)
    return im


def sheet(columns, out, title, notes):
    tiles = {lab: [tile(n, lab) for n, _ in columns] for lab, _ in ROWS}
    widths = [t.width for t in tiles['today']]
    W = LABEL_W + sum(widths) + 8 * len(widths)
    top, bottom = 96, 34 + 24 * len(notes)
    img = Image.new('RGB', (W, top + (H + 8) * len(ROWS) + bottom), (22, 23, 26))
    d = ImageDraw.Draw(img)
    d.text((16, 12), title, font=font(30, True), fill=(240, 240, 240))
    x = LABEL_W
    for (n, head), w in zip(columns, widths):
        d.text((x + 8, 62), head, font=font(19, True), fill=(220, 220, 220))
        x += w + 8
    for j, (lab, key) in enumerate(ROWS):
        y = top + j * (H + 8)
        img.paste(row_label(key), (0, y))
        x = LABEL_W
        for t in tiles[lab]:
            img.paste(t, (x, y)); x += t.width + 8
    y = top + len(ROWS) * (H + 8) + 10
    for n in notes:
        d.text((16, y), n, font=font(17), fill=(190, 192, 196)); y += 24
    img.save(out)
    print(out, img.size)


common = ['All four posed in the same captured game pose (leon-source bones), same camera per column, same 512 atlas and hair pair textures.',
          'A and B keep the skeleton, bones, bind matrices, roles and textures; only the render geometry changes (logic untouched).']
sheet([('flat-front', 'front'), ('flat-back', 'back'), ('flat-side', 'right side'), ('flat-game', 'play camera (over the shoulder)'),
       ('flat-hair', 'hair, rear three-quarter'), ('flat-face', 'face, front three-quarter')],
      R / 'sheet-ingame.png', 'ps2leon: Leon arms in the in-game shading (texture only, unlit, culling off)',
      ['In-game shading model of the coarse owner path: texture x constant white (no lighting), hair alpha-blended with the I4 mask. Blender EEVEE, offline.',
       'The two close-ups hide the knife (role 2, drawn only while Leon holds it), which crosses the face in this captured pose.'] + common)
sheet([('clay-front', 'shape front'), ('clay-back', 'shape back'), ('wire-front', 'edges front'), ('wire-back', 'edges back'),
       ('wire-game', 'edges, play camera'), ('wire-hair', 'edges hair'), ('wire-face', 'edges face')],
      R / 'sheet-shape.png', 'ps2leon: shape and where the triangles go (untextured, lit; triangle edges)',
      ['Untextured and lit: the silhouette and faceting the unlit in-game draw hides. Edge views: where each mesh spends its triangles. Close-ups hide the knife (role 2).'] + common)
