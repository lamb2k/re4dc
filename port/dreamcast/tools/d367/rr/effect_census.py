#!/usr/bin/env python3
"""effect_census.py: per-room effect-set census gate (lane fix-r100-props26, 2026-10-26).

  effect_census.py <ref tree> <cand tree> <claims.tsv> [--json OUT]

Counts the effect sets of every route room archive (st1/*.dar, st2/*.dar) in two extracted disc trees (fullplay/fp_iso.py
extract: the reference release, Test 23, and the candidate) and fails when a candidate room has fewer of any kind than the
reference. The kinds, from the room payload:
  - EFF (src/game/eff_sys.cpp EffData, version 0xB): EST sequences, SST sequences, paths, effect models (EFM ids),
    effect pictures (texture ids);
  - ETS: placed etc-model effects (EtcSetData count);
  - ETM: effect model sub-files.
A drop is named "r100:EST" (and so on); a room archive gone from the candidate is "r100:room". claims.tsv has the
MEMBER-CENSUS format (<glob> TAB <set or commit> TAB <reason>); an unclaimed drop fails (exit 1). Gains are listed
only. Prints "EFFECT-CENSUS PASS|FAIL: n rooms, n drops, n claimed, n unclaimed" last.
"""
import fnmatch
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent.parent), str(HERE.parent), str(HERE)]
import room_smd as rs  # noqa: E402
import ps2_objects as po  # noqa: E402
from member_census import payload  # noqa: E402

KINDS = ('EST', 'SST', 'PATH', 'EFM', 'EFFTEX', 'ETS', 'ETM')


def eff_counts(b):
    """EFF block: counts of its five lists (each list starts with a u32 count)."""
    if len(b) < 48:
        return {}
    h = struct.unpack_from('<12I', b, 0)
    if h[0] != 0xB:
        return {'EFF_UNPARSED': 1}
    out = {}
    for name, o in (('EFFTEX', h[1]), ('EST', h[2]), ('SST', h[3]), ('PATH', h[4]), ('EFM', h[5])):
        out[name] = struct.unpack_from('<I', b, o)[0] if o and o + 4 <= len(b) else 0
    return out


def room_counts(dar):
    pay = payload(dar)
    c = dict.fromkeys(KINDS, 0)
    if pay is None:
        c['UNPARSED'] = 1
        return c
    for t, s, e in rs.tagged_entries(pay, '<'):
        tag = t.rstrip(b'\0').decode('latin1')
        body = pay[s:e]
        if tag == 'EFF':
            for k, v in eff_counts(body).items():
                c[k] = c.get(k, 0) + v
        elif tag == 'ETS' and len(body) >= 2:
            c['ETS'] += struct.unpack_from('<H', body, 0)[0]
        elif tag == 'ETM':
            try:
                c['ETM'] += len(list(po.etm_entries(body, '<')))
            except Exception:
                c['ETM'] += 1
    return c


def census(tree):
    out = {}
    for d in ('st1', 'st2'):
        for p in sorted((tree / d).glob('r*.dar')):
            out[p.stem] = room_counts(p.read_bytes())
    return out


def main():
    a = sys.argv[1:]
    js = None
    if '--json' in a:
        i = a.index('--json'); js = a[i + 1]; del a[i:i + 2]
    ref, cand, claims = Path(a[0]), Path(a[1]), Path(a[2])
    rows = []
    for ln in claims.read_text().splitlines():
        if ln.strip() and not ln.startswith('#'):
            p = ln.split('\t')
            rows.append((p[0], p[1] if len(p) > 1 else '?'))
    rc, cc = census(ref), census(cand)
    drops, res = [], []
    for room in sorted(rc):
        if room not in cc:
            drops.append(('%s:room' % room, 'room archive removed'))
            continue
        for k in sorted(set(rc[room]) | set(cc[room])):
            x, y = rc[room].get(k, 0), cc[room].get(k, 0)
            if y < x:
                drops.append(('%s:%s' % (room, k), '%d -> %d' % (x, y)))
            elif y > x:
                print('info: %s:%s %d -> %d' % (room, k, x, y))
    bad = 0
    for name, what in drops:
        who = next((s for g, s in rows if fnmatch.fnmatchcase(name, g)), None)
        res.append(dict(item=name, what=what, claimed_by=who))
        if who is None:
            bad += 1
            print('UNCLAIMED %s (%s)' % (name, what))
    if js:
        Path(js).write_text(json.dumps(dict(ref=rc, cand=cc, drops=res), indent=1))
    print('EFFECT-CENSUS %s: %d rooms, %d drops, %d claimed, %d unclaimed'
          % ('PASS' if bad == 0 else 'FAIL', len(rc), len(drops), len(drops) - bad, bad))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
