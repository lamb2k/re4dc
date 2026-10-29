#!/usr/bin/env python3
"""Qualify the existing log guard selector using actual append/device bodies.

Synthetic coherent scheduling only. Masked byte counts are work counts, never
SH-4 duration, NMI safety, cache visibility or a passing memory observation.
"""
import argparse, hashlib, importlib.util, json, os, subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
DC=HERE.parents[2]
ROOT=DC.parents[1]
spec=importlib.util.spec_from_file_location('extract',DC/'tools/d367/world_submit_spike/check_runtime.py')
extract=importlib.util.module_from_spec(spec);spec.loader.exec_module(extract)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--sanitize',action='store_true')
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    mem=DC/'game/platform/mem.cpp';fault=DC/'game/platform/fault.cpp'
    source=(HERE/'log16_fixture.cpp.in').read_text()
    source=source.replace('@RAW@',extract.function(mem.read_text(),'void re4dc_log_raw('))
    source=source.replace('@CALLBACK@',extract.function(fault.read_text(),'static int ringWriteBuffer('))
    source=source.replace('@APPEND@',extract.function(mem.read_text(),'static void logAppend('))
    source=source.replace('@LOG@',extract.function(mem.read_text(),'void re4dc_log('))
    fixture=out/'fixture.cpp';fixture.write_text(source)
    make_source=(DC/'game/game30.mk').read_text()
    first=make_source.index('# LOG_ATOMIC16:')
    selector=make_source[first:make_source.index('ifeq ($(LOGIC_TRACE),1)',first)]
    knob=out/'knob.mk';knob.write_text(selector+'\n.PHONY: all\nall:\n\t@:\n')
    selector_values={}
    for value in ('0','1','','2','0 1','-1'):
        r=subprocess.run(['make','-s','-f',str(knob),'all','OBJDIR=obj','LOG_ATOMIC16='+value],capture_output=True)
        assert (r.returncode==0)==(value in ('0','1')),(value,r.stderr)
        selector_values[value]=r.returncode
    rows=[]
    for size in (16384,65536):
        for old,new in ((0,0),(0,1),(1,0),(1,1)):
            label=f'ring{size}-old{old}-new{new}';binary=out/label
            command=['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror',f'-DRE4DC_LOG_ATOMIC={old}',
                     f'-DRE4DC_LOG_ATOMIC16={new}',f'-DTEST_RING_SIZE={size}',str(fixture),'-o',str(binary)]
            if a.sanitize:command[2:3]=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie']
            c=subprocess.run(command,capture_output=True);(out/(label+'-compile.log')).write_bytes(c.stdout+c.stderr)
            if c.returncode:raise RuntimeError(c.stderr.decode())
            env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
            r=subprocess.run([str(binary)],capture_output=True,env=env);(out/(label+'-run.log')).write_bytes(r.stdout+r.stderr)
            if r.returncode:raise RuntimeError(label+': '+r.stderr.decode())
            row=json.loads(r.stdout);row['command']=command;rows.append(row)
    paths=(mem,fault,Path(__file__),HERE/'log16_fixture.cpp.in')
    receipt=dict(status='PASS_SCOPED_HOST_GUARD_AND_DEVICE_CONTRACT',sanitized=a.sanitize,rows=rows,selector_values=selector_values,
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        limits=['arbitrary append work remains proportional to supplied length',
                'masked byte-store counts cover the append loop, not header/IRQ/formatting instructions or duration',
                'forced synchronous/NMI-style reentry counterexamples are expected and retained',
                'coherent host polls only; target IRQ duration and raw RAM/cache visibility unqualified',
                'no original failed observation retry or memory acceptance'])
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(status=receipt['status'],sanitized=a.sanitize,compositions=len(rows),results=[{k:v for k,v in r.items() if k!='command'} for r in rows])))

if __name__=='__main__':main()
