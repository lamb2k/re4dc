#!/usr/bin/env python3
"""Replay retained traces with named call watches; never alter or delete inputs.

Event costs are inclusive diagnostics and must not be added together. Aggregate
cg.cg.tsv stores nonoverlapping self costs, usable by account.py --cg-dir OUT.
Trace presence groups describe the image prepared after Frame_cnt increments and
rendered at the start of the next physical iteration. They do not describe the
console benchmark's physical drawn/skip tick partition.
"""
import argparse
import collections
import csv
import json
import hashlib
import os
import re
import subprocess
from pathlib import Path

EXACT = {'TaskScheduler', 'TaskSchedulerMain', 'iTaskScheduler', 'Trans', 'Render',
         'Render_before', 'Render_done', 'Render_swap', 're4dc_pace_begin',
         're4dc_pace_decide_image', 're4dc_pace_end', 're4dc_pace_itask',
         're4dc_pace_test_draw', 're4dc_coarse_tick', 're4dc_coarse_draw',
         're4dc_ps2_world_draw', 'ModelRender', 'ModelRenderBody', 'objTrans', 'emTrans',
         'EspTrans', 'EspgenTrans', 're4dc_ui_frame', 're4dc_ui_begin', 're4dc_ui_end',
         're4dc_ui_begin_skip', 're4dc_ui_end_frame_skip',
         'Esp09_Trans', 'Esp0e_Trans', 'Esp45_Trans', 'Esp47_Trans',
         're4dc_actor_plan_ganado', 're4dc_actor_transaction_stage',
         're4dc_actor_transaction_draw', 'pvr_scene_begin', 'pvr_scene_finish'}
MAIN_WINDOWS = ('TaskScheduler', 'Trans', 'iTaskScheduler', 'Render_before', 'Render',
                'Render_done', 'Render_swap', 're4dc_pace_end')


def key(name):
    return name.replace('(anonymous namespace)::', '').split('(', 1)[0]


def write_tsv(path, rows, fields):
    with path.open('w', encoding='utf-8', newline='') as out:
        writer = csv.DictWriter(out, fields, delimiter='\t', extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--trace-list', type=Path, help='optional newline list of selected raw trace paths')
    parser.add_argument('--simulator', type=Path, default=Path('/root/probe/d367-agents/design-logic/tools/hwsim_cg'))
    parser.add_argument('--nm', default='/opt/toolchains/dc/sh-elf/bin/sh-elf-nm')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--summarize-only', action='store_true', help='rebuild summaries for an existing replay')
    parser.add_argument('--phase-config', type=Path, help='ELF-locked phase boundary and busy-loop addresses')
    parser.add_argument('--benchmark-phases', action='store_true', help='read OTHER_PROFILE marker PCs from this ELF')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if (args.out / 'cg.cg.tsv').exists() and not args.summarize_only:
        raise SystemExit('Output already contains a replay; choose a new --out directory')
    elf = args.evidence / 're4dc-game.elf'
    environment = os.environ.copy()
    environment.pop('OTHER_MARKERS_FILE', None)
    phase_keys = {'OTHER_SEGMENT_ENTRY','OTHER_WAIT_LOOP_START','OTHER_WAIT_LOOP_END',
                  'OTHER_WAIT_FUNC_START','OTHER_WAIT_FUNC_END','OTHER_WAIT_CALL_PC','OTHER_WAIT_RETURN_PC'}
    for name in phase_keys:
        environment.pop(name, None)
    if args.phase_config:
        phase = json.loads(args.phase_config.read_text())
        if hashlib.sha256(elf.read_bytes()).hexdigest() != phase['elf_sha256']:
            raise SystemExit('Phase addresses do not match the exact ELF SHA256')
        if set(phase['environment']) != phase_keys:
            raise SystemExit('Incomplete or unsupported phase address configuration')
        for name, value in phase['environment'].items():
            if not re.fullmatch('[0-9a-fA-F]+', value):
                raise SystemExit('Invalid phase environment')
            environment[name] = value
        (args.out / 'phase-config.json').write_text(json.dumps(phase, indent=2) + '\n')
    raw = subprocess.check_output([args.nm, '-n', str(elf)], text=True)
    demangled = subprocess.check_output([args.nm, '-n', '-C', str(elf)], text=True)
    symbols = [line.split(None, 2) for line in demangled.splitlines()]
    symbols = [s for s in symbols if len(s) == 3 and s[1] in 'TtWw']
    marker_symbols = [s for s in symbols if 're4dc_other_marker_' in s[2]]
    symbols = [s for s in symbols if 're4dc_other_marker_' not in s[2]]
    if args.benchmark_phases:
        kinds = {'phase0':1,'phase1':2,'phase2':3,'phase3':4,'phase4':5,'phase5':6,
                 'instr_begin':7,'instr_end':8,'push_actor':9,'pop_actor':10}
        markers = []
        for addr,kind,name in marker_symbols:
            match = re.fullmatch(r'_?re4dc_other_marker_(main|trans|coarse)_(phase[0-5]|instr_begin|instr_end|push_actor|pop_actor)_[0-9]+',name)
            if not match:
                raise SystemExit(f'Unsupported benchmark marker: {name}')
            markers.append(dict(pc=addr,event=kinds[match[2]],unit=match[1],kind=match[2],symbol=name))
        if set(kinds.values()) != {m['event'] for m in markers} or {m['unit'] for m in markers} != {'main','trans','coarse'}:
            raise SystemExit('Incomplete OTHER_PROFILE marker set')
        if len({m['pc'] for m in markers}) != len(markers):
            raise SystemExit('Duplicate marker addresses')
        marker_path = args.out / 'bench_markers.txt'
        marker_path.write_text(''.join(f"{m['pc']} {m['event']}\n" for m in markers))
        (args.out/'bench_markers.json').write_text(json.dumps(dict(elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest(),
             markers=markers,phase6='instrumentation',initial_phase=4,
             reason='Frame_cnt advances in OTHER immediately before phase0; marker symbols excluded from function starts'),indent=2)+'\n')
        environment['OTHER_MARKERS_FILE'] = str(marker_path)
    funcs = sorted({s[0] for s in symbols})
    watches = [s for s in symbols if key(s[2]) in EXACT or
               re.search(r'(sourceActorPrepare|sourceActorPlan|draw_actors|draw_scenery)', key(s[2]))]
    (args.out / 'cg.syms.txt').write_text(''.join(' '.join(s) + '\n' for s in symbols))
    (args.out / 'cg.funcs.txt').write_text('\n'.join(funcs) + '\n')
    (args.out / 'cg.watch.txt').write_text('\n'.join(sorted({s[0] for s in watches})) + '\n')
    write_tsv(args.out / 'watch_names.tsv', [dict(entry=s[0], func=s[2]) for s in watches], ('entry', 'func'))
    vbr = next((line.split()[0] for line in raw.splitlines() if line.split()[-1] == '_irq_vma_table'), '0')
    if args.trace_list:
        traces = [Path(line) for line in args.trace_list.read_text().splitlines() if line.strip()]
    else:
        traces = sorted((args.evidence / 'trace').glob('trace-*.bin'))
    if not traces or any(not t.is_file() for t in traces):
        raise SystemExit('Missing raw traces; preserve inputs before the standard cg cleanup')
    (args.out / 'inputs.txt').write_text(''.join(str(t) + '\n' for t in traces))
    command = [str(args.simulator), '--elf', str(elf), '--out', str(args.out / 'cgsim'),
               '--cg', str(args.out / 'cg'), '--cg-vbr', vbr,
               '--cg-funcs', str(args.out / 'cg.funcs.txt'), '--cg-watch', str(args.out / 'cg.watch.txt')]
    command += [str(t) for t in traces]
    (args.out / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    if args.prepare_only:
        print(json.dumps({'out': str(args.out), 'traces': len(traces), 'watches': len(watches), 'prepared': True}))
        return
    if not args.summarize_only:
        with (args.out / 'cg.log').open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, env=environment)
    entry_counter = args.out / 'trace_entries'
    subprocess.run(['cc', '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror',
                    str(Path(__file__).with_name('trace_entries.c')), '-o', str(entry_counter)], check=True)
    with (args.out / 'raw_entries.tsv').open('w') as dst:
        subprocess.run([str(entry_counter), str(args.out / 'cg.watch.txt')] + [str(t) for t in traces],
                       stdout=dst, check=True)
    names = {s[0]: s[2] for s in watches}
    raw_count = collections.defaultdict(collections.Counter)
    with (args.out / 'raw_entries.tsv').open() as source:
        for row in csv.DictReader(source, delimiter='\t'):
            raw_count[int(row['sample_index'])][key(names[row['entry']])] += int(row['executed_entry_pc_count'])
    by_frame = collections.defaultdict(list)
    with (args.out / 'cg.calls.tsv').open() as source:
        for row in csv.DictReader(source, delimiter='\t'):
            row['func'] = names.get(row['entry'], '<unknown>')
            by_frame[int(row['frame'])].append(row)
    groups = collections.defaultdict(list)
    frame_rows = []
    event_rows = []
    window_rows = []
    for idx, trace in enumerate(traces):
        calls = by_frame[idx]
        count = collections.Counter(key(c['func']) for c in calls)
        window_ms = collections.defaultdict(float)
        for call in calls:
            n = key(call['func'])
            if n in MAIN_WINDOWS:
                window_ms[n] += float(call['incl_cycles']) / 200000.0
        actual = raw_count[idx]
        if actual['re4dc_ui_begin'] == 1 and not actual['re4dc_ui_begin_skip'] and actual['re4dc_ps2_world_draw']:
            group = 'drawn_image'
        elif actual['re4dc_ui_begin_skip'] == 1 and not actual['re4dc_ui_begin'] and not actual['re4dc_ps2_world_draw']:
            group = 'dropped_image'
        else:
            group = 'ambiguous_image'
        groups[group].append(str(trace))
        for event_idx, call in enumerate(calls):
            event_rows.append(dict(sample_index=idx, trace=str(trace), event_index=event_idx,
                                   **call, inclusive_nominal_ms=float(call['incl_cycles']) / 200000.0))
        frame_rows.append(dict(sample_index=idx, trace=str(trace), group=group,
                               task_calls=actual['TaskScheduler'], itask_calls=actual['iTaskScheduler'],
                               trans_calls=actual['Trans'], render_calls=actual['Render'],
                               world_draw_calls=actual['re4dc_ps2_world_draw'],
                               actor_plan_calls=actual['re4dc_actor_plan_ganado'],
                               actor_draw_calls=actual['re4dc_actor_transaction_draw'],
                               ui_begin_entries=actual['re4dc_ui_begin'],
                               ui_skip_entries=actual['re4dc_ui_begin_skip'],
                               watched_call_count=len(calls)))
        for n in MAIN_WINDOWS:
            window_rows.append(dict(sample_index=idx, trace=str(trace), group=group, func=n,
                                    executed_entry_pcs=actual[n], completed_calls=count[n],
                                    complete=count[n] == actual[n],
                                    inclusive_nominal_ms=window_ms[n] if count[n] == actual[n] else ''))
    write_tsv(args.out / 'events.tsv', event_rows,
              ('sample_index', 'trace', 'event_index', 'frame', 'entry', 'func', 'depth', 'incl_cycles', 'inclusive_nominal_ms'))
    write_tsv(args.out / 'trace_groups.tsv', frame_rows,
              ('sample_index', 'trace', 'group', 'task_calls', 'itask_calls', 'trans_calls', 'render_calls',
               'world_draw_calls', 'actor_plan_calls', 'actor_draw_calls', 'ui_begin_entries', 'ui_skip_entries',
               'watched_call_count'))
    write_tsv(args.out / 'main_windows.tsv', window_rows,
              ('sample_index', 'trace', 'group', 'func', 'executed_entry_pcs', 'completed_calls',
               'complete', 'inclusive_nominal_ms'))
    for name in ('drawn_image', 'dropped_image', 'ambiguous_image'):
        paths = groups.get(name, [])
        (args.out / (name + '.txt')).write_text(''.join(p + '\n' for p in paths))
    print(json.dumps({'out': str(args.out), 'groups': {k: len(v) for k, v in groups.items()},
                      'warning': 'Groups track Render N after prep N; not console physical drawn/skip ticks.'}))


if __name__ == '__main__':
    main()
