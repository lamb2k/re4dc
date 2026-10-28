#!/usr/bin/env python3
"""Whole production actor TU: Build32 format/header/ownership integration.

The established hosted AVK and SQ adapters are explicit platform boundaries.
The production converter, cone admission, clipping, fast lighting and chunk
window control execute unchanged. Native UI binding is represented by its
actual pure admission helper and request lifecycle; target compilation/link
and private hardware tests qualify the real UI implementation separately.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
ADAPTER = DC / 'tools/d367/actor_setup_lean/check_runtime.py'
spec = importlib.util.spec_from_file_location('actor32_host_platform', ADAPTER)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new, 1)


def fixture():
    text = (ADAPTER.parent / 'fixture_actor.cpp.in').read_text()
    text = text[:text.index('void ordinary(')]
    text = replace_once(text, 'alignas(32) pvr_vertex_t scratch_vertices[256];',
                        'alignas(32) pvr_vertex_t scratch_storage[257];\npvr_vertex_t* const scratch_vertices=scratch_storage+1;')
    text = replace_once(text, 'std::memset(scratch_vertices,0xa5,sizeof scratch_vertices);',
                        'std::memset(scratch_storage,0xa5,sizeof scratch_storage);')
    text = replace_once(text, 'unsigned locks=0, unlocks=0;', '''unsigned locks=0, unlocks=0;
re4dc::format32::UvRequest request;
unsigned bound_width=128, bound_height=64, pcw=0, set_bits=0, clear_bits=0;
std::vector<unsigned> headers;
void binding(const Re4dcModelPart* p,bool success) {
    const unsigned pending=request.take();
    if(!success)return;
    request.result=pending?re4dc::format32::uv_decide(pending&63U,(p->flags&0x80000000U)!=0,
        p->uv_offset,bound_width,bound_height,us,vs):re4dc::format32::NotRequested;
    pcw=(set_bits&~clear_bits)|(set_bits&clear_bits);
    if(pending)pcw=kPcwStripLength6|(request.result==re4dc::format32::Uv16?kPcwUv16:0U);
    set_bits=clear_bits=0;
}''')
    text = replace_once(text, 'const std::uint32_t h[]={0x80840000u,p->cull',
                        'headers.push_back(pcw);\n    const std::uint32_t h[]={0x80840000u|pcw,p->cull')
    text = replace_once(text, 'words(h,8);',
                        'std::memcpy(scratch_vertices-1,h,sizeof h);words(h,8);')
    text = replace_once(text, 'if(check::begin_ok)check::header(p);',
                        'check::binding(p,check::begin_ok);if(check::begin_ok)check::header(p);')
    text = replace_once(text, 'check::event(7,check::scratch_capacity);if(!check::direct_ok)return 0;',
                        'check::event(7,check::scratch_capacity);if(!check::direct_ok){check::request.cancel();return 0;}\n    check::binding(p,true);')
    text = replace_once(text, 'extern "C" void re4dc_model_next_header_pcw(unsigned,unsigned){}', '''extern "C" void re4dc_model_next_header_pcw(unsigned set,unsigned clear){check::set_bits=set;check::clear_bits=clear;}
extern "C" void re4dc_model_uv16_request32(unsigned certificate){check::request.prepare(certificate);}
extern "C" unsigned re4dc_model_uv16_result32(){return check::request.result;}
extern "C" unsigned re4dc_model_uv16_live32(const Re4dcModelPart* p,unsigned certificate){
    return re4dc::format32::uv_decide(certificate,(p->flags&0x80000000U)!=0,p->uv_offset,
        check::bound_width,check::bound_height,check::us,check::vs);
}
extern "C" int re4dc_actor_obj_id(const void*){return -1;}''')
    text = replace_once(text, 'ta.clear();events.clear();calls.clear();sources.clear();locks=unlocks=0;',
                        'ta.clear();events.clear();calls.clear();sources.clear();headers.clear();locks=unlocks=0;\n    request.cancel();pcw=set_bits=clear_bits=0;bound_width=128;bound_height=64;')
    return text + (HERE / 'actor_runtime_cases.cpp.in').read_text()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / 'host/dc').mkdir(parents=True)
    (out / 'host/dc/pvr.h').write_text(adapter.PVR)
    (out / 'host/dc/sq.h').write_text(adapter.SQ)
    source, adaptations = adapter.host_source(adapter.ACTOR.read_text())
    (out / 'native_actor_host.inc').write_text(source)
    (out / 'fixture.cpp').write_text(fixture())
    rows = []
    for grouped in (0, 1, 2):
        defs = dict(RE4DC_ACTOR_FORMAT32=1, RE4DC_ACTOR_LIGHT_FAST_ONLY=1,
                    RE4DC_ACTOR_UV16=1, RE4DC_ACTOR_DIRECT=1,
                    RE4DC_ACTOR_BACKFACE_CONE=2, RE4DC_COARSE_ONE_SUBMIT=grouped,
                    RE4DC_ACTOR_VTX_KERNEL=1, RE4DC_ACTOR_ASM=0,
                    RE4DC_AVK_RIGID6=1, RE4DC_ACTOR_LIGHT_N16=0,
                    RE4DC_ACTOR_NO_CLEAR=1, RE4DC_ACTOR_MOVCA=0,
                    RE4DC_ACTOR_LOD_BUDGET=0, RE4DC_NATIVE_ACTOR_SKIN=1,
                    RE4DC_NATIVE_ACTOR_SKIN_LAZY=1, RE4DC_ACTOR_PRELIT=1,
                    RE4DC_ACTOR_SETUP_LEAN=1, RE4DC_COARSE_GATE_ONCE=0)
        exe = out / ('grouped' + str(grouped))
        command = ['g++', '-std=c++20', '-O2', '-fno-fast-math', '-ffp-contract=off',
                   '-ffunction-sections', '-fdata-sections', '-Wall', '-Wextra',
                   *['-D'+k+'='+str(v) for k,v in defs.items()],
                   '-I'+str(out / 'host'), '-I'+str(DC / 'game/platform'),
                   '-I'+str(DC / 'game/platform/include'), '-I'+str(DC / 'room'),
                   str(out / 'fixture.cpp'), str(DC / 'room/pvr_geometry.cpp'),
                   str(DC / 'room/source_lighting.cpp'), '-Wl,--gc-sections', '-o', str(exe)]
        if args.sanitize:
            command[1:1] = ['-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-fno-omit-frame-pointer']
        built = subprocess.run(command, capture_output=True)
        (out / (exe.name + '.compile.log')).write_bytes(built.stdout + built.stderr)
        if built.returncode:
            raise RuntimeError(built.stderr.decode()[-10000:])
        environment = dict(os.environ)
        if args.sanitize:
            environment['ASAN_OPTIONS'] = 'detect_leaks=0'
        run = subprocess.run([str(exe)], capture_output=True, env=environment)
        (out / (exe.name + '.stdout')).write_bytes(run.stdout)
        (out / (exe.name + '.stderr')).write_bytes(run.stderr)
        if run.returncode:
            raise RuntimeError(run.stderr.decode()[-10000:])
        result = json.loads(run.stdout)
        assert result['checks'] > 0 and result['uv_admitted'] > 0 and result['cone_admitted'] > 0
        rows.append(dict(grouped=grouped, result=result, command=command))
        print(json.dumps(rows[-1]['result']), flush=True)
    inputs = [Path(__file__), HERE / 'actor_runtime_cases.cpp.in', ADAPTER,
              ADAPTER.parent / 'fixture_actor.cpp.in', adapter.ACTOR,
              DC / 'game/platform/include/actor_cone32.hpp',
              DC / 'game/platform/include/actor_format32_uv.hpp',
              DC / 'game/platform/include/actor_format32_uv_source.inc']
    report = dict(status='PASS', scope=__doc__, profiles=rows, adaptations=adaptations,
                  sanitizers='address,undefined; leak detection disabled for runner /proc restriction' if args.sanitize else None,
                  source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
    (out / 'actor-runtime.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    main()
