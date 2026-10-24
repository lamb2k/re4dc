#!/usr/bin/env python3
"""Compare actual optional selector admission and existing replay control flow.

Uses exact production bodies with controlled visibility/emit_pick edges. It
checks queue records, order, material/sky/UV state, accounting and aborts. The
separate SH4 full-TU fixture checks actual selector math, type layout and cost.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
DC=HERE.parents[2]
ROOT=DC.parents[1]
SOURCE=DC/'game/platform/native_static.cpp'
spec=importlib.util.spec_from_file_location('world_runtime',HERE.parent/'backface_cone_front/world_runtime_test.py')
runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
 args.output.mkdir(parents=True,exist_ok=False);out=args.output.resolve()
 raw=SOURCE.read_text();source=runtime.expand_selector_include(raw)
 start=source.index('#if RE4DC_SCENERY_SELECT_ONLY\n            {')
 end=source.index('#if RE4DC_PS2_VERTEX_ALPHA\n            const bool marked=',start)
 early=source[start:end]
 full_end=source.index('#if RE4DC_SCENERY_CHUNK\n            // SCENERY_CHUNK: select now',end)
 full=source[end:full_end]
 dispatch_end=source.index('#if RE4DC_PS2_PVS\n            d.pvs_finish(result>0);',full_end)
 far=(SOURCE.parent/'include/scenery_part_far.inc').read_text()
 values={'PICK_DEFINITION':runtime.function(source,'struct Pick {')+';',
         'CHUNK_OK':runtime.function(source,'bool chunk_ok()const'),
         'CHUNK_EMIT':runtime.function(source,'__attribute__((noinline)) int chunk_emit('),
         'CHUNK_PART':runtime.function(source,'struct ChunkPart {'),
         'CHUNK_FLUSH':runtime.function(source,'auto chunk_flush=[&]()->int'),
         'EARLY_BRANCH':early,'FULL_SETUP':full,'CHUNK_DISPATCH':source[full_end:dispatch_end]}
 text=(HERE/'queue_fixture.cpp.in').read_text()
 for key,value in values.items():
  value=value.replace('#include "include/scenery_part_far.inc"',far)
  text=text.replace('@'+key+'@',value)
 fixture=out/'queue.cpp';fixture.write_text(text)
 results=[]
 for mode in (0,1):
  binary=out/('queue%d'%mode)
  cmd=['g++','-std=c++20','-O2','-Wall','-Wextra','-Wno-unused-variable','-DRE4DC_SCENERY_SELECT_ONLY=%d'%mode,str(fixture),'-o',str(binary)]
  run=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  (out/('compile%d.log'%mode)).write_bytes(run.stdout)
  if run.returncode:raise RuntimeError(run.stdout.decode())
  run=subprocess.run([str(binary)],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  (out/('queue%d.stdout'%mode)).write_bytes(run.stdout);(out/('queue%d.stderr'%mode)).write_bytes(run.stderr)
  if run.returncode:raise RuntimeError(run.stderr.decode())
  results.append(run.stdout)
 if results[0]!=results[1]:
  a,b=results[0].decode().splitlines(),results[1].decode().splitlines()
  differences=[dict(old=x,new=y) for x,y in zip(a,b) if x!=y]
  (out/'differences.json').write_text(json.dumps(differences,indent=2)+'\n')
  raise AssertionError('%d queue controls differ; see differences.json'%len(differences))
 report=dict(status='PASS',cases=len(results[0].splitlines()),source_sha256=hashlib.sha256(raw.encode()).hexdigest(),
             extracted_sha256={k:hashlib.sha256(v.encode()).hexdigest() for k,v in values.items()},
             scope='Actual new/old admission, full setup assignments, queue records, chunk_flush and chunk_emit control flow with controlled chunk_select/emit_pick edges; no target object layout, renderer output or timing claim.')
 (out/'queue-controls.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS queue equivalence: %d cases'%report['cases'])

if __name__=='__main__':main()
