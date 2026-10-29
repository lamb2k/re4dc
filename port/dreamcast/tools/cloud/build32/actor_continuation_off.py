#!/usr/bin/env python3
"""EF04 absent/zero whole actor host output and allocated-byte identity.

This is a hosted actor-TU control. The separate target compilation/full recipe
gate must establish the other changed TUs and shared layout propagation.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('continuation_runtime', HERE / 'actor_runtime_host.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline', default='255964fdc7d22a61acff1ef59734a36ec91ebff0')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / 'host/dc').mkdir(parents=True)
    (out / 'host/dc/pvr.h').write_text(runtime.adapter.PVR)
    (out / 'host/dc/sq.h').write_text(runtime.adapter.SQ)
    (out / 'fixture.cpp').write_text(runtime.fixture())
    actor = runtime.adapter.ACTOR
    baseline = subprocess.check_output(['git', 'show', args.baseline+':'+str(actor.relative_to(runtime.ROOT))], cwd=runtime.ROOT).decode()
    current = actor.read_text()
    defs = dict(RE4DC_ACTOR_FORMAT32=1, RE4DC_ACTOR_LIGHT_FAST_ONLY=1, RE4DC_ACTOR_UV16=1,
                RE4DC_ACTOR_DIRECT=1, RE4DC_ACTOR_BACKFACE_CONE=2, RE4DC_COARSE_ONE_SUBMIT=1,
                RE4DC_ACTOR_VTX_KERNEL=1, RE4DC_ACTOR_ASM=0, RE4DC_AVK_RIGID6=1,
                RE4DC_ACTOR_LIGHT_N16=0, RE4DC_ACTOR_NO_CLEAR=1, RE4DC_ACTOR_MOVCA=0,
                RE4DC_ACTOR_LOD_BUDGET=0, RE4DC_NATIVE_ACTOR_SKIN=1, RE4DC_NATIVE_ACTOR_SKIN_LAZY=1,
                RE4DC_ACTOR_PRELIT=1, RE4DC_ACTOR_SETUP_LEAN=1, RE4DC_COARSE_GATE_ONCE=0)
    rows=[]
    for name, source, flags in [('baseline', baseline, []), ('absent', current, []),
                                ('zero', current, ['-DRE4DC_NATIVE_FE_CONTINUATION=0'])]:
        adapted, _ = runtime.adapter.host_source(source)
        (out / 'native_actor_host.inc').write_text(adapted)
        exe = out / name
        cmd = ['g++', '-std=c++20', '-O2', '-fno-fast-math', '-ffp-contract=off',
               '-ffunction-sections', '-fdata-sections', *['-D'+k+'='+str(v) for k,v in defs.items()], *flags,
               '-I'+str(out / 'host'), '-I'+str(runtime.DC / 'game/platform'),
               '-I'+str(runtime.DC / 'game/platform/include'), '-I'+str(runtime.DC / 'room'),
               str(out / 'fixture.cpp'), str(runtime.DC / 'room/pvr_geometry.cpp'),
               str(runtime.DC / 'room/source_lighting.cpp'), '-Wl,--gc-sections', '-o', str(exe)]
        built = subprocess.run(cmd, capture_output=True)
        (out / (name+'.compile.log')).write_bytes(built.stdout+built.stderr)
        if built.returncode:raise RuntimeError(built.stderr.decode()[-8000:])
        result = subprocess.check_output([str(exe)])
        # objcopy's flat image includes every loadable section; build-id notes
        # are omitted by this explicit stable allocated-code/data selection.
        image = out / (name+'.allocated.bin')
        subprocess.run(['objcopy', '-O', 'binary', '--only-section=.text', '--only-section=.rodata',
                        '--only-section=.data', '--only-section=.bss', str(exe), str(image)], check=True)
        rows.append(dict(name=name, result=result.decode().strip(),
                         allocated_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
                         allocated_bytes=image.stat().st_size, command=cmd))
        print(json.dumps({k:v for k,v in rows[-1].items() if k!='command'}), flush=True)
    assert len({r['allocated_sha256'] for r in rows}) == 1
    assert len({r['result'] for r in rows}) == 1
    (out / 'actor-continuation-off.json').write_text(json.dumps(dict(status='PASS', baseline=args.baseline,
        scope=__doc__, arms=rows), indent=2)+'\n')


if __name__ == '__main__':main()
