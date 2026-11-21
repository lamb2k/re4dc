#!/usr/bin/env python3
"""outcome.py: the strict plays-right reader (lane eng-svc5). Judges two runs of the same inputs by outcome, and fails
closed: anything it cannot read, or cannot find, is a failure, never a pass.

    outcome.py A B [--tolerances tol.json] [--offset N] [--expect-ticks LO:HI] [--actors SEL,...]
                   [--pos all|final] [--log a|b|ab] [--json out.json] [--quiet]

A is the reference run, B the run under test (the engine, or a native build of re4ref). B's tick t + N is compared with
A's tick t (--offset N). Docs: docs/engine/PLAYS_RIGHT.md section "Outcome reader".

Formats (the first record decides; both files may differ):
    re4ref    re4ref trace v1/v2 ("# re4ref trace", H, T, A, R lines) and the engine's hill trace (the same lines)
    logic     logic-trace records (LT, LE, LF, LL, GE and the other L* records of logic_trace.cpp / the engine)

What is compared (the outcome; never tick-exact agreement of the whole state):
    route     Leon's position at the last tick within `pos` units per axis
    position  Leon's and every actor's position within `pos` per axis on every compared tick (--pos all, default), or
              only at the last tick each actor has in both runs (--pos final)
    yaw       Leon's and every actor's yaw within `ang_deg` degrees (wrapped) on the same ticks as the position (lane
              eng-e1k; both runs must record it: a run without any yaw for an actor the other run has fails closed)
    kills     which actors' life reaches 0 (from above 0), and when (within `event_ticks`)
    damage    every drop of an actor's (and Leon's, when both runs record it) life: the amounts, exact, in order; the
              ticks within `event_ticks`
    triggers  actor spawns (first tick in the alive list) and removals (gone before the run ends), by actor, within
              `event_ticks`; and the event word's changes (Stop_flg, when both runs record it), in order
    clears    the room clear: the first tick at which every list enemy that has appeared is dead or gone (or none), within
              `event_ticks`
Tolerances (tolerances.json): pos (units, PLAYS_RIGHT.md section 5), ang_deg (degrees, the plays-right fixtures'
one degree), event_ticks (ticks).

Fails closed. Each of these is a FAIL whatever the values (kind in brackets, as the report names it):
    [missing-file]    a trace file that does not exist or cannot be read
    [no-records]      a file with no trace record, or of no known format
    [unknown-line]    a record tag the reader does not know; in a trace file, any line that is not a record (serial logs
                      are read with --log, where non-record lines are skipped and counted)
    [malformed]       a record without a field the outcome needs, or one that does not parse; a position or angle field
                      that is present but holds the not-recorded sentinel ('-', '~': lane eng-e1k)
    [non-finite]      a NaN or infinity in a position or angle
    [duplicate]       two player records of one tick, or two records of one actor in one tick
    [short-run]       ticks missing from the expected set (from --expect-ticks, else the H line's ticks=0..N; a logic
                      trace without --expect-ticks fails: its run length is not known); in a re4ref trace whose H line
                      declares a room, a T tick without its R line (R lines are required, not only checked when some
                      are there: lane eng-e1k)
    [missing-sample]  an actor without a record on a tick between its first and last record (lane eng-e1k: every actor
                      must be sampled on every tick it is alive in the run; a park and re-queue is not hosted yet)
    [extra-tick]      ticks outside the expected set
    [missing-actor]   an actor named by --actors absent from either run, or an actor of one run never in the other
Then the outcome checks: [route], [position], [yaw], [kill], [damage], [trigger], [clear].

Exit status: 0 PASS; 1 FAIL (every problem is listed, the first one first); 2 usage error.
"""
import argparse
import json
import math
import os
import re
import struct
import sys

DEFAULT_TOL = {'pos': 1.0, 'ang_deg': 1.0, 'event_ticks': 3}

# the records each format knows; a tag outside these is an unknown line
RE4REF_TAGS = {'H', 'T', 'A', 'R'}
LOGIC_TAGS = {'LT', 'LE', 'LF', 'LL', 'GE', 'LP', 'LD', 'LA', 'LSS', 'LU', 'LX'}
RECORD = re.compile(r'^([A-Z][A-Z0-9]{0,3}) t=(-?\d+)\b')
# the fields each record must carry for the outcome
NEED = {
    'T': ('t', 'p', 'a', 'm', 'r'),
    'A': ('t', 'k', 'id', 'e', 'p', 'a', 'm', 'r', 'hp'),
    'R': ('t', 'spawn'),
    'LT': ('t', 'p'),
    'LE': ('t', 'k', 'id', 'hp', 'pos'),
    'LL': ('t', 'hp'),
    'GE': ('t', 'e', 'id'),
}


class Problems:
    def __init__(self):
        self.items = []

    def add(self, kind, trace, tick=None, what='', detail=''):
        self.items.append({'kind': kind, 'trace': trace, 'tick': tick, 'what': what, 'detail': detail})


def f32(bits):
    return struct.unpack('<f', struct.pack('<I', int(bits, 16) & 0xFFFFFFFF))[0]


def vec(v, n):
    """'xxxxxxxx,yyyyyyyy,...' -> n floats; None when absent or not recorded ('-', '~'); ValueError when bad."""
    if v is None or v in ('-', '') or '~' in v:
        return None
    parts = v.split(',')
    if len(parts) < n:
        raise ValueError('expected %d values' % n)
    return [f32(x) for x in parts[:n]]


def need_vec(kv, key, n):
    """A position or angle field the record carries: absent -> None; present but holding the not-recorded sentinel
    ('-', '~', empty) -> ValueError (lane eng-e1k: a sentinel is not a value, and a skipped value cannot fail)."""
    if key not in kv:
        return None
    v = vec(kv[key], n)
    if v is None:
        raise ValueError('%s=%s: present but not recorded' % (key, kv[key]))
    return v


def kv_of(line):
    out = {}
    for tok in line.split()[1:]:
        if '=' in tok:
            k, v = tok.split('=', 1)
            out[k] = v
    return out


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


class Run:
    """One trace, read into per-tick player records and per-actor records."""

    def __init__(self, name):
        self.name = name          # 'A' or 'B'
        self.path = None
        self.fmt = None
        self.header = {}
        self.player = {}          # tick -> {'p': [x,y,z], 'hp': int|None, 'ev': str|None}
        self.actors = {}          # key -> {tick: {'p': [...], 'hp': int}}
        self.rlines = set()       # ticks with an R line (re4ref)
        self.skipped = 0          # non-record lines (--log)
        self.records = 0


def actor_key(id_hex, e_hex, rank_of):
    """An actor's identity across runs: its enemy-list entry; an actor not from the list (e=ff, or no e=) by id and the
    order of its first appearance among that id."""
    if e_hex is not None and e_hex.lower() != 'ff':
        return 'e=%02x' % int(e_hex, 16)
    return 'id=%02x#%d' % (int(id_hex, 16), rank_of)


def read(path, name, as_log, probs):
    run = Run(name)
    run.path = path
    if not os.path.isfile(path):
        probs.add('missing-file', name, None, path, 'no such file')
        return None
    try:
        lines = open(path, errors='strict').read().splitlines()
    except (OSError, UnicodeDecodeError) as e:
        probs.add('missing-file', name, None, path, 'cannot read: %s' % e)
        return None
    first_rank = {}           # (tick, id) -> per-tick counters for id-keyed actors
    seen_id_order = {}        # id -> list of first-seen identities (k at first tick) for id-keyed actors
    le_last = None
    for no, line in enumerate(lines, 1):
        s = line.rstrip('\r')
        if not s.strip():
            continue
        if s.startswith('#'):
            if run.fmt is None and s.startswith('# re4ref trace'):
                run.fmt = 're4ref'
            elif not s.startswith('# re4ref trace') and not as_log:
                probs.add('unknown-line', name, None, 'line %d' % no, s[:80])
            continue
        if s.startswith('H ') and run.fmt in (None, 're4ref'):
            run.fmt = 're4ref'
            run.header = kv_of(s)
            continue
        m = RECORD.match(s)
        if not m:
            if as_log:
                run.skipped += 1
            else:
                probs.add('unknown-line', name, None, 'line %d' % no, s[:80])
            continue
        tag, t = m.group(1), int(m.group(2))
        if tag in RE4REF_TAGS:
            fmt = 're4ref'
        elif tag in LOGIC_TAGS:
            fmt = 'logic'
        else:
            probs.add('unknown-line', name, t, 'line %d' % no, 'unknown record %s: %s' % (tag, s[:60]))
            continue
        if run.fmt is None:
            run.fmt = fmt
        elif run.fmt != fmt:
            probs.add('unknown-line', name, t, 'line %d' % no, '%s record in a %s trace' % (tag, run.fmt))
            continue
        run.records += 1
        kv = kv_of(s)
        need = NEED.get(tag, ())
        miss = [f for f in need if f not in kv or kv[f] == '']
        if miss:
            probs.add('malformed', name, t, tag, 'line %d: no %s' % (no, ','.join(miss)))
            continue
        try:
            if tag == 'T':
                if t in run.player:
                    probs.add('duplicate', name, t, 'T', 'line %d' % no)
                    continue
                p = vec(kv['p'], 3)
                a = vec(kv['a'], 3)
                if p is None or a is None:
                    probs.add('malformed', name, t, 'T', 'line %d: Leon not recorded (p=-)' % no)
                    continue
                run.player[t] = {'p': p, 'a': a, 'hp': None, 'ev': None}
            elif tag == 'A':
                key = actor_key(kv['id'], kv['e'], 0)
                if key.startswith('id='):
                    order = seen_id_order.setdefault(kv['id'].lower(), [])
                    tk = (t, kv['id'].lower())
                    n = first_rank.get(tk, 0)
                    first_rank[tk] = n + 1
                    key = actor_key(kv['id'], None, n)
                    if key not in order:
                        order.append(key)
                rec = run.actors.setdefault(key, {})
                if t in rec:
                    probs.add('duplicate', name, t, key, 'line %d' % no)
                    continue
                p = vec(kv['p'], 3)
                if p is None:
                    probs.add('malformed', name, t, key, 'line %d: no position' % no)
                    continue
                rec[t] = {'p': p, 'a': need_vec(kv, 'a', 3), 'hp': int(kv['hp'])}
            elif tag == 'R':
                if t in run.rlines:
                    probs.add('duplicate', name, t, 'R', 'line %d' % no)
                    continue
                run.rlines.add(t)
            elif tag == 'LT':
                if t in run.player:
                    probs.add('duplicate', name, t, 'LT', 'line %d' % no)
                    continue
                p = vec(kv['p'], 3)
                if p is None:
                    probs.add('malformed', name, t, 'LT', 'line %d: Leon not recorded (p=~)' % no)
                    continue
                ev = kv.get('sp')
                run.player[t] = {'p': p, 'a': need_vec(kv, 'a', 3), 'hp': None,
                                 'ev': ev if ev and '~' not in ev else None}
            elif tag == 'LL':
                pr = run.player.setdefault(t, {'p': None, 'a': None, 'hp': None, 'ev': None, '_ll_only': True})
                if pr.get('_ll'):
                    probs.add('duplicate', name, t, 'LL', 'line %d' % no)
                    continue
                pr['_ll'] = True
                pr['hp'] = s16(int(kv['hp'], 16))
                if kv.get('sp'):
                    pr['ev'] = kv['sp']
            elif tag == 'LE':
                key = actor_key(kv['id'], kv.get('e'), 0)
                if key.startswith('id='):
                    tk = (t, kv['id'].lower())
                    n = first_rank.get(tk, 0)
                    first_rank[tk] = n + 1
                    key = actor_key(kv['id'], None, n)
                rec = run.actors.setdefault(key, {})
                if t in rec:
                    probs.add('duplicate', name, t, key, 'line %d' % no)
                    le_last = None
                    continue
                # lane eng-e1k: the position must be recorded (pos=~ is a malformed record, not a skipped one); the
                # engine's fight trace carries the yaw in the LE line itself (ay=), the old game's in the LF line
                ay = need_vec(kv, 'ay', 1)
                rec[t] = {'p': need_vec(kv, 'pos', 3), 'a': [None, ay[0], None] if ay else None,
                          'hp': s16(int(kv['hp'], 16) & 0xFFFF)}
                le_last = (key, t, kv['k'])
            elif tag == 'LF':
                if le_last and le_last[1] == t and le_last[2] == kv.get('k') and 'ay' in kv:
                    run.actors[le_last[0]][t]['a'] = [None, need_vec(kv, 'ay', 1)[0], None]
            # GE, LP, LD, LA, LSS, LU, LX: known records the outcome does not need (GE events are derived again from
            # the life and the alive list, so the two runs are judged alike)
        except ValueError as e:
            probs.add('malformed', name, t, tag, 'line %d: %s' % (no, e))
    if run.fmt is None or run.records == 0:
        probs.add('no-records', name, None, path, 'no trace record')
        return None
    # a logic trace's LL-only ticks (no LT): the player's position is not recorded on that tick
    for t, pr in list(run.player.items()):
        if pr.get('_ll_only') and pr.get('p') is None:
            probs.add('malformed', name, t, 'LL', 'LL without LT: no position')
    return run


def finite_list(v):
    return v is None or all(x is None or math.isfinite(x) for x in v)


def structure(run, expect, offset, probs):
    """The run's ticks against the expected set (A's numbering); positions finite; R lines for every T tick."""
    have = set(t - offset for t in run.player)
    want = set(expect)
    for t in sorted(want - have):
        probs.add('short-run', run.name, t + offset, 'player', 'tick %d (A numbering %d) missing' % (t + offset, t))
    for t in sorted(have - want):
        probs.add('extra-tick', run.name, t + offset, 'player', 'outside the expected %d..%d' % (min(want), max(want)))
    # lane eng-e1k: a re4ref trace whose H line declares a room must carry an R line on every T tick (before, the check
    # ran only when the trace had some R line, so a trace with every R line removed passed)
    if run.fmt == 're4ref' and (run.rlines or run.header.get('room')):
        missing = sorted(set(run.player) - run.rlines)
        for t in missing[:20]:
            probs.add('short-run', run.name, t, 'R', 'no R line')
        if len(missing) > 20:
            probs.add('short-run', run.name, None, 'R', '%d more ticks without an R line' % (len(missing) - 20))
    # lane eng-e1k: every actor sampled on every tick from its first record to its last (before, positions were compared
    # only where both runs had a record, so an interior record deleted from a stationary actor passed)
    for key, rec in sorted(run.actors.items()):
        if not rec:
            continue
        gaps = [t for t in range(min(rec), max(rec) + 1) if t not in rec]
        for t in gaps[:20]:
            probs.add('missing-sample', run.name, t, key, 'no record between its first (%d) and last (%d)' % (min(rec), max(rec)))
        if len(gaps) > 20:
            probs.add('missing-sample', run.name, None, key, '%d more ticks without a record' % (len(gaps) - 20))
    for t, pr in run.player.items():
        if not finite_list(pr.get('p')) or not finite_list(pr.get('a')):
            probs.add('non-finite', run.name, t, 'Leon', '%s %s' % (pr.get('p'), pr.get('a')))
    for key, rec in run.actors.items():
        for t, r in rec.items():
            if not finite_list(r.get('p')) or not finite_list(r.get('a')):
                probs.add('non-finite', run.name, t, key, '%s %s' % (r.get('p'), r.get('a')))
            if (t - offset) not in want:
                probs.add('extra-tick', run.name, t, key, 'actor record outside the expected ticks')
            elif t not in run.player:
                probs.add('short-run', run.name, t, key, 'actor record on a tick without a player record')


def life_events(rec):
    """-> (damage [(tick, before, after)], kill tick or None) from an actor's per-tick life."""
    dmg, kill, last = [], None, None
    for t in sorted(rec):
        hp = rec[t]['hp']
        if hp is None:
            continue
        if last is not None and hp < last:
            dmg.append((t, last, hp))
            if hp <= 0 < last and kill is None:
                kill = t
        last = hp
    return dmg, kill


def clear_tick(run, keys, end):
    """First tick at which every list enemy that has appeared is dead or gone; None when never (or no enemy)."""
    lst = [k for k in keys if k.startswith('e=')]
    if not lst:
        return None
    first = {k: min(run.actors[k]) for k in lst if run.actors.get(k)}
    for t in sorted(run.player):
        live = 0
        appeared = 0
        for k in lst:
            rec = run.actors.get(k, {})
            if not rec or first[k] > t:
                continue
            appeared += 1
            r = rec.get(t)
            if r is not None and r['hp'] > 0:
                live += 1
        if appeared and live == 0 and appeared == len(lst):
            return t
    return None


def compare(A, B, tol, offset, pos_mode, required, probs, report):
    pt = tol['pos']
    et = tol['event_ticks']
    ticks = sorted(t for t in A.player if (t + offset) in B.player)
    report['ticks_compared'] = len(ticks)
    if not ticks:
        probs.add('short-run', 'A/B', None, 'player', 'no tick in both runs')
        return
    # actors: every required one in both; every actor of one run in the other
    for sel in required:
        for run in (A, B):
            if sel not in run.actors:
                probs.add('missing-actor', run.name, None, sel, 'required actor absent')
    for key in sorted(set(A.actors) | set(B.actors)):
        if key not in A.actors or key not in B.actors:
            probs.add('missing-actor', 'B' if key in A.actors else 'A', None, key, 'in one run only')
    report['actors'] = sorted(set(A.actors) & set(B.actors))

    def over(p, q):
        return max(abs(x - y) for x, y in zip(p, q))
    # route: Leon at the last compared tick
    last = ticks[-1]
    d = over(A.player[last]['p'], B.player[last + offset]['p'])
    report['route'] = {'tick': last, 'diff': d}
    if d > pt:
        probs.add('route', 'A/B', last, 'Leon', 'final position %.3f units off (tolerance %g)' % (d, pt))
    # position
    worst = (0.0, None, None)
    nover = 0
    for key in ['Leon'] + report['actors']:
        if key == 'Leon':
            pa, pb = A.player, B.player
            ts = ticks
        else:
            pa, pb = A.actors[key], B.actors[key]
            ts = sorted(t for t in pa if (t + offset) in pb)
        if pos_mode == 'final':
            ts = ts[-1:]
        for t in ts:
            p, q = pa[t].get('p'), pb[t + offset].get('p')
            if p is None or q is None:
                continue
            dd = over(p, q)
            if dd > worst[0]:
                worst = (dd, t, key)
            if dd > pt:
                nover += 1
                if nover <= 20:
                    probs.add('position', 'A/B', t, key, '%.3f units off (tolerance %g)' % (dd, pt))
    if nover > 20:
        probs.add('position', 'A/B', None, '...', '%d more ticks over' % (nover - 20))
    report['position'] = {'mode': pos_mode, 'max': worst[0], 'max_at': worst[1], 'max_actor': worst[2], 'over': nover}
    # yaw (lane eng-e1k): within ang_deg degrees, wrapped, on the position's ticks; a yaw one run records on a tick and
    # the other does not fails closed; an actor neither run records a yaw for is listed as not compared
    at = tol['ang_deg']
    yworst = (0.0, None, None)
    yover = 0
    nyaw = []
    for key in ['Leon'] + report['actors']:
        if key == 'Leon':
            pa, pb, ts = A.player, B.player, ticks
        else:
            pa, pb = A.actors[key], B.actors[key]
            ts = sorted(t for t in pa if (t + offset) in pb)
        if pos_mode == 'final':
            ts = ts[-1:]
        seen = 0
        for t in ts:
            ya, yb = (pa[t].get('a') or [None, None])[1], (pb[t + offset].get('a') or [None, None])[1]
            if ya is None and yb is None:
                continue
            seen += 1
            if ya is None or yb is None:
                yover += 1
                if yover <= 20:
                    probs.add('yaw', 'A/B', t, key, 'yaw recorded in %s only' % ('B' if ya is None else 'A'))
                continue
            dd = abs(math.degrees(math.remainder(ya - yb, 2.0 * math.pi)))
            if dd > yworst[0]:
                yworst = (dd, t, key)
            if dd > at:
                yover += 1
                if yover <= 20:
                    probs.add('yaw', 'A/B', t, key, '%.3f degrees off (tolerance %g)' % (dd, at))
        if not seen:
            nyaw.append(key)
    if yover > 20:
        probs.add('yaw', 'A/B', None, '...', '%d more ticks over' % (yover - 20))
    report['yaw'] = {'max_deg': yworst[0], 'max_at': yworst[1], 'max_actor': yworst[2], 'over': yover}
    if nyaw:
        report['not_compared'] = report.get('not_compared', []) + ['yaw of %s (in neither run)' % ', '.join(nyaw)]

    def near(ta, tb):
        return ta is not None and tb is not None and abs((tb - offset) - ta) <= et
    # kills, damage, spawns and removals per actor
    kills = []
    dmgs = []
    trig = []
    for key in report['actors']:
        ra, rb = A.actors[key], B.actors[key]
        da, ka = life_events(ra)
        db, kb = life_events(rb)
        kills.append((key, ka, kb))
        if (ka is None) != (kb is None) or (ka is not None and not near(ka, kb)):
            probs.add('kill', 'A/B', ka if ka is not None else kb, key, 'A kill tick %s, B %s (tolerance %d)' % (ka, kb, et))
        dmgs.append((key, len(da), len(db)))
        if [x[1] - x[2] for x in da] != [x[1] - x[2] for x in db]:
            probs.add('damage', 'A/B', (da or db)[0][0] if (da or db) else None, key,
                      'A amounts %s, B %s' % ([x[1] - x[2] for x in da], [x[1] - x[2] for x in db]))
        else:
            for x, y in zip(da, db):
                if not near(x[0], y[0]):
                    probs.add('damage', 'A/B', x[0], key, 'A at %d, B at %d (tolerance %d)' % (x[0], y[0], et))
        sa, sb = min(ra), min(rb)
        trig.append((key, 'spawn', sa, sb))
        if not near(sa, sb):
            probs.add('trigger', 'A/B', sa, key, 'spawn: A %d, B %d (tolerance %d)' % (sa, sb, et))
        ga = max(ra) if max(ra) < last else None
        gb = max(rb) if max(rb) < last + offset else None
        if (ga is None) != (gb is None) or (ga is not None and not near(ga, gb)):
            probs.add('trigger', 'A/B', ga if ga is not None else gb, key, 'removed: A after %s, B after %s' % (ga, gb))
    # Leon's life, where both runs record it
    if any(A.player[t].get('hp') is not None for t in ticks) and any(B.player[t + offset].get('hp') is not None for t in ticks):
        la = {t: {'hp': A.player[t]['hp']} for t in ticks}
        lb = {t + offset: {'hp': B.player[t + offset]['hp']} for t in ticks}
        da, ka = life_events(la)
        db, kb = life_events(lb)
        if [x[1] - x[2] for x in da] != [x[1] - x[2] for x in db]:
            probs.add('damage', 'A/B', None, 'Leon', 'A amounts %s, B %s' % ([x[1] - x[2] for x in da], [x[1] - x[2] for x in db]))
        dmgs.append(('Leon', len(da), len(db)))
    else:
        report['not_compared'] = report.get('not_compared', []) + ["Leon's life (not in both runs)"]
    # the event word (Stop_flg), where both runs record it: its changes in order
    eva = [(t, A.player[t]['ev']) for t in ticks if A.player[t].get('ev') is not None]
    evb = [(t, B.player[t + offset]['ev']) for t in ticks if B.player[t + offset].get('ev') is not None]
    if eva and evb:
        ca = [(t, v) for i, (t, v) in enumerate(eva) if i == 0 or eva[i - 1][1] != v]
        cb = [(t, v) for i, (t, v) in enumerate(evb) if i == 0 or evb[i - 1][1] != v]
        if [v for _, v in ca] != [v for _, v in cb]:
            probs.add('trigger', 'A/B', None, 'events', 'event word changes differ: A %s, B %s' % (ca[:6], cb[:6]))
        else:
            for x, y in zip(ca, cb):
                if abs(x[0] - y[0]) > et:
                    probs.add('trigger', 'A/B', x[0], 'events', 'event word %s: A at %d, B at %d' % (x[1], x[0], y[0]))
        trig.append(('events', 'changes', len(ca), len(cb)))
    else:
        report['not_compared'] = report.get('not_compared', []) + ['event word (not in both runs)']
    # room clear
    ca, cb = clear_tick(A, report['actors'], last), clear_tick(B, report['actors'], last + offset)
    report['clear'] = {'A': ca, 'B': cb}
    if (ca is None) != (cb is None) or (ca is not None and not near(ca, cb)):
        probs.add('clear', 'A/B', ca if ca is not None else cb, 'room', 'A clear at %s, B at %s (tolerance %d)' % (ca, cb, et))
    report['kills'] = [{'actor': k, 'A': a, 'B': b} for k, a, b in kills if a is not None or b is not None]
    report['damage'] = [{'actor': k, 'A': a, 'B': b} for k, a, b in dmgs if a or b]
    report['triggers'] = [{'actor': k, 'kind': w, 'A': a, 'B': b} for k, w, a, b in trig]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('a', help='the reference run (trace file)')
    ap.add_argument('b', help='the run under test (trace file)')
    ap.add_argument('--tolerances', help='JSON: pos (units), event_ticks (ticks)')
    ap.add_argument('--offset', type=int, default=0, help="B's tick = A's tick + offset")
    ap.add_argument('--expect-ticks', help="LO:HI, A's ticks both runs must hold (default: the H line's 0..ticks)")
    ap.add_argument('--actors', default='', help='actors both runs must have: e=<entry>, id=<id>#<rank>, comma separated')
    ap.add_argument('--pos', choices=('all', 'final'), default='all', help='positions on every tick (default) or the last')
    ap.add_argument('--log', default='', help="a, b or ab: that file is a serial log (non-record lines skipped, counted)")
    ap.add_argument('--json', help='write the report as JSON')
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()
    tol = dict(DEFAULT_TOL)
    if args.tolerances:
        try:
            with open(args.tolerances) as f:
                tol.update({k: v for k, v in json.load(f).items() if not k.startswith('_')})
        except (OSError, ValueError) as e:
            print('outcome: tolerances %s: %s' % (args.tolerances, e), file=sys.stderr)
            sys.exit(2)
    probs = Problems()
    A = read(args.a, 'A', 'a' in args.log, probs)
    B = read(args.b, 'B', 'b' in args.log, probs)
    report = {'a': args.a, 'b': args.b, 'offset': args.offset, 'tolerances': {k: tol[k] for k in DEFAULT_TOL},
              'pos': args.pos}
    if A and B:
        report['formats'] = [A.fmt, B.fmt]
        expect = None
        if args.expect_ticks:
            lo, hi = (int(x) for x in args.expect_ticks.split(':'))
            expect = range(lo, hi + 1)
        elif A.header.get('ticks'):
            expect = range(0, int(A.header['ticks']) + 1)
            if B.fmt == 're4ref' and B.header.get('ticks') and int(B.header['ticks']) != int(A.header['ticks']) + 0:
                probs.add('short-run', 'B', None, 'header', 'H ticks=%s, A has %s' % (B.header['ticks'], A.header['ticks']))
        else:
            probs.add('short-run', 'A', None, 'expected ticks', 'no H line and no --expect-ticks: the run length is not known')
        if expect is not None:
            report['expected_ticks'] = [expect[0], expect[-1]]
            structure(A, expect, 0, probs)
            structure(B, expect, args.offset, probs)
        required = [s.strip() for s in args.actors.split(',') if s.strip()]
        required = [actor_key(s[3:].split('#')[0], None, int(s.split('#')[1]) if '#' in s else 0) if s.startswith('id=')
                    else 'e=%02x' % int(s[2:], 16) for s in required]
        compare(A, B, tol, args.offset, args.pos, required, probs, report)
        report['skipped_lines'] = [A.skipped, B.skipped]
    verdict = 'PASS' if not probs.items else 'FAIL'
    report['verdict'] = verdict
    kinds = {}
    for p in probs.items:
        kinds[p['kind']] = kinds.get(p['kind'], 0) + 1
    report['problem_kinds'] = kinds
    report['problems'] = probs.items[:300]
    if not args.quiet:
        print('%s  %s vs %s: %s' % (verdict, args.a, args.b, ', '.join('%s %d' % kv for kv in sorted(kinds.items())) or
                                    '%d ticks, %d actors, route %.4f, position max %.4f' % (
                                        report.get('ticks_compared', 0), len(report.get('actors', [])),
                                        report.get('route', {}).get('diff', 0.0), report.get('position', {}).get('max', 0.0)) +
                                    ', yaw max %.4f deg' % report.get('yaw', {}).get('max_deg', 0.0)))
        if probs.items:
            p = probs.items[0]
            print('  first: [%s] %s tick %s %s %s' % (p['kind'], p['trace'], p['tick'], p['what'], p['detail']))
        else:
            print('  kills %s; damage %s; clear %s' % (
                [(k['actor'], k['A']) for k in report.get('kills', [])],
                [(d['actor'], d['A']) for d in report.get('damage', [])], report.get('clear')))
    if args.json:
        with open(args.json, 'w') as f:
            json.dump(report, f, indent=1)
    sys.exit(0 if verdict == 'PASS' else 1)


if __name__ == '__main__':
    main()
