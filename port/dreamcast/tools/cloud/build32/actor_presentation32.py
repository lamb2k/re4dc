#!/usr/bin/env python3
"""Current-image Luis: actual source hooks, registry, transaction and consumer.

SDK arithmetic and texture/TA transport have explicit synthetic boundaries.
No private package, target ABI/codegen, visual or console acceptance is inferred.
"""
from __future__ import annotations
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import skin_admit32 as extract

ROOT=extract.ROOT
GAME=ROOT/'port/dreamcast/game'
INC=GAME/'platform/include'
BASE='d45eb759dd92685255929625e04fae3d7a46bca7'
HERE=Path(__file__).resolve().parent

def read(path,base=False):
    return subprocess.check_output(['git','show',f'{BASE}:{path.relative_to(ROOT)}'],cwd=ROOT).decode() if base else path.read_text()

def fixture(base=False):
    trans=read(ROOT/'src/game/trans.cpp',base)
    fast=read(GAME/'platform/native_actor_fast.cpp',base)
    registry=read(GAME/'coarse_actor_owner_registry.inc',base)
    tx=read(GAME/'coarse_actor_transaction.inc',base)
    f=extract.function;r=extract.region
    skins=r(fast,'struct SkinEntry {','// ---------------------------------------------------------- info context --')
    for name in ('native_actor_owner_pool.inc','native_actor_owner_registry.inc','native_actor_skin_reserve.inc','native_actor_skin_admit32.inc'):
        skins=skins.replace(f'#include "include/{name}"',read(INC/name,base))
    hooks=read(INC/'source_actor_owner_hooks.inc',base)
    if '#include "source_actor_presentation32.inc"' in hooks:
        hooks=hooks.replace('#include "source_actor_presentation32.inc"',read(INC/'source_actor_presentation32.inc'))
    source='\n'.join(f(trans,prefix) for prefix in ('bool sourceActorRam(','void sourceActorRetire()',
        'bool sourceActorIdentity(','ModelIdentity sourceActorModel(','static bool sourceActorNativeOwner('))
    types=r(registry,'namespace nmr {','// Explicit capacities')
    binding=r(registry,'struct RegistryBinding {','#if RE4DC_NMR_POOL\n// NATIVE_MODEL_REGISTRY_POOL:')
    reg_funcs='\n'.join(f(registry,prefix) for prefix in ('inline bool registry_id(',
        'inline const nmr::Descriptor* registry_descriptor(','Re4dcUiImage registry_image(',
        'bool registry_skin_init(','bool registry_skeleton(','bool registry_bind(',
        'int registry_palettes(','extern "C" int re4dc_actor_plan_registry(',
        'extern "C" int re4dc_registry_covered_roles(','extern "C" int re4dc_registry_candidate('))
    if not base:
        reg_funcs+='\n#if RE4DC_ACTOR_PRESENTATION32\n'+f(registry,'extern "C" int re4dc_registry_presentation32_class(')+'#endif\n'
    records=r(tx,'struct ActorOwnedPart {','#if RE4DC_NATIVE_MODEL_REGISTRY_CENSUS\nbool actor_certificate_reached;')
    acquire=r(tx,'ActorOwnedRecord* actor_acquire(','\n}\n#if RE4DC_ACTOR_GANADO_DEATH_FADE\n#include "coarse_actor_death_fade.inc"')
    functions='\n'.join(f(tx,prefix) for prefix in ('bool actor_release(','bool actor_plan_layout(',
        'bool actor_semantics(','ActorOwnedRecord* actor_decline('))
    functions+='\n#if RE4DC_ACTOR_PRESENTATION32\n'+(read(GAME/'actor_presentation32.inc') if not base else '')+'\n#endif\n'+acquire
    # The normal draw function's shared body follows its diagnostic wrappers.
    draw=tx[tx.rindex('extern "C" int re4dc_actor_transaction_draw(cModel* m) {'):]
    draw='extern "C" int re4dc_actor_transaction_draw(cModel* m) {\n'+draw[draw.index('    RE4DC_BFC_SCOPE'):]
    draw=f(draw,'extern "C" int re4dc_actor_transaction_draw(')
    retire=f(tx,'extern "C" void re4dc_actor_transaction_retire()')
    consumer=r(trans,'#if RE4DC_ACTOR_TRANSACTION\n    if(!flag) {','    while (info != 0) {')
    state=r(trans,'        if (info->flagsDC & 2) {','        if (PTR_INVALID(d)) {')
    values=dict(SOURCE=source,HOOKS=hooks,SKINS=skins,REGISTRY_TYPES=types,REGISTRY_BINDING=binding,
        REGISTRY=reg_funcs,RECORDS=records,FUNCTIONS=functions,DRAW=draw,RETIRE=retire,CONSUMER=consumer,
        UV=r(trans,'#define UV_WRAP_HI(x)','// For every model info'),STATE=state,
        OWNER_WORKSPACE=read(INC/'native_actor_owner_workspace.inc',base),
        REGISTER=f(fast,'extern "C" int re4dc_actor_skin_register('))
    code=(HERE/'actor_presentation32_fixture.cpp.in').read_text()
    for key,value in values.items():
        assert f'// @{key}@' in code,key
        code=code.replace(f'// @{key}@',value)
    assert '// @' not in code
    return code

PROFILE=['ACTOR_TRANSACTION=1','COARSE_SOURCE_ACTORS=1','ACTOR_SKIN_RESERVE=1','NATIVE_ACTOR_FAST=1',
    'NATIVE_ACTOR_SKIN_LAZY=1','NATIVE_MODEL_REGISTRY=1','NATIVE_MODEL_REGISTRY_PACK=1','ROUTE_CH22=1',
    'ACTOR_SKIN_OWNER_POOL=0','NATIVE_MODEL_REGISTRY_BONES=96']

def make_control():
    fragment=GAME/'actor_presentation32.mk'
    rules=f'OBJDIR := fixture\ninclude {fragment}\nprint:;@echo $(GAME_CPPFLAGS):$(PLATFORM_CPPFLAGS)\n'
    for target in ('src/game/trans','coarse_actor','platform/native_actor_fast','platform/native_ui'):
        flags='PLATFORM_CPPFLAGS' if target.startswith('platform/') else 'GAME_CPPFLAGS'
        rules+=f'fixture/{target}.o:;@echo $({flags})\n'
    def check(value=None,options=PROFILE,target='print'):
        return subprocess.run(['make','--no-print-directory','-f','-',target,*options,
            *([] if value is None else ['ACTOR_PRESENTATION32='+value])],input=rules,cwd=GAME,capture_output=True,text=True)
    for recipe in ([],['SKIN_RECIPE32=0'],['SKIN_RECIPE32=1']):
        a,b=check(options=PROFILE+recipe),check('0',options=PROFILE+recipe)
        assert a.returncode==b.returncode==0 and a.stdout==b.stdout==':\n'
    for bad in ('','2','-1','%','0%','1%','0 1','1 1','yes','0 ','1 '):
        assert check(bad).returncode,bad
    for dependency in PROFILE:
        key,value=dependency.split('=')
        opts=[x for x in PROFILE if x!=dependency]+[key+'='+('1' if value=='0' else '0')]
        assert check('1',options=opts).returncode,dependency
    assert check('1').returncode==check('1',options=PROFILE+['SKIN_RECIPE32=0']).returncode==0
    assert check('1',options=PROFILE+['SKIN_RECIPE32=1']).returncode
    for bones in ('48','64','80','%','96%','96 128','96 '):
        assert check('1',options=PROFILE+['NATIVE_MODEL_REGISTRY_BONES='+bones]).returncode,bones
    assert check('1',options=PROFILE+['NATIVE_MODEL_REGISTRY_BONES=128']).returncode==0
    for target in ('src/game/trans','coarse_actor','platform/native_actor_fast','platform/native_ui'):
        p=check('1',target='fixture/'+target+'.o')
        assert p.returncode==0,p.stderr
        assert p.stdout.count('-DRE4DC_ACTOR_PRESENTATION32=1')==int('native_ui' not in target)
    print('PASS literal/default0 controls, prerequisites, three-TU scope and recipe composition guard')

def primary_make(out):
    kos=out/'kos';kos.mkdir()
    (kos/'Makefile.rules').write_text('KOS_LDFLAGS += -T'+str(kos/'utils/ldscripts/shlelf.xc')+'\n')
    deps=PROFILE+['NATIVE_ACTOR=1','NATIVE_ACTOR_SKIN=1','SKIN_PALETTE_LAZY=1','SKIN_ADMISSION32=1',
        'NATIVE_STATIC=1','COARSE_LEON=1','COARSE_GANADO=1','COARSE_GANADO_CAST=1',
        'COARSE_ONE_SUBMIT=1','COARSE_SKIN_FTRV=1','COARSE=1','PACE_CATCHUP=2','PACE_TRANS_SKIP=4063',
        'GAME_ATCHK=1','GAME_ATCHK_LIST=1','D349_RENDERER_STACK=1','PVR_STREAM=1',
        'ROUTE_CH21=1','ROUTE_OVL=1','EM10_SHARED=1','WORLD_STAGE_MODULES=0',
        'COARSE_ACTOR_ASSET_DIR='+str(out)]
    # Only expands the real compile commands: no private asset or SDK is built.
    (out/'leon4k_runtime.h').write_text('// Make dry-run prerequisite only\n')
    targets=['obj/src/game/trans.o','obj/platform/native_actor_fast.o','obj/coarse_actor.o','obj/platform/native_ui.o']
    # The coordinator owns the primary Makefile. Until its single include is
    # attached, load this fragment as the second makefile against the real one.
    inclusion='include actor_presentation32.mk'
    includes=(GAME/'Makefile').read_text().splitlines().count(inclusion)
    assert includes in (0,1),includes
    files=['-f','Makefile']+([] if includes else ['-f','actor_presentation32.mk'])
    def check(extra):
        p=subprocess.run(['make',*files,'-n','KOS_BASE='+str(kos),*deps,*targets,*extra],
            cwd=GAME,capture_output=True,text=True)
        return p,[x for x in p.stdout.splitlines() if x.startswith('kos-c++')]
    for recipe in ([],['SKIN_RECIPE32=0'],['SKIN_RECIPE32=1']):
        absent,a=check(recipe);zero,z=check(recipe+['ACTOR_PRESENTATION32=0'])
        assert absent.returncode==zero.returncode==0,absent.stderr+zero.stderr
        assert a==z and len(a)==4
        assert all('-DRE4DC_ACTOR_PRESENTATION32' not in line for line in a)
    absent,a=check(['ACTOR_PRESENTATION32=1'])
    zero,z=check(['ACTOR_PRESENTATION32=1','SKIN_RECIPE32=0'])
    assert absent.returncode==zero.returncode==0,absent.stderr+zero.stderr
    assert a==z and len(a)==4
    for line,target in zip(a,targets):
        args=shlex.split(line)
        assert args.count('-DRE4DC_ACTOR_PRESENTATION32=1')==int('native_ui' not in target),line
        if 'trans.o' in target:assert args.count('-DRE4DC_NATIVE_MODEL_REGISTRY_PACK=1')==1,line
    rejected,_=check(['ACTOR_PRESENTATION32=1','SKIN_RECIPE32=1'])
    assert rejected.returncode and 'joint source-credit qualification' in rejected.stderr,rejected.stderr
    print('PASS primary Make effective flags/OFF identity/recipe absent,0,1 guard; '+
        ('primary include' if includes else 'coordinator include pending, second makefile loaded'))

def layout32(out):
    # Extract the production value records; substitute only standard unsigned
    # aliases to compile without a 32-bit SDK or C++ library installation.
    code='namespace std {using uint32_t=unsigned;using uintptr_t=unsigned;}\n'
    code+=extract.region(read(INC/'coarse_source_frame.h'),'struct FrameIdentity {','enum class ModelPath')
    code+=extract.region(read(INC/'source_actor_presentation32.inc'),'struct SourceActorPresentation32 {',
        'SourceActorPresentation32 partnerPresentation32;')
    code+=extract.region(read(GAME/'actor_presentation32.inc'),'struct ActorPresentation32Ticket {',
        'ActorPresentation32Ticket actor_presentation32_capture(')
    code+='static_assert(sizeof(void*)==4 && sizeof(FrameIdentity)==24 && sizeof(ModelIdentity)==12);\n'
    code+='static_assert(sizeof(SourceActorPresentation32)==52 && sizeof(ActorPresentation32Ticket)==12);\n'
    path=out/'layout32.cpp';path.write_text(code)
    extract.run(['g++','-m32','-std=c++20','-ffreestanding','-nostdinc++','-c',str(path),'-o',str(out/'layout32.o')])
    print('PASS 32-bit data-model value record=52 ticket=12 (host compiler, not SH-4 codegen)')

def target_conditioned_identity(out):
    flags=['g++','-E','-P','-std=gnu++20','-fpermissive','-w','-I'+str(ROOT/'include'),
        '-I'+str(ROOT/'src'),'-I'+str(ROOT/'src/game'),'-I'+str(INC),'-D__sh__','-U__PPC__',
        '-DRE4DC_GAME=1','-DRE4DC_FRONT_NATIVE=1','-DRE4DC_FRONT_TEXOBJ=1','-DRE4DC_ACTOR_TRANSACTION=1',
        '-DRE4DC_ACTOR_SKIN_RESERVE=1','-DRE4DC_NATIVE_ACTOR_FAST=1','-DRE4DC_NATIVE_ACTOR_SKIN=1',
        '-DRE4DC_NATIVE_ACTOR_SKIN_LAZY=1','-DRE4DC_COARSE_SOURCE_ACTORS=1','-DRE4DC_COARSE=1',
        '-DRE4DC_PACE_CATCHUP=2','-DRE4DC_PACE_TRANS_SKIP=4063','-DRE4DC_ATCHK_LIST=1',
        '-DRE4DC_NATIVE_MODEL_REGISTRY=1','-DRE4DC_NATIVE_MODEL_REGISTRY_PACK=1','-DRE4DC_ROUTE_CH22=1']
    original=out/'base-trans.cpp';original.write_text(read(ROOT/'src/game/trans.cpp',True))
    for leon in (0,2):
        opts=flags+[f'-DRE4DC_LEON_NO_GC_FRONT={leon}']
        values=[extract.run([*opts,*extra,str(path)]) for path,extra in
            ((original,[]),(ROOT/'src/game/trans.cpp',[]),(ROOT/'src/game/trans.cpp',['-DRE4DC_ACTOR_PRESENTATION32=0']))]
        assert values[0]==values[1]==values[2],f'full __sh__ OFF text differs Leon={leon}'
        on=extract.run([*opts,'-DRE4DC_ACTOR_PRESENTATION32=1',str(ROOT/'src/game/trans.cpp')])
        halts=lambda s:[x.strip() for x in s.splitlines() if 're4dc_halt("D:/Bio4/Prog/trans.cpp",' in x]
        assert len(halts(on))==2 and halts(on)==halts(values[0])
        print(f'PASS full trans __sh__ OFF exact text Leon={leon} bytes={len(values[0])}; HALTs preserved ON/OFF')

def main():
    make_control()
    with tempfile.TemporaryDirectory(prefix='actor-present32-') as directory:
        out=Path(directory);primary_make(out);layout32(out);target_conditioned_identity(out)
        base=out/'base.cpp';base.write_text(fixture(True))
        current=out/'current.cpp';current.write_text(fixture())
        common=['-std=c++20','-O2','-fpermissive','-Wall','-Wextra','-Wno-unused-parameter','-Wno-unused-variable',
            '-I'+str(INC),'-I'+str(GAME),'-DRE4DC_ACTOR_TRANSACTION=1','-DRE4DC_ACTOR_SKIN_RESERVE=1',
            '-DRE4DC_NATIVE_ACTOR_FAST=1','-DRE4DC_NATIVE_ACTOR_SKIN_LAZY=1','-DRE4DC_NATIVE_ACTOR_SKIN=1',
            '-DRE4DC_NATIVE_MODEL_REGISTRY=1','-DRE4DC_NATIVE_MODEL_REGISTRY_PACK=1','-DRE4DC_ROUTE_CH22=1',
            '-DRE4DC_ACTOR_SKIN_OWNER_POOL=0','-DRE4DC_COARSE_SOURCE_ACTORS=1','-DRE4DC_SKIN_ADMISSION32=1','-DRE4DC_NMR_BONES=96']
        for leon in (0,2):
            opts=common+[f'-DRE4DC_LEON_NO_GC_FRONT={leon}']
            text=[];objects=[];results=[]
            for path,mode,extra in ((base,'base',[]),(current,'absent',[]),(current,'zero',['-DRE4DC_ACTOR_PRESENTATION32=0'])):
                pp=extract.run(['g++',*opts,*extra,'-E','-P',str(path)]);text.append(pp)
                obj=out/f'{leon}-{mode}.o'
                p=subprocess.run(['g++','-std=c++20','-O2','-fpermissive','-x','c++','-c','-','-o',str(obj)],input=pp,capture_output=True,text=True)
                assert p.returncode==0,p.stderr[-12000:]
                objects.append(obj.read_bytes())
                exe=out/f'{leon}-{mode}'
                extract.run(['g++',*opts,*extra,str(path),'-o',str(exe)])
                results.append(extract.run([str(exe)]))
            assert text[0]==text[1]==text[2] and objects[0]==objects[1]==objects[2],f'OFF exact identity Leon={leon}'
            assert len(set(results))==1,results
            print(f'PASS OFF baseline/absent/zero object Leon={leon} bytes={len(objects[0])}; '+results[0].strip())
            for sanitized in (False,True):
                exe=out/f'{leon}-on-{int(sanitized)}'
                san=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-fno-pie','-no-pie'] if sanitized else []
                extract.run(['g++',*opts,'-DRE4DC_ACTOR_PRESENTATION32=1',*san,str(current),'-o',str(exe)])
                result=extract.run([str(exe)],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0')).strip()
                print(f'PASS ON Leon={leon} sanitizer={int(sanitized)} '+result)

if __name__=='__main__':main()
