#!/usr/bin/env python3
"""Account for every self-cost row in a D367 hardware-model run exactly once.

This is NOT the console benchmark's OTHER phase. Flat functions are classified
by implementation; call-tree self costs retain their caller. The call tree uses
the nominal model, while wi_console is a separate calibrated projection. No
inclusive timings or projection ratios are used to manufacture ownership.
"""
import argparse
import bisect
import collections
import csv
import hashlib
import importlib.util
import json
import re
from pathlib import Path

FIELDS = ('hw_ms', 'wi_console', 'base', 'dep_load', 'dep_fpu', 'dep_fdiv',
          'dep_other', 'flock', 'branch', 'imiss', 'dmiss', 'pfwait', 'sq', 'uncached')
WAIT = {'re4dc_pace_end', 're4dc_vi_retrace_count', 'thd_idle', 'arch_sleep',
        'genwait_wait', 'thd_sleep', 'thd_sleep_ms', 'thd_pass', 'thd_yield'}


def canonical(name):
    name = name.replace('(anonymous namespace)::', '')
    name = re.sub(r'^(?:void|int|bool|float|double|unsigned int|unsigned long)\s+', '', name)
    return name.split('(', 1)[0].strip()


def signature(name):
    return re.sub(r'^(?:void|int|bool|float|double|unsigned int|unsigned long)\s+', '',
                  name.replace('(anonymous namespace)::', '')).strip()


def read_tsv(path):
    with path.open(encoding='utf-8') as src:
        return list(csv.DictReader(src, delimiter='\t'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_tsv(path, rows, fields):
    with path.open('w', encoding='utf-8', newline='') as out:
        writer = csv.DictWriter(out, fields, delimiter='\t', extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def classifier(split_path):
    spec = importlib.util.spec_from_file_location('bench_split', split_path)
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)

    def category(name, file=''):
        n = canonical(name)
        f = file.replace('\\', '/').split('/')[-1]
        if n in {'memcpy', 'memset', 'memmove', 'memcmp', 'bzero', 'memclr_asm'} or re.match(
                r'^(L_(store|movmem|al[0-9]|word|byte|copy|unal)|__movmem|__movstr)', n) or re.search(
                r'(memcpy|memset|memmove|memcmp)\.(o|c|S)$', f):
            return 'shared copies and clears'
        if n in WAIT:
            return 'pacing, retrace and idle routines'
        if n in {'pcsIrq'} or f == 'pc_sampler.cpp':
            return 'interrupts and device service'
        if re.match(r'^(irq_|exception_|save_regs|restore_regs|timer_|perf_cntr_|re4dc_pc_sampler|maple_|g2_)', n):
            return 'interrupts and device service'
        if re.match(r'^(thd_|genwait_|mutex_|sem_|cond_)', n):
            return 'KOS scheduling and synchronization'
        if n.startswith('re4dc_ps2_world_direct_begin'):
            return 'world direct begin'
        if re.search(r'(hwfog|haze|fog_)', n, re.I) or n.startswith('GXSetFog'):
            return 'fog and haze'
        if re.match(r'^(clearOtWork|ExecOt|AddOt|GetPrimBuff)', n) or f == 'trans_ot.cpp':
            return 'ordering tables and primitive allocation'
        if 'packet' in n.lower():
            return 'packet setup and submit'
        if re.match(r'^(pvr_|sq_)', n):
            return 'PVR and store queue helpers'
        if f == 'gx_stub.cpp' or n.startswith('GX'):
            return 'GX state and command stubs'
        if n.startswith('re4dc_ui') or f == 'ui_bridge.cpp':
            return 'UI submission and bridge'
        if f == 'native_ui.cpp':
            return 'shared image and material helpers'
        if n in {'main', 'TaskScheduler', 'iTaskScheduler', 'Trans', 'Render', 'Render_before',
                 'Render_after', 'DRAWREMAIN', 'DRAW_REMAIN'} or n.startswith('re4dc_pace_'):
            return 'frame scheduling self'
        if f in {'native_draw_plan.cpp', 'model_packets.cpp'}:
            return 'actor submit'
        if f == 'native_static.cpp' or f.startswith(('mesh_', 'ps2_world')):
            return 'world submit'
        if f.startswith(('native_actor', 'coarse_actor')):
            return 'actor submit'
        if n.startswith(('re4dc_sh4_MTX', 're4dc_zam_MTX')):
            return 'shared math and formatting'
        if f == 'audio_aica.cpp' or n == 'audio_step':
            return 'audio'
        result = legacy.bucket(n, file)
        return 'shared math and formatting' if result == 'shared math/copies' else result
    return category


def frame_info(path, cycles_per_ms):
    rows = read_tsv(path)
    if not rows:
        raise ValueError(f'No frames in {path}')
    return {'samples': len(rows),
            'mean_ms': sum(float(r['cycles']) for r in rows) / len(rows) / cycles_per_ms,
            'traces': [r['trace'] for r in rows]}


def flat_account(evidence, out, classify, cycles_per_ms):
    source = evidence / 'proj/rep/functions.tsv'
    rows = read_tsv(source)
    totals = collections.defaultdict(lambda: collections.defaultdict(float))
    for index, row in enumerate(rows):
        row['row'] = index
        row['category'] = classify(row['func'], row.get('file', ''))
        for field in FIELDS:
            totals[row['category']][field] += float(row.get(field) or 0)
    groups = [dict(category=k, **v) for k, v in totals.items()]
    groups.sort(key=lambda r: r['wi_console'], reverse=True)
    write_tsv(out / 'flat_functions.tsv', rows, ('row', 'category', 'func', 'file') + FIELDS)
    write_tsv(out / 'flat_categories.tsv', groups, ('category',) + FIELDS)
    metrics = {}
    for field, frame_name in [('wi_console', 'console.frames.tsv'), ('hw_ms', 'hw.frames.tsv')]:
        path = evidence / 'proj' / frame_name
        # hwproject uses nominal.frames.tsv on some versions.
        if not path.exists() and field == 'hw_ms':
            path = evidence / 'proj/nominal.frames.tsv'
        total = sum(float(r.get(field) or 0) for r in rows)
        metrics[field] = {'flat_row_sum_ms': total, 'assigned_category_sum_ms': sum(g[field] for g in groups)}
        if path.exists():
            info = frame_info(path, cycles_per_ms)
            metrics[field].update(info)
            delta = total - info['mean_ms']
            # functions.tsv rounds each value to four decimal places.
            tolerance = len(rows) * 0.00005 + 0.00001
            metrics[field].update(rounding_delta_ms=delta, rounding_bound_ms=tolerance,
                                  reconciled=abs(delta) <= tolerance)
            if not metrics[field]['reconciled']:
                raise ValueError(f'{field} flat sum does not reconcile: {metrics[field]}')
    return rows, {'source': str(source), 'source_sha256': sha(source), 'rows': len(rows),
                  'categories': groups, 'reconciliation': metrics}


def call_account(cg, out, rows, classify, cycles_per_ms):
    symbols = []
    for line in (cg / 'cg.syms.txt').read_text(encoding='utf-8').splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3:
            symbols.append((int(parts[0], 16), parts[2]))
    symbols.sort(key=lambda s: s[0])
    addresses = [s[0] for s in symbols]
    paths = {signature(r['func']): r.get('file', '') for r in rows}
    by_canon = collections.defaultdict(set)
    for row in rows:
        by_canon[canonical(row['func'])].add(row.get('file', ''))

    def resolve(addr):
        idx = bisect.bisect_right(addresses, addr) - 1
        if idx < 0 or addresses[idx] != addr:
            return f'<unresolved-entry-{addr:08x}>'
        return symbols[idx][1]

    info = frame_info(cg / 'cgsim.frames.tsv', cycles_per_ms)
    nframes = info['samples']
    denom = cycles_per_ms * nframes
    nodes = {}
    for row in read_tsv(cg / 'cg.cg.tsv'):
        idx = int(row['node'])
        name = resolve(int(row['entry'], 16)) if idx else '<trace-root>'
        file = paths.get(signature(name), '')
        alternatives = by_canon[canonical(name)]
        if not file and len(alternatives) == 1:
            file = next(iter(alternatives))
        nodes[idx] = dict(node=idx, parent=int(row['parent']), entry=row['entry'], func=name,
                          file=file, category=classify(name, file),
                          self_cycles=float(row['self_cycles']), calls=int(row['calls']))

    grouped = collections.defaultdict(lambda: [0.0, 0])
    cats = collections.defaultdict(float)
    owners = collections.defaultdict(float)

    def ownership(idx):
        seen = set()
        while idx and idx not in seen:
            seen.add(idx)
            n = canonical(nodes[idx]['func'])
            if n in {'TaskScheduler', 'TaskSchedulerMain'}:
                return 'logic scheduler call tree'
            if n == 'iTaskScheduler':
                return 'iTask scheduler call tree'
            if n in {'re4dc_ps2_world_draw', 're4dc_ps2_mesh_draw'}:
                return 'world draw call tree'
            if n in {'re4dc_actor_transaction_draw', 'draw_actors'}:
                return 'actor transaction draw call tree'
            if n in {'ModelRender', 'ModelRenderBody'}:
                return 'model OT callback; EmMgr membership unresolved'
            if n in {'emTrans', 'objTrans', 'sourceActorPrepare', 'sourceActorPlan'}:
                return 'actor preparation call tree'
            if n.startswith('re4dc_actor_') and any(t in n for t in ('plan_', 'stage', 'retire')):
                return 'actor preparation call tree'
            if n in {'EspTrans', 'EspgenTrans', 'EspCommonTrans'} or n.startswith('IDSystem::trans'):
                return 'effect and ID presentation call tree'
            if n in {'Render_before', 'Render_done', 'Render_swap'}:
                return n + ' call tree'
            if n in WAIT:
                return 'wait and idle call tree'
            if n.startswith(('irq_', 'vma_table_', 'thd_', 'maple_')):
                return 'interrupt or KOS service; interrupted phase unresolved'
            if n in {'Trans', 'Render', 're4dc_coarse_draw'}:
                return n + ' residual; phase unresolved'
            idx = nodes[idx]['parent']
        return 'outside recognized call context'

    for node in nodes.values():
        parent = nodes[node['parent']]
        node['caller'] = parent['func'] if node['node'] else '<boundary>'
        node['caller_category'] = parent['category'] if node['node'] else '<boundary>'
        node['self_nominal_ms_per_sample'] = node['self_cycles'] / denom
        node['calls_per_sample'] = node['calls'] / nframes
        node['ownership'] = ownership(node['node'])
        # Every node is included once, including trace-boundary/root self time.
        key = (node['category'], node['func'], node['caller_category'], node['caller'])
        grouped[key][0] += node['self_cycles']
        grouped[key][1] += node['calls']
        cats[node['category']] += node['self_cycles'] / denom
        owners[node['ownership']] += node['self_cycles'] / denom
    callers = [dict(category=k[0], func=k[1], caller_category=k[2], caller=k[3],
                    self_nominal_ms_per_sample=v[0] / denom, calls_per_sample=v[1] / nframes)
               for k, v in grouped.items()]
    callers.sort(key=lambda r: r['self_nominal_ms_per_sample'], reverse=True)
    node_rows = sorted(nodes.values(), key=lambda r: r['self_cycles'], reverse=True)
    write_tsv(out / 'call_nodes.tsv', node_rows,
              ('node', 'parent', 'entry', 'ownership', 'category', 'func', 'file', 'caller_category', 'caller',
               'self_cycles', 'calls', 'self_nominal_ms_per_sample', 'calls_per_sample'))
    write_tsv(out / 'callers.tsv', callers,
              ('category', 'func', 'caller_category', 'caller', 'self_nominal_ms_per_sample', 'calls_per_sample'))
    write_tsv(out / 'call_ownership.tsv',
              [dict(ownership=k, self_nominal_ms_per_sample=v) for k, v in
               sorted(owners.items(), key=lambda kv: kv[1], reverse=True)],
              ('ownership', 'self_nominal_ms_per_sample'))
    total = sum(n['self_cycles'] for n in nodes.values()) / denom
    delta = total - info['mean_ms']
    if abs(delta) > 1 / cycles_per_ms:
        raise ValueError(f'Call-tree self sum differs from frame total by {delta} ms')
    return {'source': str(cg), 'cg_sha256': sha(cg / 'cg.cg.tsv'), 'symbols_sha256': sha(cg / 'cg.syms.txt'),
            'nodes': len(nodes), 'frame_info': info, 'self_sum_ms': total,
            'reconciled': True, 'delta_ms': delta, 'categories_nominal_ms': dict(cats),
            'ownership_nominal_ms': dict(owners)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--split-script', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'benchmark/bench-split.py')
    parser.add_argument('--cg-dir', type=Path)
    parser.add_argument('--cycles-per-ms', type=float, default=200000.0)
    parser.add_argument('--label', default='model sample interval; pacing/fixture must be checked separately')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    classify = classifier(args.split_script)
    rows, flat = flat_account(args.evidence, args.out, classify, args.cycles_per_ms)
    cg = args.cg_dir or args.evidence / 'cg'
    result = {'label': args.label, 'evidence': str(args.evidence.resolve()),
              'units': 'milliseconds per sampled trace interval',
              'warning': 'MODEL DIAGNOSTIC. Function categories are not console benchmark phases. '
                         'Nominal caller costs are not calibrated console costs. No inclusive time is summed. '
                         'Draw/skip pipeline alignment must be established before per-picture comparison.',
              'cycles_per_ms': args.cycles_per_ms, 'flat': flat}
    if (cg / 'cg.cg.tsv').exists():
        result['call_tree'] = call_account(cg, args.out, rows, classify, args.cycles_per_ms)
    result['provenance'] = {name: (args.evidence / name).read_text(encoding='utf-8').strip()
                            for name in ('candidate.txt', 'elf.sha256', 'fixture.json', 'source-commit.txt')
                            if (args.evidence / name).exists()}
    (args.out / 'account.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'out': str(args.out), 'flat_rows': flat['rows'],
                      'reconciliation': {k: {a:b for a,b in v.items() if a != 'traces'}
                                         for k,v in flat['reconciliation'].items()},
                      'call_tree_self_ms': result.get('call_tree', {}).get('self_sum_ms')}, indent=2))


if __name__ == '__main__':
    main()
