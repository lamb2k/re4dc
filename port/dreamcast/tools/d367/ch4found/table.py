#!/usr/bin/env python3
# table.py <harness> <suffix>[,<suffix>...] : one row per room (latest suffix wins) for CH4-FOUNDATIONS (Windows python).
import json, re, sys, glob, os
H = os.path.join(r'C:\Flycast-Evidence\re4-dreamcast\ch4found-20261016', sys.argv[1], 'scenarios')
rows = {}
for suf in sys.argv[2].split(','):
    for d in sorted(glob.glob(os.path.join(H, 'cx-r*-walk-' + suf))):
        room = os.path.basename(d).split('-')[1]
        try:
            res = json.load(open(os.path.join(d, 'rfp-result.json')))
            log = open(os.path.join(d, 'capture', 'run-output.txt'), 'rb').read().decode('latin1')
        except Exception:
            continue
        if not log:
            continue
        L = log.splitlines()
        ch = res.get('checks', {})
        bad = [k for k, v in ch.items() if v == 'FAIL']
        unp = [k for k, v in ch.items() if v == 'UNPROVEN' and k not in ('short_walk', 'model_ps2_asset_provenance')]
        arc = [l for l in L if 'heap4 water' in l and 'read.cpp(131)' in l]
        frees = [int(m.group(1)) for l in L for m in [re.search(r'heap4 water: room \S+ free (\d+)', l)] if m and 'FAILED' not in l]
        failed = [l for l in L if 'heap4 water' in l and 'FAILED' in l]
        vr = [l for l in L if l.startswith('vram room:') and ('r=%s' % room[1:]) in l]
        v = vr[-1] if vr else ''
        g = lambda k: (re.search(k + r'=(\d+)', v) or [None, '-'])[1]
        peak = [l for l in L if 'alivecap: peak' in l]
        holds = len([l for l in L if 'alivecap: hold' in l or 'alivecap: defer' in l])
        tex = len([l for l in L if 'texchk: FAIL' in l])
        nm = [l for l in L if re.search(r'NMRS .*declined=[1-9]', l)]
        gcm = sorted(set(re.search(r'id=(\w+)', l).group(1) for l in nm))
        fault = [l for l in L if l.startswith('FAULT') or 'HALT' in l]
        rows[room] = dict(suf=suf, overall=res.get('overall'), fail=bad, unp=unp,
                          arc=(re.search(r'free (\d+)', arc[0]).group(1) if arc else '-'),
                          heap4_min=(min(frees) if frees else '-'), heap4_failed=len(failed),
                          pinned=g('pinned'), dynamic=g('dynamic'), free=g('free'), largest=g('largest'),
                          min_free=g('min_free'), evicted=g('evicted'),
                          peak=(re.search(r'peak (\d+)', peak[-1]).group(1) if peak else '-'), holds=holds,
                          tex=tex, gc_models=gcm, aica=len(res.get('aica_does_not_fit', [])), fault=fault[:1],
                          ev=d)
for r in sorted(rows):
    x = rows[r]
    print('%s %s %s fail=%s unp=%s heap4_after_arc=%s heap4_failed=%d vram pinned=%s dyn=%s free=%s largest=%s min_free=%s evicted=%s peak=%s holds=%d tex=%d gcmodel=%s aica=%d %s' % (
        r, x['suf'], x['overall'], ','.join(x['fail']), ','.join(x['unp']), x['arc'], x['heap4_failed'], x['pinned'],
        x['dynamic'], x['free'], x['largest'], x['min_free'], x['evicted'], x['peak'], x['holds'], x['tex'],
        ','.join(x['gc_models']), x['aica'], ' '.join(x['fault'])))
