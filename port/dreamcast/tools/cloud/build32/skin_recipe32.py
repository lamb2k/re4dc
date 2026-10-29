#!/usr/bin/env python3
"""Build32 sparse recipe contract: extracted producer, allocator, readers and leases.

Math/SDK calls are controlled host boundaries. Only the legacy materializer's
32-bit palette cast is widened in the host adapter; recipe and lease bodies are
compiled verbatim. No target performance or game acceptance is inferred.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import skin_admit32 as admit

HERE = Path(__file__).resolve().parent
ROOT, TRANS, ACTOR, INC = admit.ROOT, admit.TRANS, admit.ACTOR, admit.INC
BASE = 'd45eb759dd92685255929625e04fae3d7a46bca7'

def read(path: Path, baseline: bool = False) -> str:
    if baseline:
        return subprocess.check_output(['git', 'show', f'{BASE}:{path.relative_to(ROOT)}'], cwd=ROOT).decode()
    return path.read_text()

def fixture(baseline=False):
    t, a = read(TRANS, baseline), read(ACTOR, baseline)
    registry = admit.region(a, 'struct SkinEntry {', '// ---------------------------------------------------------- info context --')
    for name in ('native_actor_owner_pool.inc', 'native_actor_owner_registry.inc',
                 'native_actor_skin_reserve.inc', 'native_actor_skin_admit32.inc', 'native_actor_skin_recipe32.inc'):
        marker = f'#include "include/{name}"'
        if marker in registry:
            registry = registry.replace(marker, read(INC / name, baseline))
    funcs = [admit.function(t, prefix) for prefix in (
        'void SetPrimBuffPtr()', 'void* GetPrimBuff(int size)',
        'extern "C" void* re4dc_prim_tail(unsigned bytes, unsigned reserve)',
        'int re4dc_skin_defer(cModelInfo* info, ModelData* d)',
        'int re4dc_skin_defer_lazy(cModelInfo* info, ModelData* d)',
        'static void skinLazyBuild(void* w, u32 n, int ext, void* dst)',
        'static int skinDeferPending(cModel* m, cModelInfo* info, ModelData* d, int* mtxBuilt)',
        'extern "C" void re4dc_skin_palette_resolve(const float* palette)')]
    if not baseline:
        allocator = admit.region(t, '#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32\nstatic unsigned skin_recipe_credit', '// Allocates `size` bytes')
        funcs.insert(0, allocator)
        funcs.append('#if RE4DC_SKIN_RECIPE32\n' + admit.function(t, 'extern "C" const float* re4dc_skin_recipe_materialize(') + '#endif\n')
    materialize = admit.function(t, 'extern "C" int re4dc_skin_materialize(const void* info_ptr, const float* palette)')
    assert materialize.count('g_skin_palette = (u32) palette;') == 1
    materialize = materialize.replace('g_skin_palette = (u32) palette;', 'g_skin_palette = reinterpret_cast<std::uintptr_t>(palette); // host-only legacy address adapter')
    funcs += [materialize, admit.function(t, 'int commonScreenMatSub(cModel* m, cModelInfo* info)')]
    readers = '\n'.join(admit.function(a, prefix) for prefix in (
        'extern "C" int re4dc_actor_skin_register(',
        'extern "C" const float* re4dc_actor_skin_palette(',
        'extern "C" int re4dc_actor_skin_lazy_known(',
        'extern "C" void re4dc_actor_materialize(',
        'extern "C" int re4dc_actor_skin_rearm(',
        'extern "C" int re4dc_actor_materialize_lazy(',
        'bool lazy_skin(const Re4dcModelPart& p)',
        'bool one_qualifies(const Re4dcModelPart& p, const SkinEntry*& se, Re4dcActorSource& src)',
        'Frame* prepare_frame(const Re4dcModelPart& p, float near_distance, float far_distance)',
        'Frame& one_frame(const Re4dcModelPart& p,'))
    final_blocks = []
    for name, prefix, signature in (
        ('coarse_actor_transaction.inc', 'extern "C" int re4dc_actor_transaction_draw(cModel* m)', 'int final_general(Record* r,unsigned pass,unsigned n) {'),
        ('coarse_actor_leon_pipe.inc', 'int leon_pass(cModel* m,ActorOwnedRecord& r,bool admitting)', 'int final_leon(Record& r,unsigned pass,unsigned n) {')):
        whole = read(ROOT / 'port/dreamcast/game' / name, baseline)
        body = admit.function(whole[whole.rindex(prefix):], prefix)
        final_blocks.append(signature + '\n' + body[body.rindex('    ATD('):])
        choice = 'if(!re4dc_actor_transaction_choose(m,2)){actor_release(*r);actor_fail();return -1;}'
        assert choice in whole
    choose = 'int pre_choice(Record* r) { cModel* m=nullptr;\n' + choice + '\nreturn 1;\n}\n'
    # These are actual source caller predicates, not a guessed null-position lookup.
    prop_predicate = admit.region(t, '        if (info->pPosBuf[pG->vtx_buf_no] != 0 || !re4dc_actor_skin_lazy_known(info))', '        if (!propGateWeights(')
    native = read(ROOT / 'port/dreamcast/game/platform/native_model.cpp', baseline)
    native_predicate = admit.region(native, '    Re4dcModelPart lazy_part;\n    if(p && !p->positions)', '#if RE4DC_MODEL_STREAM_FIX')
    # Retain its preprocessor else pairing, whose opening is outside the region.
    native_predicate = '#if RE4DC_NATIVE_ACTOR_SKIN\n#if RE4DC_NATIVE_ACTOR_SKIN_LAZY\n' + native_predicate
    one_chunk = admit.function(a, 'int one_chunk(Re4dcModelPart& p, OneWindow& w)')
    frame_call = '    Frame& f = one_frame(p, near_distance, far_distance, *se, src, w.screen);'
    one_guard = ''
    if not baseline:
        one_guard = admit.region(one_chunk, '#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32\n    if(se->materialized==kSkinRecipePending)', frame_call)
    code = (HERE / 'skin_recipe32_fixture.cpp.in').read_text()
    replacements = {
        'REGISTRY': registry,
        'OWNER_RETIRE': admit.function(read(INC / 'native_actor_owner_workspace.inc', baseline), 'extern "C" void re4dc_actor_owner_retire()'),
        'FRAME': admit.region(a, 'enum Mode : unsigned {', '// Frame workspace, two-ended:'),
        'LAZY_MTX': admit.region(t, '#define SKIN_LAZY_MTX(m, built)', '\n#endif'),
        'LAZY_HEAD': admit.region(t, 'struct SkinLazyHead {', '// Trans()\'s palette of weights'),
        'UV_MACROS': admit.region(t, '#define UV_WRAP_HI(x)', '// For every model info'),
        'FUNCTIONS': '\n'.join(funcs), 'READERS': readers,
        'FINALS': '\n'.join(final_blocks) + choose,
        'PROP_PREDICATE': prop_predicate,
        'NATIVE_PREDICATE': native_predicate,
        'ONE_GUARD': one_guard,
    }
    for key, value in replacements.items():
        assert f'// @{key}@' in code, key
        code = code.replace(f'// @{key}@', value)
    assert '// @' not in code
    return code

def make_control():
    fragment = ROOT / 'port/dreamcast/game/skin_recipe32.mk'
    deps = ['SKIN_ADMISSION32=1', 'ACTOR_TRANSACTION=1', 'ACTOR_SKIN_RESERVE=1',
            'NATIVE_ACTOR_FAST=1', 'NATIVE_ACTOR_SKIN_LAZY=1', 'SKIN_PALETTE_LAZY=1',
            'COARSE_SOURCE_ACTORS=1', 'ACTOR_SKIN_OWNER_POOL=0']
    rules = f'OBJDIR := fixture\ninclude {fragment}\nprint:;@echo $(GAME_CPPFLAGS):$(PLATFORM_CPPFLAGS)\nfixture/src/game/trans.o:;@echo $(GAME_CPPFLAGS)\nfixture/platform/native_actor_fast.o:;@echo $(PLATFORM_CPPFLAGS)\nfixture/coarse_actor.o:;@echo $(GAME_CPPFLAGS)\nfixture/platform/native_ui.o:;@echo $(PLATFORM_CPPFLAGS)\n'
    def check(value=None, target='print', options=deps):
        return subprocess.run(['make', '--no-print-directory', '-f', '-', target, *options,
                               *([] if value is None else ['SKIN_RECIPE32='+value])],
                              input=rules, capture_output=True, text=True, cwd=ROOT / 'port/dreamcast/game')
    assert check().returncode == check('0').returncode == 0
    assert check().stdout == check('0').stdout == ':\n'
    for bad in ('', '2', '-1', '%', '0%', '1%', '0 1', '1 1', 'yes', '0 ', '1 '):
        assert check(bad).returncode, (bad, check(bad).stdout)
    for dep in deps:
        name, value = dep.split('=')
        bad = name + '=' + ('1' if value == '0' else '0')
        result = check('1', options=[x for x in deps if x != dep]+[bad])
        assert result.returncode, (dep, result.stdout)
    assert check('1', options=[x for x in deps if not x.startswith('SKIN_PALETTE_LAZY=')]+['SKIN_PALETTE_LAZY=2']).returncode
    for target in ('fixture/src/game/trans.o', 'fixture/platform/native_actor_fast.o', 'fixture/coarse_actor.o', 'fixture/platform/native_ui.o'):
        result = check('1', target=target)
        assert result.returncode == 0, result.stderr
        assert result.stdout.count('-DRE4DC_SKIN_RECIPE32=1') == int('native_ui' not in target)
    print('PASS recipe Make literal controls, prerequisites and target scope')



def full_trans_identity(out):
    game = ROOT / 'port/dreamcast/game'
    ppflags = ['g++', '-E', '-P', '-std=gnu++20', '-fpermissive', '-w',
               '-I'+str(ROOT/'include'), '-I'+str(ROOT/'src'), '-I'+str(ROOT/'src/game'),
               '-I'+str(game/'platform/include'), '-DRE4DC_GAME=1', '-DRE4DC_FRONT_NATIVE=1',
               '-DRE4DC_FRONT_TEXOBJ=1', '-D__sh__', '-U__PPC__',
               '-DRE4DC_ACTOR_TRANSACTION=1', '-DRE4DC_ACTOR_SKIN_RESERVE=1',
               '-DRE4DC_NATIVE_ACTOR_FAST=1', '-DRE4DC_NATIVE_ACTOR_SKIN=1',
               '-DRE4DC_NATIVE_ACTOR_SKIN_LAZY=1', '-DRE4DC_SKIN_PALETTE_LAZY=1',
               '-DRE4DC_SKIN_ADMISSION32=1', '-DRE4DC_COARSE_SOURCE_ACTORS=1',
               '-DRE4DC_COARSE=1','-DRE4DC_PACE_CATCHUP=2','-DRE4DC_PACE_TRANS_SKIP=4063','-DRE4DC_ATCHK_LIST=1']
    old = out/'full-base-trans.cpp'
    old.write_text(read(TRANS, True))
    values=[]
    for path, extra in ((old, []), (TRANS, []), (TRANS, ['-DRE4DC_SKIN_RECIPE32=0'])):
        values.append(admit.run([*ppflags, *extra, str(path)]))
    assert values[0] == values[1] == values[2], 'full trans __sh__ OFF preprocessing differs'
    halts=[x.strip() for x in values[0].splitlines() if 're4dc_halt("D:/Bio4/Prog/trans.cpp",' in x]
    assert len(halts)==2 and all('OSReport("HALT %s(%d)' in x for x in halts)
    enabled=admit.run([*ppflags,'-DRE4DC_SKIN_RECIPE32=1',str(TRANS)])
    assert 're4dc_prim_recipe_claim' in enabled and 're4dc_actor_skin_recipe_retire();' in enabled
    assert halts == [x.strip() for x in enabled.splitlines() if 're4dc_halt("D:/Bio4/Prog/trans.cpp",' in x]
    print(f'PASS full trans.cpp __sh__ baseline/absent/zero PP identity bytes={len(values[0])}; both source HALT diagnostics preserved ON/OFF')


def primary_make(out):
    game=ROOT/'port/dreamcast/game'
    kos=out/'kos';kos.mkdir();(kos/'Makefile.rules').write_text('')
    deps=['ACTOR_TRANSACTION=1','NATIVE_ACTOR=1','NATIVE_ACTOR_FAST=1','NATIVE_ACTOR_SKIN=1',
          'NATIVE_ACTOR_SKIN_LAZY=1','SKIN_PALETTE_LAZY=1','SKIN_ADMISSION32=1','ACTOR_SKIN_RESERVE=1',
          'ACTOR_SKIN_OWNER_POOL=0','COARSE_SOURCE_ACTORS=1','COARSE_LEON=1','COARSE_GANADO=1',
          'COARSE_GANADO_CAST=1','COARSE_ONE_SUBMIT=1','COARSE_SKIN_FTRV=1','COARSE=1',
          'PACE_CATCHUP=2','PACE_TRANS_SKIP=4063','GAME_ATCHK=1','GAME_ATCHK_LIST=1',
          'COARSE_ACTOR_ASSET_DIR='+str(out),'D349_RENDERER_STACK=1','PVR_STREAM=1']
    # Empty prerequisite for command expansion only; no generated asset is compiled.
    (out/'leon4k_runtime.h').write_text('// Make dry-run prerequisite only\n')
    targets=['obj/src/game/trans.o','obj/platform/native_actor_fast.o','obj/coarse_actor.o','obj/platform/native_ui.o']
    arms=[]
    for extra in ([],['SKIN_RECIPE32=0'],['SKIN_RECIPE32=1']):
        p=subprocess.run(['make','-f','Makefile','-n','KOS_BASE='+str(kos),*deps,*targets,*extra],cwd=game,capture_output=True,text=True)
        assert p.returncode==0,p.stderr[-3000:]
        arms.append([x for x in p.stdout.splitlines() if x.startswith('kos-c++')])
    assert arms[0]==arms[1] and len(arms[2])==4
    for line,target in zip(arms[2],targets):
        assert line.count('-DRE4DC_SKIN_RECIPE32=1')==int('native_ui' not in target),line
    print('PASS primary Make absent/zero commands identical; recipe flag scoped to trans/actor/coarse')


def layout32(out):
    a=read(ACTOR)
    owner=read(INC/'actor_native_owner.h')
    desc=read(INC/'native_actor_skin_recipe32.inc')
    code='\n'.join([admit.region(a,'struct SkinEntry {','#if defined(RE4DC_SKIN_RECIPE32)'),
        admit.region(owner,'struct Re4dcActorSkinBackup {','#ifndef RE4DC_ACTOR_PL08'),
        admit.region(desc,'struct SkinRecipe {','static constexpr unsigned kSkinRecipeBytes')])
    # No SDK headers or libraries: this checks the 32-bit C++ data model only.
    p=out/'layout32.cpp';p.write_text(code)
    admit.run(['g++','-m32','-std=c++20','-ffreestanding','-nostdinc++','-c',str(p),'-o',str(out/'layout32.o')])
    print('PASS 32-bit data-model ABI assertions row=20 backup=24 descriptor=32 (host compiler, not SH-4 codegen)')


def temporal_contract(out, baseline, current, flags):
    common=flags+['-DRE4DC_ACTOR_SKIN_OWNER_POOL=0','-DRE4DC_SKIN_PALETTE_LAZY=1',
                  '-DRE4DC_SKIN_RECIPE32_TEMPORAL=1']
    for sanitized in (False,True):
        values=[]
        for path,mode,extra in ((baseline,'base',[]),(current,'absent',[]),
                                (current,'zero',['-DRE4DC_SKIN_RECIPE32=0']),
                                (current,'on',['-DRE4DC_SKIN_RECIPE32=1'])):
            exe=out/f'temporal-{mode}-{int(sanitized)}'
            opts=common+extra+(['-fsanitize=address,undefined','-fno-sanitize-recover=all',
                               '-fno-omit-frame-pointer','-fno-pie','-no-pie'] if sanitized else [])
            admit.run(['g++',*opts,str(path),'-o',str(exe)])
            values.append(admit.run([str(exe)],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0')).strip())
        assert len(set(values))==1, f'baseline/absent/zero/ON temporal contract differs: {values}'
        print(f'PASS temporal baseline/absent/zero/ON sanitizer={int(sanitized)} '+values[0])


def main():
    make_control()
    with tempfile.TemporaryDirectory(prefix='skin-recipe32-') as temp:
        out=Path(temp)
        full_trans_identity(out)
        primary_make(out)
        layout32(out)
        current, baseline=out/'current.cpp', out/'baseline.cpp'
        current.write_text(fixture())
        baseline.write_text(fixture(True))
        flags=['-std=c++20','-O2','-Wall','-Wextra','-Wno-unused-parameter','-Wno-unused-variable',
               '-DRE4DC_GAME=1','-DRE4DC_PRIMITIVE_BUFFERS=1','-DRE4DC_ACTOR_TRANSACTION=1',
               '-DRE4DC_ACTOR_SKIN_RESERVE=1','-DRE4DC_NATIVE_ACTOR_SKIN_LAZY=1',
               '-DRE4DC_NATIVE_ACTOR_SKIN=1','-DRE4DC_SKIN_ADMISSION32=1']
        temporal_contract(out,baseline,current,flags)
        for pool, lazy in ((0,1),(1,1),(0,2)):
            common=flags+[f'-DRE4DC_ACTOR_SKIN_OWNER_POOL={pool}',f'-DRE4DC_SKIN_PALETTE_LAZY={lazy}']
            if lazy == 2: # Comparison mode is excluded by admission's LAZY1 gate; compile old non-admission compatibility.
                common=[x for x in common if x!='-DRE4DC_SKIN_ADMISSION32=1']
            pre, objects=[],[]
            for path, mode in ((baseline,'base'),(current,'absent'),(current,'zero')):
                opts=common+(['-DRE4DC_SKIN_RECIPE32=0'] if mode=='zero' else [])
                pp=admit.run(['g++',*opts,'-E','-P',str(path)])
                pre.append(pp)
                obj=out/f'{pool}-{lazy}-{mode}.o'
                p=subprocess.run(['g++','-std=c++20','-O2','-x','c++','-c','-','-o',str(obj)],input=pp,capture_output=True,text=True)
                if p.returncode: raise RuntimeError(p.stderr[-15000:])
                objects.append(obj.read_bytes())
            assert pre[0]==pre[1]==pre[2], f'OFF PP differs pool={pool} lazy={lazy}'
            assert objects[0]==objects[1]==objects[2], f'OFF object differs pool={pool} lazy={lazy}'
            print(f'PASS baseline/absent/zero identity pool={pool} lazy={lazy} object={len(objects[0])}')
        common=flags+['-DRE4DC_ACTOR_SKIN_OWNER_POOL=0','-DRE4DC_SKIN_PALETTE_LAZY=1','-DRE4DC_SKIN_RECIPE32=1']
        for sanitized in (False,True):
            exe=out/f'on-{sanitized}'
            opts=common+(['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-fno-pie','-no-pie'] if sanitized else [])
            admit.run(['g++',*opts,str(current),'-o',str(exe)])
            print(f'PASS recipe sanitizer={int(sanitized)} '+admit.run([str(exe)],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0')).strip())
    print('PASS source digest='+hashlib.sha256((TRANS.read_bytes()+ACTOR.read_bytes()+(INC/'native_actor_skin_recipe32.inc').read_bytes())).hexdigest()[:16])

if __name__=='__main__': main()
