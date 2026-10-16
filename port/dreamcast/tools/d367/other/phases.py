#!/usr/bin/env python3
"""Reconstruct physical-iteration means from complete ordered forced-two-tick traces.

Prefix is before pace_begin; suffix begins at its actual entry PC. The exact
boundary is audited against this ELF. Reconstructed means use different sampled
iterations, not adjacent captured pairs or console benchmark phase boundaries.
"""
import argparse
import collections
import csv
import json
from pathlib import Path
import account


def read(path):
    with path.open() as src:
        return list(csv.DictReader(src, delimiter='\t'))


def write(path, rows, fields):
    with path.open('w', newline='') as dst:
        out = csv.DictWriter(dst, fields, delimiter='\t')
        out.writeheader()
        out.writerows(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--replay', required=True, type=Path)
    p.add_argument('--account', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--forced-alternating', required=True, action='store_true',
                   help='Confirm this fixture alternates draw/drop; required for reconstruction')
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    groups = {int(r['sample_index']): r['group'] for r in read(a.replay/'trace_groups.tsv')}
    n = collections.Counter(groups.values())
    if set(n) != {'drawn_image', 'dropped_image'}:
        raise ValueError('Both unambiguous alternating image groups are required')
    boundary = read(a.replay/'cg.segment_counts.tsv')
    if len(boundary) != len(groups) or any(int(r['boundary_entries']) != 1 for r in boundary):
        raise ValueError('Every trace must cross exactly one pace_begin entry')
    symbols = {}
    for line in (a.replay/'cg.syms.txt').read_text().splitlines():
        addr, kind, name = line.split(None, 2)
        symbols[addr] = name
    symbols['00000000'] = '<unknown code>'
    file_by_name = {account.signature(r['func']):r['file'] for r in read(a.account/'flat_functions.tsv')}
    classify = account.classifier(Path(__file__).resolve().parents[1]/'benchmark/bench-split.py')
    expected = {(int(r['frame']),r['entry']):int(r['self_cycles_16'])
                for r in read(a.replay/'cg.function_frames.tsv')}
    observed = collections.Counter()
    function = collections.Counter()
    sums = collections.Counter()
    for row in read(a.replay/'cg.function_segments.tsv'):
        frame, seg, cyc = int(row['frame']), int(row['segment']), int(row['self_cycles_16'])
        entry, group = row['entry'], groups[frame]
        observed[(frame,entry)] += cyc
        function[(group,seg,entry)] += cyc
        sums[(group,seg)] += cyc
    if observed != expected:
        raise ValueError('Function phase costs do not exactly reconcile with per-frame function costs')
    waits = collections.Counter()
    wait_pcs = collections.Counter()
    wait_frames = collections.Counter()
    for row in read(a.replay/'cg.wait_segments.tsv'):
        frame, seg = int(row['frame']), int(row['segment'])
        cyc = int(row['self_cycles_16'])
        waits[(groups[frame],seg,row['context'])] += cyc
        wait_frames[(frame,'retrace' if row['context'].startswith('retrace_') else 'busy_loop')] += cyc
        wait_pcs[(groups[frame],seg,row['context'],row['pc'])] += cyc
    config = json.loads((a.replay/'phase-config.json').read_text())
    retrace_entry = config['environment']['OTHER_WAIT_FUNC_START'].lower()
    pace_end_entry = next(addr for addr,name in symbols.items() if name == 're4dc_pace_end')
    for frame in groups:
        if wait_frames[(frame,'retrace')] != expected.get((frame,retrace_entry),0):
            raise ValueError(f'Retrace caller split does not reconcile in frame {frame}')
        if wait_frames[(frame,'busy_loop')] > expected.get((frame,pace_end_entry),0):
            raise ValueError(f'Busy-loop cost exceeds pace_end self cost in frame {frame}')
    scale = 16 * 200000
    phase_rows, physical, cat_physical = [], collections.Counter(), collections.Counter()
    for (group,seg,entry),cyc in function.items():
        name = symbols.get(entry,f'<unresolved-{entry}>')
        file = file_by_name.get(account.signature(name),'')
        category = classify(name,file)
        # Alternation: prefix belongs to previous presentation, suffix to current.
        drawn = (group == 'drawn_image') == bool(seg)
        label = 'physical_draw_mean' if drawn else 'physical_skip_mean'
        ms = cyc/scale/n[group]
        phase_rows.append(dict(group=group,segment='suffix' if seg else 'prefix',entry=entry,
                               func=name,file=file,category=category,self_nominal_ms=ms))
        physical[(label,entry,name,file,category)] += ms
        cat_physical[(label,category)] += ms
    phase_rows.sort(key=lambda r:(r['group'],r['segment'],-r['self_nominal_ms']))
    write(a.out/'phase_functions.tsv',phase_rows,
          ('group','segment','entry','func','file','category','self_nominal_ms'))
    physical_rows = [dict(physical_group=k[0],entry=k[1],func=k[2],file=k[3],category=k[4],self_nominal_ms=v)
                     for k,v in physical.items()]
    physical_rows.sort(key=lambda r:(r['physical_group'],-r['self_nominal_ms']))
    write(a.out/'physical_functions.tsv',physical_rows,
          ('physical_group','entry','func','file','category','self_nominal_ms'))
    write(a.out/'physical_categories.tsv',
          [dict(physical_group=k[0],category=k[1],self_nominal_ms=v) for k,v in sorted(cat_physical.items())],
          ('physical_group','category','self_nominal_ms'))
    wait_rows = [dict(group=k[0],segment='suffix' if k[1] else 'prefix',context=k[2],pc=k[3],
                      self_nominal_ms=v/scale/n[k[0]]) for k,v in sorted(wait_pcs.items())]
    write(a.out/'wait_pcs.tsv',wait_rows,('group','segment','context','pc','self_nominal_ms'))
    phase_summary, physical_summary = {}, {}
    for group in sorted(n):
        phase_summary[group] = {}
        for seg in (0,1):
            w = {ctx:waits[(group,seg,ctx)]/scale/n[group]
                 for ctx in ('busy_loop_pc','retrace_from_busy_loop','retrace_other_call')}
            phase_summary[group]['suffix' if seg else 'prefix'] = {
                'nominal_ms':sums[(group,seg)]/scale/n[group],
                'identified_pace_polling_nominal_ms':w['busy_loop_pc']+w['retrace_from_busy_loop'],
                'wait_detail_nominal_ms':w}
    for label,parts in {
        'physical_draw_mean':(('drawn_image','suffix'),('dropped_image','prefix')),
        'physical_skip_mean':(('dropped_image','suffix'),('drawn_image','prefix'))}.items():
        vals = [phase_summary[g][s] for g,s in parts]
        total = sum(v['nominal_ms'] for v in vals)
        polling = sum(v['identified_pace_polling_nominal_ms'] for v in vals)
        physical_summary[label] = {'parts':[f'{g}.{s}' for g,s in parts], 'nominal_ms':total,
            'identified_pace_polling_nominal_ms':polling,
            'after_identified_pace_polling_nominal_ms':total-polling}
    result = {'status':'PASS','scope':'Nominal offline model, reconstructed population means, no console timing.',
        'samples':dict(n),'boundaries_exactly_one_per_trace':True,
        'function_phase_reconciliation_exact':True,
        'retrace_caller_split_reconciliation_exact':True,
        'busy_loop_is_subset_of_pace_end_self':True,
        'phase_config':config,
        'phase_means':phase_summary,'reconstructed_physical_means':physical_summary,
        'caveats':[
            'Each physical mean combines independently sampled prefix and suffix means, not adjacent captured ticks.',
            'Phase boundary assigns costs when charged by the model; some pipeline stalls are attributed to an earlier PC.',
            'Identified polling includes the final successful loop check; all bookkeeping, other retrace callers, IRQs and unknown waits remain.',
            'FORCE=2 runs iTaskScheduler every iteration; this is not the production catchup schedule.',
            'This is not the console OTHER benchmark phase and cannot validate a claimed console skip saving.']}
    (a.out/'phases.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
