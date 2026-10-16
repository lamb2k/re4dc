"""sheet2.py: still sheets for worldtest16 phase 2 (Windows Python, PIL).
  sheet2.py land                 -> TEST16-r101-cross.png (t15/int world32 | test 16 C set, same ELF w16mrT, same frozen tick)
  sheet2.py terrain [room ...]   -> TERRAIN-<room>.png (A current | T terrain-only), rows = the room's two cameras
The frozen frame is the first pair of consecutive identical scene shots (freeze 400). MODELLED ms from price-terrain.json
(room-budget console fit, 1.1 ms per 1k on-screen world TA vertices): MODELLED, not measured."""
import os, re, sys, json
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageStat
OUT = r'C:\Game Dev\Emulators\worldtest-20261016'
EW = r'C:\Flycast-Evidence\re4-dreamcast\worldtest-20261016'
EL = r'C:\Flycast-Evidence\re4-dreamcast\wt16land-20261016'
F = ImageFont.truetype('arial.ttf', 15); FB = ImageFont.truetype('arialbd.ttf', 17)
CW, CH = 640, 480


def kind(im):
    r, g, b = ImageStat.Stat(im.resize((64, 48))).mean
    if b > 60 and r < 40 and g < 40:
        return 'hang'
    return 'black' if r + g + b < 30 else 'scene'


def pick(rd):
    d = os.path.join(rd, 'capture', 'shots')
    shots = sorted(os.listdir(d))
    ims = [(t, Image.open(os.path.join(d, t, 'frames', 'fb0.png')).convert('RGB')) for t in shots]
    best = None
    for (t0, a), (t1, b) in zip(ims, ims[1:]):
        if kind(a) == 'scene' and kind(b) == 'scene':
            diff = ImageChops.difference(a, b).convert('L')
            if sum(1 for p in diff.getdata() if p > 8) < 200:
                best = (t0, a); break
    log = open(os.path.join(rd, 'capture', 'run-output.txt'), encoding='latin-1').read()
    m = re.search(r'warp: frozen at tick (\d+)', log)
    wv = re.findall(r'WORLDVERT room=(\w+) want=\d+ loaded=(\d+)', log)
    vr = re.findall(r'VRAM_ROOM[^\n]*', log)
    return best, (m.group(1) if m else None), wv, vr


def sheet(title, cols, rows, path, notes=()):
    """cols: [(header, sub)], rows: [(caption, [run dir per col])]."""
    n = len(cols)
    S = Image.new('RGB', (n * (CW + 10) + 10, 100 + len(rows) * (CH + 72) + 22 * len(notes)), (24, 24, 24))
    d = ImageDraw.Draw(S)
    d.text((10, 8), title, font=F, fill=(230, 230, 230))
    for i, (h, sub) in enumerate(cols):
        d.text((10 + i * (CW + 10), 32), h, font=FB, fill=(255, 220, 120))
        d.text((10 + i * (CW + 10), 54), sub, font=F, fill=(200, 200, 200))
    y = 82
    stats = []
    for cap, runs in rows:
        d.text((10, y), cap, font=FB, fill=(150, 210, 255)); y += 26
        ims = []
        for i, rd in enumerate(runs):
            try:
                best, tick, wv, vr = pick(rd)
            except FileNotFoundError:
                best, tick, wv, vr = None, None, [], []
            im = best[1].resize((CW, CH)) if best else Image.new('RGB', (CW, CH), (80, 0, 0))
            ims.append(im); S.paste(im, (10 + i * (CW + 10), y))
            lv = ','.join('%s:%s' % x for x in wv) or '-'
            d.text((14 + i * (CW + 10), y + CH + 4), '%s tick %s shot %s WORLDVERT %s' % (os.path.basename(rd), tick,
                   best[0] if best else None, lv), font=F, fill=(255, 255, 0))
        for i in range(1, len(ims)):
            diff = ImageChops.difference(ims[0], ims[i]).convert('L')
            pct = 100.0 * sum(1 for q in diff.getdata() if q > 16) / (CW * CH)
            stats.append((cap, i, pct))
            d.text((14 + i * (CW + 10), y + CH + 24), 'pixels differing >16 vs column 1: %.1f%%' % pct, font=F, fill=(255, 160, 160))
        y += CH + 46
    for t in notes:
        d.text((10, y), t, font=F, fill=(230, 230, 230)); y += 22
    S.save(path); print(path, stats)
    return stats


def land():
    sheet('TEST 16 r101 world: in game at the village cross (Flycast JIT, trace ELF w16mrT = lane/worldtest16 5197fa04, '
          'WORLD_VERT=1 LEVEL=5, View Full, fog on); same ELF and frozen tick, only the r101 world data differs',
          [('t15/int data (wv32r101 = world32 as in test 15)', 'stake crossbar / pyre plank / fence rails cut by the reducer'),
           ('test 16 data (wt16r101 = version C)', 'world32 + bins kept + vertex box at the stake, pyre and house fence')],
          [('village cross (-7914,0,2000) yaw 1.57, crowd alerted, freeze 400', [os.path.join(EL, 'm-still-o'), os.path.join(EL, 'm-still-n2')])],
          os.path.join(OUT, 'TEST16-r101-cross.png'))


CAMS = {'r100': ['door from r101 (96524,-6771,-8536) yaw 5.50', 'em12 (-83950,830,-32960) yaw 0.39'],
        'r102': ['door from r101 (-19691,0,-19088) yaw .785', 'merchant spot em18 (-12210,-8720,38420) yaw 2.75'],
        'r103': ['door from r101 (-47609,12,7084) yaw 2.36', 'em12 (-27380,40,-18290) yaw 1.18'],
        'r104': ['door from r106 (-3443,0,12338) yaw 2.75', 'em22 (-6040,1010,8570) yaw 2.36'],
        'r105': ['door from r107 (-33040,0,-1792) yaw 1.96', 'em15 (32440,2840,-7090) yaw 5.50'],
        'r106': ['door from r103 (11141,-893,-120) yaw 1.18', 'em2a (113010,-8260,-33390) yaw 1.18'],
        'r107': ['door from r104 (29683,-13,-28512) yaw 1.96', 'em12 (74980,180,-34790) yaw 3.93'],
        'r108': ['door from r102 (-43905,-38,-14737) yaw 1.96', 'worst view em16 (-1390,10000,-19250) yaw 1.96'],
        'r10a': ['door from r109 (-58327,7346,69786) yaw 1.18', 'worst view em12 (41850,-10000,89330) yaw 1.18']}
CAMID = {'r102': ('c1', 'c2b'), 'r106': ('c1', 'c3')}


def terrain(rooms):
    P = json.load(open(os.path.join(OUT, 'price-terrain.json')))
    for room in rooms:
        a, t = P['%s:A' % room], P['%s:T' % room]
        kept = t['corners'] / a['corners']
        cols = [('A current world (t15/int)', 'MODELLED world %.1f ms p90, %.1f worst view' % (a['ms_p90'], a['ms_max'])),
                ('T terrain/rock-only reduction', 'kept %.3f of corners | MODELLED world %+.2f ms p90 (%+.2f worst view)' % (
                    kept, t['ms_p90'] - a['ms_p90'], t['ms_max'] - a['ms_max']))]
        rows = []
        for ci, cam in enumerate(CAMID.get(room, ('c1', 'c2'))):
            msc = ' | MODELLED this view A %.1f, T %.1f ms' % (a['ms_cams'][ci], t['ms_cams'][ci]) if a['ms_cams'] else ''
            rows.append(('camera %d: %s%s' % (ci + 1, CAMS[room][ci], msc),
                         [os.path.join(EW, 't-%s-%s-%s' % (room, cam, arm)) for arm in 'AT']))
        sheet('TERRAIN %s: in game (Flycast JIT, trace ELF w16mrT, WORLD_VERT=1 LEVEL=5, View Full, fog on), same frozen tick per '
              'row; only the world data differs (T adds ps2-wv5.re4mesh: ladder --mode terrain --keep-walk-mm 1500 --keep-pieces)' % room,
              cols, rows, os.path.join(OUT, 'TERRAIN-%s.png' % room))


if __name__ == '__main__':
    if sys.argv[1] == 'land':
        land()
    else:
        terrain(sys.argv[2:] or list(CAMS))
