#!/usr/bin/env python3
"""Exercise the production PS2 package epoch, prepared plan and portal receipts.

The package and cell bytes are synthetic. Production publisher functions,
prepared runtime, portal runtime, cell loader, chunk emitter and receipt flush
are compiled with controlled same-address owner changes. This is source/host
evidence, not an authored-world, target-runtime, visual or hardware result.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
PLATFORM = ROOT / 'port/dreamcast/game/platform'
spec = importlib.util.spec_from_file_location(
    'extract', ROOT / 'port/dreamcast/tools/d367/world_submit_spike/check_runtime.py')
extract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract)


def between(source, begin, end):
    at = source.index(begin) + len(begin)
    return source[at:source.index(end, at)]


def publisher(source):
    return source[source.index('inline bool worldPackageCurrent(){'):
                  source.index('\n#endif', source.index('inline bool worldPackageCurrent(){'))]


def compile_run(output, name, code, sanitize):
    cpp = output / (name + '.cpp')
    cpp.write_text(code)
    binary = output / name
    flags = ['-std=c++20', '-O1' if sanitize else '-O2', '-g' if sanitize else '-g0',
             '-Wall', '-Wextra', '-Wno-misleading-indentation', '-Wno-unused-parameter',
             '-Wno-unused-variable']
    if sanitize:
        flags += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-no-pie']
    cmd = ['g++', *flags, '-I', str(PLATFORM / 'include'), '-I', str(output),
           str(cpp), '-o', str(binary)]
    result = subprocess.run(cmd, capture_output=True)
    (output / (name + '-compile.log')).write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr.decode()
    result = subprocess.run([str(binary)], capture_output=True,
                            env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0',
                                     UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
    (output / (name + '-run.log')).write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr.decode()
    return {'name': name, 'output': result.stdout.decode(), 'binary_bytes': binary.stat().st_size,
            'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest()}


PLAN_MAIN = r'''
int main(){
    placements[1].placement=1;placements[1].affine[3]=100;
    CHECK(worldPackageCurrent());wplan29::open();
    const unsigned first=wplan29::bound_incarnation;
    unsigned count=0;const auto* stale=wplan29::run(0,0,count);
    CHECK(stale && count==1 && stale->key[2]==64);
    CHECK(re4dc::wp29::matches(*stale,meta[0],0));
    ++meta[0].fnv;CHECK(!re4dc::wp29::matches(*stale,meta[0],0));--meta[0].fnv;
    ++meta[0].texture;CHECK(!re4dc::wp29::matches(*stale,meta[0],0));--meta[0].texture;
    ++meta[0].reserved;CHECK(!re4dc::wp29::matches(*stale,meta[0],0));--meta[0].reserved;
    CHECK(wplan29::current(first) && wplan29::bounds(1,first));
    for(unsigned n=0;n<20;++n){count=0;CHECK(wplan29::run(0,0,count)==stale && count==1);}
    // Movie loan revokes the old prepared pointer before the retained arena is reused.
    worldPackageRevoke();CHECK(!worldPackageCurrent());CHECK(!wplan29::current(first));
#ifdef __SANITIZE_ADDRESS__
    __asan_poison_memory_region(wplan29::allocation,wplan29::allocation_bytes);
#endif
    CHECK(guarded_record_index(stale,first)==-1);
#ifdef __SANITIZE_ADDRESS__
    __asan_unpoison_memory_region(wplan29::allocation,wplan29::allocation_bytes);
#endif
    // Return attempt first overwrites the same address with changed sidecar bytes.
    worldPackageRevoke();meta[0].width=128;++source_cell_token;
    CHECK(worldPackagePublish() && worldPackageCurrent());
    wplan29::open();count=0;const auto* changed=wplan29::run(0,0,count);
    CHECK(changed && changed->key[2]==128 && !wplan29::current(first));
    const unsigned second=wplan29::bound_incarnation;
    // An overwrite that later fails never grants plan reads or a publication.
    worldPackageRevoke();meta[0].width=256;++source_cell_token;
#ifdef __SANITIZE_ADDRESS__
    __asan_poison_memory_region(meta,sizeof(meta));
#endif
    CHECK(!wplan29::current(second));CHECK(guarded_record_index(changed,second)==-1);
    wplan29::open();CHECK(!wplan29::records && !worldPackageCurrent());
#ifdef __SANITIZE_ADDRESS__
    __asan_unpoison_memory_region(meta,sizeof(meta));
#endif
    // A second restore attempt advances again; only its validated bytes publish.
    const unsigned failed=sourceWorldPackageGeneration;
    worldPackageRevoke();CHECK(sourceWorldPackageGeneration==failed+1);
    CHECK(worldPackagePublish());wplan29::open();
    count=0;CHECK(wplan29::run(0,0,count)->key[2]==256);
    // Cell incarnation and room generation guard same-pointer reuse independently.
    const unsigned third=wplan29::bound_incarnation;
    ++source_cell_token;CHECK(!worldPackageCurrent() && !wplan29::current(third));
    worldPackageRevoke();worldPackagePublish();wplan29::open();CHECK(wplan29::current(wplan29::bound_incarnation));
    ++room_generation;CHECK(!worldPackageCurrent());
    external_retire_all();wplan29::close();
    package_generation=room_generation;worldPackageRevoke();worldPackagePublish();
    wplan29::open();CHECK(wplan29::current(wplan29::bound_incarnation));
    // Penultimate -> terminal is permanent, including attempted republish.
    worldPackageRevoke();sourceWorldPackageGeneration=~0U-1U;
    CHECK(worldPackagePublish());wplan29::open();CHECK(wplan29::current(wplan29::bound_incarnation));
    const unsigned penultimate=wplan29::bound_incarnation;
    worldPackageRevoke();CHECK(sourceWorldPackageGeneration==~0U);
    CHECK(!worldPackagePublish() && !worldPackageCurrent() && !wplan29::current(penultimate));
    worldPackageRevoke();CHECK(sourceWorldPackageGeneration==~0U);
    wplan29::open();CHECK(!wplan29::records);
    wplan29::close();CHECK(blocks.empty() && allocations==frees);
    std::printf("mutation31 prepared production runtime: %u checks PASS; allocations=%u frees=%u\n",checks,allocations,frees);
}
'''


PORTAL_MAIN = r'''
static unsigned* material_key(unsigned part,unsigned out[6]){
    const auto& m=meta[part];out[0]=m.crc;out[1]=m.fnv;out[2]=m.width;out[3]=m.height;out[4]=m.pass;out[5]=m.cull;return out;
}
static void fresh(){
    load_good();scene_ok=opaque_ok=source_ok=true;
    wp29::begin(0,ps2w.projection,10,20000);expect(wp29::candidate);
}
int main(){
    using Completion=re4dc::portal29::Completion;
    fresh();unsigned k0[6],k1[6];material_key(0,k0);material_key(1,k1);
    auto t0=wp29::capture(0,0,k0),t1=wp29::capture(1,1,k1);
    expect(t0.serial && t1.serial);
    const auto done=Completion::emitted(1,true,2,2,true);
    wp29::finish(t0,done,k0);wp29::finish(t1,done,k1);
    wp29::activate();expect(pc::st.active && wp29::receipts.count==2);
    for(unsigned n=0;n<20;++n){wp29::activate();expect(pc::st.active);}
    // Movie loan: a complete copied receipt and ticket lose authority before reuse.
    worldPackageRevoke();wp29::activate();expect(!pc::st.active && !wp29::receipts.count);
    wp29::finish(t0,done,k0);expect(!wp29::receipts.count);
    // Same-address changed material after return; image readiness starts empty.
    ++meta[0].fnv;++source_cell;
    worldPackageRevoke();expect(worldPackagePublish());fresh();
    // Same material bytes with changed geometry and a live new publisher still
    // cannot replay a selection or commit a ticket from the previous epoch.
    unsigned geometry_key[6];material_key(0,geometry_key);
    const auto geometry_ticket=wp29::capture(0,0,geometry_key);
    MiniEmitter selected_before_reload;
    const unsigned geometry_epoch=sourceWorldPackageGeneration;
    worldPackageRevoke();ps2w.package.mesh[0].step[0]*=2;++source_cell;
    expect(worldPackagePublish() && worldPackageCurrent());
    expect(!worldPackageSelectionCurrent(geometry_epoch));
    SelectorBase::Pick stale_pick{};
    expect(selected_before_reload.chunk_emit(&stale_pick,1)<0 && !selected_before_reload.input);
    TestPart stale_part;expect(test_flush(selected_before_reload,stale_part,-1,false,0,0)<0);
    wp29::finish(geometry_ticket,done,geometry_key);expect(!wp29::receipts.count);
    fresh();
    // A queued completion releases a batch after end_direct. A named writer
    // invoked by that release must be refused before completion construction.
    TestPart released_part;material_key(0,released_part.key);
    released_part.wp29_ticket=wp29::capture(0,0,released_part.key);
    expect(released_part.wp29_ticket.serial);
    MiniEmitter released;revoke_on_close=true;
    expect(test_flush(released,released_part,1,true,stats.strips_clipped,stats.strips_culled)<0);
    expect(!worldPackageCurrent() && !wp29::receipts.count);
    expect(worldPackagePublish());fresh();
    unsigned changed[6];material_key(0,changed);
    wp29::finish(t0,done,k0);expect(!wp29::receipts.count);
    t0=wp29::capture(0,0,changed);t1=wp29::capture(1,1,k1);
    opaque_ok=false;wp29::finish(t0,done,changed);expect(!wp29::receipts.count);
    opaque_ok=true;wp29::finish(t0,done,changed);expect(wp29::receipts.count==1);
    wp29::activate();expect(!pc::st.active);
    // A pending partial/abort is never a receipt; revoke before any retry.
    wp29::finish(t1,Completion::emitted(-1,true,2,2,true),k1);expect(wp29::receipts.count==1);
    worldPackageRevoke();wp29::finish(t1,done,k1);wp29::activate();
    expect(!pc::st.active && !wp29::receipts.count);
    // Failed sidecar overwrite can leave the same pointer and poisoned bytes.
    ++meta[0].fnv;++source_cell;
#ifdef __SANITIZE_ADDRESS__
    __asan_poison_memory_region(meta,sizeof(meta));
#endif
    wp29::finish(t0,done,changed);wp29::begin(0,ps2w.projection,10,20000);
    expect(!wp29::candidate && !wp29::receipts.count);
    expect(!wp29::numeric_bounds() && !wp29::sources() && !wp29::witness(0,0));
    expect(!wp29::material_matches(0,changed));
#ifdef __SANITIZE_ADDRESS__
    __asan_unpoison_memory_region(meta,sizeof(meta));
#endif
    // The retry has a new epoch; stale complete and partial tickets both fail.
    worldPackageRevoke();expect(worldPackagePublish());fresh();
    wp29::finish(t0,done,changed);wp29::finish(t1,done,k1);expect(!wp29::receipts.count);
    material_key(0,changed);t0=wp29::capture(0,0,changed);t1=wp29::capture(1,1,k1);
    wp29::finish(t0,done,changed);wp29::finish(t1,done,k1);
    wp29::activate();expect(pc::st.active && wp29::receipts.count==2);
    // Penultimate package epoch may publish; terminal cannot read or commit.
    worldPackageRevoke();sourceWorldPackageGeneration=~0U-1U;
    expect(worldPackagePublish());fresh();t0=wp29::capture(0,0,changed);expect(t0.serial);
    worldPackageRevoke();expect(sourceWorldPackageGeneration==~0U && !worldPackagePublish());
    wp29::finish(t0,done,changed);wp29::begin(0,ps2w.projection,10,20000);
    expect(!wp29::candidate && !wp29::receipts.count);
    worldPackageRevoke();expect(sourceWorldPackageGeneration==~0U);
    // Independently, a terminal cell epoch never reopens portal authority.
    pc::unload();pc::wp29_generation=~0U-1U;pc::wp29_clear();
    expect(pc::wp29_generation==~0U);
    file_bytes=valid_cell();pc::st.ok=true;pc::adopt_live(0x103,0x1111,0x2222,4096);
    expect(!pc::load() && !pc::data.block);
    pc::unload();expect(allocations==frees);
    std::printf("mutation31 portal production runtime: %u checks PASS; allocations=%u frees=%u\n",checks,allocations,frees);
}
'''


def plan_fixture(source):
    start = source.index('// WORLD_PREPARED09_EARLY_BEGIN') + len('// WORLD_PREPARED09_EARLY_BEGIN')
    end = source.index('// WORLD_PREPARED09_EARLY_END', start)
    at = source.index('            const auto* plan_part=plan?plan+k:nullptr;')
    stop = source.index('            if(plan_part)++wplan29::planned;else ++wplan29::legacy;', at)
    stop += len('            if(plan_part)++wplan29::planned;else ++wplan29::legacy;')
    guard = source.rindex('#if RE4DC_WORLD_PREPARED09', 0, at)
    guard_end = source.index('#endif', guard) + len('#endif')
    values = {'EARLY': source[start:end],
              'WORLD_BOX': extract.function(source, 'inline void world_box('),
              'METADATA': source[at:stop], 'RECORD_GUARD': source[guard:guard_end]}
    fixture = (HERE / 'world_prepared09_fixture.cpp.in').read_text()
    for key, value in values.items():
        fixture = fixture.replace('@' + key + '@', value)
    fixture = fixture[:fixture.index('int main(){')]
    # The older fixture's metadata_address helper is shaped for its former
    # extraction point. This runner exercises the new live-record match itself.
    at = fixture.index('static const Ps2Part* metadata_address(')
    stop = fixture.index('static void external_retire_all()', at)
    fixture = fixture[:at] + fixture[stop:]
    fixture = fixture.replace('#define RE4DC_WORLD_PREPARED09 1',
                              '#define RE4DC_WORLD_MUTATION31 1\n#define RE4DC_WORLD_PREPARED09 1', 1)
    fixture = fixture.replace('#include "world_part_plan29.hpp"',
                              '#include "world_mutation31.hpp"\n#include "world_part_plan29.hpp"', 1)
    fixture = fixture.replace('unsigned sourceWorldPackageGeneration=1;',
        'unsigned sourceWorldPackageGeneration=1,sourceWorldSidecarCrc=0;bool sourceWorldPackagePublished=true;\n'
        'const void* sourceWorldPackageStorage=ps2w.storage;unsigned sourceWorldPackageBytes=64,\n'
        'sourceWorldPackageRoomGeneration=7,sourceWorldPackageCell=10000;', 1)
    fixture = fixture.replace('void re4dc_log(const char*,...){}',
                              'void re4dc_log(const char*,...){}\n' + publisher(source), 1)
    return fixture + PLAN_MAIN, values


LEGACY_MAIN = r'''
int main(){
    load_good();unsigned k0[6]{1,2,32,32,0,0},k1[6]{3,4,32,32,0,0};
    wp29::begin(0,ps2w.projection,10,20000);expect(wp29::candidate);
    wp29::finish(0,0,true,k0);wp29::finish(1,1,true,k1);
    wp29::activate();expect(pc::st.active && wp29::receipts.count==2);
    // Same-address reload restores publication with unchanged camera, frame
    // and cell. A copied complete legacy receipt still must be rejected.
    worldPackageRevoke();++meta[0].fnv;++source_cell;
    expect(worldPackagePublish() && worldPackageCurrent());
    wp29::activate();expect(!pc::st.active && !wp29::receipts.count);
    wp29::finish(0,0,true,k0);expect(!wp29::receipts.count);
    k0[1]=meta[0].fnv;wp29::begin(0,ps2w.projection,10,20000);
    expect(wp29::candidate);opaque_ok=false;wp29::finish(0,0,true,k0);
    expect(!wp29::receipts.count);opaque_ok=true;
    wp29::finish(0,0,true,k0);wp29::finish(1,1,false,k1);
    wp29::activate();expect(!pc::st.active && wp29::receipts.count==1);
    wp29::finish(1,1,true,k1);wp29::activate();expect(pc::st.active);
    // Failed overwrite after loan remains unpublished before any cached read.
    worldPackageRevoke();++meta[0].fnv;++source_cell;
#ifdef __SANITIZE_ADDRESS__
    __asan_poison_memory_region(meta,sizeof(meta));
#endif
    wp29::activate();wp29::finish(0,0,true,k0);
    expect(!pc::st.active && !wp29::receipts.count);
    expect(!wp29::numeric_bounds() && !wp29::sources() && !wp29::witness(0,0));
#ifdef __SANITIZE_ADDRESS__
    __asan_unpoison_memory_region(meta,sizeof(meta));
#endif
    pc::unload();expect(allocations==frees);
    std::printf("mutation31 legacy portal runtime: %u checks PASS; allocations=%u frees=%u\n",checks,allocations,frees);
}
'''


def legacy_fixture(source, output):
    core = source[source.index('inline void setup_state(State& st,'):
                  source.index('State& trans_state();', source.index('inline void setup_state(State& st,'))]
    (output / 'portal29_pc_core.inc').write_text(core)
    base = (HERE / 'portal_runtime_fixture.cpp').read_text()
    base = '#define RE4DC_WORLD_MUTATION31 1\n#define RE4DC_WORLD_PREPARED09 1\n' \
           '#ifdef __SANITIZE_ADDRESS__\n#include <sanitizer/asan_interface.h>\n#endif\n' + base
    base = base[:base.index('int main(){')]
    base = base.replace('#include "world_portal29.hpp"',
                        '#include "world_mutation31.hpp"\n#include "world_portal29.hpp"', 1)
    base = base.replace('unsigned nplacements=2,room=0x103;',
                        'unsigned nplacements=2,room=0x103,bytes=4096;', 1)
    state = '''unsigned sourceWorldPackageGeneration=1,sourceWorldSidecarCrc=0;bool sourceWorldPackagePublished=true;
const void* sourceWorldPackageStorage=ps2w.storage;unsigned sourceWorldPackageBytes=4096,
sourceWorldPackageRoomGeneration=7,sourceWorldPackageCell=55;
static unsigned room_gen=7,source_cell=55;
extern "C" int re4dc_room4_live_generation(unsigned* out){*out=room_gen;return 1;}
extern "C" unsigned re4dc_room4_cell_incarnation(const void* p,unsigned bytes,unsigned gen){
    return p==ps2w.storage && bytes==ps2w.bytes && gen==room_gen?source_cell:0;
}
'''
    base = base.replace('#include "world_portal29_runtime.inc"',
                        state + publisher(source) + '\n#include "world_portal29_runtime.inc"', 1)
    return base + LEGACY_MAIN


def source_owner_fixture(source):
    package = (PLATFORM / 'include/native_source_world.inc').read_text()
    function = extract.function(package, 'extern "C" int re4dc_ps2_source_package(unsigned* generation) {')
    return r'''#define RE4DC_WORLD_MUTATION31 1
#include <cassert>
#include <cstdint>
#include <cstdio>
struct Header {unsigned version=3,bytes=510048,crc=3459209119U,mesh_count=63,part_count=152;};
struct Package {Header h;const Header& header()const{return h;}};
struct World {Package package;void* storage=reinterpret_cast<void*>(1);
    void* parts=reinterpret_cast<void*>(2);void* placements=reinterpret_cast<void*>(3);
    void* lut=reinterpret_cast<void*>(4);void* gather=reinterpret_cast<void*>(5);
    unsigned room=0x200,want=0x200,nplacements=90;} ps2w;
namespace dyn {unsigned char data[90];const unsigned char* ids=data;unsigned nids=90;}
unsigned sourceWorldPackageGeneration=17,sourceWorldSidecarCrc=4040448078U;
bool published=true;bool worldPackageCurrent(){return published && sourceWorldPackageGeneration!=~0U;}
''' + function + r'''
int main(){
    unsigned g=0;assert(re4dc_ps2_source_package(&g) && g==17);
    published=false;assert(!re4dc_ps2_source_package(&g));
    published=true;sourceWorldPackageGeneration=~0U;assert(!re4dc_ps2_source_package(&g));
    sourceWorldPackageGeneration=18;sourceWorldSidecarCrc=0;assert(!re4dc_ps2_source_package(&g));
    std::puts("mutation31 r200 source consumer: PASS");
}
'''


def reload_fixture(source):
    body = extract.function(source, 'bool ps2_movie_reload(){')
    fixture = (HERE / 'world_mutation31_reload.cpp.in').read_text()
    assert '@RELOAD@' in fixture and '@PUBLISHER@' in fixture
    return fixture.replace('@RELOAD@', body).replace('@PUBLISHER@', publisher(source)), body


def portal_fixture(source, output):
    core = source[source.index('inline void setup_state(State& st,'):
                  source.index('State& trans_state();', source.index('inline void setup_state(State& st,'))]
    (output / 'portal29_pc_core.inc').write_text(core)
    base = (HERE / 'portal_runtime_fixture.cpp').read_text()
    base = '#define RE4DC_WORLD_MUTATION31 1\n#define RE4DC_WORLD_PREPARED09 1\n' \
           '#define RE4DC_WORLD_PORTAL_COMPLETION 1\n' \
           '#ifdef __SANITIZE_ADDRESS__\n#include <sanitizer/asan_interface.h>\n#endif\n' + base
    base = base.replace('#include "world_portal29.hpp"',
                        '#include "world_mutation31.hpp"\n#include "world_portal29.hpp"', 1)
    base = base.replace('struct SelectStats {',
                        'struct SelectStats {unsigned strips_clipped=0,strips_culled=0;', 1)
    base = base[:base.index('int main(){')]
    base = base.replace('unsigned nplacements=2,room=0x103;',
                        'unsigned nplacements=2,room=0x103,bytes=4096;', 1)
    state = '''unsigned sourceWorldPackageGeneration=1,sourceWorldSidecarCrc=0;bool sourceWorldPackagePublished=true;
const void* sourceWorldPackageStorage=ps2w.storage;unsigned sourceWorldPackageBytes=4096,
sourceWorldPackageRoomGeneration=7,sourceWorldPackageCell=55;
static unsigned room_gen=7,source_cell=55;
extern "C" int re4dc_room4_live_generation(unsigned* out){*out=room_gen;return 1;}
extern "C" unsigned re4dc_room4_cell_incarnation(const void* p,unsigned bytes,unsigned gen){
    return p==ps2w.storage && bytes==ps2w.bytes && gen==room_gen?source_cell:0;
}
'''
    base = base.replace('#include "world_portal29_runtime.inc"',
                        state + publisher(source) + '\n#include "world_portal29_runtime.inc"', 1)
    base = base.replace('int re4dc_pvs23_opaque_ready(',
                        'static bool fixture_sq_held=false;\nint re4dc_pvs23_opaque_ready(', 1)
    base = base.replace('return opaque_ok && key && !key[4];',
                        'return !fixture_sq_held && opaque_ok && key && !key[4];', 1)
    extra = (HERE / 'portal_completion_fixture.cpp.in').read_text()
    extra = extra[:extra.index('static unsigned* material_key(')]
    extra = extra.replace('static bool sq_held=false;', 'static bool& sq_held=fixture_sq_held;')
    extra = extra.replace('void re4dc_ps2_world_batch_close(Batch* b){expect(!b->held);sq_held=false;++closes;}',
                          'static bool revoke_on_close=false;\n'
                          'void re4dc_ps2_world_batch_close(Batch* b){expect(!b->held);sq_held=false;++closes;'
                          'if(revoke_on_close){revoke_on_close=false;worldPackageRevoke();}}', 1)
    extra = extra.replace('void re4dc_model_packet_commit(unsigned){}',
                          'void re4dc_model_packet_abort(){}\nvoid re4dc_model_packet_commit(unsigned){}', 1)
    extra = extra.replace('void test_flush(', 'int test_flush(', 1)
    extra = extra.replace('struct {Batch batch;} submit_scope;',
                          'struct {Batch batch;} submit_scope;\n'
                          '    struct {unsigned aborts=0;} c;unsigned nctx=0,npk=0;\n'
                          '    const unsigned draw_package_generation=e.mutation_epoch;', 1)
    extra = extra.replace('@FLUSH@\n}', '@FLUSH@\n    return 1;\n}', 1)
    extra = extra.replace('    int emit_pick(const Pick&){',
                          '    unsigned mutation_epoch=sourceWorldPackageGeneration;\n'
                          '    bool mutation_current()const{return worldPackageSelectionCurrent(mutation_epoch);}\n'
                          '    int emit_pick(const Pick&){', 1)
    values = {'CHUNK_EMIT': extract.function(source, '    __attribute__((noinline)) int chunk_emit(const Pick* pk,unsigned n){'),
              'FLUSH': between(source, '// PORTAL_COMPLETION_FLUSH_BEGIN', '// PORTAL_COMPLETION_FLUSH_END')}
    for key, value in values.items():
        extra = extra.replace('@' + key + '@', value)
    assert not re.search(r'@[A-Z_]+@', extra)
    return base + '\n' + extra + PORTAL_MAIN, values


def guards(output, source):
    makefile = output / 'guard.mk'
    makefile.write_text('OBJDIR:=unused\ninclude ' + str(ROOT / 'port/dreamcast/game/world_plan29.mk') +
                        '\nall:\n\t@echo $(WORLD_MUTATION31)\n')
    supported = ['WORLD_MUTATION31=1', 'WORLD_PREPARED09=1', 'WORLD_PAGES31=1',
                 'WORLD_PART_PLAN29=1', 'NATIVE_PKG_HIGH=1', 'PS2_WORLD_MESH=1',
                 'MOVIE_WORLD_ARENA=1', 'STATIC_OBJ_LIFETIME05=1', 'SCENERY_CHUNK=1']
    cases = [('absent', [], True), ('zero', ['WORLD_MUTATION31=0'], True),
             ('supported', supported, True)]
    cases += [('invalid-' + str(i), supported + ['WORLD_MUTATION31=' + value], False)
              for i, value in enumerate(('', '2', '-1', '0 1', '%', '0%', '1%', '0 ', '1 '))]
    cases += [('missing-' + name, supported + [name + '=0'], False)
              for name in ('WORLD_PREPARED09', 'WORLD_PAGES31', 'WORLD_PART_PLAN29',
                           'MOVIE_WORLD_ARENA', 'STATIC_OBJ_LIFETIME05', 'SCENERY_CHUNK')]
    results = []
    for name, values, accepted in cases:
        result = subprocess.run(['make', '--no-print-directory', '-f', str(makefile),
                                 'all', *values], capture_output=True)
        assert (result.returncode == 0) == accepted, (name, result.stderr.decode())
        results.append({'case': name, 'accepted': accepted})
    guard_source = source[source.index('#ifndef RE4DC_WORLD_MUTATION31'):
                          source.index('#if defined(RE4DC_ACTOR_LIGHT_FAST_ONLY)',
                                       source.index('#ifndef RE4DC_WORLD_MUTATION31'))]
    for name, defines, accepted in [
        ('source-supported', ['-DRE4DC_WORLD_MUTATION31=1',
                              '-DRE4DC_WORLD_PREPARED09=1', '-DRE4DC_WORLD_PAGES31=1',
                              '-DRE4DC_MOVIE_WORLD_ARENA=1'], True),
        ('source-invalid', ['-DRE4DC_WORLD_MUTATION31=2'], False),
        ('source-missing-page', ['-DRE4DC_WORLD_MUTATION31=1',
                                 '-DRE4DC_WORLD_PREPARED09=1', '-DRE4DC_MOVIE_WORLD_ARENA=1'], False)]:
        result = subprocess.run(['g++', '-E', '-P', '-x', 'c++', '-I', str(PLATFORM),
                                 *defines, '-'], input=guard_source.encode(), capture_output=True)
        assert (result.returncode == 0) == accepted, (name, result.stderr.decode())
        results.append({'case': name, 'accepted': accepted})
    # The source-level default is zero, with no Make CPPFLAGS emitted at zero.
    assert 'WORLD_MUTATION31 ?= 0' in makefile.read_text() or \
           'WORLD_MUTATION31 ?= 0' in (ROOT / 'port/dreamcast/game/world_plan29.mk').read_text()
    assert not re.search(r'__LINE__|__FILE__', source)
    for path in ('world_part_plan29_runtime.inc', 'world_portal29_runtime.inc',
                 'world_portal29_cells.inc'):
        assert not re.search(r'__LINE__|__FILE__', (PLATFORM / 'include' / path).read_text())
    return results


def source_order(source):
    # Named real publishers only. Both file reads occur after the retry revoke.
    for begin, end, before in [
        ('bool ps2_open(){', 'bool ps2_movie_reload(){', 'ps2w.attempted=true;'),
        ('void ps2_movie_unpublish(){', 'unsigned sourceWorldPackageGeneration=', 'ps2w.package.close();'),
        ('bool ps2_movie_reload(){', 'bool ps2_movie_dyn_valid(){', 'read_package(fm,data,files.mesh,0)'),
        ('extern "C" void re4dc_ps2_mesh_retire(){', '#if RE4DC_PS2_WORLD_DYNAMIC', 'ps2w.package.close();')]:
        region = source[source.index(begin):source.index(end, source.index(begin))]
        assert region.index('worldPackageRevoke();') < region.index(before), begin
    assert source.count('if(!worldPackagePublish())') == 2
    # These checks protect retained-reference loop conditions and immediate
    # reconstruction in the real MeshDraw/ps2_pass source. They are source
    # ordering assertions, not a full actual MeshDraw execution fixture.
    assert source.count("if(!mutation_current())return -1; // before the retained") == 3
    flush = between(source, '// PORTAL_COMPLETION_FLUSH_BEGIN', '// PORTAL_COMPLETION_FLUSH_END')
    close = flush.index('re4dc_ps2_world_batch_close(&submit_scope.batch);',
                        flush.index('if(x.wp29_ticket.serial)'))
    assert close < flush.index('if(!worldPackageSelectionCurrent(draw_package_generation))', close) < \
           flush.index('active_page->complete(wp29_source.first_meshlet)', close)
    immediate = source[source.index('const int result=d.run();'):]
    assert immediate.index('d.end_direct();') < immediate.index('if(!worldPackageSelectionCurrent(draw_package_generation))') < \
           immediate.index('MeshDraw k{{part,{},near,far},pk,pk.parts()[index]')


def off_identity(output):
    """Exact extracted prepared/portal host bytes, with production diagnostics intact."""
    baseline = 'd45eb759dd92685255929625e04fae3d7a46bca7'
    native = 'port/dreamcast/game/platform/native_static.cpp'
    includes = ('world_part_plan29.hpp', 'world_part_plan29_runtime.inc',
                'world_portal29_cells.inc', 'world_portal29_runtime.inc')
    def read(path, old):
        return subprocess.check_output(['git', 'show', baseline + ':' + path], cwd=ROOT).decode() \
            if old else (ROOT / path).read_text()
    results = {}
    for name in ('prepared', 'portal-legacy', 'portal-completion'):
        arms = []
        for old in (True, False):
            branch = output / ('off-' + name + ('-base' if old else '-current'))
            branch.mkdir();(branch / 'include').mkdir()
            source = read(native, old)
            for header in includes:
                (branch / 'include' / header).write_text(read('port/dreamcast/game/platform/include/' + header, old))
            if name == 'prepared':
                at = source.index('            const auto* plan_part=plan?plan+k:nullptr;')
                stop = source.index('            if(plan_part)++wplan29::planned;else ++wplan29::legacy;', at)
                stop += len('            if(plan_part)++wplan29::planned;else ++wplan29::legacy;')
                guard = source.rindex('#if RE4DC_WORLD_PREPARED09', 0, at)
                values = {'EARLY': between(source, '// WORLD_PREPARED09_EARLY_BEGIN', '// WORLD_PREPARED09_EARLY_END'),
                          'WORLD_BOX': extract.function(source, 'inline void world_box('),
                          'METADATA': source[at:stop],
                          'RECORD_GUARD': source[guard:source.index('#endif', guard) + len('#endif')]}
                code = (HERE / 'world_prepared09_fixture.cpp.in').read_text()
                # Keep fixture assert locations fixed across differently sized
                # inserted blocks. Production source and diagnostic constants
                # are copied literally, without replacement or normalization.
                for number, (key, value) in enumerate(values.items()):
                    code = code.replace('@' + key + '@', '#line 1 "production-' + key + '"\n' + value +
                                        '\n#line ' + str(1000 + 1000 * number) + ' "fixture.cpp"\n')
            else:
                core = source[source.index('inline void setup_state(State& st,'):
                              source.index('State& trans_state();', source.index('inline void setup_state(State& st,'))]
                (branch / 'portal29_pc_core.inc').write_text(core)
                code = (HERE / 'portal_runtime_fixture.cpp').read_text()
                if name == 'portal-completion':
                    code = '#define RE4DC_WORLD_PORTAL_COMPLETION 1\n#define RE4DC_WORLD_PREPARED09 1\n' + code
                    code = code.replace('wp29::finish(', 'fixture_finish(')
                    helper = '''void fixture_finish(unsigned placement,unsigned part,bool success,const unsigned*){
    const auto& m=meta[part];const unsigned key[6]={m.crc,m.fnv,m.width,m.height,m.pass,m.cull};
    wp29::finish(wp29::capture(placement,part,key),re4dc::portal29::Completion::emitted(success?1:0,success,2,success?2:0,success),key);
}
'''
                    code = code.replace('int main(){', helper + 'int main(){', 1)
            (branch / 'fixture.cpp').write_text(code)
            flags = ['-std=c++20', '-O2', '-g0', '-DRE4DC_WORLD_MUTATION31=0',
                     '-Iinclude', '-I.', '-I' + str(PLATFORM / 'include')]
            pp = subprocess.run(['g++', *flags, '-E', '-P', 'fixture.cpp'], cwd=branch, capture_output=True)
            assert pp.returncode == 0, pp.stderr.decode()
            (branch / 'fixture.ii').write_bytes(pp.stdout)
            obj = subprocess.run(['g++', '-std=c++20', '-O2', '-g0', '-c', 'fixture.ii', '-o', 'fixture.o'],
                                 cwd=branch, capture_output=True)
            assert obj.returncode == 0, obj.stderr.decode()
            arms.append((pp.stdout, (branch / 'fixture.o').read_bytes()))
        assert arms[0] == arms[1], name + ' OFF preprocessor/object bytes changed'
        results[name] = {'preprocessor_sha256': hashlib.sha256(arms[0][0]).hexdigest(),
                         'object_sha256': hashlib.sha256(arms[0][1]).hexdigest(),
                         'object_bytes': len(arms[0][1])}
    return {'baseline': baseline, 'scope': 'extracted prepared plan and portal runtime/cell host fixtures only',
            'rows': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = (PLATFORM / 'native_static.cpp').read_text()
    source_order(source)
    plan, plan_values = plan_fixture(source)
    all_room_plan = plan.replace('#define RE4DC_PS2_WORLD_SOURCE_OWNER 1',
                                 '#define RE4DC_PS2_WORLD_SOURCE_OWNER 0', 1)
    portal, portal_values = portal_fixture(source, args.output)
    reload_code, reload_body = reload_fixture(source)
    rows = [compile_run(args.output, 'plan', plan, args.sanitize),
            compile_run(args.output, 'plan-all-room', all_room_plan, args.sanitize),
            compile_run(args.output, 'portal', portal, args.sanitize),
            compile_run(args.output, 'portal-legacy', legacy_fixture(source, args.output), args.sanitize),
            compile_run(args.output, 'r200-source', source_owner_fixture(source), args.sanitize),
            compile_run(args.output, 'reload', reload_code, args.sanitize)]
    check = guards(args.output, source)
    off = off_identity(args.output) if not args.sanitize else None
    files = [PLATFORM / 'native_static.cpp', PLATFORM / 'include/world_mutation31.hpp',
             PLATFORM / 'include/world_part_plan29_runtime.inc',
             PLATFORM / 'include/world_portal29_runtime.inc',
             PLATFORM / 'include/world_portal29_cells.inc',
             ROOT / 'port/dreamcast/game/world_plan29.mk',
             HERE / 'world_mutation31_reload.cpp.in', Path(__file__)]
    report = {'status': 'PASS', 'scope': __doc__, 'sanitize': args.sanitize,
              'rows': rows, 'guards': check, 'off_identity': off,
              'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in files},
              'extracted_sha256': {key: hashlib.sha256(value.encode()).hexdigest()
                                   for key, value in {**plan_values, **portal_values,
                                                      'PUBLISHER': publisher(source),
                                                      'RELOAD': reload_body}.items()}}
    (args.output / 'receipt.json').write_text(json.dumps(report, indent=2) + '\n')
    for row in rows:
        print(row['output'], end='')
    print('mutation31 guards:', len(check), 'PASS')


if __name__ == '__main__':
    main()
