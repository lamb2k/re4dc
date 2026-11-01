#!/usr/bin/env python3
"""Build24 actual observer + existing PM14 owner, deterministic synthetic controls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
CASES = ('partition', 'skipped', 'lifecycle', 'nesting', 'stale', 'alien',
         'incomplete', 'backward', 'depth', 'invalid')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--sanitize',action='store_true')
    args=parser.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    files=[DC/'game/draw_setup_audit.cpp',DC/'game/platform/include/draw_setup_audit.h',
           DC/'game/perf_phase_miss.cpp',DC/'game/platform/include/perf_phase_miss.h',
           DC/'game/platform/include/perf_phase_accounting.hpp',HERE/'check_core.cpp',Path(__file__)]
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    inputs=hashes();results=[];commands=[]
    env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0')
    for event in (0,15,37):
        exe=out/f'core-{event}'
        command=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',
                 '-Wno-misleading-indentation','-DRE4DC_DRAW_SETUP_AUDIT_HOST=1',
                 '-DRE4DC_DRAW_SETUP_AUDIT=1','-DRE4DC_DRAW_SETUP_AUDIT_WINDOW=3',
                 '-I'+str(DC/'game/platform/include')]
        if args.sanitize:command+=['-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
        command += [str(DC/'game/draw_setup_audit.cpp'),str(HERE/'check_core.cpp')]
        if event:command += ['-DRE4DC_PERF_PHASE_MISS=1','-DRE4DC_PERF_PHASE_MISS_HOST=1',
                            '-DRE4DC_WORLD_CENSUS24=1',f'-DRE4DC_PERF_PHASE_MISS_EVENT={event}',str(DC/'game/perf_phase_miss.cpp')]
        command += ['-o',str(exe)];commands.append(command)
        p=subprocess.run(command,capture_output=True,text=True)
        (out/f'compile-{event}.log').write_text(p.stdout+p.stderr)
        if p.returncode:raise RuntimeError(p.stderr)
        for case in CASES+(('pm-loss','pm-unrun','pm-wrap') if event else ()):
            p=subprocess.run([str(exe),case],env=env,capture_output=True,text=True)
            (out/f'{event}-{case}.log').write_text(p.stdout+p.stderr)
            if p.returncode:raise RuntimeError(f'{event}/{case}: {p.stdout}{p.stderr}')
            results.append(dict(event=event,case=case,status='PASS'))
    assert inputs==hashes(),'inputs changed while running'
    report=dict(status='PASS',scope=__doc__,sanitized=args.sanitize,source_sha256=inputs,
                commands=commands,cases=results,case_count=len(results),
                limits='Injected clocks/registers; verifies accounting, isolation, parity of denominators and ownership. No console timing or hardware PMU qualification.')
    (out/'core-controls.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',cases=len(results),sanitized=args.sanitize,receipt=str(out/'core-controls.json'))))

if __name__=='__main__':main()
