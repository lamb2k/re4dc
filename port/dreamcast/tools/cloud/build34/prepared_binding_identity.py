#!/usr/bin/env python3
"""Pinned OFF identity, actual Make selection and host footprint for prepared binding."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
DC=HERE.parents[2]
ROOT=DC.parents[1]
PLATFORM=DC/'game/platform'
ROOM=DC/'room'
BASE='14b5c196db699640f7a9f39bc2318df22dc45ade'
MODEL=PLATFORM/'native_model.cpp'
UI=PLATFORM/'native_ui.cpp'
MAKE=DC/'game/prepared_binding34.mk'

def run(command):
    result=subprocess.run(command,capture_output=True,text=True,cwd=ROOT)
    if result.returncode:raise RuntimeError(f'{command!r}\n{result.stderr}')
    return result.stdout

def sha(data):return hashlib.sha256(data).hexdigest()

def primary_make(out):
    kos=out/'make-kos';kos.mkdir();(kos/'Makefile.rules').write_text('')
    deps=['ACTOR_TRANSACTION=1','NATIVE_ACTOR=1','NATIVE_ACTOR_FAST=1',
          'NATIVE_ACTOR_SKIN=1','NATIVE_ACTOR_SKIN_LAZY=1','SKIN_PALETTE_LAZY=1',
          'COARSE_SOURCE_ACTORS=1','COARSE_LEON=1',
          'COARSE_GANADO=1','COARSE_GANADO_CAST=1','COARSE_ONE_SUBMIT=1',
          'COARSE_SKIN_FTRV=1','COARSE=1','PACE_CATCHUP=2','PACE_TRANS_SKIP=4063',
          'GAME_ATCHK=1','GAME_ATCHK_LIST=1','COARSE_ACTOR_ASSET_DIR='+str(kos),
          'D349_RENDERER_STACK=1','PVR_STREAM=1','PLAN_OWNER_SCOPED=1',
          'MODEL_DRAW_PLANS=1','UI_HANDLES=1','PS2_UPLOAD_INCARNATION=1']
    targets=['obj/platform/native_model.o','obj/platform/native_ui.o',
             'obj/platform/native_draw_plan_owner.o','obj/src/game/atari.o']
    def command(extra):
        return subprocess.run(['make','--no-print-directory','-f','Makefile','-n',
            'KOS_BASE='+str(kos),*deps,*extra,*targets],cwd=DC/'game',capture_output=True,text=True)
    arms=[]
    for extra in ([],['PREPARED_BINDING34=0'],['PREPARED_BINDING34=1']):
        result=command(extra);assert result.returncode==0,result.stderr
        arms.append([line for line in result.stdout.splitlines() if line.startswith('kos-c++')])
    assert arms[0]==arms[1] and len(arms[2])==len(targets)
    for i,line in enumerate(arms[2]):
        assert line.count('-DRE4DC_PREPARED_BINDING34=1')==int(i<2),line
    assert all('RE4DC_PREPARED_BINDING34' not in line for line in arms[0])
    for value in ('','2','%','0%','1%','0 1'):
        result=command(['PREPARED_BINDING34='+value])
        assert result.returncode!=0 and 'PREPARED_BINDING34 must be exactly 0 or 1' in result.stderr,value
    return dict(absent_zero_identical=True,on_scoped_targets=targets[:2],unaffected_targets=targets[2:])

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    primary=primary_make(out)
    stub=out/'stub';(stub/'dc').mkdir(parents=True);(stub/'kos').mkdir()
    (stub/'dc/pvr.h').write_text('#pragma once\n#include <cstddef>\n#include <cstdint>\n'
        'struct pvr_vertex_t{std::uint32_t flags;float x,y,z,u,v;std::uint32_t argb,oargb;};\n'
        'struct pvr_poly_hdr_t{std::uint32_t words[8];};\n'
        '#define PVR_CMD_VERTEX 0xe0000000U\n#define PVR_CMD_VERTEX_EOL 0xf0000000U\n'
        'int pvr_prim(const void*,std::size_t);\n')
    for name in ('kos.h','dc/sq.h','kos/fs.h'):(stub/name).write_text('')
    baseline=out/'baseline';baseline.mkdir()
    for filename in ('native_model.cpp','native_ui.cpp'):
        (baseline/filename).write_bytes(subprocess.check_output(
            ['git','show',f'{BASE}:port/dreamcast/game/platform/{filename}'],cwd=ROOT))
    includes=['-I'+str(stub),'-I'+str(PLATFORM),'-I'+str(PLATFORM/'include'),'-I'+str(ROOM)]
    model_flags=['-DRE4DC_D349_RENDERER_STACK=1','-DRE4DC_MODEL_DRAW_PLANS=1','-DRE4DC_PLAN_OWNER_SCOPED=1']
    ui_flags=[*model_flags,'-DRE4DC_ACTOR_TRANSACTION=1','-DRE4DC_UI_HANDLES=1',
              '-DRE4DC_PS2_UPLOAD_INCARNATION=1','-DRE4DC_PVR_STREAM=1']
    identity={}
    for label,base,current,flags,kinds in (
        ('native_model',baseline/'native_model.cpp',MODEL,model_flags,('pre','obj')),
        ('native_ui',baseline/'native_ui.cpp',UI,ui_flags,('pre',))):
        identity[label]={}
        for mode in ('absent','zero'):
            extra=[] if mode=='absent' else ['-DRE4DC_PREPARED_BINDING34=0']
            identity[label][mode]={}
            for kind in kinds:
                suffix='cpp' if kind=='pre' else 'o'
                generated=[]
                for source,arm in ((base,'base'),(current,'current')):
                    destination=out/f'{label}-{mode}-{arm}.{suffix}'
                    command=['g++','-std=c++20','-O2','-fno-ident',*includes,*flags,*extra,
                             *(['-E','-P'] if kind=='pre' else ['-c']),str(source),'-o',str(destination)]
                    run(command);generated.append(destination.read_bytes())
                assert generated[0]==generated[1],(label,mode,kind)
                identity[label][mode][kind]=dict(equal=True,bytes=len(generated[0]),sha256=sha(generated[0]))
    fixture=out/'fragment.mk'
    fixture.write_text('OBJDIR := /tmp/binding34-identity-objects\nPLATFORM_CPPFLAGS :=\ninclude '+str(MAKE)+
        '\n.PHONY: all $(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/native_model.o\n'
        'all: $(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/native_model.o\n'
        '$(OBJDIR)/platform/native_ui.o:\n\t@printf "ui:%s\\n" "$(PLATFORM_CPPFLAGS)"\n'
        '$(OBJDIR)/platform/native_model.o:\n\t@printf "model:%s\\n" "$(PLATFORM_CPPFLAGS)"\n')
    required=['ACTOR_TRANSACTION=1','PLAN_OWNER_SCOPED=1','D349_RENDERER_STACK=1',
              'MODEL_DRAW_PLANS=1','UI_HANDLES=1','PS2_UPLOAD_INCARNATION=1','PVR_STREAM=1']
    make={}
    for value in ('0','1','','2','%','1 1'):
        command=['make','--no-print-directory','-f',str(fixture),'all','PREPARED_BINDING34='+value,*required]
        result=subprocess.run(command,capture_output=True,text=True,cwd=ROOT)
        assert (result.returncode==0)==(value in ('0','1')),(value,result.stderr)
        make[value]=result.stdout.strip() if result.returncode==0 else 'REJECTED'
    assert make['0']=='ui:\nmodel:'
    assert make['1']=='ui:-DRE4DC_PREPARED_BINDING34=1 -DRE4DC_PLAN_OWNER_SCOPED=1\nmodel:-DRE4DC_PREPARED_BINDING34=1'
    for missing in required:
        command=['make','--no-print-directory','-f',str(fixture),'all','PREPARED_BINDING34=1',
                 *(x for x in required if x!=missing)]
        result=subprocess.run(command,capture_output=True,text=True,cwd=ROOT)
        assert result.returncode!=0,missing
    footprint={}
    for enabled in (0,1):
        target=out/f'model-footprint{enabled}.o'
        run(['g++','-std=c++20','-O2','-fstack-usage',*includes,*model_flags,
             f'-DRE4DC_PREPARED_BINDING34={enabled}','-c',str(MODEL),'-o',str(target)])
        rows=(out/f'model-footprint{enabled}.su').read_text().splitlines()
        stack=[int(row.split('\t')[-2]) for row in rows if ':void re4dc_model_submit(' in row]
        assert len(stack)==1
        footprint[str(enabled)]=dict(model_submit_stack_bytes=stack[0],model_object_bytes=target.stat().st_size)
    report=dict(status='PASS',base=BASE,identity=identity,make=make,primary_make=primary,make_missing_prerequisites_rejected=required,
                footprint=footprint,source_sha256={str(path.relative_to(ROOT)):sha(path.read_bytes())
                    for path in (MODEL,UI,MAKE,Path(__file__))})
    receipt=out/'prepared-binding-identity.json'
    receipt.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',identity=identity,make=make,footprint=footprint,receipt=str(receipt))))

if __name__=='__main__':main()
