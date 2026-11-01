#!/usr/bin/env python3
"""Host exercise of the actual scoped prepare, wrapper, plan/bounds and model consumer.

Texture I/O, owner publication and KOS packets are controlled external edges;
the source renderer, actual assets and SH target are outside this fixture.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
DC=HERE.parents[2]
ROOT=DC.parents[1]
UI=DC/'game/platform/native_ui.cpp'
MODEL=DC/'game/platform/native_model.cpp'
BRIDGE=DC/'game/model_bridge.cpp'
HEADER=DC/'game/platform/include/model_prepared_binding34.h'
TEMPLATE=HERE/'prepared_binding_fixture.cpp.in'
spec=importlib.util.spec_from_file_location('extract',DC/'tools/d367/world_submit_spike/check_runtime.py')
extract=importlib.util.module_from_spec(spec);spec.loader.exec_module(extract)

def fragments(source):
    error=source.index('#error PREPARED_BINDING34 requires scoped draw plans')
    first=source.rfind('#if defined(RE4DC_PREPARED_BINDING34)',0,error)
    assert first>=0
    begin=source.index('extern "C" int re4dc_model_packet_begin(',error)
    prepared=source[first:begin]
    assert prepared.endswith('#endif\n')
    wrapper=extract.function(source,'extern "C" int re4dc_model_packet_begin_prepared34(')
    size=extract.function(source,'unsigned image_size(const Re4dcUiImage& i)')
    shape=extract.function(source,'inline bool handle_shape(const Re4dcUiImage& i,unsigned& shape,bool allow_indexed)')
    peek=extract.function(source,'Entry* resolve_peek(const Re4dcUiImage& image,const Re4dcModelPart* masked)')
    handle=re.search(r'struct alignas\(32\) Handle \{[^\n]+\};',source)
    assert handle and all(word not in peek for word in ('load(', 'resolve(', 'stream_select(', 'malloc(', 'new '))
    bridge=BRIDGE.read_text()
    assignment=re.search(r'p\.static_geometry=rigid && m->kindid==2 && !d->shapeOfs && !\(info->be_flag&2\);',bridge)
    assert assignment
    return dict(PREPARED=prepared,WRAPPER=wrapper,IMAGE_SIZE=size,HANDLE_SHAPE=shape,
                PEEK=peek,HANDLE=handle.group(),STATIC_ASSIGN=assignment.group())

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--sanitize',action='store_true')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    source=UI.read_text();parts=fragments(source)
    text=TEMPLATE.read_text()
    for key,value in parts.items():text=text.replace('@'+key+'@',value)
    assert not re.search(r'@[A-Z_]+@',text)
    fixture=args.output/'prepared_binding.cpp';fixture.write_text(text)
    stub=args.output/'dc';stub.mkdir()
    (stub/'pvr.h').write_text('#pragma once\n#include <cstddef>\n#include <cstdint>\n'
        'struct pvr_vertex_t{std::uint32_t flags;float x,y,z,u,v;std::uint32_t argb,oargb;};\n'
        'struct pvr_poly_hdr_t{std::uint32_t words[8];};\n'
        '#define PVR_CMD_VERTEX 0xe0000000U\n#define PVR_CMD_VERTEX_EOL 0xf0000000U\n'
        'int pvr_prim(const void*,std::size_t);\n')
    game=DC/'game';room=DC/'room'
    runs=[]
    for enabled in (0,1):
        exe=args.output/f'prepared{enabled}'
        flags=['-std=c++20','-O2','-DRE4DC_PREPARED_BINDING34='+str(enabled),
            '-DRE4DC_PLAN_OWNER_SCOPED=1','-DRE4DC_D349_RENDERER_STACK=1',
            '-DRE4DC_MODEL_DRAW_PLANS=1','-DRE4DC_ACTOR_TRANSACTION=1',
            '-DRE4DC_UI_HANDLES=1','-DRE4DC_PS2_UPLOAD_INCARNATION=1']
        if args.sanitize:flags[1:2]=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie']
        command=['g++',*flags,'-I'+str(args.output),'-I'+str(game/'platform/include'),'-I'+str(room),
            str(fixture),str(MODEL),str(room/'pvr_geometry.cpp'),str(room/'native_draw_plan.cpp'),
            str(room/'source_lighting.cpp'),'-o',str(exe)]
        run=subprocess.run(command,capture_output=True,text=True)
        (args.output/f'compile-{enabled}.log').write_text(run.stdout+run.stderr)
        assert run.returncode==0,run.stderr
        run=subprocess.run([str(exe)],capture_output=True,text=True,
            env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
        (args.output/f'run-{enabled}.log').write_text(run.stdout+run.stderr)
        assert run.returncode==0,run.stderr
        runs.append(run.stdout.strip())
    assert re.search(r'hash=([0-9a-f]+)',runs[0]).group(1)==re.search(r'hash=([0-9a-f]+)',runs[1]).group(1)
    assert source==UI.read_text()
    report=dict(status='PASS',scope=__doc__,sanitize=args.sanitize,runs=runs,
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in (UI,MODEL,BRIDGE,HEADER,TEMPLATE,Path(__file__))},
        extracted_sha256={k:hashlib.sha256(v.encode()).hexdigest() for k,v in parts.items()})
    receipt=args.output/'prepared-binding-host.json'
    receipt.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',runs=runs,receipt=str(receipt))))

if __name__=='__main__':main()
