#!/usr/bin/env python3
"""Link complete production native UI emit code with private layout exports.

Raw draw/glyph function sections must match the independently compiled source
without fixture exports. Package metadata lookup has typed fixture edges.
stream_send is an observed unchanged edge in the interpreter. Other unresolved
paths are linked to unmapped address zero and fail closed if reached; only
cached-header draws are qualified, not allocation, upload, KOS or GPU services.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
import build_profile as p


def build(args):
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    cxx,kos,sdk=args.sh4_cxx.resolve(),args.kos_root.resolve(),args.sdk_root.resolve()
    flags,profile=p.derive(out/'profile',cxx,kos,sdk,variants=('public',),units=('native_ui','pvr_geometry'))
    b=p.Build(out);nf=flags['public']['native_ui'];pf=flags['public']['pvr_geometry']
    geom=p.DC/'room/pvr_geometry.cpp';go=out/'pvr_geometry.o'
    b.run([*pf,'-x','c++','-','-c','-o',go],cwd=geom.parent,source=geom.read_bytes(),label='geometry')
    edges=out/'edges.cpp';edges.write_bytes((HERE/'native_edges.cpp.in').read_bytes());eo=out/'edges.o'
    b.run([*nf,'-I'+str(p.DC/'room'),'-c',edges,'-o',eo],label='edges')
    script=out/'fixture.ld';script.write_text('''SECTIONS {
 /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) }
 . = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) }
 . = 0x200000; .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) }
}
''')
    source=p.DC/'game/platform/native_ui.cpp';current=source.read_bytes();append=(HERE/'native_fixture.inc').read_bytes()
    arms={};specs=[('l0',0,current),('l1',1,current)]
    if args.initial_source:specs.append(('initial',1,args.initial_source.read_bytes()))
    if args.inline_probe:
        old=b'auto vertex=[&](float x,float y,float u,float v,unsigned flags){'
        new=b'auto vertex=[&](float x,float y,float u,float v,unsigned flags) __attribute__((always_inline)) {'
        assert current.count(old)==1,'inline probe expects the original scalar lambda once'
        clone=current.replace(old,new)
        (out/'inline.source.cpp').write_bytes(clone)
        specs.append(('inline',1,clone))
    for name,lean,blob in specs:
        obj=out/(name+'.o');prod=out/(name+'-production.o');elf=out/(name+'.elf')
        for path,text in ((prod,blob),(obj,blob+b'\n'+append)):
            b.run([*nf,f'-DRE4DC_UI_DRAW_LEAN={lean}','-x','c++','-','-c','-fstack-usage','-o',path],
                cwd=source.parent,source=text,label=path.stem)
        compared=[]
        for section in ('.text._ZL12ui_draw_quadj',)+ (('.text._ZN12_GLOBAL__N_1L14glyph_draw_runEjj',) if lean else ()):
            files=[]
            for path in (prod,obj):
                dump=out/(path.stem+'-'+str(len(compared))+'.bin')
                b.run([str(cxx).removesuffix('g++')+'objcopy','--dump-section',section+'='+str(dump),path,
                    out/(path.stem+'-section-copy.o')],label=path.stem+'-section')
                files.append(dump)
            assert files[0].read_bytes()==files[1].read_bytes(),(name,section,'fixture changed production function')
            compared.append(dict(section=section,bytes=files[0].stat().st_size,sha256=p.sha(files[0])))
        b.run([cxx,'-m4-single','-ml','-nostartfiles','-Wl,--gc-sections','-Wl,--unresolved-symbols=ignore-all',
            '-Wl,-T,'+str(script),'-Wl,-e,_ui_fixture_draw','-Wl,-u,_ui_fixture_layout',obj,go,eo,'-lm','-o',elf],label=name+'-link')
        (out/(name+'.disassembly.txt')).write_bytes(b.run([str(cxx).removesuffix('g++')+'objdump','-dC',elf],label=name+'-objdump'))
        arms[name]=dict(elf=str(elf),sha256=p.sha(elf),object_sha256=p.sha(prod),source_sha256=hashlib.sha256(blob).hexdigest(),
            sections=p.sections(prod),stack_usage=p.stack_usage(prod.with_suffix('.su')),production_function_identity=compared)
    assert source.read_bytes()==current,'source changed during build'
    result=dict(status='PASS',scope=__doc__,arms=arms,profile=profile,
        source_sha256={str(x.relative_to(p.ROOT)):p.sha(x) for x in (source,geom,Path(__file__),HERE/'native_fixture.inc',HERE/'native_edges.cpp.in',HERE/'build_profile.py')})
    (out/'native-build.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','sh4-cxx','kos-root','sdk-root'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--initial-source',type=Path)
    parser.add_argument('--inline-probe',action='store_true',help='temporary forced-inline clone; does not edit the production source')
    r=build(parser.parse_args());print(json.dumps(dict(status=r['status'],arms=list(r['arms']))))


if __name__=='__main__':main()
