#!/usr/bin/env python3
"""Joint source-owner/recipe qualification; no SDK or private assets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import actor_presentation32 as present
import skin_recipe32 as recipe_source

HERE=Path(__file__).resolve().parent;ROOT=present.ROOT;GAME=present.GAME;INC=present.INC
BASE='88e3045ac48ffce4253759c6229796c1755accce'
def fixture(negative_accounting=False):
    original_read=present.read
    def read(path,base=False):
        text=original_read(path,base)
        if negative_accounting and path==GAME/'actor_presentation32.inc':
            old=subprocess.check_output(['git','show',f'{BASE}:{path.relative_to(ROOT)}'],cwd=ROOT,text=True)
            sig='bool actor_presentation32_forget_source('
            text=text.replace(present.extract.function(text,sig),present.extract.function(old,sig))
        return text
    present.read=read
    try:code=present.fixture()
    finally:present.read=original_read
    code=code.replace('#include <initializer_list>','#include <initializer_list>\n#include <vector>\nusing u32=std::uint32_t;')
    code=code.replace('struct cModelInfo {','struct ModelData {unsigned weight_ext_num=0,weight_palette_num=1;void* pWeight=nullptr;};\nstruct cModelInfo {',1)
    fast=original_read(GAME/'platform/native_actor_fast.cpp');trans=original_read(ROOT/'src/game/trans.cpp')
    f=present.extract.function;r=present.extract.region
    primitive='alignas(32) unsigned char primitive[512*1024],actor_workspace[128*1024];unsigned primitive_used=0;'
    code=code.replace(primitive,'alignas(32) unsigned char primitive[512*1024],actor_workspace[128*1024];\n'
        'struct GxWork {u8* prim=primitive;}; GxWork work;GxWork* GXWORK(){return &work;}\n'
        '#define primitive_used unsigned(work.prim-primitive)\n'
        '#define PTR_INVALID(p) (!(p))\n#define U32Set(d,s) ((d)=(s))\n'
        'struct Log {unsigned errors=0;template<class...T>void err(int,int,const char*,T...){++errors;}} log_state,*pLog=&log_state;')
    code=code.replace('primitive_used=0','work.prim=primitive')
    allocator=r(trans,'#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32\nstatic unsigned skin_recipe_credit','// Allocates `size` bytes')
    allocator+='\n'+f(trans,'void* GetPrimBuff(int size)')+'\n'+f(trans,'extern "C" void* re4dc_prim_tail(unsigned bytes, unsigned reserve)')
    # Named host address/OOM adapters only. Source globals retain the actual
    # s32 ABI fields for identity; source allocator arithmetic uses host bytes.
    allocator=allocator.replace('const u8* base=(const u8*)pG->prim_cnt;',
        'const u8* base=pG->prim_cnt?primitive:nullptr;\n    if(!allocation_ok)return false;')
    allocator=allocator.replace('u8* base = (u8*) pG->prim_cnt;', 'u8* base = pG->prim_cnt?primitive:nullptr;')
    # In recipe0, the same controlled allocator refusal used by the existing
    # presentation suite must enter before touching the synthetic cursor.
    allocator=allocator.replace('extern "C" void* re4dc_prim_tail(unsigned bytes, unsigned reserve)\n{',
        'extern "C" void* re4dc_prim_tail(unsigned bytes, unsigned reserve)\n{\n    if(!allocation_ok)return nullptr;')
    old=f(code,'extern "C" void* re4dc_prim_tail(');code=code.replace(old,allocator)
    head=r(trans,'struct SkinLazyHead {',"// Trans()'s palette of weights")
    source_build=(HERE/'actor_joint32_source.cpp.in').read_text().replace('// @HEAD@',head)
    funcs='\n'.join(f(trans,sig) for sig in ('static void skinLazyBuild(', 'static int skinDeferPending(',
        'extern "C" void re4dc_skin_palette_resolve('))
    funcs+='\n#if RE4DC_SKIN_RECIPE32\n'+f(trans,'extern "C" const float* re4dc_skin_recipe_materialize(')+'\n#endif\n'
    funcs+='\n'+f(fast,'extern "C" const float* re4dc_actor_skin_palette(')
    setter=f(trans,'void SetPrimBuffPtr()').replace('gx->prim = (u8*) pG->prim_cnt + pG->nPrim * pG->vtx_buf_no;',
        'gx->prim = primitive + pG->nPrim * pG->vtx_buf_no; // host address adapter')
    source_build=source_build.replace('// @FUNCTIONS@',funcs+'\n'+setter)
    code=code.replace('extern "C" void re4dc_bind_actor_frame()',source_build+'\nextern "C" void re4dc_bind_actor_frame()',1)
    reset='skin_count=0;skin_frame=~0u;owned_skin_serial=0;skin_admission_pending={};skin_admission_serial=0;'
    code=code.replace(reset,reset+'\n#if RE4DC_SKIN_RECIPE32\n    skin_recipe_credit=0;skin_recipe_epoch=1;skin_recipe_building=false;\n#endif\n'
        '    g_skinLazyMtx=nullptr;g_skinLazyMtxFrame=~0u;source_palette_builds=0;wire.clear();joint_partial=0;')
    code=code.replace('sourceActorRetire();if(advance)','SetPrimBuffPtr();if(advance)')
    # Keep original source tests, plus compare complete ordered owned-run
    # geometry/material/palette inputs at the unchanged TA transport boundary.
    marker='extern "C" int re4dc_actor_submit_owned_runs('
    at=code.index(marker)
    code=code[:at]+(HERE/'actor_joint32_capture.cpp.in').read_text()+code[at:]
    code=code.replace('++submits;for(unsigned i=0;i<n;++i){',
        '++submits;capture_inputs(b,r,n,m,count);for(unsigned i=0;i<n;++i){')
    code=code.replace('emitted_pose[emitted_n++]=skin->palette[9];}return 1;',
        'emitted_pose[emitted_n++]=skin->palette[9];if(joint_partial)return -1;}return 1;')
    code=code[:code.index('int main(){')]+(HERE/'actor_joint32_cases.cpp.in').read_text()
    # Reset refers to transport state declared before reset, but source adapters
    # are above it. Actual production source bodies remain otherwise verbatim.
    return code

def demand_fixture():
    code=recipe_source.fixture();code=code[:code.index('int main(){')]
    code+=present.extract.function((GAME/'actor_presentation32.inc').read_text(),'bool actor_presentation32_forget_source(')
    return code+(HERE/'actor_joint32_demand.cpp.in').read_text()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--negative-accounting',action='store_true',help='preserve old forget body in otherwise current whole-actor fixture; expected failure')
    p.add_argument('--demand-only',action='store_true')
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    path=out/'fixture.cpp';body=fixture(a.negative_accounting);path.write_text(body)
    common=['-std=c++20','-O2','-fpermissive','-Wall','-Wextra','-Wno-unused-parameter','-Wno-unused-variable',
        '-I'+str(INC),'-I'+str(GAME),'-I'+str(GAME/'platform'),'-DRE4DC_GAME=1','-DRE4DC_PRIMITIVE_BUFFERS=1',
        '-DRE4DC_ACTOR_TRANSACTION=1','-DRE4DC_ACTOR_SKIN_RESERVE=1','-DRE4DC_NATIVE_ACTOR_FAST=1',
        '-DRE4DC_NATIVE_ACTOR_SKIN_LAZY=1','-DRE4DC_NATIVE_ACTOR_SKIN=1','-DRE4DC_NATIVE_MODEL_REGISTRY=1',
        '-DRE4DC_NATIVE_MODEL_REGISTRY_PACK=1','-DRE4DC_ROUTE_CH22=1','-DRE4DC_ACTOR_SKIN_OWNER_POOL=0',
        '-DRE4DC_COARSE_SOURCE_ACTORS=1','-DRE4DC_SKIN_ADMISSION32=1','-DRE4DC_NMR_BONES=96',
        '-DRE4DC_SKIN_PALETTE_LAZY=1','-DRE4DC_ACTOR_PRESENTATION32=1']
    rows=[]
    for leon in (() if a.demand_only else ((0,) if a.negative_accounting else (0,2))):
        for recipe in ((1,) if a.negative_accounting else (0,1)):
            for san in ((False,) if a.negative_accounting else (False,True)):
                name=f'l{leon}-r{recipe}-s{int(san)}';exe=out/name
                opts=[*common,f'-DRE4DC_LEON_NO_GC_FRONT={leon}',f'-DRE4DC_SKIN_RECIPE32={recipe}']
                if san:opts+=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-fno-pie','-no-pie']
                cmd=['g++',*opts,str(path),'-o',str(exe)]
                build=subprocess.run(cmd,capture_output=True,text=True);(out/f'{name}-compile.log').write_text(build.stdout+build.stderr)
                if build.returncode:raise RuntimeError(build.stderr[-12000:])
                run=subprocess.run([str(exe)],capture_output=True,text=True,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1'))
                (out/f'{name}-run.log').write_text(run.stdout+run.stderr)
                if a.negative_accounting:
                    assert run.returncode,'old accounting unexpectedly passed'
                    receipt={'verdict':'EXPECTED_FAIL_OLD_FORGET_IN_ACTUAL_ACTOR_PATH','returncode':run.returncode,
                        'baseline_helper':BASE,'command':cmd,'stderr':run.stderr,'production_guards_unmodified':True}
                    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2));return
                if run.returncode:raise RuntimeError(name+' '+run.stdout+run.stderr)
                rows.append({'name':name,'command':cmd,'output':run.stdout});print(name+' '+run.stdout.strip(),flush=True)
    # Every recipe arm must publish exactly the same independently captured
    # owned geometry/material/palette transcript as the presentation-only arm.
    hashes=[next(x for x in row['output'].splitlines() if x.startswith('OUTPUT ')) for row in rows]
    if hashes:assert len(set(hashes))==1,hashes
    demand=out/'demand.cpp';demand.write_text(demand_fixture())
    for san in (False,True):
        name='demand-s'+str(int(san));exe=out/name
        opts=['-std=c++20','-O2','-Wall','-Wextra','-Wno-unused-parameter','-Wno-unused-variable',
            '-DRE4DC_GAME=1','-DRE4DC_PRIMITIVE_BUFFERS=1','-DRE4DC_ACTOR_TRANSACTION=1',
            '-DRE4DC_ACTOR_SKIN_RESERVE=1','-DRE4DC_NATIVE_ACTOR_SKIN_LAZY=1','-DRE4DC_NATIVE_ACTOR_SKIN=1',
            '-DRE4DC_SKIN_ADMISSION32=1','-DRE4DC_ACTOR_SKIN_OWNER_POOL=0','-DRE4DC_SKIN_PALETTE_LAZY=1','-DRE4DC_SKIN_RECIPE32=1']
        if san:opts+=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-no-pie']
        cmd=['g++',*opts,str(demand),'-o',str(exe)]
        c=subprocess.run(cmd,capture_output=True,text=True);(out/f'{name}-compile.log').write_text(c.stdout+c.stderr)
        assert not c.returncode,c.stderr[-12000:]
        r=subprocess.run([str(exe)],capture_output=True,text=True,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1'))
        (out/f'{name}-run.log').write_text(r.stdout+r.stderr);assert not r.returncode,r.stdout+r.stderr
        rows.append({'name':name,'command':cmd,'output':r.stdout});print(name+' '+r.stdout.strip(),flush=True)
    inputs=[GAME/'actor_presentation32.inc',INC/'source_actor_presentation32.inc',GAME/'coarse_actor_transaction.inc',
        GAME/'platform/native_actor_fast.cpp',INC/'native_actor_skin_recipe32.inc',ROOT/'src/game/trans.cpp',
        Path(__file__),HERE/'actor_joint32_source.cpp.in',HERE/'actor_joint32_capture.cpp.in',HERE/'actor_joint32_cases.cpp.in',HERE/'actor_joint32_demand.cpp.in']
    receipt={'verdict':'PASS','rows':rows,
        'source_sha256':{str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in inputs},
        'output_equal':bool(hashes),'output_scope':'ordered owned-run geometry/material/palette transport inputs; SDK/TA adapters remain explicit'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
