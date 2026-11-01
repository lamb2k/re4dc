#!/usr/bin/env python3
"""Actual DFA/FA29/window collectors plus exact bounded-ring lifecycle oracle.

The host IRQ shim serializes worker writers but does not model KOS latency.
Snapshots and last-N drawn-attempt sums are exercised without private data,
gameplay, rendering or GPU-presentation claims.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;DC=HERE.parents[2];ROOT=DC.parents[1];GAME=DC/'game'


def source_files():
    return [Path(__file__),HERE/'window_fixture.cpp.in',GAME/'draw_fallback_audit.cpp',GAME/'fallback_audit29.cpp',
        GAME/'fallback_window35.cpp',*[GAME/'platform/include'/name for name in ('fallback_window35.h',
        'fallback_window35_core.hpp','fallback_audit29.h','fallback_audit35.h','draw_fallback_audit.h')],
        *sorted((GAME/'platform/include').glob('draw_fallback_*.def')),
        GAME/'platform/include/fallback_audit29.def',GAME/'platform/include/fallback_audit35.def']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path);parser.add_argument('--sanitize',action='store_true')
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    files=source_files();frozen={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (out/'arch').mkdir();(out/'arch/irq.h').write_text('#pragma once\nextern "C" int irq_disable();\nextern "C" void irq_restore(int);\n')
    cpp=out/'fixture.cpp';cpp.write_bytes((HERE/'window_fixture.cpp.in').read_bytes())
    results=[]
    for gaps,n in ((0,1),(0,64),(1,1),(1,3),(1,32),(1,64)):
        name=f'gap{gaps}-n{n}';binary=out/name
        flags=['-std=c++17','-O2','-Wall','-Wextra','-Werror','-Wno-address','-pthread',
            '-DRE4DC_DRAW_FALLBACK_AUDIT=1','-DRE4DC_FALLBACK_AUDIT29=1',
            '-DRE4DC_FALLBACK_AUDIT35='+str(gaps),'-DRE4DC_FALLBACK_WINDOW35='+str(n),
            '-I'+str(out),'-I'+str(GAME)]
        if args.sanitize:flags[1:2]=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie']
        build=subprocess.run(['g++',*flags,str(cpp),'-o',str(binary)],capture_output=True)
        (out/(name+'-compile.log')).write_bytes(build.stdout+build.stderr)
        if build.returncode:raise RuntimeError(build.stderr.decode())
        env=dict(os.environ)
        if args.sanitize:env.update(ASAN_OPTIONS='detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        run=subprocess.run([str(binary)],capture_output=True,env=env)
        (out/(name+'-run.log')).write_bytes(run.stdout+run.stderr)
        assert run.returncode==0,(name,run.stdout.decode(),run.stderr.decode())
        results.append(dict(profile=name,**json.loads(run.stdout)))
        print('PASS',name,flush=True)
    assert frozen=={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in frozen},'source changed during host gate'
    report=dict(status='PASS',scope=__doc__,sanitize=args.sanitize,source_sha256=frozen,profiles=results,
        checks=sum(row['checks'] for row in results),sanitizer_scope='ASan/UBSan; leak inspection disabled for sandbox /proc restrictions' if args.sanitize else None,
        coverage=['every DFA/FA29/FA35 reason','skipped current vs retained lastdraw','outside-active worker events',
            'interrupt/pause/resume/room/restart','tick32 wrap','ring expiry1/3/32/64','per-tick overflow expiry',
            'room-only saturation does not poison window','u64 denominator saturation','max sums and192-byte rows'])
    (out/'window-host.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',profiles=len(results),checks=report['checks'])))


if __name__=='__main__':main()
