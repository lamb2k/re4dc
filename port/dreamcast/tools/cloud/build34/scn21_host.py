#!/usr/bin/env python3
"""Bounded source-extracted SCCN/SCPS reader and chunk fallback-counter checks.

The production loader and sink are compiled verbatim. Synthetic cones come
from the existing public builder, with controlled malformed variants. This is
format/lifecycle validation, not a geometry certificate or a console result.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import re
import struct
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
STATIC = DC / 'game/platform/native_static.cpp'
CHUNK = DC / 'game/platform/native_actor_chunk.inc'
HEADER = DC / 'game/platform/include/scn21_validate34.hpp'
BUILDER = DC / 'tools/d367/scenery21/scn21_build.py'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


extractor = module('build34_extract', DC / 'tools/d367/world_submit_spike/check_runtime.py')
function = extractor.function


def source_fragments():
    chunk = CHUNK.read_text()
    declaration = chunk.index('unsigned chunk_backend_meshlets, chunk_backend_fallbacks;')
    begin = chunk.rindex('#if !RE4DC_ACTOR_LIGHT_FAST_ONLY', 0, declaration)
    return {
        'OPEN': function(STATIC.read_text(), 'void scn21_open(GCASSET_STATIC_ONLY_PARAM)'),
        'DECLARATIONS': chunk[begin:chunk.index('\n', declaration)],
        'SINK': function(chunk, 'struct ChunkSink {') + ';',
        'BEGIN': function(chunk, 'inline void chunk_sink_begin('),
        'DISPATCH': function(chunk, 'inline bool chunk_sink_strips('),
    }


def builder_bytes():
    builder = module('build34_builder', BUILDER)
    rng = random.Random(3401)
    records = []
    for i in range(128):
        if i == 0:
            pos = [(0, 0, 0), (10, 0, 0), (0, 10, 0)]
        else:
            pos = [tuple(rng.randrange(0, 65536) for _ in range(3)) for _ in range(3)]
        strips = [[0, 1, 2]] if i % 19 != 18 else [[0, 0, 0]]
        lo = tuple(min(p[a] for p in pos) for a in range(3))
        hi = tuple(max(p[a] for p in pos) for a in range(3))
        record, _ = builder.cone(strips, pos, lo, hi)
        records.append(record)
    assert records[0][3] != 0 and any(r[3] == 0 for r in records)
    return struct.pack('<64f', *builder.TAB2) + b''.join(records)


def render(template, values):
    source = (HERE / template).read_text()
    for name, value in values.items():
        source = source.replace('@' + name + '@', value)
    assert not re.search(r'@[A-Z_0-9]+@', source)
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    files = [STATIC, CHUNK, HEADER, BUILDER, DC / 'game/scenery19.mk', Path(__file__),
             HERE / 'scn21_fixture.cpp.in', HERE / 'chunk_counter_fixture.cpp.in',
             DC / 'tools/d367/world_submit_spike/check_runtime.py']
    frozen = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    fragments = source_fragments()
    data = builder_bytes()
    (out / 'builder-cones.bin').write_bytes(data)
    values = dict(fragments, BUILDER_BYTES=','.join(map(str, data)), MESHLETS='32', GROUPS='4')
    paths = {}
    for kind, template in [('scn21', 'scn21_fixture.cpp.in'), ('counter', 'chunk_counter_fixture.cpp.in')]:
        path = out / (kind + '.cpp')
        path.write_text(render(template, values))
        paths[kind] = path
    results = []
    variants = []
    for cone, piece in [(1, 0), (0, 1), (1, 1)]:
        for ab in (0, 1):
            for gc in (0, 1):
                variants.append(('scn21', f'c{cone}-p{piece}-ab{ab}-gc{gc}', {
                    'RE4DC_SCENERY_CONE': cone, 'RE4DC_SCENERY_PIECE_STATE': piece,
                    'RE4DC_SCENERY21_AB': ab, 'RE4DC_GC_ASSET_GATE': gc}))
    for backend in (0, 1):
        for fast in (0, 1):
            for audit in (0, 1):
                variants.append(('counter', f'be{backend}-fast{fast}-audit{audit}', {
                    'RE4DC_CHAR_CHUNK_BACKEND': backend, 'RE4DC_ACTOR_LIGHT_FAST_ONLY': fast,
                    'RE4DC_DRAW_FALLBACK_AUDIT': audit}))
    for kind, label, flags in variants:
        binary = out / (kind + '-' + label)
        command = ['g++', '-std=c++17', '-O2', '-ffast-math', '-Wall', '-Wextra',
                   '-Wno-unused-function', '-Wno-unused-variable', '-Wno-unused-parameter',
                   '-I', str(HEADER.parent)]
        if args.sanitize:
            command[2:3] = ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-no-pie']
        command += [f'-D{k}={v}' for k, v in flags.items()] + [str(paths[kind]), '-o', str(binary)]
        run = subprocess.run(command, cwd=ROOT, capture_output=True)
        (out / ('compile-' + binary.name + '.log')).write_bytes(run.stdout + run.stderr)
        if run.returncode:
            raise RuntimeError(run.stderr.decode())
        env = dict(os.environ, ASAN_OPTIONS='detect_leaks=0', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1') if args.sanitize else None
        run = subprocess.run([str(binary)], cwd=ROOT, capture_output=True, env=env)
        (out / (binary.name + '.stdout')).write_bytes(run.stdout)
        (out / (binary.name + '.stderr')).write_bytes(run.stderr)
        if run.returncode:
            raise RuntimeError(binary.name + ': ' + run.stderr.decode())
        results.append(dict(kind=kind, label=label, **json.loads(run.stdout)))
    for p in files:
        assert frozen[str(p.relative_to(ROOT))] == hashlib.sha256(p.read_bytes()).hexdigest(), str(p) + ' changed during checks'
    report = {
        'status': 'PASS', 'sanitize': args.sanitize, 'fast_math': True, 'variants': results,
        'cases': sum(r['cases'] for r in results), 'checks': sum(r['checks'] for r in results),
        'source_sha256': frozen, 'fragment_sha256': {k: hashlib.sha256(v.encode()).hexdigest() for k, v in fragments.items()},
        'builder_data_sha256': hashlib.sha256(data).hexdigest(),
        'scope': 'Actual loader and sink dispatch with controlled room/package/backend edges; no private geometry or target timing.',
        'limits': 'SCCN format checks do not authenticate the geometric cone certificate. A finite undersized radius is explicitly accepted by a limitation test.'
    }
    (out / 'host.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('status', 'sanitize', 'cases', 'checks')}))


if __name__ == '__main__':
    main()
