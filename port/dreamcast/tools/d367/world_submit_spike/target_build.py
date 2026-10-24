#!/usr/bin/env python3
"""Build isolated real SH4 world direct-boundary + uncontended KOS fixtures.

The complete native_ui TU is compiled after replacing only load() and
stream_open() with explicit controlled cold edges. Hot renderer/cache/packet
code and actual KOS sq/mutex/genwait/MMU functions are retained. No vertex
transform/emission, game frame, storage I/O, scheduler contention or PVR wait
is priced by this fixture.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import build_profile
from build_profile import Build, sections, sha, stack_usage

HERE=Path(__file__).resolve().parent
DC=HERE.parents[2]
ROOT=DC.parents[1]
BASELINE="86c1b91a72a8d6d419cf9c5fa0c335ff3f552a9d"
TRAPS=("__assert", "__dreamcast_get_ticks", "abort", "memalign", "puts",
       "pvr_list_begin", "pvr_list_finish", "pvr_prim", "pvr_set_presort_mode",
       "re4dc_lbx_open", "re4dc_log", "re4dc_missing", "re4dc_ui_heap_free",
       "thd_add_to_runnable", "thd_block_now", "thd_get_errno", "thd_remove_from_runnable")
CONTROLLED_GLOBALS=("dbglog_level", "hardware_sys_mode", "re4dc_mv_receiver", "re4dc_ps2_sky_header")


def replace_body(source, signature, body, end_marker=None):
    assert source.count(signature)==1,signature
    start=source.index(signature)
    first=source.index("{",start)
    if end_marker is not None:
        # load() has mutually exclusive preprocessor branches opening braces;
        # its explicit post-definition macro cleanup is the stable delimiter.
        end=source.index(end_marker,first)+2
        return source[:first]+"{"+body+"}"+source[end:]
    depth=0
    tokens=re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]')
    for match in tokens.finditer(source,first):
        token=match.group()
        if token=="{":depth+=1
        elif token=="}":
            depth-=1
            if not depth:return source[:first]+"{"+body+"}"+source[match.end():]
    raise ValueError("Unclosed source definition: "+signature)


def kos_flags(compiler,kos):
    values=[str(compiler).removesuffix("g++")+"gcc", "-std=gnu17", "-O2", "-fno-PIC", "-fno-PIE",
            "-fomit-frame-pointer", "-m4-single", "-ml", "-mfsrra", "-mfsca",
            "-ffunction-sections", "-fdata-sections", "-matomic-model=soft-gusa", "-ftls-model=local-exec",
            "-D__DREAMCAST__", "-D_arch_dreamcast=1", "-D_arch_sub_pristine=1", "-Wall"]
    for path in (kos/"include",kos/"kernel/arch/dreamcast/include",kos/"addons/include"):
        values += ["-isystem",str(path)]
    return values


def build(args):
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    compiler=args.sh4_cxx.resolve();kos=args.kos_root.resolve();sdk=args.sdk_root.resolve()
    builder=Build(output)
    profiles,profile=build_profile.derive(output/"release-profile",compiler,kos,sdk,cost_dependencies=True)
    cflags=kos_flags(compiler,kos)
    dependencies=[];inputs={}
    for name,relative in (("sq","kernel/arch/dreamcast/hardware/sq.c"),
                          ("mutex","kernel/thread/mutex.c"),
                          ("genwait","kernel/thread/genwait.c"),
                          ("mmu","kernel/arch/dreamcast/kernel/mmu.c"),
                          ("pvr_prim","kernel/arch/dreamcast/hardware/pvr/pvr_prim.c")):
        source=kos/relative;obj=output/("kos-"+name+".o")
        builder.run([*cflags,"-c",source,"-o",obj],label="kos-"+name)
        dependencies.append(obj);inputs[str(source)]=sha(source)
    state=HERE/"target_kos_state.c";obj=output/"kos-state.o"
    builder.run([*cflags,"-c",state,"-o",obj],label="kos-state")
    dependencies.append(obj);inputs[str(state.relative_to(ROOT))]=sha(state)
    traps=output/"forbidden-edges.S"
    assembly=[]
    for name in TRAPS:
        symbol="_"+name
        assembly += ['.section .text.'+symbol+',"ax"', '.align 1', '.global '+symbol,
                     '.type '+symbol+',@function',symbol+':','trapa #255','.size '+symbol+',.-'+symbol]
    for name in CONTROLLED_GLOBALS:
        symbol="_"+name
        assembly += ['.section .bss.'+symbol+',"aw",@nobits','.align 2','.global '+symbol,
                     '.type '+symbol+',@object',symbol+':','.space 4','.size '+symbol+',4']
    traps.write_text('\n'.join(assembly)+'\n')
    obj=output/"forbidden-edges.o"
    builder.run([str(compiler).removesuffix("g++")+"gcc","-m4-single","-ml","-c",traps,"-o",obj],label="forbidden-edges")
    dependencies.append(obj)
    for name in ("texture_package","pvr_geometry"):
        source=DC/("room/"+name+".cpp");obj=output/(name+".o")
        builder.run([*profiles[name],"-c",source,"-o",obj],label=name)
        dependencies.append(obj);inputs[str(source.relative_to(ROOT))]=sha(source)
    linker=output/"fixture.ld"
    linker.write_text("""SECTIONS {
 /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) }
 . = 0x100000;
 .text : { *(.text*) }
 .rodata : { *(.rodata*) }
 .data : { *(.data*) }
 .bss : { *(.bss*) *(COMMON) }
}
""")
    source_path=DC/"game/platform/native_ui.cpp"
    old=subprocess.check_output(["git","show",args.baseline+":"+str(source_path.relative_to(ROOT))],cwd=ROOT).decode()
    current=source_path.read_text();template=(HERE/"target_fixture.cpp.in").read_text()
    inputs[str(source_path.relative_to(ROOT))]=sha(source_path)
    inputs[str((HERE/"target_fixture.cpp.in").relative_to(ROOT))]=sha(HERE/"target_fixture.cpp.in")
    arms={}
    for arm,source,knob in (("baseline",old,0),("batch",current,1)):
        source=replace_body(source,"Entry* load(const Re4dcUiImage& image,bool pin=true,const Key* prepared_key=nullptr)",
                            " return static_cast<Entry*>(fixture_load_control(&image,pin,prepared_key)); ",
                            "\n}\n#undef RE4DC_OPEN_PACKAGE")
        source=source.replace("Entry* load(const Re4dcUiImage& image,bool pin=true,const Key* prepared_key=nullptr)",
                              "__attribute__((noinline,noclone)) Entry* load(const Re4dcUiImage& image,bool pin=true,const Key* prepared_key=nullptr)",1)
        source=replace_body(source,"void stream_open()", " fixture_scene_open_control(); ")
        text=template.replace("@TEXTURE_HEADER@",str(DC/"room/texture_package.hpp")).replace("@NATIVE_UI_SOURCE@",source)
        fixture=output/(arm+"-fixture.cpp");fixture.write_text(text)
        obj=output/(arm+"-fixture.o")
        builder.run([*profiles["native_ui"],"-DRE4DC_SCENERY_SUBMIT_BATCH="+str(knob),
                     "-iquote",source_path.parent,"-fstack-usage","-c",fixture,"-o",obj],label=arm+"-fixture")
        elf=output/(arm+".elf")
        roots=["_fixture_submit","_fixture_layout","_fixture_configure","_fixture_snapshot", "_fixture_kos_reset",
               "_fixture_prepare_normal_end","_fixture_normal_end"]
        command=[compiler,"-m4-single","-ml","-nostartfiles","-Wl,--gc-sections","-Wl,-T,"+str(linker),
                 "-Wl,-e,_fixture_submit",*("-Wl,-u,"+name for name in roots),obj,*dependencies,"-lm","-o",elf]
        try:
            builder.run(command,label=arm+"-link")
        except RuntimeError:
            # Fail explicitly until every cold/unavailable edge is reviewed;
            # never make unknown symbols silently return success.
            raise
        prefix=str(compiler).removesuffix("g++")
        (output/(arm+".disassembly.txt")).write_bytes(builder.run([prefix+"objdump","-d","-C",elf],label=arm+"-disassembly"))
        (output/(arm+".symbols.txt")).write_bytes(builder.run([prefix+"nm","-n","-C",elf],label=arm+"-symbols"))
        arms[arm]=dict(elf=str(elf),sha256=sha(elf),fixture_sha256=sha(fixture),
                       sections=sections(elf),stack_usage=stack_usage(obj.with_suffix(".su")))
    report=dict(status="PASS",scope=__doc__,baseline=args.baseline,profile=profile,kos_flags=cflags,
                forbidden_call_edges=list(TRAPS),controlled_zero_globals=list(CONTROLLED_GLOBALS),
                input_sha256=inputs,arms=arms)
    (output/"target-build-controls.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--sh4-cxx",type=Path,required=True)
    parser.add_argument("--kos-root",type=Path,required=True)
    parser.add_argument("--sdk-root",type=Path,required=True)
    parser.add_argument("--baseline",default=BASELINE)
    report=build(parser.parse_args());print(json.dumps({"status":report["status"],"arms":list(report["arms"])}))


if __name__=="__main__":main()
