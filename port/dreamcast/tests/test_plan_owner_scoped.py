"""EF07: actual fixed draw-plan owner, cold reclamation and prepared-state stamps."""
import ast
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[3]
GAME=ROOT/'port/dreamcast/game'
ROOM=ROOT/'port/dreamcast/room'
INCLUDE=GAME/'platform/include'

def existing_fixture():
    tree=ast.parse((ROOT/'port/dreamcast/tests/test_native_draw_plan.py').read_text())
    for call in ast.walk(tree):
        if isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute) and call.func.attr=='write_text' and call.args:
            arg=call.args[0]
            if isinstance(arg,ast.Constant) and isinstance(arg.value,str) and 'int main(){' in arg.value:
                return arg.value.split('int main(){',1)[0]
    raise AssertionError('existing owner harness not found')

def function(text,signature):
    start=text.index(signature);end=text.index('{',start)+1;depth=1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[start:end]

def structure(text,name):
    return function(text,'struct '+name+' {')+';'

class ScopedPlanOwner(unittest.TestCase):
    def test_actual_owner_collisions_replacement_bounds_leases_compaction_and_retirement(self):
        prefix=existing_fixture().replace('native_metadata[32768]','native_metadata[65536]')
        model=(GAME/'platform/native_model.cpp').read_text()
        state=structure(model,'PositionState')+'\n'+structure(model,'NormalState')
        light_start=model.index('struct StaticLightContext {')
        light_end=model.index('\n#endif\n\n#if RE4DC_D349_RENDERER_STACK',light_start)
        state+='\nRe4dcModelWorkStats work_stats{};\nalignas(32) unsigned char light_memory[8192];\nextern "C" void* re4dc_model_static_lighting_storage(unsigned* n){*n=sizeof light_memory;return light_memory;}\n'+model[light_start:light_end]
        code=prefix+r'''
#include "native_draw_owner_stamp.hpp"
#include "native_draw_plan_owner.cpp"
#include <limits>
'''+state+r'''
alignas(8192) unsigned char archives[4][8192];int keys[4];
void fill(unsigned char* a,unsigned count=4){std::memset(a,0,8192);a[32]=0x98;put16(a+33,count);
 for(unsigned i=0;i<count;++i){put16(a+35+i*6,i%4);put16(a+37+i*6,0);put16(a+39+i*6,i%4);}}
Re4dcModelPart part(unsigned i){Re4dcModelPart p{};p.part=archives[i];p.stream=archives[i]+32;p.stream_bytes=27;
 p.positions=archives[3]+128;p.normals=archives[3]+192;p.position_count=4;p.normal_count=1;
 p.position_stride=p.normal_stride=8;p.static_geometry=1;return p;}
const re4dc::render::NativeDrawPlan* lookup(const Re4dcModelPart& p){int invalid=0;auto* plan=re4dc_model_acquire_draw_plan(&p,&invalid);assert(!invalid);return plan;}
void release(){re4dc_model_release_draw_plan();}
int main(){
 for(unsigned i=0;i<4;++i){fill(archives[i]);re4dc_model_bind_draw_owner(&keys[i],archives[i],8192,i!=3);}
 for(unsigned i=0;i<4;++i){short x=short(i*10);std::memcpy(archives[3]+128+i*8,&x,2);}
 Re4dcModelPart p[3]={part(0),part(1),part(2)};int invalid=0;
 assert(((reinterpret_cast<std::uintptr_t>(p[0].stream)>>5)&255)==((reinterpret_cast<std::uintptr_t>(p[1].stream)>>5)&255));
 const re4dc::render::NativeDrawPlan* plans[3];const re4dc::render::DrawLocalPlan* local[3];
 for(unsigned i=0;i<3;++i){plans[i]=install(&p[i],&invalid);assert(plans[i]&&!invalid);local[i]=re4dc_model_acquired_locals();assert(local[i]);release();}
 // Delete the middle of a three-owner collision chain. C stays visible and B's
 // failed reinstall must remain a tombstone instead of hiding C behind EMPTY.
 const auto resets=re4dc_model_draw_plan_stats()->resets;
 re4dc_model_unbind_draw_owner(&keys[1]);assert(!lookup(p[1]));assert(lookup(p[2])==plans[2]);release();
 assert(re4dc_model_draw_plan_stats()->resets==resets);
 archives[1][32]=0x61;re4dc_model_bind_draw_owner(&keys[1],archives[1],8192,1);
 assert(re4dc_model_prepare_draw_plan(&p[1])==-1);assert(lookup(p[2]));release();
 fill(archives[1]);re4dc_model_bind_draw_owner(&keys[1],archives[1],8192,1);
 re4dc_model_begin_asset_update();for(auto& q:p)assert(re4dc_model_prepare_draw_plan(&q)==1);re4dc_model_finish_asset_update();
 // Replacing A at the same address cannot retire unrelated C's live topology.
 auto* c=lookup(p[2]);assert(c);auto copied=*c;auto primitive=c->primitives()[0];release();
 auto before=*re4dc_model_draw_plan_stats();auto a_stamp=re4dc_model_draw_owner_stamp(p[0].stream,27);
 re4dc_model_bind_draw_owner(&keys[0],archives[0],8192,1);
 assert(!(a_stamp==re4dc_model_draw_owner_stamp(p[0].stream,27)) && !lookup(p[0]));
 assert(lookup(p[2])==c && re4dc_model_acquired_locals());release();
 assert(re4dc_model_draw_plan_stats()->installs==before.installs&&re4dc_model_draw_plan_stats()->resets==before.resets);
 // A lease pins structural/local/bounds metadata through logical invalidation.
 auto* leased=lookup(p[2]);auto* leased_bounds=re4dc_model_acquired_bounds();auto* leased_local=re4dc_model_acquired_locals();
 assert(leased&&leased_bounds&&leased_local);const auto saved_bounds=*leased_bounds;
 const auto used_with_lease=re4dc_model_draw_plan_stats()->used;
 re4dc_model_unbind_draw_owner(&keys[2]);assert(!lookup(p[2]));
 assert(!re4dc_model_prepare_draw_plan(&p[0]));assert(!re4dc_model_begin_asset_update());
 assert(!std::memcmp(&copied,leased,sizeof copied)&&!std::memcmp(&primitive,leased->primitives(),sizeof primitive));
 assert(!std::memcmp(&saved_bounds,leased_bounds,sizeof saved_bounds)&&leased_local->batches);
 assert(re4dc_model_draw_plan_stats()->used==used_with_lease);release();
 // Only the no-lease registration boundary compacts; no topology decode is
 // required to keep B. Allocation cursor/entry count remain fixed and bounded.
 auto* b=lookup(p[1]);assert(b);const auto b_copy=*b;release();
 const auto b_installs=re4dc_model_draw_plan_stats()->installs;
 assert(re4dc_model_begin_asset_update());assert(re4dc_model_prepare_draw_plan(&p[1])==1);re4dc_model_finish_asset_update();
 b=lookup(p[1]);assert(b&&!std::memcmp(&b_copy,b,sizeof b_copy));release();
 assert(re4dc_model_draw_plan_stats()->used<used_with_lease&&re4dc_model_draw_plan_stats()->installs==b_installs);
 // Position owner D is independent of B's topology owner. Publishing D keeps
 // topology while invalidating old bounds and native prepared-array snapshots.
 PositionState positions;NormalState normals;re4dc::render::SourceLighting lighting{};p[1].lighting=&lighting;
 positions.assign(p[1]);normals.assign(p[1]);assert(positions.matches(p[1])&&normals.matches(p[1]));
 auto* light=prepare_room_static_lighting(p[1]);assert(light);const auto light_generation=light->generation;
 const auto before_bounds=*re4dc_model_draw_plan_stats();re4dc_model_bind_draw_owner(&keys[3],archives[3],8192,0);
 assert(!positions.matches(p[1])&&!normals.matches(p[1]));
 assert(prepare_room_static_lighting(p[1])->generation!=light_generation);
 assert(lookup(p[1])==b&&!re4dc_model_acquired_bounds());release();
 short changed=90;std::memcpy(archives[3]+128,&changed,2);
 assert(re4dc_model_prepare_draw_plan(&p[1])==1);assert(lookup(p[1])&&re4dc_model_acquired_bounds());
 assert(re4dc_model_acquired_bounds()->group.maximum[0]>=90);release();
 assert(re4dc_model_draw_plan_stats()->installs==before_bounds.installs);
 // Existing explicit mutation/global-storage-loan reset remains global and
 // deferred until the final outstanding metadata lease is returned.
 auto* loan=lookup(p[1]);assert(loan);re4dc_model_reset_draw_plans();assert(!lookup(p[1]));assert(loan->corner_count==4);release();
 assert(re4dc_model_prepare_draw_plan(&p[1])==1);
 loan=lookup(p[1]);assert(loan);re4dc_model_retire_draw_plans();assert(!lookup(p[1]));assert(loan->corner_count==4);release();
 assert(!re4dc_model_draw_plan_stats()->used&&!re4dc_model_draw_plan_stats()->capacity);
 // Repeated same-address replacement reuses tombstones and cold arena space.
 re4dc_model_bind_draw_owner(&keys[1],archives[1],8192,1);
 for(unsigned round=0;round<700;++round){re4dc_model_bind_draw_owner(&keys[1],archives[1],8192,1);
  assert(re4dc_model_prepare_draw_plan(&p[1])==1);assert(lookup(p[1]));release();
  assert(re4dc_model_draw_plan_stats()->used<=sizeof native_metadata);}
 // Incarnation wrap conservatively selects a global reset; aliases are never
 // accepted as a unique immutable owner, nor resurrected from old metadata.
 auto stamp=re4dc_model_draw_owner_stamp(p[1].stream,27);owners[stamp.slot].incarnation=~0U;
 re4dc_model_bind_draw_owner(&keys[1],archives[1],8192,1);assert(!lookup(p[1]));assert(re4dc_model_prepare_draw_plan(&p[1])==1);
 int alias;re4dc_model_bind_draw_owner(&alias,archives[1],8192,0);assert(!lookup(p[1]));
 re4dc_model_unbind_draw_owner(&alias);assert(!lookup(p[1]));assert(re4dc_model_prepare_draw_plan(&p[1])==1);
 // An unknown/ambiguous stamp is absence of authority, never equality proof.
 auto unknown=p[1];unknown.part=archives[0]+4096; // no longer a registered topology publisher
 positions.assign(unknown);normals.assign(unknown);assert(!positions.matches(unknown)&&!normals.matches(unknown));
 auto* unknown_light=prepare_room_static_lighting(unknown);assert(unknown_light);auto unknown_generation=unknown_light->generation;
 assert(prepare_room_static_lighting(unknown)->generation!=unknown_generation);
 int position_alias;re4dc_model_bind_draw_owner(&position_alias,archives[3],8192,0);
 positions.assign(p[1]);normals.assign(p[1]);assert(!positions.matches(p[1])&&!normals.matches(p[1]));
 light=prepare_room_static_lighting(p[1]);auto ambiguous_generation=light->generation;
 assert(prepare_room_static_lighting(p[1])->generation!=ambiguous_generation);re4dc_model_unbind_draw_owner(&position_alias);
 // Fixed table/arena exhaustion selects reference fallback and leaves live
 // entries untouched. Draw-time lookups never compact, parse or allocate.
 re4dc_model_retire_draw_plans();
 std::vector<unsigned char> many(257*64);int many_key;
 for(unsigned i=0;i<257;++i){auto* a=many.data()+i*64;a[32]=0x98;put16(a+33,4);
  for(unsigned j=0;j<4;++j){put16(a+35+j*6,j);put16(a+37+j*6,0);put16(a+39+j*6,j);}}
 re4dc_model_bind_draw_owner(&many_key,many.data(),many.size(),1);re4dc_model_begin_asset_update();
 Re4dcModelPart q{};q.position_count=4;q.normal_count=1;q.stream_bytes=27;
 for(unsigned i=0;i<256;++i){q.part=many.data()+i*64;q.stream=many.data()+i*64+32;assert(re4dc_model_prepare_draw_plan(&q)==1);}
 q.part=many.data()+256*64;q.stream=many.data()+256*64+32;assert(!re4dc_model_prepare_draw_plan(&q));re4dc_model_finish_asset_update();
 q.part=many.data();q.stream=many.data()+32;const auto stable=*re4dc_model_draw_plan_stats();
 for(unsigned i=0;i<100;++i){assert(lookup(q));release();}
 assert(re4dc_model_draw_plan_stats()->used==stable.used&&re4dc_model_draw_plan_stats()->installs==stable.installs);
 assert(re4dc_model_draw_plan_stats()->used<=sizeof native_metadata);
 // Registry exhaustion grants no ownership; unrelated installed source still hits.
 std::vector<unsigned char> extra(50*64);int extra_keys[50];
 for(unsigned i=0;i<50;++i)re4dc_model_bind_draw_owner(&extra_keys[i],extra.data()+i*64,64,0);
 assert(!re4dc_model_draw_owner_stamp(extra.data()+49*64,64).valid());assert(lookup(q));release();
 // Unknown and overflowing attribute extents cannot authenticate bounds.
 assert(!re4dc_model_draw_array_owner(archives[3],~0U,8).valid());
}
'''
        with tempfile.TemporaryDirectory(prefix='re4dc-plan-owner-') as td:
            tmp=Path(td);(tmp/'kos').mkdir();(tmp/'kos/fs.h').write_text('#pragma once\n#include <sys/types.h>\n#include <cstddef>\n#include <fcntl.h>\nusing file_t=int;\n#define FILEHND_INVALID -1\nfile_t fs_open(const char*,int);ssize_t fs_read(file_t,void*,size_t);ssize_t fs_total(file_t);int fs_close(file_t);\n')
            (tmp/'kos.h').write_text('#include <kos/fs.h>\n#include <cstdint>\nstd::uint64_t timer_us_gettime64();\n')
            cpp=tmp/'fixture.cpp';cpp.write_text(code);exe=tmp/'fixture'
            args=['g++','-std=c++20','-O2','-DRE4DC_MODEL_DRAW_PLANS=1','-DRE4DC_MODEL_STREAM_FIX=1','-DRE4DC_PLAN_OWNER_SCOPED=1',
                  '-ffunction-sections','-fdata-sections','-Wl,--gc-sections','-fsanitize=address,undefined','-fno-pie','-no-pie',
                  '-I'+str(tmp),'-I'+str(INCLUDE),'-I'+str(GAME/'platform'),'-I'+str(ROOM),str(cpp),
                  str(ROOM/'native_draw_plan.cpp'),str(ROOM/'room_storage.cpp'),'-o',str(exe)]
            for lean in (0,1):
                with self.subTest(plan_admit_lean=lean):
                    build=subprocess.run([*args,'-DRE4DC_PLAN_ADMIT_LEAN='+str(lean)],capture_output=True,text=True)
                    self.assertEqual(build.returncode,0,build.stderr)
                    run=subprocess.run([str(exe)],capture_output=True,text=True);self.assertEqual(run.returncode,0,run.stdout+run.stderr)

    def test_wrap_reset_revokes_actual_raw_consumers_and_pending_views(self):
        prefix=existing_fixture().replace('extern "C" void re4dc_model_invalidate_static_lighting(){++lighting_invalidations;}',
                                        'extern "C" void re4dc_model_invalidate_static_lighting();')
        prefix=prefix.replace('extern "C" void re4dc_model_invalidate_pending(){}','extern "C" void re4dc_model_invalidate_pending();')
        model=(GAME/'platform/native_model.cpp').read_text();ui=(GAME/'platform/native_ui.cpp').read_text()
        types='\n'.join(structure(model,n) for n in ('StaticLightContext','StaticLightValue','StaticLighting','PositionState','NormalState'))
        invalidate=function(model,'    void invalidate(){position_valid=normal_valid=lights_valid=channels_valid=false;domain=nullptr;}')
        code=prefix+'\n#include "native_draw_owner_stamp.hpp"\n#include "native_draw_plan_owner.cpp"\n'+types+r'''
StaticLighting lighting_memory,*static_lighting=&lighting_memory;
struct RawPreparation {PositionState position;NormalState normal;bool position_valid=true,normal_valid=true,lights_valid=true,channels_valid=true;
 const void* domain=reinterpret_cast<void*>(1);
'''+invalidate+r'''
} raw_preparation,*prepared_batch=&raw_preparation;
void* deferred_first=nullptr;bool draining_parts=false,stream_aborted=false;
void reset_deferred(){deferred_first=nullptr;}
'''+function(model,'extern "C" void re4dc_model_invalidate_static_lighting()')+'\n'+function(ui,'extern "C" void re4dc_model_invalidate_pending()')+r'''
int main(){alignas(32) unsigned char archive[128]{};int key;
 re4dc_model_bind_draw_owner(&key,archive,sizeof archive,0);re4dc_model_bind_draw_owner(&key,archive,sizeof archive,0);
 Re4dcModelPart p{};p.part=archive;p.positions=archive+64;p.normals=archive+96;p.position_count=4;p.normal_count=1;p.position_stride=p.normal_stride=8;
 re4dc::render::SourceLighting material{};p.lighting=&material;raw_preparation.position.assign(p);raw_preparation.normal.assign(p);
 auto token=re4dc_model_draw_owner_stamp(archive,32);assert(token.incarnation==2);
 raw_preparation.position_valid=raw_preparation.normal_valid=raw_preparation.lights_valid=raw_preparation.channels_valid=true;
 raw_preparation.domain=archive;lighting_memory.contexts[0].part=archive;lighting_memory.contexts[0].generation=2;lighting_memory.values[0].generation=2;
 owners[token.slot].incarnation=~0U;
 re4dc_model_bind_draw_owner(&key,archive,sizeof archive,0);
 // This wrap reaches an early token again. The actual full-reset call chain
 // revokes the authority flags and both static-light contexts/values first.
 assert(re4dc_model_draw_owner_stamp(archive,32).incarnation==2);
 assert(raw_preparation.position.matches(p)&&raw_preparation.normal.matches(p));
 assert(!raw_preparation.position_valid&&!raw_preparation.normal_valid&&!raw_preparation.lights_valid&&!raw_preparation.channels_valid&&!raw_preparation.domain);
 assert(!lighting_memory.contexts[0].part&&!lighting_memory.contexts[0].generation&&!lighting_memory.values[0].generation);
 deferred_first=archive;re4dc_model_invalidate_pending();assert(!deferred_first&&stream_aborted);
}
'''
        with tempfile.TemporaryDirectory(prefix='re4dc-plan-wrap-') as td:
            tmp=Path(td);(tmp/'kos').mkdir();(tmp/'kos/fs.h').write_text('#pragma once\n#include <sys/types.h>\n#include <cstddef>\n#include <fcntl.h>\nusing file_t=int;\n#define FILEHND_INVALID -1\nfile_t fs_open(const char*,int);ssize_t fs_read(file_t,void*,size_t);ssize_t fs_total(file_t);int fs_close(file_t);\n')
            (tmp/'kos.h').write_text('#include <kos/fs.h>\n#include <cstdint>\nstd::uint64_t timer_us_gettime64();\n')
            cpp=tmp/'fixture.cpp';cpp.write_text(code);exe=tmp/'fixture'
            args=['g++','-std=c++20','-O2','-DRE4DC_MODEL_DRAW_PLANS=1','-DRE4DC_MODEL_STREAM_FIX=1','-DRE4DC_PLAN_OWNER_SCOPED=1','-DRE4DC_D349_RENDERER_STACK=1',
                  '-ffunction-sections','-fdata-sections','-Wl,--gc-sections','-fsanitize=address,undefined','-fno-pie','-no-pie',
                  '-I'+str(tmp),'-I'+str(INCLUDE),'-I'+str(GAME/'platform'),'-I'+str(ROOM),str(cpp),str(ROOM/'native_draw_plan.cpp'),str(ROOM/'room_storage.cpp'),'-o',str(exe)]
            build=subprocess.run(args,capture_output=True,text=True);self.assertEqual(build.returncode,0,build.stderr)
            run=subprocess.run([str(exe)],capture_output=True,text=True);self.assertEqual(run.returncode,0,run.stdout+run.stderr)

    def test_disabled_owner_object_is_identical_to_parent_and_zero(self):
        source=GAME/'platform/native_draw_plan_owner.cpp'
        old=subprocess.check_output(['git','show','77461a84ef85e978e44aab5d936a1b80a2cd93a4:port/dreamcast/game/platform/native_draw_plan_owner.cpp'],cwd=ROOT,text=True)
        with tempfile.TemporaryDirectory(prefix='re4dc-plan-owner-off-') as td:
            tmp=Path(td);(tmp/'kos').mkdir()
            (tmp/'kos/fs.h').write_text('#pragma once\n#include <sys/types.h>\n#include <cstddef>\n#include <fcntl.h>\nusing file_t=int;\n#define FILEHND_INVALID -1\n')
            objects=[]
            for name,text,flags in [('parent',old,[]),('absent',source.read_text(),[]),('zero',source.read_text(),['-DRE4DC_PLAN_OWNER_SCOPED=0'])]:
                dest=tmp/(name+'.o')
                args=['g++','-std=c++20','-g0','-O2','-DRE4DC_MODEL_DRAW_PLANS=1','-DRE4DC_MODEL_STREAM_FIX=1',*flags,
                      '-I'+str(tmp),'-I'+str(INCLUDE),'-I'+str(ROOM),'-x','c++','-','-c','-o',str(dest)]
                build=subprocess.run(args,input=text,capture_output=True,text=True,cwd=source.parent)
                self.assertEqual(build.returncode,0,build.stderr);objects.append(dest.read_bytes())
            self.assertEqual(objects[0],objects[1]);self.assertEqual(objects[0],objects[2])

    def test_make_control_strict_default_off_and_exact_two_consumers(self):
        with tempfile.TemporaryDirectory(prefix='re4dc-plan-owner-make-') as td:
            tmp=Path(td);mk=tmp/'fixture.mk';targets=['obj/platform/native_draw_plan_owner.o','obj/platform/native_model.o']
            mk.write_text('OBJDIR := obj\ninclude '+str(GAME/'scenery30.mk')+'\n'+
                          '\n'.join(t+':\n\t@echo FLAGS $(PLATFORM_CPPFLAGS)' for t in targets)+'\n')
            for value in (None,'0','1','2','-1'):
                args=['make','--no-print-directory','-f',str(mk),*targets,'MODEL_DRAW_PLANS=1']
                if value is not None:args+=['PLAN_OWNER_SCOPED='+value]
                run=subprocess.run(args,capture_output=True,text=True,cwd=tmp)
                if value in ('2','-1'):
                    self.assertNotEqual(run.returncode,0);self.assertIn('PLAN_OWNER_SCOPED must be 0 or 1',run.stderr)
                else:
                    self.assertEqual(run.returncode,0,run.stderr)
                    self.assertEqual(run.stdout.count('-DRE4DC_PLAN_OWNER_SCOPED=1'),2 if value=='1' else 0)
            run=subprocess.run(['make','--no-print-directory','-f',str(mk),targets[0],'PLAN_OWNER_SCOPED=1','MODEL_DRAW_PLANS=0'],capture_output=True,text=True,cwd=tmp)
            self.assertNotEqual(run.returncode,0);self.assertIn('PLAN_OWNER_SCOPED needs MODEL_DRAW_PLANS=1',run.stderr)

if __name__=='__main__':unittest.main()
