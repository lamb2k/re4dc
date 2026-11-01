#!/usr/bin/env python3
"""Execute actual UI submission/deferral bodies with controlled external edges.

This is a final-packet ordering/state comparison, not an asset-backed actor
transform test or a Dreamcast timing/visual result. The real header builder,
packet/direct submission, source-view queue, FIFO drain and Build33 helper are
compiled from the current source. Texture loading and KOS/SQ are instrumented
fixtures. No proprietary game data is used.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
UI = DC / 'game/platform/native_ui.cpp'
BRIDGE = DC / 'game/model_bridge.cpp'
spec = importlib.util.spec_from_file_location('cloud33_extract', DC / 'tools/d367/world_submit_spike/check_runtime.py')
extractor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extractor)
function = extractor.function


def between(source, first, last):
    start = source.index(first) + len(first)
    return source[start:source.index(last, start)]


def own_blocks(source, first_only=False):
    """Return exact Build33 conditional blocks, including their guards."""
    lines = source.splitlines(keepends=True)
    result = []
    at = 0
    while at < len(lines):
        if re.match(r'\s*#\s*if.*\bRE4DC_STATIC_OBJ_BATCH33\b', lines[at]):
            start, depth = at, 1
            at += 1
            while at < len(lines) and depth:
                if re.match(r'\s*#\s*(if|ifdef|ifndef)\b', lines[at]):
                    depth += 1
                elif re.match(r'\s*#\s*endif\b', lines[at]):
                    depth -= 1
                at += 1
            assert not depth
            result.append(''.join(lines[start:at]))
            if first_only:
                return result[0]
        else:
            at += 1
    return '\n'.join(result)


def sources():
    source = UI.read_text()
    result = {
        'RESERVE': function(source, 'extern "C" int re4dc_model_packet_reserve('),
        'BEGIN': function(source, 'extern "C" int re4dc_model_packet_begin('),
        'COMMIT': function(source, 'extern "C" void re4dc_model_packet_commit('),
        'ABORT': function(source, 'extern "C" void re4dc_model_packet_abort('),
        'DIRECT_BEGIN': function(source, 'extern "C" int re4dc_model_direct_begin('),
        'DIRECT_END': between(source, '// WORLD_SUBMIT_END_IMPLEMENTATION\n', '// WORLD_SUBMIT_END_IMPLEMENTATION_END'),
        'STREAM_SELECT': function(source, 'void stream_select(pvr_list_t list){'),
        'STREAM_SEND': between(source, '// SOB33_STREAM_SEND_BEGIN\n', '// SOB33_STREAM_SEND_END'),
        'SELECT_PASS': function(source, 'pvr_list_t select_model_pass('),
        'UI_ORDER_LIST': function(source, 'static pvr_list_t ui_order_polygon_list('),
        'UI_ORDER_HEADER': function(source, 'static void ui_order_polygon_header('),
        'PT_BEGIN': function(source, 'extern "C" int re4dc_model_pt_begin('),
        'WORLD_PACKET': function(source, 'extern "C" int re4dc_ps2_world_packet('),
        'WORLD_PACKET_CULL': function(source, 'extern "C" int re4dc_ps2_world_packet_cull('),
        'SOURCES_RESET': own_blocks(source[source.index('unsigned entry_closed[kTextureCount];'):], first_only=True),
        'QUEUE_TYPES': between(source, 'using SourceLighting=re4dc::render::SourceLighting;', 'bool draining_parts=false,source_draws_finished=false;'),
        'RESET_DEFERRED': function(source, 'void reset_deferred()'),
        'DEFER': function(source, 'int defer_part(const Re4dcModelPart* p,const SourceLighting* source)'),
        'FINISH': function(source, 'extern "C" void re4dc_model_finish_source_draws()'),
        'INVALIDATE': function(source, 'extern "C" void re4dc_model_invalidate_pending()'),
        'OPEN_BARRIER': own_blocks(function(source, 'void stream_open() {')),
        'CLOSE_BARRIER': own_blocks(function(source, 'void stream_close(bool present) {')),
        'FRAME_BARRIER': own_blocks(function(source, 'extern "C" void re4dc_ui_begin()')),
        'RETIRE_BARRIER': own_blocks(function(source, 'extern "C" void re4dc_ui_retire_room()')),
        'SKIP_BARRIER': own_blocks(function(source, 'extern "C" void re4dc_ui_begin_skip()')),
        'LEON_BARRIER': own_blocks(function(source, 'extern "C" std::uint32_t* re4dc_leon_direct_switch(')),
        'COARSE_BARRIER': own_blocks(function(source, 'extern "C" std::uint32_t* re4dc_coarse_begin(')),
        'COARSE_MODE_BARRIER': own_blocks(function(source, 'extern "C" std::uint32_t* re4dc_coarse_begin_mode(')),
        'WORLD_BARRIER': own_blocks(between(source, '// WORLD_SUBMIT_BEGIN_IMPLEMENTATION\n', '// WORLD_SUBMIT_BEGIN_IMPLEMENTATION_END')),
        'BATCH33_STATE': between(source, '// SOB33_STATE_BEGIN\n', '// SOB33_STATE_END'),
    }
    retire = function(source, 'extern "C" void re4dc_ui_retire_room(){')
    assert 'reset_deferred();' in retire and 'sources_reset();' in retire
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    helper = DC / 'game/platform/include/static_obj_batch33.hpp'
    frozen_paths = (UI, BRIDGE, helper, Path(__file__), HERE / 'ui_fixture.cpp.in',
                    DC / 'game/platform/include/native_model.h', DC / 'room/source_lighting.hpp')
    frozen = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in frozen_paths}
    values = sources()
    fixture = (HERE / 'ui_fixture.cpp.in').read_text()
    for key, value in values.items():
        fixture = fixture.replace('@' + key + '@', value)
    assert not re.search(r'@[A-Z_0-9]+@', fixture), 'Unsubstituted source fragment'
    path = out / 'ui_fixture.cpp'
    path.write_text(fixture)
    compositions, mismatches, total_cases = [], [], 0
    for batch in (0, 1):
        for ta_hash in (0, 1):
            name = f'batch{batch}-hash{ta_hash}'
            results, traces = [], []
            for mode in (0, 1):
                label = f'{name}-mode{mode}'
                binary = out / ('ui-' + label)
                command = ['g++', '-std=c++20', '-O2', '-Wall', '-Wextra', '-fpermissive',
                           '-Wno-unused-function', '-Wno-unused-variable',
                           f'-DCHECK_HASH={ta_hash}', f'-DCHECK_BATCH={batch}',
                           '-DRE4DC_STATIC_OBJ_BATCH33=' + str(mode), '-I', str(DC / 'game/platform/include'),
                           str(path), '-o', str(binary)]
                if args.sanitize:
                    command[2:3] = ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-no-pie']
                run = subprocess.run(command, cwd=ROOT, capture_output=True)
                (out / f'compile-{label}.log').write_bytes(run.stdout + run.stderr)
                if run.returncode:
                    raise RuntimeError(run.stderr.decode())
                trace = out / f'run-{label}.semantic.bin'
                environment = None
                if args.sanitize:
                    # LeakSanitizer cannot inspect this sandbox's /proc task
                    # map; address/undefined checks remain enabled and fatal.
                    environment = dict(os.environ, ASAN_OPTIONS='detect_leaks=0',
                                       UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
                run = subprocess.run([str(binary), str(trace)], cwd=ROOT, capture_output=True, env=environment)
                (out / f'run-{label}.stdout').write_bytes(run.stdout)
                (out / f'run-{label}.stderr').write_bytes(run.stderr)
                if run.returncode:
                    raise RuntimeError(label + ': ' + run.stderr.decode())
                results.append([json.loads(line) for line in run.stdout.splitlines()])
                traces.append(trace)
            old, new = results
            assert traces[0].read_bytes() == traces[1].read_bytes(), \
                name + ': exact ordered vertex/header, return, pin or logical asset-packet vectors differ'
            assert len(old) == len(new) and old, 'Missing result rows'
            for a, b in zip(old, new):
                for key in ('case', 'semantic', 'vertices', 'returns', 'pins', 'locks', 'unlocks', 'aborted', 'queue_drops'):
                    if a[key] != b[key]:
                        mismatches.append(dict(composition=name, case=a['case'], field=key, old=a[key], new=b[key]))
                assert a['locks'] == a['unlocks'] and b['locks'] == b['unlocks']
                assert b['headers'] <= a['headers'], (a, b)
                if a['case'] % 100 in (0, 1, 2, 3):
                    assert b['headers'] == 1 and b['headers'] < a['headers'], (name, a, b, 'eligible path never reused')
                if a['case'] % 100 == 4:
                    assert a['headers'] == 5 and b['headers'] == 3, (name, a, b, 'ordered blends failed')
            total_cases += len(old)
            compositions.append(dict(name=name, cases=len(old), old=old, new=new,
                exact_trace_comparison=dict(equal=True, file=traces[0].name, bytes=traces[0].stat().st_size,
                    sha256=hashlib.sha256(traces[0].read_bytes()).hexdigest())))
    (out / 'differences.json').write_text(json.dumps(mismatches, indent=2) + '\n')
    assert not mismatches, 'Output/ordering/state mismatch; see differences.json'
    assert frozen == {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in frozen}, \
        'Source changed during host gate; rerun against one complete snapshot'
    barrier_coverage = {key: dict(executed=True, bytes=len(value), sha256=hashlib.sha256(value.encode()).hexdigest())
                        for key, value in values.items() if key.endswith('_BARRIER')}
    assert all(row['bytes'] for row in barrier_coverage.values()), 'An expected barrier hook is missing'
    report = dict(status='PASS', scope=__doc__, cases=total_cases, sanitize=args.sanitize,
                  sanitizer_scope='ASan+UBSan; leak inspection disabled because sandbox /proc task traversal is unavailable' if args.sanitize else None,
                  source_sha256=frozen, barrier_coverage=barrier_coverage,
                  extracted_sha256={k: hashlib.sha256(v.encode()).hexdigest() for k, v in values.items()},
                  compositions=compositions,
                  coverage=dict(previous_refusals=['single part across placements', '17/65/257 parts', 'ordered blended FIFO'],
                    final_headers='Every one of eight words changed; 256 individual bit flips in helper controls',
                    foreign_packets='Actual custom PT/world/world-cull packet begin and actual subscreen FIFO branch',
                    queue='Actual source-key marker compression/restoration; caller mutation after enqueue does not alter saved marker',
                    logical_asset_audit='Exact full packets compared independently of physical header removal',
                    lifecycle='Actual guarded hooks with controlled scene/frame/retirement/foreign-direct edges'))
    (out / 'ui-controls.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(status='PASS', cases=total_cases, receipt=str(out / 'ui-controls.json'))))


if __name__ == '__main__':
    main()
