#!/usr/bin/env python3
"""Host controls using actual fresh-open SDO3 binding and movie-layout source.

All compiler/binary scratch stays in RAM. This does not execute KOS movie I/O,
SH4 rendering or a target memory gate.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('source-tree','baseline-native','legacy','compact','output'):ap.add_argument('--'+n,type=Path,required=True)
    ap.add_argument('--expected-source',required=True)
    a=ap.parse_args();out=a.output.resolve()
    head=subprocess.check_output(['git','-C',str(a.source_tree),'rev-parse','HEAD'],text=True).strip()
    if head!=a.expected_source:raise ValueError('Source HEAD mismatch')
    if subprocess.check_output(['git','-C',str(a.source_tree),'status','--porcelain','--untracked-files=no']):raise ValueError('Tracked source is dirty')
    if not out.is_relative_to(Path('/dev/shm')):raise ValueError('RAM output required')
    out.mkdir(parents=True,exist_ok=False);dc=a.source_tree/'port/dreamcast'
    spec=importlib.util.spec_from_file_location('extract',dc/'tools/d367/world_submit_spike/check_runtime.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    raw=(dc/'game/platform/native_static.cpp').read_text();function=mod.function
    start=raw.index('// Bind alternate source CRC/extent')
    chunks={'OPEN':function(raw[start:],'if(fm!=FILEHND_INVALID){'),
            'BOUND':function(raw,'if(ok && msize>=80U){'),
            'LAYOUT':function(raw,'bool ps2_movie_layout(unsigned room){'),
            'CRC':function(raw,'std::uint32_t ps2_crc32('),
            'FNV':function((dc/'game/platform/include/movie_world_arena_lifecycle.inc').read_text(),'inline unsigned fnv(')}
    text=(HERE/'fixture_strip_binding.cpp.in').read_text()
    for k,v in chunks.items():text=text.replace('@'+k+'@',v)
    cpp=out/'binding.cpp';cpp.write_text(text);binary=out/'binding'
    env=dict(os.environ,TMPDIR='/dev/shm',PYTHONDONTWRITEBYTECODE='1')
    cmd=['g++','-std=c++17','-O2','-DRE4DC_SCENERY_DEDUP=3','-DRE4DC_MOVIE_WORLD_ARENA_S30=1',
         '-I'+str(dc/'tools/d367/ps2world/hostinc'),'-I'+str(dc/'room'),str(cpp),'-o',str(binary)]
    c=subprocess.run(cmd,capture_output=True,env=env);(out/'compile.log').write_bytes(c.stdout+c.stderr)
    if c.returncode:raise RuntimeError(c.stderr.decode())
    results={}
    for room in ('r100','r101','r103'):
        paths=[a.baseline_native/room/'ps2-world.re4mesh',a.legacy/(room+'-linear')/'ps2-dd3.re4mesh',a.compact/room/'ps2-dd3.re4mesh']
        c=subprocess.run([str(binary),*[str(p) for p in paths]],capture_output=True,env=env)
        if c.returncode:raise RuntimeError((room,c.returncode,c.stderr.decode()))
        results[room]={'stdout':c.stdout.decode().strip(),'input_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
    report=dict(status='PASS_HOST_BINDING_LAYOUT_ONLY',source=head,source_sha256=hashlib.sha256(raw.encode()).hexdigest(),
        reader_sha256=hashlib.sha256((dc/'room/instanced_mesh.hpp').read_bytes()).hexdigest(),
        helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256((HERE/'fixture_strip_binding.cpp.in').read_bytes()).hexdigest(),
        extracted_sha256={k:hashlib.sha256(v.encode()).hexdigest() for k,v in chunks.items()},results=results,
        limits='Actual extracted fresh baseline-header selection, source extent/CRC and alternate body CRC branch; actual reader; actual movie-layout predicate and whole-file CRC/FNV. Mock file I/O. Actual KOS movie reload/world generation and rendered target/memory gates remain pending.')
    (out/'strip-binding-controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'rooms':list(results)}))


if __name__=='__main__':main()
