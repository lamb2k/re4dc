#!/usr/bin/env python3
"""Real portrait producer -> existing deferred queue -> native actor emitter.

Only source game structs, primitive allocation, texture/SQ/SH4 transport are
host adapters. Queue/view/lighting snapshots, portrait pose calculation,
immutable proof and the complete actor TU are extracted from current sources.
Synthetic arrays are the only asset input; no private artwork is embedded.
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
spec = importlib.util.spec_from_file_location('runtime', HERE / 'actor_runtime_host.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
DC = runtime.DC
GAME = DC / 'game'
PLATFORM = GAME / 'platform'


def make_policy():
    text = 'OBJDIR := fixture\ninclude '+str(GAME / 'actor_format32.mk')+'\nprint:;@echo $(GAME_CPPFLAGS):$(PLATFORM_CPPFLAGS)\n'
    def run(*options):
        return subprocess.run(['make', '--no-print-directory', '-f', '-', 'print', *options],
                              input=text.encode(), capture_output=True)
    absent, zero = run(), run('NATIVE_FE_CONTINUATION=0')
    assert absent.returncode == zero.returncode == 0 and absent.stdout == zero.stdout == b':\n'
    profile = ['ACTOR_FORMAT32=1', 'NATIVE_ACTOR=1', 'NATIVE_ACTOR_FAST=1', 'NATIVE_ACTOR_UV16=1',
               'ACTOR_TRANSACTION=1', 'NATIVE_ACTOR_SKIN_LAZY=1', 'ACTOR_SOURCE_SPAN=1',
               'LEON_PS2_PORTRAIT_HAIR=1', 'PS2_LEON=1', 'LEON_LOD=0']
    enabled = run(*profile, 'NATIVE_FE_CONTINUATION=1')
    assert enabled.returncode == 0 and enabled.stdout.count(b'-DRE4DC_NATIVE_FE_CONTINUATION=1') == 2
    for bad in ('', '2', '0 1'):
        assert run(*profile, 'NATIVE_FE_CONTINUATION='+bad).returncode != 0
    for name in ('ACTOR_SOURCE_SPAN', 'ACTOR_TRANSACTION', 'NATIVE_ACTOR_FAST', 'LEON_PS2_PORTRAIT_HAIR', 'PS2_LEON'):
        assert run(*profile, name+'=0', 'NATIVE_FE_CONTINUATION=1').returncode != 0
    for lod in (1, 2, 3):
        assert run(*profile, 'LEON_LOD='+str(lod), 'NATIVE_FE_CONTINUATION=1').returncode != 0
    return dict(absent_zero_flags=absent.stdout.decode().strip(), enabled_flags=enabled.stdout.decode().strip(),
                rejected_profiles=11)


def fixture():
    ui = (PLATFORM / 'native_ui.cpp').read_text()
    coarse = (GAME / 'coarse_actor.cpp').read_text()
    proof = (GAME / 'coarse_actor_geometry_once.inc').read_text()
    text = runtime.fixture().split('void cone_admission(){')[0] + '\n}\n'
    # These platform hooks keep actual publication/failure order observable.
    text = 'void continuation_abort();\nvoid continuation_begin();\n' + text
    text = runtime.replace_once(text, 'check::event(6);', 'check::event(6);continuation_abort();')
    text = runtime.replace_once(text, 'check::binding(p,check::begin_ok);',
                                'continuation_begin();check::binding(p,check::begin_ok);')
    text = runtime.replace_once(text, 'check::binding(p,true);', 'continuation_begin();check::binding(p,true);')
    text += '\nnamespace {\n' + runtime.adapter.body(proof, 'struct ActorImmutableChunk') + ';\n'
    text += 'ActorImmutableChunk actor_immutable_chunks[64];\n#define RE4DC_IMMUTABLE_CHUNK_COUNT 64\n'
    text += runtime.adapter.body(proof, 'bool actor_same_span(') + '\n'
    text += runtime.adapter.body(proof, 'bool actor_same_chunk(') + '\n}\n'
    text += runtime.adapter.body(proof, 'extern "C" re4dc_source::BlobError re4dc_actor_immutable_chunk_proof(')
    text += '\n' + (HERE / 'actor_continuation_platform.cpp.in').read_text()
    text += '\nnamespace queue {\n'
    text += ui[ui.index('using SourceLighting=re4dc::render::SourceLighting;'):ui.index('DeferredPart* deferred_first=nullptr;')]
    text += ui[ui.index('DeferredPart* deferred_first=nullptr;'):ui.index('\n#endif\nunsigned dropped,unsupported,missing,drawn,culled,loads,reclaimed;')]
    text += '\n' + runtime.adapter.body(ui, 'int defer_part(') + '\n'
    text += runtime.adapter.body(ui, 'extern "C" void re4dc_model_finish_source_draws(){').replace('extern "C" ', '')
    cases = (HERE / 'actor_continuation_cases.cpp.in').read_text()
    model = (PLATFORM / 'native_model.cpp').read_text()
    dispatch = runtime.adapter.body(model, '    if(p && p->native_pose)')
    dispatch = dispatch.replace('re4dc_actor_native_submit_result(p,1);',
                                'host::last=re4dc_actor_native_submit_result(p,1);++host::emissions;')
    cases = cases.replace('// ACTUAL_MODEL_DISPATCH', dispatch)
    text += '\n}\n' + cases.split('// ACTUAL_PORTRAIT')[0]
    start = coarse.index('namespace {\nconst void* portrait_hair_info;')
    end = coarse.index('extern "C" int re4dc_portrait_hair(', start)
    text += coarse[start:end]
    text += runtime.adapter.body(coarse, 'extern "C" int re4dc_portrait_hair(')
    text += '\n' + cases.split('// ACTUAL_PORTRAIT')[1]
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    policy = make_policy()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / 'host/dc').mkdir(parents=True)
    (out / 'host/dc/pvr.h').write_text(runtime.adapter.PVR)
    (out / 'host/dc/sq.h').write_text(runtime.adapter.SQ)
    source, adaptations = runtime.adapter.host_source(runtime.adapter.ACTOR.read_text())
    (out / 'native_actor_host.inc').write_text(source)
    (out / 'fixture.cpp').write_text(fixture())
    rows = []
    for owner_pool in (0, 1):
        for fast_only in (0, 1):
            defs = dict(RE4DC_NATIVE_FE_CONTINUATION=1, RE4DC_ACTOR_SOURCE_SPAN=1,
                        RE4DC_ACTOR_TRANSACTION=1, RE4DC_ACTOR_SKIN_OWNER_POOL=owner_pool,
                        RE4DC_ACTOR_FORMAT32=1, RE4DC_ACTOR_LIGHT_FAST_ONLY=fast_only,
                        RE4DC_ACTOR_UV16=1, RE4DC_ACTOR_DIRECT=1, RE4DC_ACTOR_BACKFACE_CONE=0,
                        RE4DC_COARSE_ONE_SUBMIT=0, RE4DC_ACTOR_VTX_KERNEL=1, RE4DC_ACTOR_ASM=0,
                        RE4DC_AVK_RIGID6=1, RE4DC_ACTOR_LIGHT_N16=0, RE4DC_ACTOR_NO_CLEAR=1,
                        RE4DC_ACTOR_MOVCA=0, RE4DC_ACTOR_LOD_BUDGET=0, RE4DC_NATIVE_ACTOR_SKIN=1,
                        RE4DC_NATIVE_ACTOR_SKIN_LAZY=1, RE4DC_ACTOR_PRELIT=1,
                        RE4DC_ACTOR_SETUP_LEAN=1, RE4DC_COARSE_GATE_ONCE=0,
                        RE4DC_COPY_LEAN=1, RE4DC_D349_RENDERER_STACK=1, RE4DC_PVR_STREAM=1,
                        RE4DC_WORLD_HOLE_FIX=1, RE4DC_BRIDGE_LEAN=0,
                        RE4DC_LEON_LIGHT_HEADROOM=1)
            exe = out / ('pool%d-fast%d' % (owner_pool, fast_only))
            command = ['g++', '-std=c++20', '-O2', '-fno-fast-math', '-ffp-contract=off',
                       '-ffunction-sections', '-fdata-sections', '-Wall', '-Wextra',
                       *['-D'+k+'='+str(v) for k,v in defs.items()],
                       '-I'+str(out / 'host'), '-I'+str(PLATFORM), '-I'+str(PLATFORM / 'include'),
                       '-I'+str(DC / 'room'), str(out / 'fixture.cpp'),
                       str(DC / 'room/pvr_geometry.cpp'), str(DC / 'room/source_lighting.cpp'),
                       '-Wl,--gc-sections', '-o', str(exe)]
            if args.sanitize:
                command[1:1] = ['-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-fno-omit-frame-pointer']
            built = subprocess.run(command, capture_output=True)
            (out / (exe.name+'.compile.log')).write_bytes(built.stdout+built.stderr)
            if built.returncode:
                raise RuntimeError(built.stderr.decode()[-18000:])
            env = dict(os.environ, ASAN_OPTIONS='detect_leaks=0')
            run = subprocess.run([str(exe)], capture_output=True, env=env)
            (out / (exe.name+'.stdout')).write_bytes(run.stdout)
            (out / (exe.name+'.stderr')).write_bytes(run.stderr)
            if run.returncode:
                raise RuntimeError(run.stderr.decode()[-12000:])
            rows.append(dict(owner_pool=owner_pool, fast_only=fast_only,
                             result=json.loads(run.stdout), command=command))
            print(json.dumps(rows[-1]['result']), flush=True)
    inputs = [Path(__file__), HERE / 'actor_continuation_platform.cpp.in', HERE / 'actor_continuation_cases.cpp.in',
              PLATFORM / 'native_actor_fast.cpp', PLATFORM / 'native_ui.cpp', PLATFORM / 'native_model.cpp',
              GAME / 'coarse_actor.cpp', GAME / 'coarse_actor_geometry_once.inc']
    inputs += list((PLATFORM / 'include').glob('native_actor_*continuation*'))
    inputs += [PLATFORM / 'include/native_actor_pose_snapshot.inc']
    report = dict(status='PASS', scope=__doc__, profiles=rows, adaptations=adaptations, make_policy=policy,
                  sanitizer='address,undefined' if args.sanitize else None,
                  sha256={str(p.relative_to(runtime.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
    (out / 'actor-continuation.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
