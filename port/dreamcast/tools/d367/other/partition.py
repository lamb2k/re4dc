#!/usr/bin/env python3
"""Partition per-frame self-node deltas without replaying a changed trace history."""
import argparse
import collections
import csv
import json
from pathlib import Path
import account as accounting


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
    p.add_argument('--evidence', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    nodes = {int(r['node']): r for r in read(a.account / 'call_nodes.tsv')}
    groups = {int(r['sample_index']): r for r in read(a.replay / 'trace_groups.tsv')}
    nframes = collections.Counter(r['group'] for r in groups.values())
    nominal = read(a.replay / 'cgsim.frames.tsv')
    console = {r['trace']: float(r['cycles']) for r in read(a.evidence / 'proj/console.frames.tsv')}
    if len(nominal) != len(groups):
        raise ValueError('Trace group and model sample counts differ')
    frame_self = collections.defaultdict(float)
    function = collections.defaultdict(lambda: [0.0, 0])
    caller = collections.defaultdict(lambda: [0.0, 0])
    category = collections.defaultdict(float)
    ownership = collections.defaultdict(float)
    node_totals = collections.defaultdict(float)
    for row in read(a.replay / 'cg.self_frames.tsv'):
        frame, nid = int(row['frame']), int(row['node'])
        n, g = nodes[nid], groups[frame]['group']
        cyc, calls = float(row['self_cycles']), int(row['calls'])
        if cyc < -1e-6:
            raise ValueError('Negative node delta')
        frame_self[frame] += cyc
        node_totals[nid] += cyc
        function[(g, n['category'], n['func'])][0] += cyc
        function[(g, n['category'], n['func'])][1] += calls
        caller[(g, n['category'], n['func'], n['caller_category'], n['caller'])][0] += cyc
        caller[(g, n['category'], n['func'], n['caller_category'], n['caller'])][1] += calls
        category[(g, n['category'])] += cyc
        ownership[(g, n['ownership'])] += cyc
    for nid, node in nodes.items():
        if abs(node_totals[nid] - float(node['self_cycles'])) > 1:
            raise ValueError(f'Node {nid} does not reconcile with aggregate call tree')
    frame_rows = []
    totals = collections.defaultdict(lambda: [0.0, 0.0])
    for idx, row in enumerate(nominal):
        g = groups[idx]
        if row['trace'] != g['trace']:
            raise ValueError('Trace order mismatch')
        expected = float(row['cycles'])
        if abs(frame_self[idx] - expected) > 1:
            raise ValueError(f'Frame {idx} self sum mismatch: {frame_self[idx]} vs {expected}')
        c = console[row['trace']]
        totals[g['group']][0] += expected
        totals[g['group']][1] += c
        frame_rows.append(dict(sample_index=idx, trace=row['trace'], group=g['group'],
                               nominal_ms=expected/200000, console_projection_ms=c/200000,
                               self_sum_ms=frame_self[idx]/200000))
    write(a.out/'frames.tsv', frame_rows,
          ('sample_index','trace','group','nominal_ms','console_projection_ms','self_sum_ms'))
    fs = [dict(group=k[0], category=k[1], func=k[2], self_nominal_ms=v[0]/200000/nframes[k[0]],
               entries_per_sample=v[1]/nframes[k[0]]) for k,v in function.items()]
    cs = [dict(group=k[0], category=k[1], func=k[2], caller_category=k[3], caller=k[4],
               self_nominal_ms=v[0]/200000/nframes[k[0]], entries_per_sample=v[1]/nframes[k[0]]) for k,v in caller.items()]
    fs.sort(key=lambda r: (r['group'], -r['self_nominal_ms']))
    cs.sort(key=lambda r: (r['group'], -r['self_nominal_ms']))
    write(a.out/'functions.tsv', fs, ('group','category','func','self_nominal_ms','entries_per_sample'))
    write(a.out/'callers.tsv', cs, ('group','category','func','caller_category','caller','self_nominal_ms','entries_per_sample'))
    flat_frame_sum = collections.defaultdict(float)
    if (a.replay/'cg.function_frames.tsv').exists():
        classify = accounting.classifier(Path(__file__).resolve().parents[1]/'benchmark/bench-split.py')
        flat_input = read(a.account/'flat_functions.tsv')
        file_by_name = {accounting.signature(r['func']):r['file'] for r in flat_input}
        symbol = {}
        for line in (a.replay/'cg.syms.txt').read_text().splitlines():
            addr, kind, name = line.split(None,2)
            symbol[addr] = name
        flat_group = collections.defaultdict(float)
        flat_cat = collections.defaultdict(float)
        for row in read(a.replay/'cg.function_frames.tsv'):
            idx = int(row['frame'])
            g = groups[idx]['group']
            name = symbol.get(row['entry'], '<unknown-code>')
            file = file_by_name.get(accounting.signature(name),'')
            cat = classify(name,file)
            cycles = int(row['self_cycles_16'])/16
            flat_frame_sum[idx] += cycles
            flat_group[(g,cat,name,file)] += cycles
            flat_cat[(g,cat)] += cycles
        ff = [dict(group=k[0],category=k[1],func=k[2],file=k[3],self_nominal_ms=v/200000/nframes[k[0]])
              for k,v in flat_group.items()]
        ff.sort(key=lambda r:(r['group'],-r['self_nominal_ms']))
        write(a.out/'flat_functions.tsv',ff,('group','category','func','file','self_nominal_ms'))
        fc = [dict(group=k[0],category=k[1],self_nominal_ms=v/200000/nframes[k[0]]) for k,v in flat_cat.items()]
        fc.sort(key=lambda r:(r['group'],-r['self_nominal_ms']))
        write(a.out/'flat_categories.tsv',fc,('group','category','self_nominal_ms'))
    for name, records, label in [('categories',category,'category'),('ownership',ownership,'ownership')]:
        rows = [dict(group=k[0], **{label:k[1]}, self_nominal_ms=v/200000/nframes[k[0]]) for k,v in records.items()]
        rows.sort(key=lambda r: (r['group'], -r['self_nominal_ms']))
        write(a.out/(name+'.tsv'), rows, ('group',label,'self_nominal_ms'))
    windows = collections.defaultdict(lambda: {'complete_samples':0,'incomplete_samples':0,
                                              'executed_entry_pcs':0,'completed_calls':0,'valid_inclusive_ms_sum':0.0})
    for row in read(a.replay/'main_windows.tsv'):
        w = windows[(row['group'],row['func'])]
        w['executed_entry_pcs'] += int(row['executed_entry_pcs'])
        w['completed_calls'] += int(row['completed_calls'])
        if row['complete']=='True':
            w['complete_samples'] += 1
            w['valid_inclusive_ms_sum'] += float(row['inclusive_nominal_ms'])
        else:
            w['incomplete_samples'] += 1
    ws = []
    for (g,func),w in windows.items():
        w['mean_valid_inclusive_ms'] = (w['valid_inclusive_ms_sum']/w['complete_samples']
                                         if w['complete_samples'] else None)
        ws.append(dict(group=g,func=func,**w))
    write(a.out/'watch_coverage.tsv', ws, ('group','func','complete_samples','incomplete_samples',
                                        'executed_entry_pcs','completed_calls','valid_inclusive_ms_sum',
                                        'mean_valid_inclusive_ms'))
    summary = dict(evidence=str(a.evidence), replay=str(a.replay), all_frames_reconcile=True,
                   all_nodes_reconcile=True,
                   warning='Model diagnostic. Full trace order/cache history retained. '
                           'Function/caller subgroup costs are nominal; only group totals have console projection. '
                           'Caller ancestry is partial where stack reconstruction loses returns. '
                           'IRQ is charged to the interrupted phase on the console benchmark.',
                   groups={g:dict(samples=nframes[g],nominal_ms=v[0]/200000/nframes[g],
                                  console_projection_ms=v[1]/200000/nframes[g]) for g,v in totals.items()},
                   watch_coverage=ws)
    if flat_frame_sum:
        deltas = [(flat_frame_sum[i]-float(row['cycles']))/200000 for i,row in enumerate(nominal)]
        summary['flat_function_fixed_point_reconciliation'] = {
            'mean_delta_ms':sum(deltas)/len(deltas), 'max_abs_delta_ms':max(abs(d) for d in deltas),
            'note':'Per-PC charges use 1/16-cycle fixed-point rounding; frame timing uses doubles. '
                   'Flat function costs do not depend on reconstructed call returns or tail calls.'}
    if 'drawn_image' in totals and 'dropped_image' in totals:
        summary['reconstructed_two_tick_image_period'] = {
            'nominal_ms': sum(summary['groups'][g]['nominal_ms'] for g in ('drawn_image','dropped_image')),
            'console_projection_ms': sum(summary['groups'][g]['console_projection_ms'] for g in ('drawn_image','dropped_image')),
            'interpretation':'Sum of separately sampled group means; not measured adjacent physical tick pairs or console timing.'}
    (a.out/'partition.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='watch_coverage'},indent=2))


if __name__=='__main__':
    main()
