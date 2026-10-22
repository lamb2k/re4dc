#!/usr/bin/env python3
"""texusage.py (lane texusage22): rank textures by measured use from TEX_USAGE_LOG=1 run logs.

    texusage.py --run NAME=run-output.txt [...] --quality mip-quality.tsv --room-select room-select.tsv
                --origins scoped_origins.inc [--recover ledger.json] [--foliage ledger.json] --out-tsv T --out-md M

Each run log holds "texuse win:" / "texuse:" lines (native_ui.cpp tamat::usage_dump). Per texture key (the runtime /
pack key; the original key from scoped_origins.inc when the key is scoped) it sums over every window of every run:
headers (draws), triangles, clipped screen area and the area by texels per pixel (<1, 1-2, 2-4, 4-8, >=8). Areas are
reported per scene (pixels per frame, averaged over the run's scenes, then summed over runs). Minified = >= 2 texels
per pixel (where a mip level would be selected); strongly minified = >= 4.
Mip status from the v3 pack's mip-quality.tsv (pass = mipped, held = held + reasons; absent = not a candidate).
"""
import argparse, collections, json, re, sys

SRC = {0: 'unclassified', 1: 'world', 2: 'model', 3: 'ui', 4: 'effect'}
LIST = {0: 'OP', 2: 'TR', 4: 'PT'}
W = re.compile(r'texuse win: v=1 w=(\d+) room=(\w+) f=(\d+)\.\.(\d+) scenes=(\d+) present=(\d+) rows=(\d+) overflow=(\d+) invalid=(\d+) orphan=(\d+)')
R = re.compile(r'texuse: w=(\d+) l=(\d+) s=(\d+) k=(\w+)-(\w+) tcw=(\w+) tsp=(\w+) h=(\d+) t=(\d+) a=(\d+) b=(\d+)/(\d+)/(\d+)/(\d+)/(\d+) x=(\d+) r=(\d+)')


def load_origins(p):
    m = {}
    for l in open(p):
        v = re.findall(r'0x([0-9a-fA-F]{8})U', l)
        if len(v) == 4:
            m['%s-%s' % (v[0].lower(), v[1].lower())] = '%s-%s' % (v[2].lower(), v[3].lower())
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', action='append', required=True)
    ap.add_argument('--quality', required=True)
    ap.add_argument('--room-select', required=True)
    ap.add_argument('--origins', required=True)
    ap.add_argument('--recover')
    ap.add_argument('--foliage')
    ap.add_argument('--out-tsv', required=True)
    ap.add_argument('--out-md')
    a = ap.parse_args()
    origins = load_origins(a.origins)
    inverse = collections.defaultdict(list)
    for sk, ok in origins.items():
        inverse[ok].append(sk)
    quality = {}
    for l in open(a.quality):
        f = l.rstrip('\n').split('\t')
        if f[0] == 'key' or len(f) < 10:
            continue
        quality[f[0]] = (f[8], f[9], f[1], f[2])
    rsel = {}
    for l in open(a.room_select):
        if l.startswith('#') or l.startswith('key\t'):
            continue
        f = l.rstrip('\n').split('\t')
        if len(f) >= 5:
            rsel[f[0]] = f[4]
    recover = set()
    if a.recover:
        for k in json.load(open(a.recover))['keys']:
            recover.add(k['scoped']); recover.add(k['original'])
    foliage = {}
    if a.foliage:
        for k in json.load(open(a.foliage))['keys']:
            foliage[k['key']] = k['room']; foliage[k['original']] = k['room']
    agg = collections.defaultdict(lambda: dict(h=0, t=0, a=0.0, b=[0.0] * 5, x=0.0, rooms=set(), runs=set(), lists=set(),
                                               srcs=set(), tsp=set()))
    runinfo = {}
    classtot = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0] * 7))
    for spec in a.run:
        name, path = spec.split('=', 1)
        wins = {}
        rows = []
        for l in open(path, errors='replace'):
            m = W.search(l)
            if m:
                # gameplay windows only: the title (r120) and movie windows (no native frame advanced) are left out
                if m.group(2) == '120' or int(m.group(4)) <= int(m.group(3)):
                    continue
                wins[int(m.group(1))] = dict(room=m.group(2), scenes=int(m.group(5)), present=int(m.group(6)),
                                             rows=int(m.group(7)), overflow=int(m.group(8)), invalid=int(m.group(9)),
                                             orphan=int(m.group(10)))
                continue
            m = R.search(l)
            if m:
                rows.append(m.groups())
        scenes = sum(w['scenes'] for w in wins.values())
        runinfo[name] = dict(windows=len(wins), scenes=scenes, rooms=sorted({w['room'] for w in wins.values()}),
                             overflow=sum(w['overflow'] for w in wins.values()), orphan=sum(w['orphan'] for w in wins.values()),
                             invalid=sum(w['invalid'] for w in wins.values()), rows=len(rows))
        if not scenes:
            continue
        for g in rows:
            w, l, s, crc, fnv, tcw, tsp, h, t, ar = g[:10]
            b = [float(v) for v in g[10:15]]
            x, r = float(g[15]), int(g[16])
            win = wins.get(int(w))
            if not win:
                continue
            key = '%s-%s' % (crc, fnv)
            if key == '00000000-00000000':
                # resolved=1 with no key = an untextured row; 0 = a texture address no cache entry owns
                key = 'untex' if r else 'tcw:%s' % tcw[-6:]
            e = agg[key]
            e['h'] += int(h) / scenes; e['t'] += int(t) / scenes; e['a'] += int(ar) / scenes; e['x'] += x / scenes
            for i in range(5):
                e['b'][i] += b[i] / scenes
            e['rooms'].add('r' + win['room']); e['runs'].add(name); e['lists'].add(LIST.get(int(l), l))
            e['srcs'].add(SRC.get(int(s), s)); e['tsp'].add(tsp)
            c = classtot[name]['%s/%s' % (SRC.get(int(s), s), LIST.get(int(l), l))]
            c[0] += int(ar) / scenes; c[1] += int(h) / scenes
            for i in range(5):
                c[2 + i] += b[i] / scenes
    out = []
    for k, e in agg.items():
        if k.startswith('tcw:') or k == 'untex':
            status, reason, fmt, side = 'unresolved', '-', '-', '-'
        else:
            # The pack keys of this texture: itself, and the rect21 scoped keys whose original it is (the release
            # recipe binds original keys; the v3 pack's scoped worlds carry scoped copies of them).
            cands = [k] + inverse.get(k, [])
            qs = [(c, quality[c]) for c in cands if c in quality]
            if any(q[0] == 'pass' for _, q in qs):
                status = 'mipped' if all(q[0] == 'pass' for _, q in qs) else 'mipped-partly'
            elif qs:
                status = 'held'
            else:
                status = 'not-candidate'
            reasons = sorted({r for _, q in qs if q[0] != 'pass' for r in q[1].split(',') if r not in ('-', '', 'room-select')})
            reasons += sorted({'room-select:' + rsel[c] for c in cands if c in rsel})
            reason = ','.join(reasons) or '-'
            fmt = '/'.join(sorted({q[2] for _, q in qs})) or '-'
            side = '/'.join(sorted({q[3] for _, q in qs})) or '-'
            if len(cands) > 1:
                fmt += ' (scoped %d)' % (len(cands) - 1)
        tsp = sorted(e['tsp'])[0]
        tw, th = 8 << ((int(tsp, 16) >> 3) & 7), 8 << (int(tsp, 16) & 7)
        minA = e['b'][2] + e['b'][3] + e['b'][4]
        out.append(dict(key=k, scoped=(';'.join(inverse.get(k, [])) or '-'), cls='/'.join(sorted(e['srcs'])), lists='/'.join(sorted(e['lists'])),
                        rooms=','.join(sorted(e['rooms'])), runs=','.join(sorted(e['runs'])), px=e['a'], draws=e['h'],
                        tris=e['t'], min2=minA, min4=e['b'][3] + e['b'][4],
                        share2=minA / e['a'] if e['a'] else 0, share4=(e['b'][3] + e['b'][4]) / e['a'] if e['a'] else 0,
                        tpp=e['x'] / e['a'] if e['a'] else 0, size='%dx%d' % (tw, th), status=status, reason=reason,
                        fmt=fmt, recover=('pilot42' if any(c in recover for c in [k] + inverse.get(k, [])) else ''),
                        foliage=next((foliage[c] for c in [k] + inverse.get(k, []) if c in foliage), '')))
    out.sort(key=lambda r: -r['min2'])
    cols = ['key', 'scoped', 'cls', 'lists', 'rooms', 'runs', 'px', 'draws', 'tris', 'min2', 'min4', 'share2', 'share4', 'tpp',
            'size', 'fmt', 'status', 'reason', 'recover', 'foliage']
    with open(a.out_tsv, 'w') as f:
        f.write('rank\t' + '\t'.join(cols) + '\n')
        for i, r in enumerate(out, 1):
            f.write('%d\t' % i + '\t'.join(('%.1f' % r[c] if isinstance(r[c], float) and c not in ('share2', 'share4', 'tpp')
                                            else '%.3f' % r[c] if isinstance(r[c], float) else str(r[c])) for c in cols) + '\n')
    ct = {n: {k: dict(px=round(v[0]), screens=round(v[0] / 307200.0, 2), draws=round(v[1], 1),
                      share2=round((v[4] + v[5] + v[6]) / v[0], 3) if v[0] else 0,
                      share4=round((v[5] + v[6]) / v[0], 3) if v[0] else 0) for k, v in sorted(d.items())}
          for n, d in classtot.items()}
    json.dump(dict(runs=runinfo, keys=len(out), classes=ct), sys.stdout, indent=1)
    print()


if __name__ == '__main__':
    main()
