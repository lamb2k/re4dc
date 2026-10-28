"""fp_check.py: verdict of a full-play gate run (tools/d367/fullplay).

    python fp_check.py <evidence dir> [--known known-issues.txt] [--conf segments.conf[,segments-ch22.conf]]

Reads <evidence>/<segment>/run-output.txt + run-result.json for every segment of segments.conf that ran, applies the
failure rules (RULES below), the per-segment goals, the leak check (repeated visits of a room in one segment) and the
reset-memory check, matches failures against the known-issue list, and writes <evidence>/verdict.json and the
one-page <evidence>/REPORT.md. Exit 0 = PASS, 1 = FAIL. fp_gate.py calls it after the runs; it can be re-run alone.
"""
import json, os, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'vram'))
import vram_gate  # noqa: E402
sys.path.insert(0, str(HERE.parent))
import cast_gc  # noqa: E402  (tools/d367/cast_gc.py: CAST-GC, GameCube character / enemy draws)  (vram/vram_gate.py: the VRAM gaps of the CLAUDE.md graphics memory rule)
_VRAM_INDEX = []

def vram_index():
    """ps2lib effect key -> INDEX rows (vram_gate.load_index), read once; None when ps2lib is not on this host."""
    if not _VRAM_INDEX:
        _VRAM_INDEX.append(vram_gate.load_index(vram_gate.ps2lib_root()))
    return _VRAM_INDEX[0]

# (category, regex, what). A line matching any rule fails the segment unless a known issue covers it.
RULES = [
    ('crash', r'FAULT code=', 'CPU exception (crash screen)'),
    ('crash', r'\bHALT\b', 'HALT (game stopped itself)'),
    ('hang', r'CRASH_SCREEN: no new frame', 'no new frame for 30 s (hang)'),
    ('missing', r'RE4DC MISSING', 'missing-symbol stub called'),
    ('misalign', r'MISALIGN', 'misaligned access'),
    ('dropped-free', r'dropped \(heap', 'module free dropped (memory not returned)'),
    ('log', r'\[LOG OVERRUN|\[end: .*overruns=[1-9]', 'log ring overrun (evidence incomplete)'),
    ('gc-fallback', r'^LEONGC (?!armed)', 'GameCube Leon (MCHECK_LEONGC)'),
    ('gc-fallback', r'LHPACK dir .*why=[1-9]', 'Leon hand package missing or bad: GameCube Leon'),
    ('gc-fallback', r'PS2WORLD fallback', 'PS2 world not drawn: GameCube world fallback'),
    ('gc-fallback', r'PS2MESH open failed', 'PS2 world package not opened'),
    ('gc-fallback', r'NMRPACK refuse', 'model package refused: actors keep the GameCube path'),
    ('gc-fallback', r'NMRM decline', 'model declined: GameCube source path'),
    ('gc-fallback', r'MODEL_BLOB_FALLBACK', 'model blob fallback'),
    ('texture', r'texchk: FAIL|texchk: .*(META|VRAM) CHANGED', 'TEX_CHECK failure'),
    ('texture', r'upload FAILED|no contiguous block|pair missing', 'texture not uploaded'),
    ('texture', r'open failed|package rejected', 'file or package not opened'),
    ('alloc', r'^(?!texchk:|aica:).*(allocation failed|allocation FAILED|reserve slab of \d+ failed|FAILED \(0 B\)|NOMEM|does not fit|thd_create_ex failed)',
     'allocation failure'),
    ('sound', r'aica: blk \d+ .*does not fit', 'sound bank block does not fit in AICA RAM (silent sounds)'),
    ('alloc', r'alloc\[[0-9a-f]+\]:free\[[0-9a-f]+\]', 'heap allocation failure (alloc/free report)'),
    ('io', r'link failed|aica_str\.dat read failed|write-verify FAILED|dvd read safe: .*failed [1-9]', 'disc/VMU I/O failure'),
    ('movie', r'route movie terminal=(?!1 )\d', 'movie did not play to its end'),
    ('route', r'Coming Soon', 'Coming Soon (door to a room not on the disc)'),
]
DELIBERATE_FREEZE = re.compile(r'warp: frozen at tick|route end: .*Coming Soon, holding')

def conf_text(paths):
    """paths: one conf file or a comma-separated list; bare names are looked up next to this file"""
    out = []
    for p in str(paths).split(','):
        p = Path(p.strip())
        out.append((p if p.exists() or p.is_absolute() else HERE / p).read_text())
    return '\n'.join(out)

def parse_conf(path):
    segs = []
    for line in conf_text(path).splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        f = [x.strip() for x in line.split('|')]
        segs.append(dict(name=f[0], disc=f[1], seconds=int(f[2]), warp=f[3], pad=f[4], keys=f[5], vmu=f[6],
                         stop=None if f[7] == '-' else f[7], grace=float(f[8]),
                         goals=[g.strip() for g in f[9].split(';;') if g.strip()] if f[9] != '-' else [],
                         how=f[10], what=f[11]))
    return segs

def parse_known(path, build):
    out = []
    if not path or not Path(path).exists():
        return out
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        head = line.split('|', 3)  # the regex may contain '|': builds|cat|seg|<regex>|why (why has no '|')
        rx, why = head[3].rsplit('|', 1)
        builds, cat, seg, rx, why = head[0].strip(), head[1].strip(), head[2].strip(), rx.strip(), why.strip()
        if builds != '*' and not any(build.startswith(b.strip()) for b in builds.split(',')):
            continue
        out.append(dict(cat=cat, seg=seg, rx=re.compile(rx), why=why))
    return out

def known_for(known, cat, seg, line):
    for k in known:
        if k['cat'] == cat and (k['seg'] == '*' or k['seg'] == seg) and k['rx'].search(line):
            return k['why']
    return None

ENTER = re.compile(r'room lifecycle: phase=enter room=([0-9a-f]+) generation=(\d+) .*?free=(\d+)')
ENTER2 = re.compile(r'room lifecycle: phase=enter vram_free=(\d+) kos_free=(\d+) kos_used=(\d+)')
CENSUS = re.compile(r'heap4 census: span=\d+ walked=\d+ free=(\d+)')

def visits(lines):
    out = []
    for ln in lines:
        m = ENTER.search(ln)
        if m:
            out.append(dict(room=m.group(1), gen=int(m.group(2)), heap4_enter=int(m.group(3))))
            continue
        if out:
            m = ENTER2.search(ln)
            if m and 'vram' not in out[-1]:
                out[-1].update(vram=int(m.group(1)), kos_free=int(m.group(2)), kos_used=int(m.group(3)))
                continue
            m = CENSUS.search(ln)
            if m and 'heap4_census' not in out[-1]:
                out[-1]['heap4_census'] = int(m.group(1))
    return out

LEAK_BYTES = 32 * 1024

def leak_judge(vals, sign):
    """Floor rule (2026-10-14, replaces "3 monotonic samples"): the first entry is cold (empty caches) and is not
    judged; of the warm entries (3 or more needed), the last two must not both be worse than the worst earlier warm
    entry (the floor), with the last one worse by more than LEAK_BYTES; or every warm entry is worse than the one
    before and the warm entries lose more than LEAK_BYTES in all (a small steady leak). A cache that refills and
    empties between visits (VRAM texture cache, KOS fragments) stays inside its floor; a leak sets a new low on
    every visit."""
    warm = vals[1:]
    if len(warm) < 3:
        return False, None
    earlier, last = warm[:-2], warm[-2:]
    floor = min(earlier) if sign < 0 else max(earlier)
    worse = [(floor - x) if sign < 0 else (x - floor) for x in last]
    steady = all((b - a) * sign > 0 for a, b in zip(warm, warm[1:])) and abs(warm[-1] - warm[0]) > LEAK_BYTES
    return (all(w > 0 for w in worse) and worse[-1] > LEAK_BYTES) or steady, floor

def leak_check(vs):
    """repeated visits of the same room in one run: free memory must not keep falling below its floor (leak_judge)."""
    rows, fails = [], []
    by = {}
    for v in vs:
        by.setdefault(v['room'], []).append(v)
    for room, lst in sorted(by.items()):
        if len(lst) < 2:
            continue
        for key, sign in (('heap4_census', -1), ('heap4_enter', -1), ('kos_used', +1), ('vram', -1)):
            vals = [v.get(key) for v in lst]
            if any(x is None for x in vals):
                continue
            d = [vals[i + 1] - vals[i] for i in range(len(vals) - 1)]
            total = vals[-1] - vals[0]
            trend = all(x * sign > 0 for x in d) if sign else False  # every visit worse than the one before (report)
            bad, floor = leak_judge(vals, sign)
            rows.append(dict(room=room, metric=key, values=vals, total=total, monotonic=trend, floor=floor, fail=bad))
            if bad:
                fails.append('r%s %s %s (last two warm entries past the warm floor %d; %+d B over %d visits)' % (
                    room, key, ' -> '.join(str(x) for x in vals), floor, total, len(vals)))
    return rows, fails

def retired_world_opens(lines):
    """line numbers of `PS2MESH open failed` / `PS2WORLD fallback` (and the `reject` before them) for a room whose
    world then opened at its own entry: the chapter end pre-opens the next room's world while the old room still holds
    heap 4 (lanes/route.md 2026-10-01: "the room's own entry retires the attempt and opens it"). Not retired, and so a
    failure, when the room is never entered or its world fails again after the entry."""
    out = set()
    for i, ln in enumerate(lines):
        if 'PS2MESH open failed' not in ln:
            continue
        room = None
        for j in range(i - 1, max(-1, i - 6), -1):
            m = re.search(r'PS2MESH room=([0-9a-f]+) open', lines[j])
            if m:
                room = m.group(1); break
        if room is None:
            continue
        entered = None
        for k in range(i + 1, len(lines)):
            if re.search(r'phase=enter room=%s ' % room, lines[k]):
                entered = k; break
            if re.search(r'phase=enter room=', lines[k]):
                break
        if entered is None:
            continue
        ok = False
        for k in range(entered, len(lines)):
            if re.search(r'PS2MESH room=%s open' % room, lines[k]):
                ok = not any('open failed' in x for x in lines[k + 1:k + 4]); break
        if ok:
            for k in range(max(0, i - 2), min(len(lines), i + 3)):
                if re.search(r'PS2MESH open failed|PS2WORLD fallback', lines[k]):
                    out.add(k + 1)
    return out

def check_segment(evdir, seg, known):
    d = Path(evdir) / seg['name']
    res = dict(name=seg['name'], how=seg['how'], disc=seg['disc'], what=seg['what'], failures=[], known=[], notes=[])
    rr = d / 'run-result.json'
    out = d / 'run-output.txt'
    if not rr.exists() or not out.exists():
        res['failures'].append(dict(cat='harness', what='segment did not run', line=''))
        res['result'] = 'FAIL'
        return res, []
    r = json.loads(rr.read_text())
    res['wall_s'] = r.get('elapsed_s')
    res['stopped'] = r.get('stopped')
    lines = out.read_text(errors='replace').splitlines()
    res['log_lines'] = len(lines)
    if r.get('align'):  # crash suite (fp_run.py --align): the hwmodel logger's MISALIGN lines join the game log
        hw = d / 'hwtrace.log'
        if not hw.exists() or 'align=1' not in hw.read_text(errors='replace'):
            res['failures'].append(dict(cat='harness', what='align run without an align=1 hwtrace.log', line=''))
        else:
            mis = [l for l in hw.read_text(errors='replace').splitlines() if 'MISALIGN' in l]
            res['misalign_pcs'] = sorted({m.group(1) for m in (re.search(r'pc=([0-9a-f]+)', l) for l in mis) if m})
            lines += ['hwtrace.log: ' + l for l in mis]
    if r.get('status') != 'RUN_COMPLETE':
        res['failures'].append(dict(cat='harness', what='run failed: %s' % r.get('errors'), line=''))
    if 'early_emulator_exit' in r:
        res['failures'].append(dict(cat='crash', what='Flycast exited early (code %s)' % r['early_emulator_exit'], line=''))
    if r.get('keys_pending'):
        res['failures'].append(dict(cat='harness', what='%d host key steps never ran (title/menu not reached)' % r['keys_pending'], line=''))
    if r.get('log_idle_s', 0) >= 90 and r.get('stopped') != 'goal':
        res['failures'].append(dict(cat='hang', what='game log silent for the last %d s of the run' % r['log_idle_s'], line=''))
    froze = False
    seen = {}
    retired = retired_world_opens(lines)
    if retired:
        res['notes'].append('%d PS2 world open(s) failed before a room change and succeeded at the room entry '
                            '(chapter-end pre-open; not drawn): lines %s' % (len(retired), sorted(retired)))
    in_reset = False
    reset_drops = 0
    last_load, load_k = '', None
    handoff = set()
    skipped = set()
    qte_passed = set()
    for i, ln in enumerate(lines, 1):
        if DELIBERATE_FREEZE.search(ln):
            froze = True
        # soft reset: from --SOFT_RESET START!! to the title's first state, a free into a heap that the reset
        # destroyed is dropped by design (RESET_HEAP_FIX, c9052efb); a drop anywhere else is the test 9 leak
        if 'SOFT_RESET START' in ln:
            in_reset = True
        elif in_reset and ('state title=1/0' in ln or 'phase=enter room=' in ln):
            in_reset = False
        if in_reset and 'dropped (heap' in ln:
            reset_drops += 1
            continue
        cats = set()
        for cat, rx, what in RULES:
            if cat not in cats and re.search(rx, ln):
                cats.add(cat)  # one finding per category per line
                if cat == 'hang' and froze:
                    continue
                if i in retired:
                    continue
                if cat == 'movie':  # a QTE movie handed to the game's frames is cancelled at its end (terminal 4)
                    mm = re.search(r'terminal=4 id=([0-9a-f]+) frames=(\d+)/(\d+)', ln)
                    if mm and mm.group(1) in handoff and mm.group(2) == mm.group(3):
                        continue
                    if mm and mm.group(1) in qte_passed:
                        continue
                    # a movie the player skipped (the skip key logged for it first) ends with terminal 2 by design
                    mm = re.search(r'terminal=2 id=([0-9a-f]+) ', ln)
                    if mm and mm.group(1) in skipped:
                        continue
                # a "package rejected" line names its file only in the "native UI: load" line before it
                ctx = ln + (' <- ' + last_load if 'package rejected' in ln and last_load else '')
                k = known_for(known, cat, seg['name'], ctx)
                # the follow-on lines of one texture load ("upload FAILED", texchk) share the verdict of its first
                # failure line
                if cat == 'texture':
                    k = k or load_k
                    load_k = k
                key = (cat, what, bool(k))
                seen[key] = seen.get(key, 0) + 1
                if seen[key] > 3:  # every line is judged; only the first 3 of each kind are listed
                    continue
                item = dict(cat=cat, what=what, line='%s:%d: %s' % (out.name, i, ctx.strip()[:220]))
                (res['known'] if k else res['failures']).append(dict(item, why=k) if k else item)
        mh = re.search(r'route movie handoff: id=([0-9a-f]+)', ln)
        if mh:
            handoff.add(mh.group(1))
        ms = re.search(r'route movie skip: id=([0-9a-f]+) ', ln)
        if ms:
            skipped.add(ms.group(1))
        # lane fix18 (#38): a passed QTE ends its cut at once (the source handler's CancelSet, r11f s00 cut 0x11:
        # the press sets Room_flg 0x80000000), so the cut's PS2 clip (id | 0x1000000, "c" file) open over the cut's
        # game frames is cancelled there (terminal 4), before its last picture: by design, not an early end.
        mq = re.search(r'route QTE: id=([0-9a-f]+) cut=\S+ frames=\d+/\d+ passed=1 .*picture=movie', ln)
        if mq:
            qte_passed.add('%x' % (int(mq.group(1), 16) | 0x1000000))
        if ln.startswith('native UI: load '):
            last_load, load_k = ln.strip(), None
    # CAST-GC (lane castgc17): a census build (NATIVE_MODEL_REGISTRY_CENSUS=1, the mW check arms) lists every model the
    # GameCube path drew; a character / enemy that castgc/allow.tsv does not list fails (Leon: LEONGC above).
    cg_rows, cg_meta, cg_why, cg_pack, _, cg_n = cast_gc.parse([str(out)])[:6]
    if not cg_n:
        res['notes'].append('CAST-GC not judged: no NMRS census lines (build without NATIVE_MODEL_REGISTRY_CENSUS=1)')
    cg_allow = cast_gc.load_allow(str(HERE.parent / 'castgc' / 'allow.tsv'))
    for (room, mid), c in sorted(cg_rows.items()):
        if not (1 <= mid <= 0x7f) or not (c['declined'] + c['registry_declined'] + c['absent']):
            continue
        if any(x[1] == mid and x[0] in ('*', room) for x in cg_allow):
            continue
        why = '; '.join(sorted(cg_why[(room, mid)]))
        ln = 'CAST-GC %s %s (%02x) drawn by the GameCube path: %s' % (room, cast_gc.name_of(mid), mid, why)
        item = dict(cat='gc-fallback', what='CAST-GC: character / enemy drawn by the GameCube path', line=ln[:220])
        k = known_for(known, 'gc-fallback', seg['name'], ln)
        (res['known'] if k else res['failures']).append(dict(item, why=k) if k else item)
    res['counts'] = {'%s/%s%s' % (k[0], k[1], ' (known)' if k[2] else ''): n for k, n in seen.items()}
    if reset_drops:
        res['notes'].append('%d module free(s) dropped inside a soft reset (destroyed heaps; by design since RESET_HEAP_FIX)' % reset_drops)
    # s30: every picture shown
    for ln in lines:
        m = re.search(r'route movie cadence id=10030 shown=(\d+) dropped=(\d+)', ln)
        if m and int(m.group(2)) > 0:
            item = dict(cat='movie', what='s30 dropped %s pictures' % m.group(2), line=ln.strip()[:200])
            k = known_for(known, 'movie', seg['name'], ln)
            (res['known'] if k else res['failures']).append(dict(item, why=k) if k else item)
    # VRAM gaps (vram/vram_gate.py; CLAUDE.md graphics memory rule): budget refusals, thrash-guard skips and GameCube
    # effect pictures that ps2lib/INDEX.tsv does not list as NONE (the known gaps) fail; "no contiguous block" lines are
    # judged by RULES above. The per-room VRAM table ("vram room:" lines, VRAM_ROOM_LOG=1) goes to REPORT.md.
    vg = vram_gate.analyse(lines, vram_index(), nocontig=False)
    res['vram_rooms'] = vg['rooms']
    res['notes'] += vg['notes']
    for item in vg['failures']:
        k = known_for(known, item['cat'], seg['name'], item['what'] + ' ' + item['line'])
        (res['known'] if k else res['failures']).append(dict(item, why=k) if k else item)
    for item in vg['known_gaps']:
        res['known'].append(dict(item, why='ps2lib INDEX.tsv ps2_source=NONE (no PS2 counterpart)'))
    text = '\n'.join(lines)
    missing_goals = [g for g in seg['goals'] if not re.search(g, text)]
    for g in missing_goals:
        res['failures'].append(dict(cat='route', what='goal not reached: %s' % g, line=''))
    vs = visits(lines)
    res['visits'] = vs
    rows, leaks = leak_check(vs)
    res['leak_rows'] = rows
    for l in leaks:
        k = known_for(known, 'leak', seg['name'], l)
        item = dict(cat='leak', what='free memory trends down on repeated visits: ' + l, line='')
        (res['known'] if k else res['failures']).append(dict(item, why=k) if k else item)
    res['result'] = 'FAIL' if res['failures'] else 'PASS'
    return res, vs

def reset_memory(results, known):
    """r100 entered after load + soft reset + New Game vs a fresh boot's r100 entry (real-newgame)."""
    fresh = next((v for r in results if r['name'] == 'real-newgame' for v in r.get('visits', []) if v['room'] == '100'), None)
    after = next((v for r in results if r['name'] == 'reset' for v in r.get('visits', []) if v['room'] == '100'), None)
    if not fresh or not after:
        return None
    out = dict(fresh=fresh, after_reset=after, failures=[], known=[])
    for key in ('heap4_enter', 'heap4_census'):
        if key in fresh and key in after and fresh[key] - after[key] > 16 * 1024:
            line = 'r100 %s fresh boot %d, after load + reset + New Game %d (%d B less)' % (key, fresh[key], after[key], fresh[key] - after[key])
            k = known_for(known, 'reset-memory', 'reset', line)
            item = dict(cat='reset-memory', what=line, line='')
            (out['known'] if k else out['failures']).append(dict(item, why=k) if k else item)
    return out

def report(evdir, results, rm, prep, meta, verdict):
    L = []
    L.append('# Full-play gate: %s' % verdict)
    L.append('')
    L.append('- Disc: %s' % meta.get('input'))
    L.append('- Tracks: %s' % meta.get('tracks_verified'))
    if prep:
        L.append('- Release binary: %s, built from %s (%s)' % (prep['release_binary_sha256'][:16], prep['release_tree_commit'][:8], prep['release_build']))
        idl = [x for x in prep.get('twin_report', []) if x.startswith(('IDENTITY', 'TWIN'))]
        L += ['- %s' % x for x in idl]
        L.append('- Twin data tree vs release: %s; release-binary base: %s' % (
            next((x for x in prep.get('twin_base_diff', []) if x.startswith('identical')), '?'),
            next((x for x in prep.get('rel_base_diff', []) if x.startswith('identical')), '?')))
    L.append('- Wall time: %s (prep %s, runs %s)' % (meta.get('wall'), meta.get('prep_wall'), meta.get('runs_wall')))
    L.append('')
    L.append('| Segment | How | Result | Wall s | Covers |')
    L.append('|---|---|---|---|---|')
    for r in results:
        L.append('| %s | %s (%s disc) | %s%s | %s | %s |' % (r['name'], r['how'], r['disc'], r['result'],
                 ' (+%d known)' % len(r['known']) if r['known'] else '', r.get('wall_s', '-'), r['what']))
    fails = [(r['name'], f) for r in results for f in r['failures']]
    if rm:
        fails += [('reset vs boot', f) for f in rm['failures']]
    L.append('')
    if fails:
        L.append('## Failures')
        for name, f in fails[:40]:
            L.append('- **%s** [%s] %s%s' % (name, f['cat'], f['what'], ('  \n  `%s`' % f['line']) if f['line'] else ''))
        if len(fails) > 40:
            L.append('- ... %d more in verdict.json' % (len(fails) - 40))
    kn = [(r['name'], k) for r in results for k in r['known']] + ([('reset vs boot', k) for k in rm['known']] if rm else [])
    if kn:
        L.append('')
        L.append('## Known issues seen (not counted)')
        done = set()
        for name, k in kn:
            key = (name, k['cat'], k['why'])
            if key in done:
                continue
            done.add(key)
            L.append('- %s [%s] %s: %s%s' % (name, k['cat'], k['what'], k['why'], ('  \n  `%s`' % k['line']) if k['line'] else ''))
    L.append('')
    vr = [(r['name'], r['vram_rooms']) for r in results if r.get('vram_rooms')]
    L.append('## VRAM per room (vram room: lines; MODELLED Flycast runs)')
    if vr:
        for name, rooms in vr:
            L.append('')
            L.append('%s:' % name)
            L.append('')
            L += vram_gate.table(rooms)
    else:
        L.append('- no "vram room:" lines (build without VRAM_ROOM_LOG=1)')
    L.append('')
    L.append('## Memory on repeated room visits (leak check)')
    any_rows = False
    for r in results:
        for row in r.get('leak_rows', []):
            if row['metric'] in ('heap4_census', 'kos_used') or row['fail']:
                any_rows = True
                L.append('- %s r%s %s: %s (total %+d)%s' % (r['name'], row['room'], row['metric'], ' -> '.join(map(str, row['values'])),
                         row['total'], ' FAIL' if row['fail'] else ''))
    if not any_rows:
        L.append('- no room was entered twice in one segment')
    if rm:
        L.append('- r100 after load + reset + New Game vs fresh boot: heap4 at entry %s vs %s, census free %s vs %s' % (
            rm['after_reset'].get('heap4_enter'), rm['fresh'].get('heap4_enter'), rm['after_reset'].get('heap4_census'), rm['fresh'].get('heap4_census')))
    L.append('')
    L.append('Evidence: %s (segment dirs: run-output.txt = game log, run-result.json, fixture-*.txt).' % evdir)
    (Path(evdir) / 'REPORT.md').write_text('\n'.join(L) + '\n', encoding='utf-8')

def main(argv):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('evidence'); ap.add_argument('--known', default=str(HERE / 'known-issues.txt'))
    ap.add_argument('--conf', help='segment conf file(s), comma-separated; default: the gate run\'s own (gate.json conf) '
                    'or segments.conf')
    a = ap.parse_args(argv)
    ev = Path(a.evidence)
    prep = json.loads((ev / 'prep.json').read_text()) if (ev / 'prep.json').exists() else None
    meta = json.loads((ev / 'gate.json').read_text()) if (ev / 'gate.json').exists() else {}
    a.conf = a.conf or meta.get('conf') or 'segments.conf'
    build = prep['release_tree_commit'] if prep else meta.get('build', '')
    known = parse_known(a.known, build)
    segs = [s for s in parse_conf(a.conf) if (ev / s['name']).exists() or s['name'] in meta.get('segments', [])]
    results = []
    for s in segs:
        r, _ = check_segment(ev, s, known)
        results.append(r)
    rm = reset_memory(results, known)
    bad = any(r['result'] != 'PASS' for r in results) or (rm and rm['failures']) or not meta.get('tracks_ok', True) \
        or not results
    verdict = 'FAIL' if bad else 'PASS'
    (ev / 'verdict.json').write_text(json.dumps(dict(verdict=verdict, build=build, segments=results, reset_memory=rm), indent=1))
    report(ev, results, rm, prep, meta, verdict)
    print('FULLPLAY %s  %s' % (verdict, ev / 'REPORT.md'))
    return 0 if verdict == 'PASS' else 1

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
