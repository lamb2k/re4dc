#!/usr/bin/env python3
"""Run Build 10's actual core against a deterministic clock/thread/PVR oracle."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
DC=HERE.parents[2]
ROOT=DC.parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--sanitize',action='store_true')
    args=parser.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    source=DC/'game/world_census24.cpp'
    header=DC/'game/platform/include/world_census24.h'
    fixture=HERE/'check_core.cpp'
    inputs=(source,header,fixture,Path(__file__))
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    command=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',
             '-DRE4DC_WORLD_CENSUS24_HOST=1','-DRE4DC_WORLD_CENSUS24=1',
             '-I'+str(header.parent),str(source),str(fixture),'-o',str(out/'core')]
    if args.sanitize:command[3:3]=['-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
    compile_run=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
    (out/'compile.log').write_text(compile_run.stdout+compile_run.stderr)
    if compile_run.returncode:raise SystemExit(compile_run.stderr)
    environment=os.environ.copy()
    if args.sanitize:
        # LeakSanitizer cannot enumerate tasks inside the managed sandbox.
        # ASan memory checks and UBSan remain enabled for the real core.
        environment['ASAN_OPTIONS']=environment.get('ASAN_OPTIONS','')+':detect_leaks=0'
    run=subprocess.run([str(out/'core')],cwd=ROOT,capture_output=True,text=True,env=environment)
    (out/'run.log').write_text(run.stdout+run.stderr)
    if run.returncode:raise SystemExit(run.stdout+run.stderr)
    assert hashes=={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},'source changed during run'
    receipt={'status':'PASS','scope':__doc__,'sanitized':args.sanitize,'leak_sanitizer':False,
             'compiler':subprocess.check_output(['g++','--version'],text=True).splitlines()[0],
             'command':command,'source_sha256':hashes,
             'assertions':run.stdout.strip(),'console_measured':False}
    (out/'core-controls.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'status':'PASS','sanitized':args.sanitize,'receipt':str(out/'core-controls.json')}))

if __name__=='__main__':main()
