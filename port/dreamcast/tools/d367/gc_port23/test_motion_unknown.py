"""Actual UNKNOWN-only accepted-path bodies; renderer host controls, no SDK."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from test_runtime_hooks import function

HERE=Path(__file__).resolve().parent
GAME=HERE.parents[2]/'game'
PLATFORM=GAME/'platform'
BASE='870789095c4c14fbdbf22043447b249063d2ec3a'

def project_ui_motion0(source):
    """Remove only the exact approved Motion-only additions, never wildcard guards."""
    include='#include "include/gc_asset_motion_unknown.h"\n'
    assert source.count(include)==1
    source=source.replace(include,'')
    blocks=[(1,'''#if RE4DC_GC_ASSET_MOTION_UNKNOWN
    re4dc_gcasset::motion_prepare();
#endif
'''),(1,'''#if RE4DC_GC_ASSET_MOTION_UNKNOWN
    re4dc_gcasset::motion_accept_pending(count); // also before quad geometry's early return
#endif
'''),(1,'''#if RE4DC_GC_ASSET_MOTION_UNKNOWN
    re4dc_gcasset::motion_unknown_flush();
#endif
'''),(2,'''#if RE4DC_GC_ASSET_MOTION_UNKNOWN
    re4dc_gcasset::motion_accept_pending(vertices);
#endif
'''),(1,'''#if RE4DC_GC_ASSET_MOTION_UNKNOWN
        re4dc_gcasset::MotionUnknownScope gcasset_motion_scope(re4dc_gcasset::MotionDelayedModel|re4dc_gcasset::MotionViewTrack);
#endif
''')]
    for count,block in blocks:
        assert source.count(block)==count
        source=source.replace(block,'')
    return source


class MotionUnknownTests(unittest.TestCase):
    def fixture(self):
        ui=(PLATFORM/'native_ui.cpp').read_text()
        actor=(PLATFORM/'native_actor_fast.cpp').read_text()
        pipe=(PLATFORM/'include/native_actor_leon_pipe.inc').read_text()
        helper=(PLATFORM/'gc_asset_motion_unknown.cpp').read_text().replace('#include "include/gc_asset_motion_unknown.h"','')
        # Full production close and actual chunk-accepted prefix, before abort.
        close=function(actor,'void one_close(')
        start=actor.index('#if RE4DC_GC_ASSET_MOTION_UNKNOWN\n        if(e.slots)')
        chunk=actor[start:actor.index('        w.sq = e.sq;',start)]
        # Exact previous interval in the real Leon switch, before new prepare.
        switch=function(ui,'extern "C" std::uint32_t* re4dc_leon_direct_switch(')
        start=switch.index('#if RE4DC_GC_ASSET_MOTION_UNKNOWN')
        interval=switch[start:switch.index('    // re4dc_model_direct_begin',start)]
        # Exact material-switch block from the owner pipeline (including failed switch).
        start=pipe.index('        if (changed && window.open && header[material].valid')
        finish=pipe.index('        const bool was_open',start)
        pipe_switch=pipe[start:finish]
        return r'''
#include "gc_asset_motion_unknown.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <string>
using namespace re4dc_gcasset;
bool protected_context;unsigned faults;std::string logs;
extern "C" void re4dc_log(const char* fmt,...){assert(!protected_context);char b[256];va_list a;va_start(a,fmt);vsnprintf(b,sizeof b,fmt,a);va_end(a);logs+=b;}
namespace re4dc_gcasset {void unresolved(Consumer c,const char*){assert(!protected_context && c==Motion);++faults;}}
'''+helper+r'''
void reset(){motion_unknown_flush();logs.clear();faults=0;motion={};}
void expected(unsigned events,unsigned records,unsigned reasons){
 assert(motion.events==events && motion.records==records && motion.reasons==reasons);
}
struct Window{bool open=true;unsigned slots=0,primed=0,motion_accounted=0;unsigned*sq=nullptr;struct{float u_scale,v_scale;}direct;};
void re4dc_model_direct_end(unsigned vertices){motion_accept_pending(vertices);}
'''+close.replace('OneWindow','Window')+r'''
void chunk(Window&w,unsigned records){MotionUnknownScope context(motion_model_reason());struct{unsigned slots;}e{records};
'''+chunk+r'''
 w.slots+=records;
}
void ordinary_interval(unsigned vertices){
'''+interval.replace('RE4DC_GCA_MODEL_TEXTURE(model_handle);','').replace('RE4DC_GCA_MODEL_ACCEPT();','')+r'''
}
unsigned direct_parts,direct_slots,frame_pvr_bytes,stream_model_bytes,stream_peak_bytes,model_used;
struct Re4dcModelPart{};struct Header{unsigned valid=1;};bool switch_ok=true;
bool leon_tr_idle(const Re4dcModelPart*){return true;}
unsigned*re4dc_leon_direct_switch(const Re4dcModelPart*,const Header*,unsigned vertices,unsigned*sq){
 if(!switch_ok)return nullptr;
 ordinary_interval(vertices);motion_prepare();return sq;
}
void material_switch(Window&window){static unsigned token;window.sq=&token;Re4dcModelPart object;auto*part=&object;
 bool changed=true,switched=false,okay=true;unsigned material=0,base=0,bound=1;Header header[1];float scale[1][2]{};
'''+pipe_switch+r'''
 (void)okay;(void)base;(void)switched;
}
int main(){
 reset();
 {MotionUnknownScope model(motion_model_reason());motion_prepare();protected_context=true;motion_accept_pending(0);motion_accept_current(0);protected_context=false;}
 expected(0,0,0); // reservation/header/cull/cancel/no-output
 // Null/stopped/current lookup is irrelevant; cached/retained model remains unknown.
 {MotionUnknownScope model(motion_model_reason());motion_prepare();protected_context=true;motion_accept_pending(3);motion_accept_pending(5);protected_context=false;}
 expected(2,8,MotionModelPose|MotionViewTrack);assert(!faults && logs.empty());
 motion_unknown_flush();assert(faults==1 && logs.find("accepted_records=8")!=std::string::npos);expected(0,0,0);
 // World/impostor leaf, independent of last model/geometry; movie never calls this leaf.
 motion_prepare();motion_accept_pending(4);expected(1,4,MotionUnclassifiedWorld|MotionViewTrack);reset();
 {MotionUnknownScope delayed(MotionDelayedModel|MotionViewTrack);{MotionUnknownScope model(motion_model_reason());motion_prepare();}}
 {MotionUnknownScope ambient(MotionMissingRoute);motion_accept_pending(7);}
 expected(1,7,MotionDelayedModel|MotionModelPose|MotionViewTrack);reset();
 // OneWindow A+B+C(culled)+D(partial then abort): own chunks exactly once.
 Window w;protected_context=true;chunk(w,3);chunk(w,4);chunk(w,0);chunk(w,2);one_close(w);protected_context=false;
 expected(3,9,MotionModelPose|MotionViewTrack);assert(!faults && logs.empty());reset();
 // Internal suppression is single-use. A later unprepared interval is UNKNOWN.
 w=Window{};chunk(w,3);one_close(w);motion_accept_pending(2);
 expected(2,5,MotionModelPose|MotionViewTrack|MotionMissingRoute);reset();
 // Ordinary material interval counts previous frozen reason, before next prepare.
 {MotionUnknownScope model(motion_model_reason());motion_prepare();}ordinary_interval(5);
 expected(1,5,MotionModelPose|MotionViewTrack);reset();
 // Successful switch, failed switch->close, and capacity close/reopen.
 w=Window{};chunk(w,3);material_switch(w);chunk(w,2);one_close(w);expected(2,5,MotionModelPose|MotionViewTrack);reset();
 switch_ok=false;w=Window{};chunk(w,6);material_switch(w);one_close(w);expected(1,6,MotionModelPose|MotionViewTrack);reset();switch_ok=true;
 w=Window{};chunk(w,8);one_close(w);w.open=true;motion_prepare();chunk(w,9);one_close(w);expected(2,17,MotionModelPose|MotionViewTrack);reset();
 // Missing and malformed external reasons cannot obtain the internal suppression marker.
 {MotionUnknownScope missing(0);motion_prepare();motion_accept_pending(1);}
 {MotionUnknownScope forged(0x80000000U);motion_prepare();motion_accept_pending(1);}
 expected(2,2,MotionMissingRoute);reset();
 motion.events=~0U-1;motion.records=~0U-1;{MotionUnknownScope model(motion_model_reason());motion_accept_current(3);motion_accept_current(3);}
 assert(motion.events==~0U && motion.records==~0U && motion.overflow==1);motion_unknown_flush();assert(faults==1 && logs.find("overflow=1")!=std::string::npos);reset();
}
'''

    def compile_run(self,text,reject=False):
        # Declarations used by extracted interval must precede it.
        decl='unsigned direct_parts,direct_slots,frame_pvr_bytes,stream_model_bytes,stream_peak_bytes,model_used;'
        text=text.replace(decl,'');text=text.replace('void ordinary_interval(',decl+'\nvoid ordinary_interval(')
        with tempfile.TemporaryDirectory(prefix='gc-motion24-',dir='/dev/shm') as temporary:
            root=Path(temporary);(root/'fixture.cpp').write_text(text)
            subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',
                '-DRE4DC_GC_ASSET_GATE=1','-DRE4DC_GC_ASSET_MOTION_UNKNOWN=1',
                '-I',str(PLATFORM/'include'),str(root/'fixture.cpp'),'-o',str(root/'run')],check=True)
            result=subprocess.run(['/lib64/ld-linux-x86-64.so.2',str(root/'run')],capture_output=True,text=True)
            if reject:self.assertEqual(result.returncode,-6,result.stderr)
            else:self.assertEqual(result.returncode,0,result.stderr)

    def test_actual_chunk_close_material_switch_and_latch(self):
        self.compile_run(self.fixture())

    def test_actual_body_mutants(self):
        fixture=self.fixture()
        for old,new in [
            ('if(w.motion_accounted)re4dc_gcasset::motion_pending_accounted();',''),
            ('if(window.motion_accounted)re4dc_gcasset::motion_pending_accounted();',''),
            ('if(e.slots){re4dc_gcasset::motion_accept_current(e.slots);w.motion_accounted=1;}','if(e.slots)w.motion_accounted=1;'),
            ('motion.pending=motion.context?sanitize(motion.context):unsigned(MotionUnclassifiedWorld|MotionViewTrack);','motion.pending=MotionMissingRoute;'),
            ('if(motion.pending==Accounted){motion.pending=MotionMissingRoute;return;}',''),
            ('    if(!records)return;\n    motion.reasons','    motion.reasons'),
            ('return reason && !(reason&~ValidReasons)?reason:unsigned(MotionMissingRoute);','return reason;'),
        ]:
            with self.subTest(mutant=old):
                self.assertEqual(fixture.count(old),1);self.compile_run(fixture.replace(old,new),True)

    def test_scope_leaf_and_old_visit_placement(self):
        ui=(PLATFORM/'native_ui.cpp').read_text();actor=(PLATFORM/'native_actor_fast.cpp').read_text()
        prepare=function(ui,'void gcasset_model_prepare(');accept=function(ui,'void gcasset_model_accept(')
        self.assertIn('motion_prepare();',prepare)
        self.assertLess(accept.index('motion_accept_pending(count)'),accept.index('payload_quads_accept'))
        commit=function(ui,'extern "C" void re4dc_model_packet_commit(')
        self.assertLess(commit.index('if(count)'),commit.index('RE4DC_GCA_MODEL_PACKET_ACCEPT'))
        for marker in ['extern "C" int re4dc_actor_submit(', 'extern "C" void re4dc_model_submit(']:
            source=actor if 'actor_submit' in marker else (PLATFORM/'native_model.cpp').read_text()
            body=source[source.index(marker):]
            first_work='++stats.parts;' if 'actor_submit' in marker else 'RE4DC_PROFILE_SCOPE(ModelSetup);'
            prefix=body[:body.index(first_work)]
            self.assertIn('MotionUnknownScope gcasset_motion_scope',prefix)
            self.assertLess(prefix.index('GeometryProducerScope'),prefix.index('MotionUnknownScope'))
        start=ui.index('Re4dcModelPart view=restore_view(deferred_first);');delayed=ui[start:ui.index('AVD_EVENT(FinishEnd',start)]
        self.assertLess(delayed.index('MotionUnknownScope'),delayed.index('re4dc_model_submit(&view)'))
        close=function(ui,'void gcasset_close_visit(');self.assertLess(close.index('gcasset_flush()'),close.index('re4dc_gcasset::end('))
        self.assertIn('motion_unknown_flush()',function(ui,'void gcasset_flush('))
        gate=(PLATFORM/'include/gc_asset_gate.h').read_text();self.assertIn('Required==0x3ff',gate)
        self.assertIn('~((1U<<re4dc_gcasset::SourceGeometry)|(1U<<re4dc_gcasset::Weapon)|(1U<<re4dc_gcasset::Motion))',ui)

    def leaf_fixture(self):
        ui=(PLATFORM/'native_ui.cpp').read_text()
        helpers=ui[ui.index('re4dc_gcasset::SourceUse gcasset_model_pending;'):ui.index('void gcasset_packet_reset()')]
        commit=function(ui,'extern "C" void re4dc_model_packet_commit(')
        start=ui.index('#if RE4DC_TA_DIRECT',ui.index('// WORLD_SUBMIT_END_IMPLEMENTATION'))
        direct='void direct_account(unsigned vertices){\n'+ui[start:ui.index('\n}\n#if RE4DC_SCENERY_SUBMIT_BATCH',start)+2]
        flush=function(ui,'void gcasset_flush(')
        close=function(ui,'void gcasset_close_visit(')
        return r'''
#include "gc_asset_motion_unknown.h"
#include "gc_asset_payloads.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <string>
using namespace re4dc_gcasset;
std::string logs;bool protected_context;
extern "C" void re4dc_log(const char*fmt,...){assert(!protected_context);char text[256];va_list ap;va_start(ap,fmt);vsnprintf(text,sizeof text,fmt,ap);va_end(ap);logs+=text;}
struct Re4dcModelPart{const void*model;const void*info;};
struct Handle{unsigned frame;};Handle handle;Handle*model_handle=&handle;
unsigned model_used,model_pending,model_peak,frame,direct_parts,direct_slots,frame_pvr_bytes,stream_model_bytes,stream_peak_bytes;
unsigned char model_packets[1024];
void stream_send(const void*,unsigned){assert(protected_context);}
void re4dc_missing(const char*){assert(false);}
#define RE4DC_GCA_MODEL_TEXTURE(...)
'''+helpers+r'''
#define RE4DC_GCA_MODEL_ACCEPT() gcasset_model_accept()
#define RE4DC_GCA_MODEL_PACKET_ACCEPT(vertices,count) gcasset_model_accept(vertices,count)
'''+commit+'\n'+direct+r'''
struct Entry{}entries[1];void gcasset_texture_flush(Entry&){}
namespace re4dc_gcasset{void bank_pump(){}}
void gcasset_packet_reset(){}bool gcasset_visit_live=true;
'''+flush+'\n'+close+r'''
int main(){install(nullptr,0);begin(0x111,1,0x1f6);logs.clear();
 int object,info;Re4dcModelPart model{&object,&info};
 // Actual packet leaf: accepted prefix survives zero final commit and abort-equivalent handle loss.
 {MotionUnknownScope context(motion_model_reason());gcasset_model_prepare(&model);}
 protected_context=true;re4dc_model_packet_commit(3);re4dc_model_packet_commit(0);protected_context=false;
 // Actual direct batch accounting remains memory-only under SQ and counts accepted prefix.
 {MotionUnknownScope context(motion_model_reason());gcasset_model_prepare(&model);}
 model_handle=nullptr;protected_context=true;direct_account(4);direct_account(0);protected_context=false;model_handle=&handle;
 assert(logs.empty());gcasset_close_visit(0);
 auto stats=logs.find("GC-MOTION-UNKNOWN");auto ending=logs.find("GC-ASSET-END");
 assert(stats!=std::string::npos && stats<ending && logs.find("reasons=00000003 events=2 accepted_records=7")!=std::string::npos);
 assert(logs.find("motion=0")!=std::string::npos && logs.find("wired=1f6")!=std::string::npos);
 assert(logs.find("GC-ASSET v=")==std::string::npos); // detector never invents a Motion asset
 // Next visit has no inherited accepted-use latch; header/reserve/cancel alone emit no diagnostic.
 begin(0x112,2,0x1f6);logs.clear();{MotionUnknownScope context(motion_model_reason());gcasset_model_prepare(&model);}
 protected_context=true;re4dc_model_packet_commit(0);direct_account(0);protected_context=false;gcasset_close_visit(0);
 assert(logs.find("GC-MOTION-UNKNOWN")==std::string::npos);
 // Startup/transition scopes use the same safe flush; never invent room0.
 begin_startup_closed(3,0x1f6);logs.clear();
 {MotionUnknownScope context(motion_model_reason());gcasset_model_prepare(&model);}
 protected_context=true;re4dc_model_packet_commit(2);protected_context=false;gcasset_close_visit(0);
 assert(logs.find("phase=startup")!=std::string::npos && logs.find("accepted_records=2")!=std::string::npos);
 begin(0x113,4,0x1f6);logs.clear();gcasset_model_prepare(nullptr);
 PayloadQuadUse use{nullptr,0,1U<<SourceGeometry};PayloadQuadBatch batch{&use,1,model_packets,4};model_pending=0;
 {PayloadQuadScope quads(batch);protected_context=true;re4dc_model_packet_commit(4);protected_context=false;}
 gcasset_close_visit(0);assert(logs.find("reasons=0000000a events=1 accepted_records=4")!=std::string::npos);
}
'''

    def test_actual_merged_cached_build_fallback_and_cancel(self):
        bridge=(GAME/'model_bridge.cpp').read_text();start=bridge.index('void flush(){',bridge.index('Entry* build('))
        merged=function(bridge[start:],'void flush(').replace('void flush(){','void merged_flush(){').replace('Entry*','BatchEntry*')
        model=(PLATFORM/'native_model.cpp').read_text();start=model.index('extern "C" void re4dc_model_submit(')
        gateway=model[start:model.index('#if defined(RE4DC_PROP_PROF)',start)]
        gateway+='gcasset_model_prepare(p);protected_context=true;re4dc_model_packet_commit(3);protected_context=false;\n}\n'
        fixture=self.leaf_fixture();fixture=fixture[:fixture.index('int main(){')]
        fixture=fixture.replace('struct Re4dcModelPart{const void*model;const void*info;};',
            'struct ModelPart{unsigned size=32;};struct Re4dcModelPart{const void*model;const void*info;const void*stream=nullptr;unsigned stream_bytes=0;ModelPart*part=nullptr;};')
        fixture+=r'''
struct Pending{bool on=true;unsigned n=2;Re4dcModelPart rec;ModelPart*parts[2];};
struct BatchEntry{unsigned char*buf;unsigned bytes;};struct State{Pending pend;};State state;State*S=&state;
struct{unsigned groups,lists,merged,saved,refused,singles;}st;
bool cached=true,built=true;unsigned char bytes[64];BatchEntry entry{bytes,64};
BatchEntry*find(const Pending&){return cached?&entry:nullptr;}BatchEntry*build(const Pending&){return built?&entry:nullptr;}
const unsigned char*list_of(ModelPart*p){return reinterpret_cast<const unsigned char*>(p);}
'''+gateway+'\n'+merged+r'''
int main(){install(nullptr,0);begin(0x111,1,0x1f6);ModelPart a,b;int object,info;state.pend.rec={&object,&info};state.pend.parts[0]=&a;state.pend.parts[1]=&b;
 for(unsigned mode=0;mode<4;++mode){logs.clear();state.pend.on=true;state.pend.n=mode==3?1:2;cached=mode==0;built=mode==1;
  {MotionUnknownScope unrelated(MotionUnclassifiedWorld|MotionViewTrack);merged_flush();}
  gcasset_flush();assert(logs.find("reasons=00000007")!=std::string::npos);
  assert(logs.find(mode==2?"events=2 accepted_records=6":"events=1 accepted_records=3")!=std::string::npos);
 }
 logs.clear();state.pend.on=false;{MotionUnknownScope unrelated(MotionMissingRoute);merged_flush();}gcasset_flush();assert(logs.empty());
}
'''
        self.compile_leaf(fixture)
        old='re4dc_gcasset::MotionUnknownScope gcasset_motion_scope(re4dc_gcasset::MotionDelayedModel|re4dc_gcasset::MotionModelPose|re4dc_gcasset::MotionViewTrack);'
        self.assertEqual(fixture.count(old),1);self.compile_leaf(fixture.replace(old,''),True)

    def test_actual_ui_leaves_flush_end_and_startup(self):
        self.compile_leaf(self.leaf_fixture())

    def compile_leaf(self,text,reject=False):
        with tempfile.TemporaryDirectory(prefix='gc-motion24-leaf-',dir='/dev/shm') as temporary:
            root=Path(temporary);(root/'fixture.cpp').write_text(text)
            subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',
                '-DRE4DC_GC_ASSET_GATE=1','-DRE4DC_GC_ASSET_MOTION_UNKNOWN=1','-DRE4DC_TA_DIRECT=1',
                '-DRE4DC_PVR_STREAM=1','-DRE4DC_SCENERY_SUBMIT_BATCH=1','-I',str(PLATFORM/'include'),
                str(root/'fixture.cpp'),*[str(PLATFORM/f) for f in ['gc_asset_motion_unknown.cpp','gc_asset_gate.cpp','gc_asset_members.cpp','gc_asset_payloads.cpp']],
                '-o',str(root/'run')],check=True)
            result=subprocess.run(['/lib64/ld-linux-x86-64.so.2',str(root/'run')],capture_output=True,text=True)
            self.assertEqual(result.returncode,-6 if reject else 0,result.stderr)

    def test_leaf_omission_and_unsafe_flush_mutants(self):
        fixture=self.leaf_fixture()
        for old,new in [
            ('    re4dc_gcasset::motion_prepare();',''),
            ('    re4dc_gcasset::motion_accept_pending(count);',''),
            ('    re4dc_gcasset::motion_accept_pending(vertices);',''),
            ('    re4dc_gcasset::motion_unknown_flush();',''),
            ('    re4dc_gcasset::motion_accept_pending(count);','    re4dc_gcasset::motion_accept_pending(count);re4dc_gcasset::motion_unknown_flush();'),
        ]:
            with self.subTest(mutant=old):
                self.assertEqual(fixture.count(old),1);self.compile_leaf(fixture.replace(old,new),True)

    def test_make_and_header_strict_admission(self):
        mk=(GAME/'gc_asset_gate.mk').read_text()
        with tempfile.TemporaryDirectory(prefix='gc-motion24-make-',dir='/dev/shm') as temporary:
            root=Path(temporary);make=root/'Makefile';make.write_text(mk+'\nall:\n\t@echo FLAGS=$(PLATFORM_CPPFLAGS) OBJS=$(PLATFORM_OBJS)\n')
            for gate,motion,fast,passed in [(0,0,1,True),(1,0,1,True),(0,1,1,False),(1,2,1,False),(1,1,0,False),(1,1,1,True)]:
                result=subprocess.run(['make','-s','-f',str(make),'all','OBJDIR=objects','PVR_STREAM=1','AICA_AUDIO=1','NATIVE_ACTOR=1',
                    'NATIVE_ACTOR_FAST='+str(fast),'GC_ASSET_GATE='+str(gate),'GC_ASSET_MOTION_UNKNOWN='+str(motion)],capture_output=True,text=True)
                self.assertEqual(result.returncode==0,passed,result.stderr)
                if passed:self.assertEqual('RE4DC_GC_ASSET_MOTION_UNKNOWN=1' in result.stdout,motion==1)
            for gate,motion,passed in [(0,0,True),(1,0,True),(0,1,False),(1,2,False),(1,1,True)]:
                result=subprocess.run(['g++','-x','c++','-fsyntax-only','-DRE4DC_GC_ASSET_GATE='+str(gate),
                    '-DRE4DC_GC_ASSET_MOTION_UNKNOWN='+str(motion),'-I',str(PLATFORM/'include'),'-'],input='#include "gc_asset_motion_unknown.h"\n',capture_output=True,text=True)
                self.assertEqual(result.returncode==0,passed,result.stderr)

    def test_helper_exact_state_and_forbidden_provider_imports(self):
        with tempfile.TemporaryDirectory(prefix='gc-motion24-imports-',dir='/dev/shm') as temporary:
            obj=Path(temporary)/'motion.o'
            subprocess.run(['g++','-std=c++17','-O2','-DRE4DC_GC_ASSET_GATE=1','-DRE4DC_GC_ASSET_MOTION_UNKNOWN=1',
                '-c',str(PLATFORM/'gc_asset_motion_unknown.cpp'),'-o',str(obj)],check=True)
            imports=subprocess.check_output(['nm','-C','--undefined-only',str(obj)],text=True)
            self.assertEqual(sorted(line.split(' U ',1)[1] for line in imports.splitlines()),
                ['re4dc_gcasset::unresolved(re4dc_gcasset::Consumer, char const*)','re4dc_log'])
            symbols=subprocess.check_output(['nm','-S','-C','--defined-only',str(obj)],text=True)
            state=[line for line in symbols.splitlines() if ' b ' in line or ' B ' in line or ' d ' in line or ' D ' in line]
            self.assertEqual(len(state),1);self.assertIn('0000000000000018 b re4dc_gcasset::(anonymous namespace)::motion',state[0])

    def test_historical_exact_ui_projection_and_mutants(self):
        from composition_references import frozen_source, GC_UNIT
        source=frozen_source(GC_UNIT,'platform/native_ui.cpp')
        baseline=subprocess.check_output(['git','-C',str(GAME.parents[2]),'show',BASE+':port/dreamcast/game/platform/native_ui.cpp'],text=True)
        self.assertEqual(project_ui_motion0(source),baseline)
        for old,new in [
            ('#if RE4DC_GC_ASSET_MOTION_UNKNOWN\n    re4dc_gcasset::motion_prepare();\n#endif','    re4dc_gcasset::motion_prepare();'),
            ('#if RE4DC_GC_ASSET_MOTION_UNKNOWN\n    re4dc_gcasset::motion_prepare();','#if RE4DC_GC_ASSET_GATE\n    re4dc_gcasset::motion_prepare();'),
            ('|(1U<<re4dc_gcasset::Motion));',');'),
        ]:
            with self.subTest(mutant=old):
                self.assertEqual(source.count(old),1)
                with self.assertRaises(AssertionError):self.assertEqual(project_ui_motion0(source.replace(old,new)),baseline)

    def test_default0_tokens_and_empty_helper(self):
        paths=['platform/native_ui.cpp','platform/native_model.cpp','platform/native_actor_fast.cpp','platform/include/native_actor_leon_pipe.inc','model_bridge.cpp']
        with tempfile.TemporaryDirectory(prefix='gc-motion24-off-',dir='/dev/shm') as temporary:
            root=Path(temporary)
            for unit in paths:
                old=subprocess.check_output(['git','-C',str(GAME.parents[2]),'show',BASE+':port/dreamcast/game/'+unit],text=True)
                current=(GAME/unit).read_text();files=[]
                for name,source in [('old',old),('current',current)]:
                    file=root/(name+'.cpp');file.write_text(re.sub(r'^#include .*\n','',source,flags=re.M));files.append(file)
                # Gate1 geometry ancestry intentionally changes in SOURCE-WEAPON24.
                # Historical UNKNOWN0 full-profile identity is not asserted.
                # Keep literal historical Gate0 identity and disabled helper.
                for gate in [0]:
                    flags=['-DRE4DC_GC_ASSET_GATE='+str(gate),'-DRE4DC_GC_ASSET_MOTION_UNKNOWN=0','-DRE4DC_COARSE_ONE_SUBMIT=1',
                        '-DRE4DC_ACTOR_DIRECT=1','-DRE4DC_NATIVE_ACTOR_SKIN_LAZY=1','-DRE4DC_NATIVE_ACTOR=1','-DRE4DC_NATIVE_ACTOR_FAST=1','-DRE4DC_MODEL_STREAM_FIX=1']
                    streams=[subprocess.check_output(['g++','-E','-P',*flags,str(f)],text=True) for f in files]
                    tokens=lambda s:re.findall(r'"(?:\\.|[^"\\])*"|[A-Za-z_]\w*|\d+|\S',s)
                    self.assertEqual(tokens(streams[0]),tokens(streams[1]),unit)
            for gate in [0,1]:
                obj=root/('off'+str(gate)+'.o')
                subprocess.run(['g++','-std=c++17','-O2','-DRE4DC_GC_ASSET_GATE='+str(gate),'-c',str(PLATFORM/'gc_asset_motion_unknown.cpp'),'-o',str(obj)],check=True)
                self.assertEqual(subprocess.check_output(['nm','--defined-only',str(obj)],text=True),'')

if __name__=='__main__':unittest.main()
