#!/usr/bin/env python3
"""Focused source-extracted world submission boundary comparisons.

This executes the production begin/end and batch functions on the host with
controlled texture, owner, packet and store-queue edges. It is a state/output
comparison, not a Dreamcast timing measurement or a complete renderer test.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
SOURCE = DC / 'game/platform/native_ui.cpp'
STATIC = DC / 'game/platform/native_static.cpp'


def function(source, signature):
    """Return one exact source definition, ignoring braces inside comments."""
    start = source.index(signature)
    begin = source.index('{', start)
    depth = 0
    tokens = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]')
    for match in tokens.finditer(source, begin):
        token = match.group()
        if token == '{':
            depth += 1
        elif token == '}':
            depth -= 1
            if not depth:
                return source[start:match.end()]
    raise ValueError('Unclosed source definition: ' + signature)


def extract(source=None):
    """Return actual production bodies; target-cost tools may reuse these."""
    source = SOURCE.read_text() if source is None else source
    def marked(name):
        first = '// WORLD_SUBMIT_' + name + '_IMPLEMENTATION\n'
        last = '// WORLD_SUBMIT_' + name + '_IMPLEMENTATION_END'
        begin = source.index(first) + len(first)
        return source[begin:source.index(last, begin)]
    world = STATIC.read_text()
    end_first = world.index('#if RE4DC_SCENERY_SUBMIT_BATCH\n    Re4dcWorldSubmitBatch* submit_batch')
    end_last = world.index('    void put(unsigned n)', end_first)
    return {
        'BATCH_HEADER': (SOURCE.parent / 'include/scenery_submit_batch.h').read_text(),
        'DIRECT_BEGIN': marked('BEGIN'),
        'DIRECT_END': marked('END'),
        'PICK_DEFINITION': function(world, 'struct Pick {'),
        'EMITTER_END': world[end_first:end_last],
        'EMITTER_BIND': function(world, 'bool bind(){'),
        'CHUNK_EMIT': function(world, '__attribute__((noinline)) int chunk_emit('),
        'CHUNK_PART': function(world, 'struct ChunkPart {'),
        'CHUNK_FLUSH': function(world, 'auto chunk_flush=[&]()->int'),
    }


def fixture_source():
    values = extract()
    source = (HERE / 'check_fixture.cpp.in').read_text()
    source = source.replace('@QUEUE_FIXTURE@', (HERE / 'check_queue.cpp.in').read_text())
    for key, value in values.items():
        source = source.replace('@' + key + '@', value)
    return source, values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    out = args.output.resolve()
    source, values = fixture_source()
    fixture = out / 'check_fixture.cpp'
    fixture.write_text(source)
    cases = list(range(41)) + list(range(100, 345))
    differences, lock_counts = [], {}
    for diagnostics in (0, 1):
        results = []
        for mode in (0, 1):
            label = 'd%d-m%d' % (diagnostics, mode)
            binary = out / ('check-' + label)
            command = ['g++', '-std=c++20', '-O2', '-Wall', '-Wextra',
                       '-DRE4DC_SCENERY_SUBMIT_BATCH=%d' % mode,
                       '-DCHECK_DIAGNOSTICS=%d' % diagnostics,
                       str(fixture), '-o', str(binary)]
            run = subprocess.run(command, cwd=ROOT, capture_output=True)
            (out / ('compile-' + label + '.log')).write_bytes(run.stdout + run.stderr)
            if run.returncode:
                raise RuntimeError(run.stderr.decode())
            stdout, stderr = [], []
            for case in cases:
                run = subprocess.run([str(binary), str(case)], cwd=ROOT, capture_output=True)
                stdout.append(run.stdout); stderr.append(run.stderr)
                if run.returncode:
                    (out / ('failed-' + label + '.stderr')).write_bytes(run.stderr)
                    raise RuntimeError('Case %d, %s: %s' % (case, label, run.stderr.decode()))
                assert len(run.stdout.splitlines()) == 1, 'Expected one complete report for case %d, %s' % (case, label)
            output, errors = b''.join(stdout), b''.join(stderr)
            (out / ('check-' + label + '.stdout')).write_bytes(output)
            (out / ('check-' + label + '.stderr')).write_bytes(errors)
            results.append(output)
            lock_counts[label] = [dict(case=int(m[0]), locks=int(m[1]), unlocks=int(m[2]))
                                  for m in re.findall(rb'(\d+) lock=(\d+) unlock=(\d+)', errors)]
            assert [row['case'] for row in lock_counts[label]] == cases, 'Missing lock reports for ' + label
            assert all(row['locks'] == row['unlocks'] for row in lock_counts[label]), 'Unbalanced lock lifetime in ' + label
        old, new = [data.decode().splitlines() for data in results]
        assert len(old) == len(new) == len(cases), 'Missing or extra state/output reports'
        differences.extend(dict(diagnostics=diagnostics, old=a, new=b)
                           for a, b in zip(old, new) if a != b)
    if differences:
        (out / 'differences.json').write_text(json.dumps(differences, indent=2) + '\n')
        raise AssertionError('Submission state/output differs; see differences.json')
    assert lock_counts['d0-m1'][0]['locks'] < lock_counts['d0-m0'][0]['locks'], 'Eligible fixture never batched'
    claimed = {row['case']: row for row in lock_counts['d0-m1']}[34]
    assert claimed['locks'] == claimed['unlocks'] == 8, 'Claimed source group retained a lock'
    report = dict(status='PASS', cases=len(cases)*2,
                  source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                  world_source_sha256=hashlib.sha256(STATIC.read_bytes()).hexdigest(),
                  extracted_sha256={key: hashlib.sha256(value.encode()).hexdigest()
                                    for key, value in values.items()},
                  lock_counts=lock_counts,
                  scope='Actual source bodies; controlled texture/owner/stream/SQ edges. No hardware timing or full-game visual claim.')
    (out / 'check-controls.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS world submission equivalence: %d controls' % report['cases'])


if __name__ == '__main__':
    main()
