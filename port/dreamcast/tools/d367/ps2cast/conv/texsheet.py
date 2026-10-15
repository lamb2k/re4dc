import sys, struct
sys.path[:0] = ['//wsl.localhost/Ubuntu-24.04/root/probe/lanes-20261014/ps2cast/tree/port/dreamcast/tools', '//wsl.localhost/Ubuntu-24.04/root/probe/lanes-20261014/ps2cast/tree/tools']
import convert_tpl, drs, numpy as np
from PIL import Image, ImageDraw
I = '//wsl.localhost/Ubuntu-24.04/root/probe/lanes/ps2cast/inputs/'
O = '//wsl.localhost/Ubuntu-24.04/root/probe/lanes-20261014/ps2cast/work/conv/'
rows = [('trap-em2a-00', 'em2a', 5), ('trap-em2a-02', 'em2a', 9), ('bat-em29-00', 'em29', 5), ('crawler-em2e-00', 'em2e', 5),
        ('crawler-em2e-01', 'em2e', 6), ('fish-em27-00', 'em27', 5), ('snake-em24-00', 'em24', 6), ('boat-pl0f-00', 'pl0f', 6)]
H = 260; tiles = []
for name, arch, tpl in rows:
    g = drs.Drs(open(I + arch + '.drs', 'rb').read())
    tims = convert_tpl.parse_tpl(g.entries[tpl - 4][1])
    gcims = [Image.fromarray(np.asarray(convert_tpl.decode_image(t), np.uint8).reshape(t.height, t.width, 4)).convert('RGB') for t in tims]
    ps2 = Image.open(O + name + '/atlas.png').convert('RGB')
    parts = gcims + [ps2]
    sc = [min(1.0, (H - 20) / p.height) for p in parts]
    w = sum(int(p.width * s) + 8 for p, s in zip(parts, sc)) + 10
    t = Image.new('RGB', (max(w, 400), H), (40, 40, 40)); d = ImageDraw.Draw(t); x = 4
    for i, (p, s) in enumerate(zip(parts, sc)):
        q = p.resize((max(1, int(p.width * s)), max(1, int(p.height * s))))
        t.paste(q, (x, 18)); d.text((x, 2), ('GC img%d %dx%d' % (i, p.width, p.height)) if i < len(gcims) else 'PS2 atlas %dx%d' % p.size, fill=(255, 255, 0)); x += q.width + 8
    d.text((t.width - 160, 2), name, fill=(0, 255, 255)); tiles.append(t)
W = max(t.width for t in tiles); sheet = Image.new('RGB', (W, H * len(tiles)), (0, 0, 0))
for i, t in enumerate(tiles): sheet.paste(t, (0, H * i))
sheet.save('C:/Game Dev/Emulators/ps2cast-20261014/conv-texture-sheet.png'); print(sheet.size)
sheet.resize((W // 2, H * len(tiles) // 2)).save('C:/Users/lambd/AppData/Local/Temp/p2conv_sheet.png')
