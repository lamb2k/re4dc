#!/usr/bin/env python3
"""drawcost.py <serial.txt> [--json <out.json>]: lane eng-draw1's reader of the renderer's cost lines.

Reads one console-disc serial log (tools/engine/build_console_disc.sh; the images of lane eng-draw1 and later):
  - E1-family scenes (LEON, HILL, FIGHT): the ROW lines (the drawing row: draw us per picture) and the renderer's DC lines
    (render/draw_cost.inc: DC PHASE, DC COUNT, one T DCP line a picture (DCP before): the spans between its stamps and four counters);
  - bench scenes: the WINDOW lines (draw mean) and the DCB lines (TIMING, PHASE, COUNT) of each window.
Prints, per scene, the drawing row (mean, p99, worst over pictures 41-640) split into the stamped phases, the remainder
(drawing time outside the stamped spans: list and scene finish), and the counters.

Lab arms (render/draw_cost.h). Bench windows "/X": each arm window's draw mean minus the mean of the same room's base
windows (no arm, no delay) is the cost of one more run of that phase. E1 boot sets DLA / DLB interleave the arms over
the pictures: each arm picture's draw (and each phase span) minus the mean of the nearest base pictures before and after
(picture % M == 0) is that picture's extra cost; the arm's mean over its pictures is reported.

The control: arm D (2 ms of busy waiting inside the world's opaque pass) must read 2.0 ms (within 0.1) in the drawing
row and in the worldOP span, in the bench and in set B; the stamped spans must never exceed the picture's drawing row.
A failed control prints FAIL and the exit status is 1; a control that is absent from the log is reported as absent."""
import json, re, sys
from collections import defaultdict

PH = ['select', 'begin', 'sky', 'preworld', 'worldOP', 'actors', 'worldPT', 'listgap', 'worldTR', 'TRextra', 'hud']
SET_ARMS = {1: (6, {1: 'S stage twice', 2: 'C copy twice', 3: 'Q select twice', 4: 'H HUD twice', 5: 'N near not a number'}),
            2: (5, {1: 'B weight sets twice', 2: 'L normals lit twice', 3: 'E actor emission twice', 4: 'D 2 ms delay (control)'}),
            3: (4, {1: 'X world without a stage', 2: 'V world copy v2', 3: 'G world near clamp (no clipping)'})}
BITS = {1: 'S', 2: 'C', 4: 'Q', 8: 'H', 16: 'N', 32: 'B', 64: 'L', 128: 'E', 256: 'D', 512: 'K', 1024: 'X', 2048: 'V', 4096: 'G', 8192: 'Z'}
LO, HI = 41, 640


def stats(v):
    v = sorted(v)
    if not v: return None
    return dict(n=len(v), mean=sum(v) / len(v), p99=v[len(v) - 1 - len(v) // 100], worst=v[-1])


def census(count):
    """The invisible share from the census counters (means a picture). The culled sign is the one the depth check says
    is the far side of the characters: on closed meshes the culled (back) faces are farther, so their mean 1/w is
    smaller. The world and the characters use the same rule (one screen convention)."""
    g = lambda k: count.get(k, {}).get('mean', 0)
    out = {}
    ineg, ipos = g('v_a_iw_neg'), g('v_a_iw_pos')
    nneg, npos = g('v_a_neg') + g('v_a_nc_neg'), g('v_a_pos') + g('v_a_nc_pos')   # culling-off triangles by sign too
    mneg = ineg / nneg if nneg else 0; mpos = ipos / npos if npos else 0
    aculled = 'n' if mneg < mpos else 'p'   # characters: the farther sign is their back side
    # the world: the sign its headers' culling removes. PVR mode 3 culls clockwise triangles; on the screen (y down)
    # (x1-x0)(y2-y0)-(x2-x0)(y1-y0) > 0 is clockwise, so mode 3 removes the positive sign, mode 2 the negative one
    wculled = 'p' if g('v_w_cullmode_cw') >= g('v_w_cullmode_ccw') else 'n'
    out['depth_check'] = dict(mean_iw_neg=mneg / 16777216, mean_iw_pos=mpos / 16777216, character_back_sign='negative' if aculled == 'n' else 'positive',
                              world_culled_sign='positive (CW headers)' if wculled == 'p' else 'negative (CCW headers)')
    for side, p, culled in (('world', 'v_w_', wculled), ('characters', 'v_a_', aculled)):
        tris = g(p + 'tris'); off = g(p + 'off'); nocull = g(p + 'nocull')
        back = g(p + ('neg' if culled == 'n' else 'pos')); front = g(p + ('pos' if culled == 'n' else 'neg'))
        area = g(p + 'area_nocull') + g(p + ('area_pos' if culled == 'n' else 'area_neg'))
        out[side] = dict(triangles=tris, offscreen=off, back_facing=back, culling_off=nocull, kept=front + nocull,
                         kept_area_px=area, overdraw=area / 307200.0,
                         dead_strips=g(p + 'deadstrips_' + culled), dead_corners=g(p + 'deadcorners_' + culled),
                         dead_vertices=g(p + ('deadvtx_' if side == 'world' else 'deadpos_') + culled),
                         dead_normals=g(p + 'deadnrm_' + culled) if side == 'characters' else None,
                         cullmode_cw=g(p + 'cullmode_cw'), cullmode_ccw=g(p + 'cullmode_ccw'))
    c = out['characters']; cs = aculled
    c['back_facing_drawn'] = g('v_a_nc_' + ('neg' if cs == 'n' else 'pos'))   # culling off in their headers: drawn
    c['back_facing_area_px'] = g('v_a_nc_area_' + ('neg' if cs == 'n' else 'pos'))
    c['if_culled_dead_strips'] = g('v_a_cdeadstrips_' + cs); c['if_culled_dead_corners'] = g('v_a_cdeadcorners_' + cs)
    c['if_culled_dead_positions'] = g('v_a_cdeadpos_' + cs)
    out['world']['clipper_front'] = g('v_w_clip_front'); out['world']['clipper_behind'] = g('v_w_clip_behind')
    out['world']['clipper_crossing'] = g('v_w_clip_cross'); out['translucent_area_px'] = g('v_tr_area')
    out['translucent_overdraw'] = g('v_tr_area') / 307200.0
    return out


def scenes(lines):
    cur = None; out = []
    for l in lines:
        m = re.match(r'CDISC RUN \d+ (\S+) (\S+)', l)
        if m:
            cur = dict(name=m.group(1), prog=m.group(2), lines=[]); out.append(cur); continue
        if l.startswith('CDISC SUMMARY BEGIN'): cur = None
        if cur is not None: cur['lines'].append(l)
    return out


def e1_scene(sc):
    draw = {}; dcp = {}; phase = {}; count = {}; lab = 0
    for l in sc['lines']:
        if l.startswith('ROW ') and ' draw ' in l:
            t = l.split(); draw[int(t[1])] = int(t[t.index('draw') + 1])
        elif l.startswith('DCP ') or l.startswith('T DCP '):   # 'T DCP' since 28a0821ca's successor (kept out of the report)
            t = [int(x) for x in l.split()[1 if l[0] == 'D' else 2:]]; dcp[t[0]] = t[1:]
        elif l.startswith('DC BEGIN set '):
            lab = int(l.split()[3])
        elif l.startswith('DC PHASE '):
            m = re.match(r'DC PHASE (\S+) m(\d+) p(\d+) w(\d+)@(\d+)', l)
            phase[m.group(1)] = dict(mean=int(m.group(2)), p99=int(m.group(3)), worst=int(m.group(4)), at=int(m.group(5)))
        elif l.startswith('DC COUNT '):
            m = re.match(r'DC COUNT (\S+) m(\d+) w(\d+)@(\d+)', l)
            count[m.group(1)] = dict(mean=int(m.group(2)), worst=int(m.group(3)), at=int(m.group(4)))
    if not dcp: return None
    pics = [i for i in range(LO, HI + 1) if i in draw and i in dcp]
    res = dict(name=sc['name'], set=lab, pictures=len(pics), faults=[])
    over = [i for i in pics if sum(dcp[i][:11]) > draw[i] + 2]
    if over: res['faults'].append('stamped spans exceed the drawing row on %d pictures (first %d)' % (len(over), over[0]))
    if not lab:
        d = stats([draw[i] / 1000 for i in pics]); res['draw'] = d
        res['phases'] = {p: stats([dcp[i][k] / 1000 for i in pics]) for k, p in enumerate(PH)}
        res['remainder'] = stats([(draw[i] - sum(dcp[i][:11])) / 1000 for i in pics])
        w = max(pics, key=lambda i: draw[i])
        res['worst_picture'] = dict(picture=w, draw=draw[w] / 1000, spans={p: dcp[w][k] / 1000 for k, p in enumerate(PH)},
                                    w_corners=dcp[w][11], w_cliptris=dcp[w][12], a_corners=dcp[w][13], a_pos=dcp[w][14])
        res['counts'] = count
        res['per_picture'] = {i: dict(draw=draw[i], spans=dcp[i][:11], w_corners=dcp[i][11], w_cliptris=dcp[i][12],
                                      a_corners=dcp[i][13], a_pos=dcp[i][14]) for i in pics}
        return res
    if lab == 4:   # the census (DLV): counts only, never timing
        res['census'] = census(count)
        return res
    M, names = SET_ARMS[lab]
    base = [i for i in pics if i % M == 0]
    arms = {}
    for r, nm in names.items():
        dd = []; dp = defaultdict(list); dc = defaultdict(list)
        for i in pics:
            if i % M != r: continue
            b0 = max([b for b in base if b < i], default=None); b1 = min([b for b in base if b > i], default=None)
            bs = [b for b in (b0, b1) if b is not None]
            if not bs: continue
            dd.append((draw[i] - sum(draw[b] for b in bs) / len(bs)) / 1000)
            for k, p in enumerate(PH): dp[p].append((dcp[i][k] - sum(dcp[b][k] for b in bs) / len(bs)) / 1000)
            for k, c in enumerate(('w_corners', 'w_cliptris', 'a_corners', 'a_pos')):
                dc[c].append(dcp[i][11 + k] - sum(dcp[b][11 + k] for b in bs) / len(bs))
        arms[nm] = dict(pictures=len(dd), draw=stats(dd), spans={p: sum(v) / len(v) for p, v in dp.items() if v},
                        counts={c: sum(v) / len(v) for c, v in dc.items() if v})
    res['arms'] = arms
    res['base_draw'] = stats([draw[i] / 1000 for i in base])
    return res


def bench_scene(sc):
    win = {}; cur = None
    for l in sc['lines']:
        m = re.match(r'DCB (\d+) BEGIN arms ([0-9a-f]+)', l)
        if m: win[int(m.group(1))] = dict(arms=int(m.group(2), 16), timing={}, phase={}, count={}); continue
        m = re.match(r'DCB (\d+) TIMING (\S+) m(\d+) w(\d+)', l)
        if m:
            w = win.setdefault(int(m.group(1)), dict(arms=None, timing={}, phase={}, count={}))
            w['timing'][m.group(2)] = dict(mean=int(m.group(3)), worst=int(m.group(4))); continue
        m = re.match(r'DCB (\d+) PHASE (\S+) m(\d+) p(\d+) w(\d+)@(\d+)', l)
        if m: win[int(m.group(1))]['phase'][m.group(2)] = dict(mean=int(m.group(3)), p99=int(m.group(4)), worst=int(m.group(5))); continue
        m = re.match(r'DCB (\d+) COUNT (\S+) m(\d+) w(\d+)', l)
        if m: win[int(m.group(1))]['count'][m.group(2)] = dict(mean=int(m.group(3)), worst=int(m.group(4))); continue
        m = re.match(r'WINDOW (\d+) (\S+) arm (\S)(.*?) draw mean ([\d.]+) p99 ([\d.]+) worst ([\d.]+)', l)
        if m:
            w = win.setdefault(int(m.group(1)), dict(arms=None, timing={}, phase={}, count={}))
            c = re.search(r'content \[([^\]]*)\]', l)
            w.update(room=m.group(2), arm=m.group(3), flags=m.group(4).strip(), mean=float(m.group(5)), p99=float(m.group(6)),
                     worst=float(m.group(7)), content=c.group(1) if c else '')
    if not win: return None
    res = dict(name=sc['name'], windows=win, arms={}, faults=[])
    for room in sorted({w.get('room') for w in win.values() if w.get('room')}):
        # base: no lab arm, no flag, survey arm 0, the content steps of today's defaults (character levels 3, effect cap 2)
        base = [w for w in win.values() if w.get('room') == room and not w['arms'] and not w.get('flags') and w.get('arm') == '0'
                and w.get('content') == 'L3E2']
        if not base: continue
        bm = sum(w['mean'] for w in base) / len(base)
        bph = {p: sum(w['phase'].get(p, {}).get('mean', 0) for w in base) / len(base) / 1000 for p in PH}
        res['arms'].setdefault(room, {})['base'] = dict(windows=len(base), draw=bm, spread=max(w['mean'] for w in base) - min(w['mean'] for w in base),
                                                       phases=bph, counts={k: v['mean'] for k, v in base[0]['count'].items()},
                                                       timing={k: v['mean'] / 1000 for k, v in base[0]['timing'].items()})
        for k, w in sorted(win.items()):
            if w.get('room') != room or w in base or w.get('flags') or w.get('arm') != '0': continue
            nm = ''.join(BITS.get(b, '?') for b in sorted(BITS) if (w['arms'] or 0) & b) or ('content ' + w.get('content', ''))
            res['arms'][room][nm] = dict(window=k, draw=w['mean'] - bm,
                                         spans={p: w['phase'].get(p, {}).get('mean', 0) / 1000 - bph[p] for p in PH})
            if nm == 'Z': res['arms'][room][nm]['census'] = census(w['count'])
    return res


def main():
    path = sys.argv[1]; js = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
    lines = open(path, errors='replace').read().splitlines()
    out = []; fail = 0
    for sc in scenes(lines):
        r = bench_scene(sc) if 'BENCH' in sc['prog'] else e1_scene(sc)
        if not r:
            if any(l.startswith('ROW ') and ' draw ' in l for l in sc['lines']) and not any(' draw  not drawn' in l for l in sc['lines']):
                print('==', sc['name']); print('  FAIL drawn scene without DC lines (an image before lane eng-draw1, or the report cut)'); fail = 1
            continue
        out.append(r)
        print('==', r['name'])
        for f in r['faults']: print('  FAIL', f); fail = 1
        if 'windows' in r:
            for room, arms in r['arms'].items():
                b = arms['base']
                print('  %s base: draw %.2f ms (%d windows, spread %.2f); phases %s' % (room, b['draw'], b['windows'], b['spread'],
                      ' '.join('%s %.2f' % (p, v) for p, v in b['phases'].items() if v >= .005)))
                for nm, a in arms.items():
                    if nm == 'base': continue
                    if nm == 'Z': print('    census:', json.dumps(a['census'])); continue
                    big = sorted(a['spans'].items(), key=lambda x: -abs(x[1]))[:2]
                    print('    arm %-3s +%.3f ms draw (%s)' % (nm, a['draw'], ', '.join('%s %+.3f' % x for x in big)))
                    if nm == 'D':
                        ok = abs(a['draw'] - 2) <= .1 and abs(a['spans']['worldOP'] - 2) <= .1
                        print('    control D (2 ms in worldOP): %s' % ('PASS' if ok else 'FAIL')); fail |= not ok
        elif r['set'] == 4:
            print('  census:', json.dumps(r['census']))
        elif r['set']:
            print('  set %c, base pictures draw mean %.2f' % ('ABCV'[r['set'] - 1], r['base_draw']['mean']))
            for nm, a in r['arms'].items():
                big = sorted(a['spans'].items(), key=lambda x: -abs(x[1]))[:2]
                print('    %-26s %3d pictures: draw %+.3f ms (p99 %+.3f) (%s) counters %s' % (nm, a['pictures'], a['draw']['mean'], a['draw']['p99'],
                      ', '.join('%s %+.3f' % x for x in big), ' '.join('%s %+.0f' % x for x in a['counts'].items())))
                if nm.startswith('D '):
                    ok = abs(a['draw']['mean'] - 2) <= .1 and abs(a['spans']['worldOP'] - 2) <= .1
                    print('    control D (2 ms in worldOP): %s' % ('PASS' if ok else 'FAIL')); fail |= not ok
        else:
            d = r['draw']
            print('  draw  m%.2f p%.2f w%.2f ms (%d pictures)' % (d['mean'], d['p99'], d['worst'], d['n']))
            for p, s in r['phases'].items():
                if s['worst'] >= .005: print('    %-9s m%6.2f p%6.2f w%6.2f' % (p, s['mean'], s['p99'], s['worst']))
            s = r['remainder']; print('    %-9s m%6.2f p%6.2f w%6.2f' % ('remainder', s['mean'], s['p99'], s['worst']))
            wp = r['worst_picture']; print('  worst picture %d: %.2f ms; %s' % (wp['picture'], wp['draw'], ' '.join('%s %.2f' % x for x in wp['spans'].items() if x[1] >= .005)))
            print('  counters (mean / worst): ' + ', '.join('%s %d/%d' % (k, v['mean'], v['worst']) for k, v in r['counts'].items()))
    if js:
        for r in out: r.pop('per_picture', None)
        json.dump(out, open(js, 'w'), indent=1)
    sys.exit(fail)


if __name__ == '__main__':
    main()
