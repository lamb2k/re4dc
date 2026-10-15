import sys
from pathlib import Path
from PIL import Image, ImageDraw
E = Path('C:/Flycast-Evidence/re4-dreamcast/items-20261014')
runs = sys.argv[2:]
TW, TH = 213, 160
rows = []
for r in runs:
    sh = sorted((E / r / 'capture' / 'shots').glob('t*/frames/fb0.png'))
    rows.append((r, sh))
n = max(len(s) for _, s in rows)
sheet = Image.new('RGB', (90 + n * TW, len(rows) * TH), (0, 0, 0))
d = ImageDraw.Draw(sheet)
for i, (r, sh) in enumerate(rows):
    d.text((4, i * TH + 4), r, fill=(255, 255, 255))
    for k, f in enumerate(sh):
        im = Image.open(f).convert('RGB'); im.thumbnail((TW, TH))
        sheet.paste(im, (90 + k * TW, i * TH))
        d.text((92 + k * TW, i * TH + 2), f.parts[-3], fill=(255, 255, 0))
sheet.save(sys.argv[1]); print(sheet.size)
