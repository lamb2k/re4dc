#!/usr/bin/env python3
"""Source-only cold atlas gates; reuse retained fixtures without regenerating assets.

Run under d367-buildslot.sh. --out must be new. Persistent outputs are bounded to
4 MiB so one later evidence mirror fits an 8 MiB combined allocation. This tool
builds only small sanitizer host probes, never a game programme, pack or image.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--fixtures',type=Path,required=True)
    ap.add_argument('--runtime-data',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    if a.out.exists():raise ValueError('preserve existing evidence; use a new output')
    if os.environ.get('D367_SLOT_HELD')!='1':raise ValueError('use d367-buildslot.sh')
    old=json.loads((a.fixtures/'binding-result.json').read_text())
    if old['candidate_sha256sums']!='9b524ee573753dcb640cb561ba7966e56c5d57e53200c5dcbd8683f0796ad2a2' or old['hair_run_fixture']!=1:
        raise ValueError('require retained square128-v2 one-hair fixtures')
    if sha(a.runtime_data/'leon_atlas_split_data.h')!=old['runtime_data_sha256']:
        raise ValueError('runtime header must match retained source fixtures')
    if shutil.disk_usage('/mnt/c').free<18*1024**3+128*1024**2:
        raise RuntimeError('C admission floor not met')
    own=Path(__file__).resolve().parent
    port=own.parents[2]
    start=time.monotonic();a.out.mkdir(parents=True)
    def guard():
        if time.monotonic()-start>=51:raise RuntimeError('51-second host deadline')
        if shutil.disk_usage('/mnt/c').free<18*1024**3+64*1024**2:raise RuntimeError('C runtime floor')
        if sum(p.stat().st_size for p in a.out.iterdir() if p.is_file())*2>=8*1024**2:
            raise RuntimeError('8 MiB evidence-plus-mirror budget')
    rows=[]
    for actor in ('standard','pl08','pl08-headless'):
        fixture=a.fixtures/actor/'atlas-bind-case.h'
        for geometry in (False,True):
            guard();name=('geometry-' if geometry else '')+actor
            defines=['RE4DC_ACTOR_PL08=1','RE4DC_LEON_ATLAS_SPLIT=1']
            if geometry:defines+=['RE4DC_NATIVE_MODEL_REGISTRY=1','RE4DC_ACTOR_PL08_PACK=1','RE4DC_LEON_HEADLESS=1']
            else:defines+=['RE4DC_ATLAS_TEST_HAIR_RUNS=1','RE4DC_ATLAS_RUNTIME_PROBE=1','RE4DC_ATLAS_DYNAMIC_PROBE=1']
            source=own/('geometry_probe.cpp' if geometry else 'cold_gate_probe.cpp')
            command=['g++','-std=c++17','-O1','-g0','-Wall','-Wextra','-Werror','-no-pie',
                '-fsanitize=address,undefined','-fno-omit-frame-pointer',
                *['-D'+d for d in defines],'-I'+str(a.runtime_data),
                '-isystem',str(port/'game/platform/include'),'-I'+str(own),
                '-I'+str(fixture.parent),str(source),'-o',str(a.out/name)]
            with (a.out/(name+'-compile.log')).open('x') as log:
                subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,
                    timeout=max(1,51-(time.monotonic()-start)))
            with (a.out/(name+'-run.log')).open('x') as out,(a.out/(name+'-run.err')).open('x') as err:
                subprocess.run([str(a.out/name)],stdout=out,stderr=err,check=True,
                    timeout=max(1,51-(time.monotonic()-start)),
                    env=dict(os.environ,ASAN_OPTIONS='detect_leaks=1:abort_on_error=1'))
            results=[json.loads(line) for line in (a.out/(name+'-run.log')).read_text().splitlines()]
            rows.append(dict(actor=actor,geometry=geometry,command=command,results=results,
                fixture=dict(path=str(fixture),sha256=sha(fixture)),
                executable_sha256=sha(a.out/name)))
            guard()
    source_files=[own/n for n in ('cold_gate_probe.cpp','bind_probe.cpp','atlas_bind.h','geometry_probe.cpp')]
    source_files += [port/'game'/n for n in ('coarse_actor_atlas_split.inc','coarse_actor_geometry_once.inc')]
    receipt=dict(status='PASS',scope='Source-format fixtures and wrapper/proof protocol; foreign roles and IDs are host sentinels. No live owner or target acceptance.',
        elapsed=time.monotonic()-start,pid=os.getpid(),pgid=os.getpgrp(),
        start_ticks=Path('/proc/self/stat').read_text().split()[21],
        results=rows,source_sha256={str(p):sha(p) for p in source_files},
        runtime_header_sha256=sha(a.runtime_data/'leon_atlas_split_data.h'),
        no_asset_regeneration=True,no_runtime_recipe_edit=True,no_programme_pack_image_guest=True)
    (a.out/'QUALIFICATION.json').write_text(json.dumps(receipt,indent=2)+'\n')
    guard();print(json.dumps(receipt))


if __name__=='__main__':main()