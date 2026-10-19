#!/usr/bin/env python3
"""cast_gc.py: the CAST-GC check (lane castgc17, 2026-10-17; user 10-17 "why do we keep falling back to gamecube models,
that shouldn't be occurring"). Stdlib only; runs on WSL or Windows Python.

    python3 tools/d367/cast_gc.py <run-output.txt>... [--allow tools/d367/castgc/allow.tsv] [--json OUT] [--rooms r100,r101]

Every character / enemy the run drew through the GameCube path, per room, with the reason, from the native census
(a build with NATIVE_MODEL_REGISTRY_CENSUS=1, e.g. NATIVE_MODEL_REGISTRY_CENSUS_PERIOD=150 for <= 60 s runs; the
mW check arms carry both):
  NMRS f= room= id= ot= parts= infos= plan= native= crowd= declined= registry_declined= absent= would=
      the scene census (coarse_actor_owner_registry.inc): every model whose first OT pass reached the actor
      transaction, by outcome. native = drawn by a native plan (L Leon / pl08, G the PS2 Ganado cast, R a registry
      package); crowd = the crowd policy did not draw it this pass; declined / registry_declined / absent = the
      transaction returned 0 and the SOURCE (GameCube) path drew the model.
  NMRD f= <descriptor> ... declined= roles= skeleton= layout= semantics= certificate= acquire= skin= plan=
      per registry descriptor: why its actors declined (the reason of a registry_declined row).
  NMRU / NMRU2 f= ...    registry actors no descriptor bound (shape / revision / roles / skeleton / finite / none ...).
  NMRPACK room=XXXX none (path) / NMRPACK refuse room=XXXX why=W   the room has no registry package / refused it.
Path per (room, model id): PS2 (native only), GC (any declined / registry_declined / absent pass), MIXED (both: some
passes fell back), or CROWD-SKIP (the crowd policy skipped every pass: not drawn, not GC). Leon (id 00) is LEON-GC's (MCHECK_LEONGC) and is listed, not judged.

Verdict: any GC or MIXED row of a character or enemy (model id 01..7f) that is not in the allowlist FAILS (exit 1). The
allowlist (tab separated: room or *, model id hex, reason, owner; '#' comments) is short and reviewed: each entry says
why that model may draw the GameCube path and who owns removing it. No census line at all: exit 2 (not a pass: the
build lacks NATIVE_MODEL_REGISTRY_CENSUS=1).

NOT-DRAWN (--not-drawn; release lane rel17b, 2026-10-18; TEST17-SCOPE "NOT-DRAWN check"): CAST-GC sees only models that
reached the draw path, so an enemy alive in logic but never drawn passed it (Krauser in r31c, 10-18: alive, attacking,
no NMRS row). The warp builds' `alivelog <period>` also logs
  warp: alivelist room XXX frame N ids II*count@nearest ...
      every enemy id alive in logic (SceCheckEmAlive, as SceCountEmAlive counts) with its count and the nearest
      distance to Leon (dbgwarp_bridge.cpp kill_poll; warp builds only, never the release image).
In-view rule (lane fix18, 10-18; replaces the 12 m --near scoping): newer warps add "/vN" per id, the number of those
enemies inside the camera's view frustum at the sample (body sphere y+900 r1200). An id is judged only when it was in view
in at least --min-samples samples; an enemy that stays out of view (held behind a gate, waiting for its wave) is listed
"out of view (not judged)" and needs no allowlist row. Logs without "/v" fall back to judging every id (older warps).
A room FAILS when a judged id (10..ff) has no NMRS row of that id in that
room (no draw pass of any outcome: native, crowd, GameCube). Reviewed exceptions: castgc/notdrawn-allow.tsv (room or *,
id hex, reason, owner). With --not-drawn and no alivelist line at all: exit 2 (not a pass: the warp lacks alivelog).
"""
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

NMRS = re.compile(r'NMRS f=(\d+) room=([0-9a-f]+) id=([0-9a-f]+) ot=(\d+) parts=(\d+) infos=(\d+) plan=(.) native=(\d+) '
                  r'crowd=(\d+) declined=(\d+) registry_declined=(\d+) absent=(\d+) would=(\d+)')
NMRD = re.compile(r'NMRD f=(\d+) (\S+) planned=(\d+) admitted=(\d+) would=(\d+) declined=(\d+) (.*)')
NMRU = re.compile(r'NMRU2? f=(\d+) (.*)')
PACK_NONE = re.compile(r'NMRPACK room=([0-9a-f]+) none \(([^)]*)\)')
PACK_REFUSE = re.compile(r'NMRPACK refuse room=([0-9a-f]+) why=(\S+)')
# PS2_ASHLEY_ROOMS (lane ashley17, 10-17): a refused partner package (Ashley, id 03) leaves her on the GameCube source
# path, outside the NMRS census (r11c at =1: "NMRPACK partner refuse room=011c why=table detail=4"). It FAILS here.
PARTNER_REFUSE = re.compile(r'NMRPACK partner refuse room=([0-9a-f]+) why=(\S+)(?: detail=(\S+?):?)?(?:\s|$)')
PARTNER_ID = 0x03
PACK_OPEN = re.compile(r'NMRPACK open room=([0-9a-f]+)')
ADMIT = re.compile(r'NMRM admit .*?room=([0-9a-f]+) .*?id=([0-9a-f]+) desc=(\S+)')
KV = re.compile(r'(\w+)=(-?\d+)')
ALIVELIST = re.compile(r'warp: alivelist room ([0-9a-f]+) frame (\d+) ids((?: [0-9a-f]{2}\*\d+@-?\d+(?:/v\d+)?)*)')
ALIVE_ID = re.compile(r'([0-9a-f]{2})\*(\d+)@(-?\d+)(?:/v(\d+))?')
REASONS = ('roles', 'skeleton', 'layout', 'semantics', 'certificate', 'acquire', 'skin', 'plan', 'shape', 'revision',
           'finite', 'none')
PLAN = {'-': 'none', 'L': 'Leon/pl08 plan', 'G': 'PS2 Ganado cast', 'R': 'registry package'}
# Model ids (cModel::id): 00 Leon, 01..0f the partner / player-class models, 10..7f the em modules (emXX).
NAMES = {0x00: 'Leon', 0x03: 'Ashley'}  # seen in the census (NMRM admit desc=ashley11); others print emXX / plXX


def name_of(i):
    return NAMES.get(i) or ('em%02x' % i if i >= 0x10 else 'pl%02x' % i)


def room3(r):
    return 'r%03x' % (int(r, 16) & 0xfff)


def parse(paths):
    rows = defaultdict(lambda: defaultdict(int))   # (room, id) -> counters
    meta = defaultdict(lambda: {'ot': set(), 'plan': set(), 'parts': set()})
    reasons = defaultdict(lambda: defaultdict(int))  # (room, id) -> reason -> count
    pack = {}                                        # room -> 'open' / 'none ...' / 'refused: why'
    admits = defaultdict(set)                        # (room, id) -> descriptor names
    partner_refused = {}                             # room -> why (NMRPACK partner refuse)
    nlines = 0
    for p in paths:
        report = {'nmrd': [], 'nmru': {}}
        last_f = None
        pending = []
        for line in Path(p).read_text(errors='replace').splitlines():
            m = PACK_OPEN.search(line)
            if m:
                pack[room3(m.group(1))] = 'open'
            m = PACK_NONE.search(line)
            if m:
                pack[room3(m.group(1))] = 'none (%s)' % m.group(2)
            m = PACK_REFUSE.search(line)
            if m:
                pack[room3(m.group(1))] = 'refused: %s' % m.group(2)
            m = PARTNER_REFUSE.search(line)
            if m:
                partner_refused[room3(m.group(1))] = 'why=%s detail=%s' % (m.group(2), m.group(3) or '?')
            m = ADMIT.search(line)
            if m:
                admits[(room3(m.group(1)), int(m.group(2), 16))].add(m.group(3))
            m = NMRD.search(line)
            if m:
                f = int(m.group(1))
                if f != last_f:
                    report = {'nmrd': [], 'nmru': {}}; last_f = f
                if int(m.group(6)):
                    kv = {k: int(v) for k, v in KV.findall(m.group(7))}
                    report['nmrd'].append((m.group(2), {k: kv[k] for k in REASONS if kv.get(k)}))
                continue
            m = NMRU.search(line)
            if m:
                f = int(m.group(1))
                if f != last_f:
                    report = {'nmrd': [], 'nmru': {}}; last_f = f
                for k, v in KV.findall(m.group(2)):
                    if int(v) and k in REASONS:
                        report['nmru'][k] = int(v)
                continue
            m = NMRS.search(line)
            if not m:
                continue
            nlines += 1
            f, room, mid = int(m.group(1)), room3(m.group(2)), int(m.group(3), 16)
            if f != last_f:
                report = {'nmrd': [], 'nmru': {}}; last_f = f
            key = (room, mid)
            c = rows[key]
            for k, g in (('native', 8), ('crowd', 9), ('declined', 10), ('registry_declined', 11), ('absent', 12)):
                c[k] += int(m.group(g))
            meta[key]['ot'].add(int(m.group(4))); meta[key]['plan'].add(m.group(7)); meta[key]['parts'].add(int(m.group(5)))
            plan = m.group(7)
            if int(m.group(12)):
                reasons[key]['no package: no plan for this model id (not Leon, not a Ganado-cast id, no registry descriptor)'] += int(m.group(12))
            if int(m.group(10)):
                if mid <= 0x0f:
                    reasons[key]['Leon/pl08 plan declined'] += int(m.group(10))
                elif plan == 'G':
                    # NMRS cannot tell these apart (both log plan G, declined): the PS2 Ganado cast took no plan for the
                    # model (no bind: info count / revision / appearance, or GANADO_LOD not ready), or its plan failed
                    # layout / semantics / acquire. ACTOR_TRANSACTION_DIAG=1 names the step.
                    reasons[key]['Ganado-class id (em10..em20): the PS2 Ganado cast did not draw it (no cast plan, or its '
                                 'layout / semantics / acquire failed) and no registry descriptor took it'] += int(m.group(10))
                else:
                    why = ', '.join('%s %d' % kv for kv in sorted(report['nmru'].items())) or 'no reason line'
                    reasons[key]['Ganado-class id: no PS2 Ganado cast appearance and no registry descriptor bound (unbound: %s)' % why] += int(m.group(10))
            if int(m.group(11)):
                tag = 'em%02x' % mid
                hits = [(d, r) for d, r in report['nmrd'] if tag in d.lower()] or report['nmrd']
                if hits:
                    for d, r in hits:
                        reasons[key]['registry package declined: %s (%s)' % (d, ', '.join('%s %d' % kv for kv in sorted(r.items())) or '?')] += int(m.group(11))
                else:
                    why = ', '.join('%s %d' % kv for kv in sorted(report['nmru'].items())) or 'no reason line'
                    reasons[key]['registry id, no descriptor bound (unbound: %s)' % why] += int(m.group(11))
    return rows, meta, reasons, pack, admits, nlines, partner_refused


def load_allow(path):
    out = []
    if path and Path(path).is_file():
        for ln in Path(path).read_text().splitlines():
            if not ln.strip() or ln.lstrip().startswith('#'):
                continue
            f = ln.split('\t')
            if len(f) < 4 or not f[2].strip() or not f[3].strip():
                sys.exit('cast_gc: allowlist line needs room, id, reason and owner: %r' % ln)
            out.append((f[0].strip(), int(f[1], 16), f[2].strip(), f[3].strip()))
    return out


def parse_alive(paths):
    """(room, id) -> [samples, max count, nearest distance, in-view samples or None]; and the number of alivelist lines."""
    alive, n = {}, 0
    for p in paths:
        for line in Path(p).read_text(errors='replace').splitlines():
            m = ALIVELIST.search(line)
            if not m:
                continue
            n += 1
            room = room3(m.group(1))
            for i, c, d, v in ALIVE_ID.findall(m.group(3)):
                s = alive.setdefault((room, int(i, 16)), [0, 0, None, None])
                s[0] += 1
                if v != '':
                    s[3] = (s[3] or 0) + (int(v) > 0)
                s[1] = max(s[1], int(c))
                if int(d) >= 0 and (s[2] is None or int(d) < s[2]):
                    s[2] = int(d)
    return alive, n


def not_drawn(a, rows):
    alive, n = parse_alive(a.logs)
    if not n:
        print('NOT-DRAWN %s: no "warp: alivelist" lines in %s: run a warp build with alivelog (not a pass)' % (a.label, ', '.join(a.logs)))
        return 2, []
    allow = load_allow(a.notdrawn_allow)
    only = set(a.rooms.split(',')) if a.rooms else None
    drawn = {k for k in rows}
    out, fails = [], 0
    for (room, mid), (samples, cnt, near, seen) in sorted(alive.items()):
        if (only and room not in only) or mid < 0x10 or mid > a.max_id:
            continue
        if a.near and (near is None or near > a.near):
            continue
        ok = (room, mid) in drawn
        verdict = 'drawn'
        if not ok and seen is not None and seen < a.min_samples:
            verdict = 'out of view (in view in %d sample(s); not judged)' % seen
        elif not ok and samples >= a.min_samples:
            hit = [x for x in allow if x[1] == mid and x[0] in ('*', room)]
            verdict = 'allowed (%s; owner %s)' % (hit[0][2], hit[0][3]) if hit else 'FAIL'
            fails += not hit
        elif not ok:
            verdict = 'not drawn, %d sample(s) < %d (not judged)' % (samples, a.min_samples)
        out.append({'room': room, 'id': '%02x' % mid, 'name': name_of(mid), 'samples': samples, 'max_alive': cnt,
                    'nearest': near, 'in_view': seen, 'verdict': verdict})
    w = '%-5s %-3s %-6s %-7s %-5s %-8s %-6s %s'
    print(w % ('room', 'id', 'name', 'samples', 'max', 'nearest', 'inview', 'verdict'))
    for r in out:
        print(w % (r['room'], r['id'], r['name'], r['samples'], r['max_alive'], r['nearest'],
                   '-' if r['in_view'] is None else r['in_view'], r['verdict']))
    print('NOT-DRAWN %s: %d alivelist lines, %d room/id rows, %d alive but never drawn%s'
          % (a.label, n, len(out), fails, '' if fails else ' (PASS)'))
    return (1 if fails else 0), out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('logs', nargs='+')
    ap.add_argument('--allow', default=str(Path(__file__).resolve().parent / 'castgc' / 'allow.tsv'))
    ap.add_argument('--json')
    ap.add_argument('--rooms', help='comma list: judge only these rooms (default every room in the census)')
    ap.add_argument('--label', default='', help='a run label printed in the table')
    ap.add_argument('--not-drawn', action='store_true', help='also run the NOT-DRAWN check (alive in logic, no draw row)')
    ap.add_argument('--notdrawn-allow', default=str(Path(__file__).resolve().parent / 'castgc' / 'notdrawn-allow.tsv'))
    ap.add_argument('--min-samples', type=int, default=2, help='NOT-DRAWN: alive samples needed to judge an id (default 2)')
    # Scoping (rel17b 10-18, open for the coordinator's review): the literal rule also flags core-program objects with no
    # cast model (em41 / em43 / em48 / em4a in most rooms), traps (em2a) and enemies alive far off screen.
    ap.add_argument('--near', type=int, default=0, help='NOT-DRAWN: also skip ids never within this many units of Leon (0 = off; the in-view rule replaces it)')
    ap.add_argument('--max-id', type=lambda s: int(s, 0), default=0xff, help='NOT-DRAWN: judge only ids up to this one (e.g. 0x3f)')
    a = ap.parse_args()
    rows, meta, reasons, pack, admits, n, partner_refused = parse(a.logs)
    if not n:
        print('CAST-GC: no NMRS census lines in %s: build with NATIVE_MODEL_REGISTRY_CENSUS=1 (not a pass)' % ', '.join(a.logs))
        sys.exit(2)
    nd_rc, nd_rows = (not_drawn(a, rows) if a.not_drawn else (0, []))
    allow = load_allow(a.allow)
    only = set(a.rooms.split(',')) if a.rooms else None
    out, fails = [], 0
    for (room, mid), c in sorted(rows.items()):
        if only and room not in only:
            continue
        gc = c['declined'] + c['registry_declined'] + c['absent']
        path = ('MIXED' if c['native'] else 'GC') if gc else ('PS2' if c['native'] else 'CROWD-SKIP')
        plan = '/'.join(PLAN.get(p, p) for p in sorted(meta[(room, mid)]['plan']))
        why = '; '.join('%s (%d)' % kv for kv in sorted(reasons[(room, mid)].items(), key=lambda kv: -kv[1]))
        if gc and room in pack and pack[room] != 'open':
            why += '; room package %s' % pack[room]
        verdict = ''
        if mid == 0:
            verdict = 'LEON-GC' if gc else ''
        elif gc and 1 <= mid <= 0x7f:
            hit = [x for x in allow if x[1] == mid and x[0] in ('*', room)]
            verdict = 'allowed (%s; owner %s)' % (hit[0][2], hit[0][3]) if hit else 'FAIL'
            fails += not hit
        out.append({'room': room, 'id': '%02x' % mid, 'name': name_of(mid), 'path': path, 'plan': plan,
                    'native': c['native'], 'gc': gc, 'crowd': c['crowd'], 'reason': why,
                    'descriptors': sorted(admits.get((room, mid), ())), 'verdict': verdict,
                    'ot': sorted(meta[(room, mid)]['ot']), 'parts': sorted(meta[(room, mid)]['parts'])})
    for room, why in sorted(partner_refused.items()):
        if only and room not in only:
            continue
        hit = [x for x in allow if x[1] == PARTNER_ID and x[0] in ('*', room)]
        verdict = 'allowed (%s; owner %s)' % (hit[0][2], hit[0][3]) if hit else 'FAIL'
        fails += not hit
        out.append({'room': room, 'id': '%02x' % PARTNER_ID, 'name': name_of(PARTNER_ID), 'path': 'GC', 'plan': 'partner package',
                    'native': 0, 'gc': 1, 'crowd': 0, 'reason': 'partner package refused (%s): Ashley keeps the GameCube source path' % why,
                    'descriptors': [], 'verdict': verdict, 'ot': [], 'parts': []})
    w = '%-5s %-3s %-8s %-9s %-7s %-7s %s'
    print(w % ('room', 'id', 'name', 'path', 'native', 'gc', 'verdict / reason'))
    for r in out:
        print(w % (r['room'], r['id'], r['name'], r['path'], r['native'], r['gc'],
                   (r['verdict'] + ': ' if r['verdict'] else '') + (r['reason'] or r['plan'] + (' ' + ','.join(r['descriptors']) if r['descriptors'] else ''))))
    print('CAST-GC %s: %d census lines, %d room/model rows, %d GC or MIXED character rows not allowed%s'
          % (a.label, n, len(out), fails, '' if fails else ' (PASS)'))
    if a.json:
        Path(a.json).write_text(json.dumps({'rows': out, 'packages': pack, 'fails': fails, 'not_drawn': nd_rows}, indent=1))
    sys.exit(1 if fails else nd_rc)


if __name__ == '__main__':
    main()
