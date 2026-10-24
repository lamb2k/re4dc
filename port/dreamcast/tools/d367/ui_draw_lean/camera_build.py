#!/usr/bin/env python3
"""Link actual messageCamera, SDK ortho and GX state functions for measurement.

The complete mes.cpp and gx_stub.cpp objects use their current public Make
flags. C_MTXOrtho is built from the normal stripped SDK source and SDK flags.
PSMTXIdentity binds to its existing scalar SH4 identity body, copied verbatim
from mtx_sh4.S solely to avoid retaining unrelated assembly functions. The
fixture alias is the same as ps_alias_sh4.ld. No production assembly/linker
changes or arithmetic edge adapters are introduced.
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
    cc=Path(str(cxx).removesuffix('g++')+'gcc')
    flags,profile=p.derive(out/'profile',cxx,kos,sdk,variants=('public',),units=('mes','gx_stub'))
    math_flags,math_profile=p.derive_math(out/'math-profile',cc,kos,sdk)
    b=p.Build(out)
    original=p.ROOT/'src/lib/mtx44.c';strip=p.DC/'game/platform/sdk/strip_cw_asm.py'
    generated=out/'mtx44.c'
    b.run([sys.executable,strip,original,generated],label='strip-mtx44')
    mtx=out/'mtx44.o';b.run([*math_flags['mtx44'],'-fstack-usage','-c',generated,'-o',mtx],label='mtx44')
    asm=p.DC/'game/platform/mtx_sh4.S';text=asm.read_text()
    first=text.index('        .global _re4dc_sh4_MTXIdentity')
    last=text.index('\n',text.index('        .size   _re4dc_sh4_MTXIdentity',first))
    identity=out/'identity.S';identity.write_text('.text\n.align 2\n'+text[first:last]+'\n')
    identity_obj=out/'identity.o'
    b.run([*math_flags['mtx_sh4'],'-c',identity,'-o',identity_obj],label='identity')
    gx=p.DC/'game/platform/gx_stub.cpp';gxobj=out/'gx_stub.o'
    b.run([*flags['public']['gx_stub'],'-x','c++','-','-c','-fstack-usage','-o',gxobj],
        cwd=gx.parent,source=gx.read_bytes(),label='gx_stub')
    script=out/'fixture.ld';script.write_text('''SECTIONS {
 /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) }
 . = 0x100000;
 .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) }
}
_PSMTXIdentity = _re4dc_sh4_MTXIdentity;
''')
    source=p.ROOT/'src/game/mes.cpp';blob=source.read_bytes();arms={}
    for lean in (0,1):
        name='l'+str(lean);obj=out/(name+'.o');elf=out/(name+'.elf')
        b.run([*flags['public']['mes'],f'-DRE4DC_UI_DRAW_LEAN={lean}','-x','c++','-',
            '-c','-fstack-usage','-o',obj],cwd=source.parent,source=blob,label=name)
        b.run([cxx,'-m4-single','-ml','-nostartfiles','-Wl,--gc-sections','-Wl,-T,'+str(script),
            '-Wl,-e,_messageCamera',obj,gxobj,mtx,identity_obj,'-lm','-o',elf],label=name+'-link')
        (out/(name+'.disassembly.txt')).write_bytes(b.run([str(cxx).removesuffix('g++')+'objdump','-dC',elf],label=name+'-objdump'))
        arms[name]=dict(elf=str(elf),sha256=p.sha(elf),object_sha256=p.sha(obj),
            sections=p.sections(obj),stack_usage=p.stack_usage(obj.with_suffix('.su')))
    assert source.read_bytes()==blob,'source changed during build'
    result=dict(status='PASS',scope=__doc__,arms=arms,profile=profile,math_profile=math_profile,
        source_sha256={str(x.relative_to(p.ROOT)):p.sha(x) for x in
            (source,gx,original,strip,asm,p.DC/'game/platform/ps_alias_sh4.ld',Path(__file__),HERE/'build_profile.py')},
        identity_excerpt_sha256=p.sha(identity),sdk_generated_sha256=p.sha(generated))
    (out/'camera-build.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','sh4-cxx','kos-root','sdk-root'):parser.add_argument('--'+name,type=Path,required=True)
    r=build(parser.parse_args());print(json.dumps(dict(status=r['status'],arms=list(r['arms']))))


if __name__=='__main__':main()
