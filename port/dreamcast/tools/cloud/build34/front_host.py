#!/usr/bin/env python3
"""Execute actual FRONT_TEXOBJ helpers against the uncached production loop.

Every effective GX word, materialized tail, sequential swap and descriptor
side effect is checked. External model/global types preserve accessed SH-4
offsets; host pointers are wider. This is no full native replay, game route,
target performance or console qualification. No proprietary assets are used.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
import front_sources as source
HERE, ROOT = source.HERE, source.ROOT
BASELINE = '36643bf8ab5a78c581274f28eca702ae8aa48330'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--sanitize', action='store_true')
    parser.add_argument('--control-ref', default=BASELINE)
    args = parser.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    files = [*source.source_files(), Path(__file__), HERE / 'front_fixture.cpp.in']
    frozen = {str(p.relative_to(ROOT)): source.sha(p) for p in files}
    results = []
    current_values = source.source_values()
    for name, ref in [('current', None), ('control', args.control_ref)]:
        values = source.source_values(ref)
        types = source.render((HERE / 'front_fixture_types.hpp.in').read_text(), values)
        text = source.render((HERE / 'front_fixture.cpp.in').read_text(), {'TYPES': types})
        cpp = out / (name + '.cpp'); cpp.write_text(text)
        binary = out / name
        flags = ['-std=c++20', '-O2', '-fpermissive', '-Wall', '-Wextra',
                 '-Wno-unused-function', '-Wno-class-memaccess', '-DRE4DC_FRONT_TEXOBJ=1']
        if args.sanitize:
            flags[1:2] = ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-no-pie']
        run = subprocess.run(['g++', *flags, str(cpp), '-o', str(binary)], capture_output=True)
        (out / (name + '-compile.log')).write_bytes(run.stdout + run.stderr)
        if run.returncode: raise RuntimeError(run.stderr.decode())
        env = dict(os.environ)
        if args.sanitize:
            env.update(ASAN_OPTIONS='detect_leaks=0', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        if ref is None:
            run = subprocess.run([str(binary)], capture_output=True, env=env)
            (out / 'current-stdout.log').write_bytes(run.stdout)
            (out / 'current-stderr.log').write_bytes(run.stderr)
            assert run.returncode == 0, run.stderr.decode()
            rows = [json.loads(line) for line in run.stdout.splitlines()]
            assert len(rows) == 23, len(rows)
        else:
            for kind in range(7):
                run = subprocess.run([str(binary), str(kind)], capture_output=True, env=env)
                (out / ('control-' + str(kind) + '.log')).write_bytes(run.stdout + run.stderr)
                assert run.returncode == 31 and b'GX word mismatch' in run.stderr, (kind, run.returncode, run.stderr.decode())
                results.append(dict(mutation=kind, expected_counterexample=True, returncode=run.returncode))
    assert frozen == {name: source.sha(ROOT / name) for name in frozen}, 'Source changed during gate'
    report = dict(status='PASS', scope=__doc__, source_sha256=frozen,
        extracted_sha256={name: hashlib.sha256(text.encode()).hexdigest() for name, text in current_values.items()},
        cases=len(rows), checks=sum(row['checks'] for row in rows), scenarios=rows,
        control_ref=args.control_ref, control_counterexamples=results,
        sanitize=args.sanitize,
        sanitizer_scope='ASan+UBSan; leak inspection disabled for unavailable sandbox /proc traversal' if args.sanitize else None,
        limits='Actual cache helpers and uncached native init loop, not the complete frontNativeModelTrans caller. '
               'Current release ACTOR_TRANSACTION forbids FRONT_NATIVE=2. No route/image/STRICT or allocation-generation proof is claimed.')
    path = out / 'front-host.json'; path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(status='PASS', cases=len(rows), checks=report['checks'], counterexamples=len(results), receipt=str(path))))


if __name__ == '__main__': main()
