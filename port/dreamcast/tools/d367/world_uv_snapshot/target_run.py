#!/usr/bin/env python3
"""Price the compiled UV replay delta with the qualified SH4 setup interpreter.

The production replay/reset/setup bodies and layout run as compiled. The actual
geometry edge is observed and excluded, as are hardware TA submission and matrix
transfer. Perfect D-cache is assumed; read/write bytes and repeated 32-byte line
touches are reported independently. These are model estimates, not console or
Flycast measurements. Queue admission snapshot copies are outside this trace.
"""
import argparse
import hashlib
import importlib.util
import json
import struct
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPLAY = HERE.parent / 'world_replay_lean'
sys.path.insert(0, str(REPLAY))
spec = importlib.util.spec_from_file_location('uv_target_reference', REPLAY / 'target_run.py')
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact(row):
    traffic = row['traffic']['cached']
    out = dict(instructions=row['instructions'], loads=traffic['load_instructions'],
        stores=traffic['store_instructions'], load_bytes=traffic['load_bytes'], store_bytes=traffic['store_bytes'],
        distinct_32b_lines=traffic['unique_data_lines'], repeated_32b_line_touches=row['segment_data_line_touches'],
        fixture_peak_stack_bytes=row['peak_stack_bytes'])
    if 'model_cycles' in row:
        out.update(warm_i_cycles=row['model_cycles'], cold_i_cycles=row['cold_icache']['model_cycles'])
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--host-cc', default='gcc')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    build = json.loads(args.build.read_text())
    cases_path = Path(build['cases'])
    cases = json.loads(cases_path.read_text())
    case = next(row for row in cases if row['name'] == 'whole-inside')
    data = (cases_path.parent / case['file']).read_bytes()
    assert hashlib.sha256(data).hexdigest() == case['sha256']
    paths = {name: Path(row['elf']) for name, row in build['arms'].items()}
    models = {}
    for name, path in paths.items():
        assert digest(path) == build['arms'][name]['sha256']
        models[name] = reference.pipeline_cost.Model(output / ('model-' + name), path, args.host_cc)
    rows = []
    for shape in (0, 1, 2):
        for parts in (0, 1, 8, 20, 48):
            arms, semantics, totals = {}, {}, {}
            for arm, path in paths.items():
                machine, symbols, layout = reference.load(path)
                reference.prepare(machine, symbols, layout, data)
                row, trace, semantic = reference.replay(machine, symbols, parts, shape)
                if shape == 0:
                    row.update(reference.price(models[arm], f'replay-{parts}', trace))
                arms[arm], semantics[arm], totals[arm] = row, semantic, compact(row)
            first = next(iter(semantics.values()))
            assert all(value == first for value in semantics.values()), (parts, shape, 'semantic replay edge mismatch')
            rows.append(dict(parts=parts, shape=shape, arms=arms, totals=totals))
            (output / 'progress.json').write_text(json.dumps(rows, indent=2) + '\n')
            print('PASS UV replay', parts, shape, flush=True)
    special_controls = []
    for words in ((0x80000000, 0x7fc12345), (0x7f812345, 0xffc54321)):
        expected = struct.pack('<2I', *words)
        semantics = []
        for arm, path in paths.items():
            machine, symbols, layout = reference.load(path)
            reference.prepare(machine, symbols, layout, data)
            address = machine.fields['material'] + machine.fields['material_uv']
            machine.map(address, expected)
            row, trace, semantic = reference.replay(machine, symbols, 8, 0)
            assert machine.bytes_at(address, 8) == expected, (arm, words, 'pending UV bits')
            assert all(bytes.fromhex(edge['uv_offset']) == expected for edge in row['edge_records']), (arm, words)
            semantics.append(semantic)
        assert all(value == semantics[0] for value in semantics)
        special_controls.append(dict(words=[hex(word) for word in words], arms=len(paths), pieces=8,
            exact_geometry_edge_and_pending_bits=True))
    frame = []
    normal = {row['parts']: row['totals'] for row in rows if row['shape'] == 0}
    for replay in (0, 1):
        for batch in (0, 1):
            totals = {u: {key: 10 * normal[48][f'r{replay}-b{batch}-u{u}'][key] + normal[20][f'r{replay}-b{batch}-u{u}'][key]
                for key in ('warm_i_cycles', 'loads', 'stores', 'load_bytes', 'store_bytes')} for u in (0, 1)}
            delta = {key: totals[1][key] - totals[0][key] for key in totals[0]}
            frame.append(dict(replay_lean=replay, submit_batch=batch, pieces=500, occupancy=[48]*10+[20],
                replay_delta=delta, replay_delta_ms_at_200mhz=delta['warm_i_cycles']/200000,
                additional_admission_copy_architectural_bytes=dict(load_bytes=4000, store_bytes=4000),
                scope='Replay-only model delta for a synthetic 500-piece frame; admission copy/address generation and D-cache miss timing are excluded.'))
    report = dict(status='PASS', baseline=build['base'], scope=__doc__, checks=len(rows),
        target_build_sha256=digest(args.build), memory_controls=reference.target_machine.memory_controls(),
        source_sha256={str(path): digest(path) for path in (Path(__file__), Path(reference.__file__),
            Path(reference.target_machine.__file__), Path(reference.target_machine.scalar.__file__),
            REPLAY / 'memory_trace.py', Path(reference.pipeline_cost.__file__))},
        model={name: model.metadata() for name, model in models.items()}, cases=rows, frame_estimates=frame,
        special_word_controls=special_controls)
    (output / 'target-controls.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(status='PASS', checks=len(rows), arms=len(paths))))


if __name__ == '__main__':
    main()
