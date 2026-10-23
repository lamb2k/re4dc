#!/usr/bin/env python3
"""Compare production selection admission and replay with controlled edges.

Extracts SELECT_ONLY's real admission branch, ordinary setup, capacity drain,
queue snapshots, chunk_flush and chunk_emit. Visibility, geometry and submit
ownership are controlled here; check_geometry/check_runtime cover their actual
runtime bodies separately. Every emitted event word is compared, not hashes.
"""
import argparse
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
spec = importlib.util.spec_from_file_location("replay_boundary", HERE / "check_runtime.py")
boundary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boundary)
function = boundary.original.function


def sources():
    path = DC / "game/platform/native_static.cpp"
    raw = path.read_text()
    selector = path.parent / "include/scenery_chunk_select.inc"
    far = path.parent / "include/scenery_part_far.inc"
    source = raw.replace('#include "include/scenery_chunk_select.inc"', selector.read_text())
    start = source.index('#if RE4DC_SCENERY_SELECT_ONLY\n            {')
    end = source.index('#if RE4DC_PS2_VERTEX_ALPHA\n            const bool marked=', start)
    full_end = source.index('#if RE4DC_SCENERY_CHUNK\n            // SCENERY_CHUNK: select now', end)
    dispatch_end = source.index('#if RE4DC_PS2_PVS\n            d.pvs_finish(result>0);', full_end)
    values = {
        'PICK_DEFINITION': function(source, 'struct Pick {') + ';',
        'CHUNK_OK': function(source, 'bool chunk_ok()const'),
        'CHUNK_EMIT': function(source, '__attribute__((noinline)) int chunk_emit('),
        'CHUNK_PART': function(source, 'struct ChunkPart {'),
        'CHUNK_FLUSH': function(source, 'auto chunk_flush=[&]()->int'),
        'REPLAY_RESTART': '#if RE4DC_SCENERY_REPLAY_LEAN\n' + function(source,
            '[[gnu::always_inline]] void chunk_restart()') + '\n#endif',
        'EARLY_BRANCH': source[start:end],
        'FULL_SETUP': source[end:full_end],
        'CHUNK_DISPATCH': source[full_end:dispatch_end],
    }
    template = (HERE / 'fixture_admission.cpp.in').read_text()
    for name, value in values.items():
        value = value.replace('#include "include/scenery_part_far.inc"', far.read_text())
        template = template.replace('@' + name + '@', value)
    assert not re.search(r'@[A-Z_]+@', template)
    return template, values, (path, selector, far)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    source, values, files = sources()
    fixture = output / 'admission.cpp'
    fixture.write_text(source)
    rows, hashes, total = [], {}, 0
    for pvs, select, batch in itertools.product((0, 1), repeat=3):
        if pvs and batch:
            continue  # existing submit batch option explicitly excludes PVS
        pair = f'p{pvs}-s{select}-b{batch}'
        baseline = None
        for replay in (0, 1):
            label = pair + f'-r{replay}'
            binary = output / label
            command = ['g++', '-std=c++20', '-O2', '-Wall', '-Wextra', '-Wno-unused-variable',
                f'-DRE4DC_SCENERY_SELECT_ONLY={select}', f'-DRE4DC_SCENERY_SUBMIT_BATCH={batch}',
                f'-DRE4DC_SCENERY_REPLAY_LEAN={replay}', f'-DRE4DC_PS2_PVS={pvs}',
                str(fixture), '-o', str(binary)]
            run = subprocess.run(command, cwd=ROOT, capture_output=True)
            (output / (label + '.compile.log')).write_bytes(run.stdout + run.stderr)
            assert run.returncode == 0, (label, run.stderr.decode())
            run = subprocess.run([str(binary)], cwd=ROOT, capture_output=True)
            (output / (label + '.stdout')).write_bytes(run.stdout)
            (output / (label + '.stderr')).write_bytes(run.stderr)
            assert run.returncode == 0, (label, run.stderr.decode())
            assert len(run.stdout.splitlines()) == 3564 * 2, label
            hashes[label] = hashlib.sha256(run.stdout).hexdigest()
            if not replay:
                baseline = run.stdout
            else:
                assert baseline == run.stdout, (label, 'full queue/admission event words differ')
        total += 3564
        rows.append(dict(pvs=pvs, select=select, batch=batch, comparisons=3564, exact_events_equal=True))
    report = dict(status='PASS', comparisons=total, configurations=len(rows)*2,
        source_sha256={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files},
        extracted_sha256={name: hashlib.sha256(value.encode()).hexdigest() for name, value in values.items()},
        combinations=rows, output_sha256=hashes, scope=__doc__)
    (output / 'admission-controls.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(status='PASS', comparisons=total, configurations=len(rows)*2)))


if __name__ == '__main__':
    main()
