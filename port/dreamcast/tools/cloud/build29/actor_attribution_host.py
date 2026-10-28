#!/usr/bin/env python3
"""Exercise the production Build29 actor attribution include and formatter.

Uses the real model-view/lighting headers; only the source-identity callback and
the selected-path Lights view are synthetic. Full production layout and flags
are checked by build_controls.py, separately. No game assets are used.
"""
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
    fixture=out/'fixture.cpp'
    fixture.write_text((HERE/'actor_attribution_fixture.cpp.in').read_text().replace('@DC@',str(DC)))
    cases=[]
    for probe in (0,2):
        exe=out/f'probe-{probe}'
        command=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',f'-DRE4DC_ACTOR_PROBE_LIGHT={probe}',
                 str(fixture),'-o',str(exe)]
        if args.sanitize:command[1:1]=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
        subprocess.run(command,check=True,capture_output=True,text=True)
        env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0') if args.sanitize else None
        result=subprocess.run([str(exe)],check=True,capture_output=True,text=True,env=env)
        cases.append(json.loads(result.stdout))
    files=[Path(__file__),HERE/'actor_attribution_fixture.cpp.in',
           DC/'game/platform/include/fallback_actor_audit29.hpp',DC/'game/platform/include/fallback_actor_audit29.inc',
           DC/'game/platform/include/native_model.h',DC/'room/source_lighting.hpp']
    report=dict(status='PASS',scope=__doc__,sanitized=args.sanitize,cases=cases,
                leak_detection=False if args.sanitize else None,
                source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    (out/'actor-attribution.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',profiles=len(cases),max_rows_bytes=max(r['max_rows_bytes'] for r in cases),
                          longest_row=max(r['longest_row'] for r in cases))))

if __name__=='__main__':main()
