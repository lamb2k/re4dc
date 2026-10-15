#!/usr/bin/env python3
"""vram_gate.py: the VRAM gaps gate of the CLAUDE.md graphics memory rule (lane vram12 D4, 2026-10-15).

    python3 vram_gate.py <run-output.txt>... [--ps2lib DIR] [--known known-issues.txt] [--seg NAME] [--json OUT]

Reads a game log (benchmark or full-play segment) and
  - prints each room visit's VRAM use from the "vram room:" / "vram gaps:" lines (native_ui.cpp VRAM_ROOM_LOG=1): the
    minimum free texture RAM and largest free block, the peak working set (pinned), the last sample's pinned / dynamic /
    other bytes, uploads after the room-entry preload (gameplay disc reads), evictions, fragmentation retries and the
    visit's gap counters;
  - fails on any VRAM budget refusal, thrash-guard refusal under eviction pressure (guard_p), "no contiguous block"
    failure, rejected texture package (tex_rej: a pack read error or a package the KOS heap or the validator refused),
    gameplay upload in a room with a resident list (D5: vram/resident/r<room>.tsv, ROOM_RESIDENT=1 preloads it, so
    any upload after the room-entry preload is a disc re-read the list does not cover; full-play checks report them),
    a KOS heap failure (D5: "Out of memory" from sbrk, the native model slab or a motion file read refused: the texture
    cache holds the KOS heap's descriptors, TEX_META_EVICT keeps a reserve and the slab is allocated before the
    preload), or GameCube effect picture ("vram gc-fx:" key) that ps2lib/INDEX.tsv does not list with ps2_source=NONE
    (the known gaps). A key is looked up through ps2lib/effects-tex/KEYS.tsv (vram/fx_keys.py) and reported with its
    INDEX row: NOT_CONVERTED (the PS2 has the picture, the converter skipped it), converted (the pack should have the
    PS2 picture: wrong tex.pak), or no row (an effect file ps2lib does not index yet, e.g. an enemy's own EFF).
    Thrash-guard skips without pressure are the EFFECT_ROOM per-frame load cap (the texture loads a frame later):
    counted, not failed.
  - A log without VRAM_ROOM_LOG lines (builds before test 12) is judged on what it has: "native UI VRAM: ...
    rejects=N" (cumulative) and the "no contiguous block" lines fail; "native effect guard: resident_only_skips=N"
    does not say whether the cache was under pressure, and GameCube effect pictures are not logged: both are noted.
D5 (10-15) also reports the TEX_META_EVICT counters: meta (uploads evicted for KOS heap) and the visit's least KOS
heap headroom (kos).
Known issues (fullplay/known-issues.txt format: builds|category|segment|regex|why) excuse a failure whose text matches.
Categories: vram (refusal, guard_p, nocontig), gc-fallback (gc-fx). Exit 0 = PASS, 1 = FAIL.
fullplay/fp_check.py calls analyse() for every segment (nocontig=False there: its RULES already fail those lines).
Numbers come from Flycast runs (MODELLED); the counters are exact event counts of the run.
"""
import json, os, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PS2LIB_DEFAULTS = ['/mnt/c/Game Dev/Emulators/re4-assets-private/ps2lib', 'C:/Game Dev/Emulators/re4-assets-private/ps2lib']

KV = re.compile(r'(\w+)=(-?[0-9a-z]+)')
GCFX = re.compile(r'^vram gc-fx: r=([0-9a-f]+) f=(\d+) key=([0-9a-f]{8}-[0-9a-f]{8})')
OLD_VRAM = re.compile(r'^native UI VRAM: frame=\d+ .*rejects=(\d+)')
OLD_GUARD = re.compile(r'^native effect guard: frame=\d+ resident_only_skips=(\d+)')
NOCONTIG = re.compile(r'no contiguous block')
KOSFAIL = re.compile(r'^Out of memory\. Requested sbrk_base|^native model slab: allocation failed|^motion key read retry')
GAP_FIELDS = ('refusals', 'guard', 'guard_p', 'nocontig', 'latched', 'absent', 'gc_fx', 'dropped', 'fx_dropped', 'tex_rej', 'snd_fail',
              'meta')
ROOM_FIELDS = ('pinned', 'dynamic', 'other', 'free', 'largest', 'min_free', 'min_largest', 'peak_pinned', 'loads', 'evicted', 'retries')
INF = 1 << 32


def resident_rooms():
    """Rooms with a ROOM_RESIDENT list (vram/resident/r<room>.tsv), as the log writes them ('101')."""
    return {p.stem[1:] for p in (HERE / 'resident').glob('r*.tsv')}


def ps2lib_root(arg=None):
    for p in [arg, os.environ.get('RE4DC_PS2LIB')] + PS2LIB_DEFAULTS:
        if p and (Path(p) / 'INDEX.tsv').exists():
            return Path(p)
    return None


def load_index(root):
    """{key: [(room, gc_id, ps2_source, dc_format, gate)]} through KEYS.tsv; None without the files."""
    if not root or not (root / 'effects-tex' / 'KEYS.tsv').exists():
        return None
    rows = {}
    for ln in (root / 'INDEX.tsv').read_text(encoding='utf-8').splitlines()[1:]:
        f = ln.split('\t')
        if len(f) >= 9 and f[0] == 'effects-tex':
            rows[f[2]] = (f[1], f[2], f[3], f[4], f[8])
    out = {}
    for ln in (root / 'effects-tex' / 'KEYS.tsv').read_text(encoding='utf-8').splitlines()[1:]:
        f = ln.split('\t')
        if len(f) >= 3:
            out.setdefault(f[0], []).append(rows.get(f[2], (f[1], f[2], '?', '?', '?')))
    return out


def classify(key, index):
    """(known: bool, text) for a GameCube-picture effect key."""
    if index is None:
        return False, 'GameCube effect picture %s (ps2lib INDEX.tsv / effects-tex/KEYS.tsv not found: cannot tell a known gap)' % key
    rows = index.get(key)
    if not rows:
        return False, 'GameCube effect picture %s has no ps2lib row (effect file not indexed, e.g. an enemy EFF)' % key
    if all(r[2] == 'NONE' for r in rows):
        return True, 'GameCube effect picture %s: no PS2 counterpart (ps2lib NONE %s)' % (key, ','.join(r[1] for r in rows))
    r = next(r for r in rows if r[2] != 'NONE')
    if r[3] == 'NOT_CONVERTED':
        return False, 'GameCube effect picture %s: PS2 picture %s not converted (ps2lib %s %s)' % (key, r[2], r[1], r[4])
    return False, 'GameCube effect picture %s: ps2lib has a PS2 conversion (%s, %s) but the GameCube one was drawn (tex.pak?)' % (key, r[1], r[3])


def fields(ln):
    return {k: v for k, v in KV.findall(ln)}


def num(d, k, default=0):
    try:
        return int(d[k])
    except (KeyError, ValueError):
        return default


def analyse(lines, index=None, nocontig=True, resident=None):
    """dict(rooms=[visit rows], failures=[dict(cat, what, line)], known_gaps=[...], notes=[...], new_format=bool).
    resident: rooms whose gameplay uploads fail (resident_rooms()); None = reported only."""
    visits = {}       # (room, start frame) -> row
    order = []
    gcfx = {}         # key -> (room, line no, line)
    old_rej = old_guard = 0
    old_rej_line = ''
    nocontig_lines = []
    kos_lines = []
    new_format = False
    for i, ln in enumerate(lines, 1):
        if ln.startswith('vram room: '):
            d = fields(ln)
            if 'r' not in d or 'f' not in d or 'frames' not in d:
                continue
            new_format = True
            r, at, f, frames = d['r'], d.get('at', '?'), num(d, 'f'), num(d, 'frames')
            k = (r, f - frames)
            v = visits.get(k)
            if v is None:
                v = visits[k] = dict(room=r, start=f - frames, samples=0, min_free=INF, min_largest=INF, peak_pinned=0,
                                     last={}, gaps={x: 0 for x in GAP_FIELDS}, closed=False, gap_lines={},
                                     preload_loads=None, preload_evicted=None, loads=0, evicted=0, retries=0)
                order.append(k)
            v['samples'] += 1
            vals = {x: num(d, x, None) for x in ROOM_FIELDS}
            if at != 'exit':
                v['last'] = dict(vals, at=at, f=f)
            if vals['min_free'] is not None:
                v['min_free'] = min(v['min_free'], vals['min_free'])
            if vals['min_largest'] is not None:
                v['min_largest'] = min(v['min_largest'], vals['min_largest'])
            v['peak_pinned'] = max(v['peak_pinned'], vals['peak_pinned'] or 0)
            for x in ('loads', 'evicted', 'retries'):
                if vals[x] is not None:
                    v[x] = max(v[x], vals[x])
            if at == 'preload' and vals['loads'] is not None:
                v['preload_loads'], v['preload_evicted'] = vals['loads'], vals['evicted']
            v['closed'] = v['closed'] or at == 'exit'
            continue
        if ln.startswith('vram gaps: '):
            d = fields(ln)
            # the matching "vram room:" line precedes it: the newest visit of this room
            k = next((x for x in reversed(order) if x[0] == d.get('r')), None)
            if k is None:
                continue
            v = visits[k]
            for name in GAP_FIELDS:
                val = num(d, name, 0)
                if val > v['gaps'][name]:
                    v['gaps'][name] = val
                    v['gap_lines'].setdefault(name, 'line %d: %s' % (i, ln.strip()[:220]))
            if 'gc_fx' in d and num(d, 'gc_fx', 0) < 0:
                v['gaps']['gc_fx'] = -1
            v['snd_used'] = num(d, 'snd_used', None)
            if num(d, 'kos', 0) > 0:
                v['min_kos'] = min(v.get('min_kos', INF), num(d, 'kos'))
            if d.get('at') != 'preload' and v['preload_loads'] is not None:
                v.setdefault('play_line', 'line %d: %s' % (i, ln.strip()[:220]))
            continue
        m = GCFX.match(ln)
        if m:
            gcfx.setdefault(m.group(3), (m.group(1), i, ln.strip()))
            continue
        m = OLD_VRAM.match(ln)
        if m and int(m.group(1)) > old_rej:
            old_rej = int(m.group(1))
            old_rej_line = 'line %d: %s' % (i, ln.strip()[:220])
        m = OLD_GUARD.match(ln)
        if m:
            old_guard = max(old_guard, int(m.group(1)))
        if NOCONTIG.search(ln):
            nocontig_lines.append('line %d: %s' % (i, ln.strip()[:220]))
        if KOSFAIL.match(ln):
            kos_lines.append('line %d: %s' % (i, ln.strip()[:220]))
    out = dict(rooms=[], failures=[], known_gaps=[], notes=[], new_format=new_format)
    for k in order:
        v = visits[k]
        out['rooms'].append(dict(room=v['room'], start=v['start'], samples=v['samples'], closed=v['closed'],
                                 min_free=None if v['min_free'] == INF else v['min_free'],
                                 min_largest=None if v['min_largest'] == INF else v['min_largest'],
                                 peak_pinned=v['peak_pinned'], last=v['last'], gaps=v['gaps'], snd_used=v.get('snd_used'),
                                 loads=v['loads'], evicted=v['evicted'], retries=v['retries'], min_kos=v.get('min_kos'),
                                 play_loads=None if v['preload_loads'] is None else v['loads'] - v['preload_loads'],
                                 play_evicted=None if v['preload_evicted'] is None else v['evicted'] - v['preload_evicted']))
        g = v['gaps']
        if g['refusals']:
            out['failures'].append(dict(cat='vram', what='r%s: %d VRAM budget refusal(s) in the visit from frame %d' % (v['room'], g['refusals'], v['start']),
                                        line=v['gap_lines']['refusals']))
        if g['guard_p']:
            out['failures'].append(dict(cat='vram', what='r%s: %d thrash-guard refusal(s) under eviction pressure (effect sprites not drawn) in the visit from frame %d'
                                        % (v['room'], g['guard_p'], v['start']), line=v['gap_lines']['guard_p']))
        if nocontig and g['nocontig']:
            out['failures'].append(dict(cat='vram', what='r%s: %d "no contiguous block" failure(s) in the visit from frame %d' % (v['room'], g['nocontig'], v['start']),
                                        line=v['gap_lines']['nocontig']))
        if g['tex_rej']:
            out['failures'].append(dict(cat='vram', what='r%s: %d rejected texture package(s) (pack read error, KOS heap or validator) in the visit from frame %d'
                                        % (v['room'], g['tex_rej'], v['start']), line=v['gap_lines']['tex_rej']))
        pl = out['rooms'][-1]['play_loads']
        if pl and resident is not None and v['room'] in resident:
            out['failures'].append(dict(cat='vram', what='r%s: %d upload(s) after the room-entry preload in a room with a resident list '
                                        '(disc re-reads: add the keys to vram/resident/r%s.tsv, resident_keys.py list)' % (v['room'], pl, v['room']),
                                        line=v.get('play_line', '')))
    if kos_lines:
        out['failures'].append(dict(cat='vram', what='%d KOS heap failure line(s) (sbrk refused, native model slab or motion read)' % len(kos_lines),
                                    line=kos_lines[0]))
    for key, (room, i, ln) in gcfx.items():
        known, text = classify(key, index)
        item = dict(cat='gc-fallback', what='r%s: %s' % (room, text), line='line %d: %s' % (i, ln[:220]))
        (out['known_gaps'] if known else out['failures']).append(item)
    if not new_format:
        if old_rej:
            out['failures'].append(dict(cat='vram', what='%d VRAM budget refusal(s) (cumulative; log without VRAM_ROOM_LOG)' % old_rej, line=old_rej_line))
        if nocontig and nocontig_lines:
            out['failures'].append(dict(cat='vram', what='%d "no contiguous block" failure(s) (log without VRAM_ROOM_LOG)' % len(nocontig_lines),
                                        line=nocontig_lines[0]))
        out['notes'].append('no "vram room:" lines (build without VRAM_ROOM_LOG=1): no per-room VRAM table; GameCube effect pictures '
                            'not logged; %d thrash-guard skips with no pressure split (not judged)' % old_guard)
    return out


def table(rooms):
    """Markdown rows: one per room visit."""
    L = ['| Room | From frame | Min free | Min largest | Peak pinned | Pinned / dynamic / other (last) | Loads after preload | Evicted | Frag retries | '
         'Refusals | Guard (pressure) | No contig | GC fx | Dropped parts | Snd fail | Tex rej | KOS evict | Min KOS |',
         '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for v in rooms:
        last = v['last']
        g = v['gaps']
        L.append('| r%s | %d | %s | %s | %d | %s | %s | %d | %d | %d | %d (%d) | %d | %s | %d | %d | %d | %d | %s |' % (
            v['room'], v['start'], v['min_free'], v['min_largest'], v['peak_pinned'],
            '%s / %s / %s' % (last.get('pinned'), last.get('dynamic'), last.get('other')) if last else '-',
            '-' if v['play_loads'] is None else v['play_loads'], v['evicted'], v['retries'],
            g['refusals'], g['guard'], g['guard_p'], g['nocontig'], g['gc_fx'] if g['gc_fx'] >= 0 else 'n/a',
            g['dropped'] + g['fx_dropped'], g['snd_fail'], g['tex_rej'], g['meta'],
            '-' if v.get('min_kos') is None else v['min_kos']))
    return L


def main(argv):
    import argparse
    sys.path.insert(0, str(HERE.parent / 'fullplay'))
    from fp_check import parse_known, known_for
    ap = argparse.ArgumentParser()
    ap.add_argument('logs', nargs='+')
    ap.add_argument('--ps2lib')
    ap.add_argument('--known', default=str(HERE.parent / 'fullplay' / 'known-issues.txt'))
    ap.add_argument('--build', default='')
    ap.add_argument('--seg', default='benchmark')
    ap.add_argument('--json')
    a = ap.parse_args(argv)
    root = ps2lib_root(a.ps2lib)
    index = load_index(root)
    known = parse_known(a.known, a.build)
    bad = False
    allres = {}
    for log in a.logs:
        lines = Path(log).read_text(errors='replace').splitlines()
        res = analyse(lines, index, resident=resident_rooms())
        fails, kn = [], list(res['known_gaps'])
        for f in res['failures']:
            k = known_for(known, f['cat'], a.seg, f['what'] + ' ' + f['line'])
            (kn if k else fails).append(dict(f, why=k) if k else f)
        res['failures'], res['known_gaps'] = fails, kn
        allres[log] = res
        verdict = 'FAIL' if fails else 'PASS'
        bad = bad or bool(fails)
        print('VRAM %s  %s  (ps2lib %s)' % (verdict, log, root or 'not found'))
        for n in res['notes']:
            print('  note: ' + n)
        if res['rooms']:
            print('\n'.join('  ' + x for x in table(res['rooms'])))
        for f in fails:
            print('  FAIL [%s] %s\n      %s' % (f['cat'], f['what'], f['line']))
        for k in kn:
            print('  known [%s] %s%s' % (k['cat'], k['what'], (' (%s)' % k['why']) if k.get('why') else ''))
    if a.json:
        Path(a.json).write_text(json.dumps(allres, indent=1))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
