#!/usr/bin/env python3
"""Build real SH4 full-TU world selector fixtures with the Test22 Make recipe.

No box, group-selection, cone or LOD arithmetic is replaced. The fixture enters
the real MeshDraw/ScenerySelector setup then chunk_select. Rendering and queue
replay are not retained by these entrypoints. Production object identity and
size are a separate build_controls gate.
"""
import argparse
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
DC=HERE.parents[2];ROOT=DC.parents[1]
SOURCE=DC/"game/platform/native_static.cpp"
_spec=importlib.util.spec_from_file_location("select2_measure_profile",HERE/"build_profile.py")
build_profile=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(build_profile)
sys.path.insert(0,str(HERE.parent/"world_setup_spike"))
import generate_fixture
from target_cases import write_cases


def build(args):
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    compiler=args.sh4_cxx.resolve()
    profiles,profile=build_profile.derive(output/"release-profile",compiler,
        args.kos_root.resolve(),args.sdk_root.resolve(),cost_dependencies=True)
    builder=build_profile.Build(output)
    sources=[SOURCE,HERE/"target_build.py",HERE/"target_cases.py",HERE/"build_profile.py",
        HERE.parent/"world_setup_spike/generate_fixture.py",
        HERE.parent/"world_setup_spike/selection_fixture.cpp.in",
        *sorted((SOURCE.parent/"include").glob("scenery_*"))]
    inputs={str(p.relative_to(ROOT)):build_profile.sha(p) for p in sources}
    fixture=output/"target_fixture.cpp"
    extracted=generate_fixture.generate_source(fixture,SOURCE)
    # Runtime SG choice remains outside the timed entry. This setter touches
    # only the same already-existing global configured by the production path.
    with fixture.open("a") as out:
        out.write('''\nextern "C" void fixture_sg_mode(unsigned value) {
#if RE4DC_SG_SELECT_LEAN
    re4dc_sg_lean_on=value;
#else
    (void)value;
#endif
}\n''')
    geometry=output/"pvr_geometry.o"
    builder.run([*profiles["pvr_geometry"],"-c",DC/"room/pvr_geometry.cpp","-o",geometry],label="geometry")
    linker=output/"fixture.ld"
    linker.write_text('''SECTIONS {
 /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) }
 . = 0x100000;
 .text : { *(.text*) }
 .rodata : { *(.rodata*) }
 .data : { *(.data*) }
 .bss : { *(.bss*) *(COMMON) }
}
''')
    roots=["fixture_layout","fixture_adopt","fixture_configure","fixture_reset",
           "fixture_snapshot","fixture_sg_mode","fixture_select_full","fixture_select_light"]
    prior=["SCENERY_SELECT_ONLY=1","SCENERY_REPLAY_LEAN=1",
           "SCENERY_SUBMIT_BATCH=1","SCENERY_UV_SNAPSHOT=1","ACTOR_SETUP_LEAN=1"]
    arms={}
    for cone,on in itertools.product((0,1) if args.cone_matrix else (0,),(0,1)):
        arm=f"c{cone}-q{on}"
        obj=output/(arm+".o")
        arm_flags,arm_profile=build_profile.expand_existing(output/"release-profile",compiler,
            args.sdk_root.resolve(),profile,[*prior,f"SCENERY_CONE={cone}",
            f"SCENERY_SELECT_LEAN2={on}"],prefix=arm)
        flags=[*arm_flags["native_static"],*("-D"+value for value in args.define)]
        builder.run([*flags,"-fstack-usage","-c",fixture,"-o",obj],label=arm)
        elf=output/(arm+".elf")
        builder.run([compiler,"-m4-single","-ml","-nostartfiles","-Wl,--gc-sections",
            "-Wl,-T,"+str(linker),"-Wl,-e,_fixture_select_light",
            *("-Wl,-u,_"+x for x in roots),obj,geometry,"-lm","-o",elf],label=arm+"-link")
        prefix=str(compiler).removesuffix("g++")
        (output/(arm+".disassembly.txt")).write_bytes(builder.run(
            [prefix+"objdump","-d","-C",elf],label=arm+"-disassembly"))
        arms[arm]=dict(elf=str(elf),sha256=build_profile.sha(elf),object_sha256=build_profile.sha(obj),
            sections=build_profile.sections(elf),stack_usage=build_profile.stack_usage(obj.with_suffix(".su")),
            flags=flags,profile=arm_profile)
    cases=write_cases(output/"cases")
    report=dict(status="PASS",scope=__doc__,base="75229c8fa54d4a939095666036c8ee1c8f52e2fe",
        profile=profile,source_sha256=inputs,extraction=extracted,fixture_sha256=build_profile.sha(fixture),
        fixture_resolution=[640,480],arms=arms,cases=str(output/"cases/cases.json"),case_count=len(cases))
    for path,digest in inputs.items():assert build_profile.sha(ROOT/path)==digest,(path,"changed during target build")
    (output/"target-build-controls.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--sh4-cxx",type=Path,required=True)
    p.add_argument("--kos-root",type=Path,required=True)
    p.add_argument("--sdk-root",type=Path,required=True)
    p.add_argument("--cone-matrix",action="store_true")
    p.add_argument("--define",action="append",default=[],help="Explicit diagnostic fixture compiler define; recorded in every arm")
    result=build(p.parse_args())
    print(json.dumps(dict(status=result["status"],arms=list(result["arms"]))))


if __name__=="__main__":main()
