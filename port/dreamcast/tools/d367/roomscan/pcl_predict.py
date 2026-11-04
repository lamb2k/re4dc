"""per-cell LOD prediction (PREDICTED, roomscan round-2 hw fit): for each 8 m cell, the gain of giving that cell's
clusters the scan1 coarse levels + dec2 caps, against the level records it adds.
  hw delta per cell = 0.19 x (mean model ms over views, scan1+caps minus ship) + 0.0013 x (added level records)
Cells with a negative delta are picked (most negative first) up to a level-record budget."""
import json, math, os, re, sys
import numpy as np
sys.path.insert(0, r'\\wsl.localhost\Ubuntu-24.04\root\work\lanes\lod27\port\dreamcast\tools\d367\roomscan')
import roomscan as RS
D = os.environ.get("ROOMSCAN_DIR", "D:/RE4DC-Lanes/roomscan")
WP = r'\\wsl.localhost\Ubuntu-24.04\root\work\lanes\lod27\port\dreamcast\tools\d367\castgc\warps'
EV = os.environ.get("ROOMSCAN_CENSUS", "E:/RE4DC-Lanes/roomscan/ev/1104-0208-a5f2531f")
BUDGET = int(os.environ.get('PCL_BUDGET', '400'))

def records(W):
    per, seen = {}, set()
    for r in W['rows']:
        if r['c'] in seen: continue
        seen.add(r['c']); per[r['cell']] = per.get(r['cell'], 0) + len(r['levels'])
    return per

out = {}
for room in sys.argv[1:]:
    ship = '%s/conv/ship/%s' % (D, room) if os.path.exists('%s/conv/ship/%s/ps2-world.re4mesh' % (D, room)) else '%s/conv/base/%s' % (D, room)
    S = RS.read_world(ship); X = RS.read_world('%s/conv/scan1/%s' % (D, room))
    cg = '%s/cg-%s/run-output.txt' % (EV, room)
    bound = set(int(x, 16) for x in re.findall(r'PS2PART bind id=([0-9a-f]+)', open(cg, errors='replace').read())) if os.path.exists(cg) else set()
    RS.LIVE.clear(); RS.LIVE.update(i for i in bound if i < 250)
    cams = RS.cameras(S['rows'], os.path.join(WP, room + '.txt'))
    views = []
    for kind, pos, ang in cams:
        e0 = pos + np.array([0, 1600.0, 0])
        for yw in ([ang] if ang is not None else [0, math.pi / 2, math.pi, -math.pi / 2]):
            views.append((kind, e0 - 2000.0 * np.array([math.sin(yw), 0, math.cos(yw)]), yw))
    allc = {r['cell'] for r in X['rows']}
    shift = {k: 2 for k in allc}
    dms = {}
    far = []   # the farthest-reaching view: the sample view with the largest ship ms (caps matter at distance)
    for kind, eye, yw in views:
        a = RS.view(S['rows'], eye, yw); b = RS.view(X['rows'], eye, yw, shift)
        for k in set(a) | set(b):
            dms[k] = dms.get(k, 0.0) + (RS.cell_ms(b.get(k, [0, 0])) - RS.cell_ms(a.get(k, [0, 0]))) / len(views)
    rs, rx = records(S), records(X)
    cells = []
    for k in set(dms) | set(rx):
        drec = rx.get(k, 0) - rs.get(k, 0)
        cells.append(dict(cell=k, dmodel=round(dms.get(k, 0.0), 3), drec=drec, hw=round(0.19 * dms.get(k, 0.0) + 0.0013 * drec, 3)))
    cells.sort(key=lambda c: c['hw'])
    pick, used, tot = [], 0, 0.0
    for c in cells:
        if c['hw'] >= 0: break
        if used + max(c['drec'], 0) > BUDGET: continue
        pick.append(c['cell']); used += max(c['drec'], 0); tot += c['hw']
    whole = round(sum(c['hw'] for c in cells), 2)
    out[room] = dict(ship=ship, views=len(views), whole_room_scan1_hw=whole, picked=len(pick), records_added=used,
                     predicted_hw_ms=round(tot, 2), cells=pick, top=cells[:5])
    print('%s: whole-room scan1 hw %+.2f | per-cell pick %d cells, +%d records, predicted %+.2f ms (budget %d)' % (room, whole, len(pick), used, tot, BUDGET))
json.dump(out, open('%s/plans/pcl-predict.json' % D, 'w'), indent=1)
