#!/usr/bin/env python3
"""Link full public bridge and GX objects with typed unchanged service edges.

Only the standalone edge TU is synthetic. It retains actual headers/layouts;
the unchanged screen-matrix concat is represented by a fixed identity-input
copy. Original SH4ZAM arithmetic, game texture lookup, camera selection and
native enqueue costs are excluded. The complete re4dc_draw_id_quad body runs.
"""
import argparse
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
import build_profile as p


def build(args):
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    cxx,kos,sdk=args.sh4_cxx.resolve(),args.kos_root.resolve(),args.sdk_root.resolve()
    flags,profile=p.derive(out/'profile',cxx,kos,sdk,variants=('public',),units=('ui_bridge','gx_stub'))
    b=p.Build(out);bf=flags['public']['ui_bridge']
    gx=p.DC/'game/platform/gx_stub.cpp';go=out/'gx_stub.o'
    b.run([*flags['public']['gx_stub'],'-x','c++','-','-c','-o',go],cwd=gx.parent,source=gx.read_bytes(),label='gx')
    edges=out/'edges.cpp';edges.write_bytes((HERE/'bridge_edges.cpp.in').read_bytes());eo=out/'edges.o'
    b.run([*bf,'-c',edges,'-o',eo],label='edges')
    script=out/'fixture.ld';script.write_text('''SECTIONS {
 /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) }
 . = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) }
 . = 0x200000; .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) }
}
''')
    source=p.DC/'game/ui_bridge.cpp';blob=source.read_bytes();arms={}
    for lean in (0,1):
        name='l'+str(lean);obj=out/(name+'.o');elf=out/(name+'.elf')
        b.run([*bf,f'-DRE4DC_UI_DRAW_LEAN={lean}','-x','c++','-','-c','-fstack-usage','-o',obj],
            cwd=source.parent,source=blob,label=name)
        b.run([cxx,'-m4-single','-ml','-nostartfiles','-Wl,--gc-sections','-Wl,--unresolved-symbols=ignore-all',
            '-Wl,-T,'+str(script),'-Wl,-e,_re4dc_draw_id_quad','-Wl,-u,_ui_fixture_bridge_layout',obj,go,eo,'-lm','-o',elf],label=name+'-link')
        (out/(name+'.disassembly.txt')).write_bytes(b.run([str(cxx).removesuffix('g++')+'objdump','-dC',elf],label=name+'-objdump'))
        arms[name]=dict(elf=str(elf),sha256=p.sha(elf),object_sha256=p.sha(obj),
            sections=p.sections(obj),stack_usage=p.stack_usage(obj.with_suffix('.su')))
    assert source.read_bytes()==blob,'source changed during build'
    result=dict(status='PASS',scope=__doc__,arms=arms,profile=profile,
        source_sha256={str(x.relative_to(p.ROOT)):p.sha(x) for x in (source,gx,Path(__file__),HERE/'bridge_edges.cpp.in',HERE/'build_profile.py')})
    (out/'bridge-build.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','sh4-cxx','kos-root','sdk-root'):parser.add_argument('--'+name,type=Path,required=True)
    r=build(parser.parse_args());print(json.dumps(dict(status=r['status'],arms=list(r['arms']))))


if __name__=='__main__':main()
