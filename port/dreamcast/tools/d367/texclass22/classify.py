#!/usr/bin/env python3
"""classify.py (lane texclass22): decide every owner-unclassified texture key by measured use.

    classify.py --coverage coverage-status.json --pack tex.pak --quality mip-quality.tsv --origins scoped_origins.inc
                --run NAME=run-output.txt [...] --out-tsv T [--out-json J]

Unclassified = a normal pack row of the whole-pack policy with no original owner category (Codex feedback21).
Usage per key from TEX_USAGE_LOG=1 logs (texusage22 format), summed over runs as pixels per frame; a runtime key
counts for itself and, when it is a rect21 scoped key, for its original. Format and size from the pack descriptor.
Decisions: convert / not-worth / never / not-on-route / needs-work / already-mipped. Generator support = square
16-bit VQ, square 16-bit twiddled, square PAL4 (tools/mipmap_vq.py, mipmap_twiddled.py, mipmap_pal4.py).
"""
import argparse, collections, json, re, struct, sys

W = re.compile(r'texuse win: v=1 w=(\d+) room=(\w+) f=(\d+)\.\.(\d+) scenes=(\d+) present')
R = re.compile(r'texuse: w=(\d+) l=(\d+) s=(\d+) k=(\w+)-(\w+) tcw=(\w+) tsp=(\w+) h=(\d+) t=(\d+) a=(\d+) '
               r'b=(\d+)/(\d+)/(\d+)/(\d+)/(\d+) x=(\d+) r=(\d+)')
SRC = {0: 'unclassified', 1: 'world', 2: 'model', 3: 'ui', 4: 'effect'}
LIST = {0: 'OP', 2: 'TR', 4: 'PT'}
FMT = {0: 'RGB565', 1: 'ARGB1555', 2: 'ARGB4444', 4: 'PAL4', 5: 'PAL8'}
LAY = {0: 'linear', 1: 'twiddled', 2: 'vq'}
MIN_PX2 = 1000      # minified px per frame (summed over runs) worth a chain
MIN_SHARE2 = 0.25   # share of the drawn area at >= 2 texels per pixel
TINY_SIDE = 16      # 16x16 or smaller: a chain buys nothing


def read_pak(blob):
    magic, ver, count, ioff, doff = struct.unpack_from('<8s4I', blob, 0)
    out = {}
    for i in range(count):
        c, f, o, n = struct.unpack_from('<4I', blob, ioff + 16 * i)
        out['%08x-%08x' % (c, f)] = blob[o:o + n]
    return out


def desc(blob):
    h = struct.unpack_from('<8s10I', blob)
    if h[4] != 1:
        return dict(fmt='multi(%d)' % h[4], w=0, h=0, mip=False, layout='-', gen='no:multi')
    t = struct.unpack_from('<64s8I', blob, h[5])
    _, w, hh, fmt, off, size, flags, layout, res = t
    d = dict(fmt=FMT.get(fmt, str(fmt)), w=w, h=hh, mip=bool(flags & 4), layout=LAY.get(layout, str(layout)))
    if not (w == hh and w & (w - 1) == 0 and 8 <= w <= 1024):
        d['gen'] = 'no:non-square'
    elif fmt in (0, 1, 2) and layout in (1, 2):
        d['gen'] = 'yes'
    elif fmt == 4 and layout == 1:
        d['gen'] = 'yes'
    else:
        d['gen'] = 'no:%s-%s' % (d['fmt'], d['layout'])
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--coverage', required=True); ap.add_argument('--pack', required=True)
    ap.add_argument('--quality', required=True); ap.add_argument('--origins', action='append', default=[])
    ap.add_argument('--run', action='append', required=True)
    ap.add_argument('--out-tsv', required=True); ap.add_argument('--out-json')
    ap.add_argument('--out-seen', help='TSV of every drawn key (all owners) with usage, for the full-route ranking')
    a = ap.parse_args()
    cov = json.load(open(a.coverage))
    owners = {r['key']: r['original_owner_categories'] for r in cov['normal_rows']}
    uncl = [k for k, o in owners.items() if not o]
    origin = {}
    for p in a.origins:
        for l in open(p):
            v = re.findall(r'0x([0-9a-fA-F]{8})U', l)
            if len(v) == 4:
                origin['%s-%s' % (v[0].lower(), v[1].lower())] = '%s-%s' % (v[2].lower(), v[3].lower())
    pack = read_pak(open(a.pack, 'rb').read())
    quality = {}
    for l in open(a.quality):
        f = l.rstrip('\n').split('\t')
        if f[0] != 'key' and len(f) >= 10:
            quality[f[0]] = f[8] + (':' + f[9] if f[8] != 'pass' else '')
    agg = collections.defaultdict(lambda: dict(h=0.0, a=0.0, b=[0.0] * 5, rooms=set(), srcs=set(), lists=set(), runs=set(),
                                               rt=set()))
    runinfo = {}
    for spec in a.run:
        name, path = spec.split('=', 1)
        wins, rows = {}, []
        for l in open(path, errors='replace'):
            m = W.search(l)
            if m:
                if m.group(2) != '120' and int(m.group(4)) > int(m.group(3)):
                    wins[int(m.group(1))] = (m.group(2), int(m.group(5)))
                continue
            m = R.search(l)
            if m:
                rows.append(m.groups())
        scenes = sum(s for _, s in wins.values())
        runinfo[name] = dict(windows=len(wins), scenes=scenes, rooms=sorted({r for r, _ in wins.values()}))
        if not scenes:
            continue
        for g in rows:
            if int(g[0]) not in wins:
                continue
            rk = '%s-%s' % (g[3], g[4])
            for k in {rk, origin.get(rk, rk)}:
                e = agg[k]
                e['h'] += int(g[7]) / scenes; e['a'] += int(g[9]) / scenes
                for i in range(5):
                    e['b'][i] += float(g[10 + i]) / scenes
                e['rooms'].add('r' + wins[int(g[0])][0]); e['srcs'].add(SRC.get(int(g[2]), g[2]))
                e['lists'].add(LIST.get(int(g[1]), g[1])); e['runs'].add(name); e['rt'].add(rk)

    def usage(k):
        e = agg.get(k)
        if not e:
            return dict(seen='never-seen', cls='-', lists='-', rooms='-', px=0.0, draws=0.0, min2=0.0, share2=0.0), set()
        min2 = e['b'][2] + e['b'][3] + e['b'][4]
        return dict(seen='drawn', cls='/'.join(sorted(e['srcs'])), lists='/'.join(sorted(e['lists'])),
                    rooms=','.join(sorted(e['rooms'], key=lambda s: int(s[1:], 16))), px=e['a'], draws=e['h'], min2=min2,
                    share2=min2 / e['a'] if e['a'] else 0.0), set(e['srcs'])

    def decide(k, u, srcs, d):
        if u['seen'] != 'drawn':
            return 'not-on-route', 'not drawn in the ch1-2 route runs'
        if srcs <= {'ui', 'unclassified'}:
            return 'never', 'UI/screen submit path only'
        if d['mip']:
            return 'already-mipped', 'v4 carries a chain'
        if max(d['w'], d['h']) <= TINY_SIDE:
            return 'not-worth', 'tiny (<= %d side)' % TINY_SIDE
        if not (srcs & {'world', 'model'}):
            return 'not-worth', 'effect path only (overdraw, magnified)'
        if u['min2'] < MIN_PX2 or u['share2'] < MIN_SHARE2:
            return 'not-worth', 'not drawn small (min2 %.0f px, %.0f%%)' % (u['min2'], 100 * u['share2'])
        if d['gen'] != 'yes':
            return 'needs-work', d['gen']
        return 'convert', 'min2 %.0f px, %.0f%% >= 2 tpp' % (u['min2'], 100 * u['share2'])

    def row_for(k):
        d = desc(pack[k]) if k in pack else dict(fmt='absent', w=0, h=0, mip=False, layout='-', gen='no:absent')
        u, srcs = usage(k)
        dec, why = decide(k, u, srcs, d)
        r = dict(key=k, decision=dec, why=why, owner=','.join(owners.get(k) or ['unclassified']) if k in owners else 'not-normal-row')
        r.update(u)
        r.update(fmt=d['fmt'], layout=d['layout'], size='%dx%d' % (d['w'], d['h']), v4mip='yes' if d['mip'] else 'no',
                 v4gate=quality.get(k, '-'), gen=d['gen'])
        return r

    cols = ['key', 'decision', 'why', 'seen', 'cls', 'lists', 'rooms', 'px', 'draws', 'min2', 'share2', 'fmt', 'layout',
            'size', 'v4mip', 'v4gate', 'gen', 'owner']

    def write(path, rows):
        with open(path, 'w') as f:
            f.write('\t'.join(cols) + '\n')
            for r in rows:
                f.write('\t'.join('%.3f' % r[c] if c == 'share2' else '%.1f' % r[c] if isinstance(r[c], float) else str(r[c])
                                  for c in cols) + '\n')
    out = sorted((row_for(k) for k in uncl), key=lambda r: (-r['min2'], r['key']))
    write(a.out_tsv, out)
    if a.out_seen:
        seen = [k for k in agg if k in pack and k not in origin]
        write(a.out_seen, sorted((row_for(k) for k in seen), key=lambda r: (-r['min2'], r['key'])))
    summ = dict(unclassified=len(uncl), counts=dict(collections.Counter(r['decision'] for r in out)),
                drawn_unclassified=sum(r['seen'] == 'drawn' for r in out), seen_keys_all=len(agg), runs=runinfo,
                formats=dict(collections.Counter('%s/%s' % (r['fmt'], r['layout']) for r in out)))
    if a.out_json:
        json.dump(summ, open(a.out_json, 'w'), indent=1)
    print(json.dumps(dict((k, v) for k, v in summ.items() if k != 'runs')))


if __name__ == '__main__':
    main()
