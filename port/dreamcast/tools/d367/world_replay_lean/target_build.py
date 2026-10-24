#!/usr/bin/env python3
"""Build real SH4 selector, replay-setup and screen-memo fixtures.

Full native_static layout and setup bodies are retained. emit_pick is the sole
replaced renderer body, an observed geometry edge. mat_load and external UI
accounting use explicit entry/return stubs. No transform, TA submission or whole
game frame is priced. Production identity is the separate build_controls gate.
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
DC=HERE.parents[2]
ROOT=DC.parents[1]
SOURCE=DC/"game/platform/native_static.cpp"
sys.path.insert(0,str(HERE.parent/"world_submit_spike"))
import build_profile
import check_runtime
sys.path.insert(0,str(HERE.parent/"world_setup_spike"))
import generate_fixture
from selection_cases import write_cases

RETURN_ONE=("fixture_emit_control","re4dc_model_packet_streaming","re4dc_ui_frame")
RETURN_VOID=("mat_load","re4dc_model_result","re4dc_model_direct_end",
             "re4dc_ps2_world_direct_end_batch","re4dc_ps2_world_batch_close",
             "re4dc_model_packet_abort")
TRAPS=("re4dc_model_packet_commit","re4dc_log","re4dc_missing")


def build(args):
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    compiler=args.sh4_cxx.resolve()
    profiles,profile=build_profile.derive(output/"release-profile",compiler,
        args.kos_root.resolve(),args.sdk_root.resolve(),cost_dependencies=True)
    builder=build_profile.Build(output)
    source=SOURCE.read_text()
    inputs={str(SOURCE.relative_to(ROOT)):hashlib.sha256(source.encode()).hexdigest()}
    for path in sorted((SOURCE.parent/"include").glob("scenery_*")):
        inputs[str(path.relative_to(ROOT))]=build_profile.sha(path)
    emit=check_runtime.function(source,"int emit_pick(const Pick& pk){")
    controlled=source.replace(emit,"int emit_pick(const Pick& pk){ return fixture_emit_control(this,&pk); }")
    modified=output/"native_static.cpp"
    modified.write_text('extern "C" int fixture_emit_control(void*,const void*);\n'+controlled)
    selection=output/"selection_fixture.cpp"
    extracted=generate_fixture.generate_source(selection,SOURCE)
    text=selection.read_text().replace(str(SOURCE.resolve()),str(modified))
    extra=(HERE/"target_fixture.cpp.in").read_text()
    chunk_part=check_runtime.function(source,"struct ChunkPart {")
    chunk_flush=check_runtime.function(source,"auto chunk_flush=[&]()->int{")
    extra=extra.replace("@CHUNK_PART@",chunk_part).replace("@CHUNK_FLUSH@",chunk_flush)
    fixture=output/"target_fixture.cpp";fixture.write_text(text+"\n"+extra)
    inputs[str((HERE/"target_fixture.cpp.in").relative_to(ROOT))]=build_profile.sha(HERE/"target_fixture.cpp.in")
    stubs=output/"edges.S";asm=[]
    for name in (*RETURN_ONE,*RETURN_VOID,*TRAPS):
        symbol="_"+name
        asm += [f'.section .text.{symbol},"ax"','.align 1',f'.global {symbol}',
                f'.type {symbol},@function',symbol+':']
        if name in TRAPS:asm+=['trapa #255']
        else:
            if name in RETURN_ONE:asm+=['mov #1,r0']
            asm+=['rts','nop']
        asm += [f'.size {symbol},.-{symbol}']
    for name,value in (("re4dc_screen_wf",0x44200000),("re4dc_screen_hf",0x43f00000),
                       ("re4dc_screen_half_wf",0x43a00000),("re4dc_screen_half_hf",0x43700000)):
        symbol="_"+name
        asm += [f'.section .data.{symbol},"aw"','.align 2',f'.global {symbol}',
                f'.type {symbol},@object',symbol+':',f'.long {value}',f'.size {symbol},4']
    stubs.write_text('\n'.join(asm)+'\n')
    stub_obj=output/"edges.o"
    builder.run([str(compiler).removesuffix("g++")+"gcc","-m4-single","-ml","-c",stubs,"-o",stub_obj],label="edges")
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
    roots=["fixture_layout","fixture_adopt","fixture_configure","fixture_reset","fixture_snapshot",
           "fixture_select_full","fixture_select_light","fixture_replay_layout","fixture_prepare_replay",
           "fixture_replay","fixture_screen"]
    common=[x for x in profiles["native_static"] if not x.startswith(("-DRE4DC_SCENERY_REPLAY_LEAN=",
        "-DRE4DC_SCENERY_SELECT_ONLY=","-DRE4DC_SCENERY_SUBMIT_BATCH="))]
    arms={}
    for replay,batch in itertools.product((0,1), (0,1) if args.batch_matrix else (0,)):
        arm=f"r{replay}-b{batch}"
        obj=output/(arm+".o")
        flags=[*common,"-DRE4DC_SCENERY_SELECT_ONLY=1",f"-DRE4DC_SCENERY_REPLAY_LEAN={replay}",
               f"-DRE4DC_SCENERY_SUBMIT_BATCH={batch}","-iquote",str(SOURCE.parent)]
        builder.run([*flags,"-fstack-usage","-c",fixture,"-o",obj],label=arm)
        elf=output/(arm+".elf")
        builder.run([compiler,"-m4-single","-ml","-nostartfiles","-Wl,--gc-sections", "-Wl,-T,"+str(linker),
            "-Wl,-e,_fixture_replay",*("-Wl,-u,_"+x for x in roots),obj,geometry,stub_obj,"-lm","-o",elf],label=arm+"-link")
        prefix=str(compiler).removesuffix("g++")
        (output/(arm+".disassembly.txt")).write_bytes(builder.run([prefix+"objdump","-d","-C",elf],label=arm+"-disassembly"))
        arms[arm]=dict(elf=str(elf),sha256=build_profile.sha(elf),object_sha256=build_profile.sha(obj),
            sections=build_profile.sections(elf),stack_usage=build_profile.stack_usage(obj.with_suffix(".su")),flags=flags)
    cases=write_cases(output/"cases")
    report=dict(status="PASS",scope=__doc__,base="451bed6faa2c37f7f9aa05d6fb1116ec64219ebc",
        profile=profile,source_sha256=inputs,extraction=extracted,
        replaced_emit_pick_sha256=hashlib.sha256(emit.encode()).hexdigest(),
        chunk_flush_sha256=hashlib.sha256(chunk_flush.encode()).hexdigest(),
        observed_return_edges=list(RETURN_ONE+RETURN_VOID),forbidden_edges=list(TRAPS),
        fixture_resolution=[640,480],
        arms=arms,cases=str(output/"cases/cases.json"),case_count=len(cases))
    for path,digest in inputs.items():
        assert build_profile.sha(ROOT/path)==digest,(path,"changed during target build")
    (output/"target-build-controls.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--sh4-cxx",type=Path,required=True)
    p.add_argument("--kos-root",type=Path,required=True)
    p.add_argument("--sdk-root",type=Path,required=True)
    p.add_argument("--batch-matrix",action="store_true")
    result=build(p.parse_args())
    print(json.dumps(dict(status=result["status"],arms=list(result["arms"]))))


if __name__=="__main__":main()
