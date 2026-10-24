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
 {MotionUnknownScope model(motion_model_reason());motion_prepare();protected_context=true;motion_accept_pending(0);protected_context=false;}
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
            ('if(motion.pending!=Accounted)accept(motion.pending,records);','accept(motion.pending,records);'),
            ('if(!records)return;',''),
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
            self.assertIn('MotionUnknownScope gcasset_motion_scope',source[source.index(marker):source.index(marker)+550])
        start=ui.index('Re4dcModelPart view=restore_view(deferred_first);');delayed=ui[start:ui.index('AVD_EVENT(FinishEnd',start)]
        self.assertLess(delayed.index('MotionUnknownScope'),delayed.index('re4dc_model_submit(&view)'))
        close=function(ui,'void gcasset_close_visit(');self.assertLess(close.index('gcasset_flush()'),close.index('re4dc_gcasset::end('))
        self.assertIn('motion_unknown_flush()',function(ui,'void gcasset_flush('))
        gate=(PLATFORM/'include/gc_asset_gate.h').read_text();self.assertIn('Required==0x3ff',gate)
        self.assertIn('~((1U<<re4dc_gcasset::SourceGeometry)|(1U<<re4dc_gcasset::Weapon)|(1U<<re4dc_gcasset::Motion))',ui)

    def test_default0_tokens_and_empty_helper(self):
        paths=['platform/native_ui.cpp','platform/native_model.cpp','platform/native_actor_fast.cpp','platform/include/native_actor_leon_pipe.inc']
        with tempfile.TemporaryDirectory(prefix='gc-motion24-off-',dir='/dev/shm') as temporary:
            root=Path(temporary)
            for unit in paths:
                old=subprocess.check_output(['git','-C',str(GAME.parents[2]),'show',BASE+':port/dreamcast/game/'+unit],text=True)
                current=(GAME/unit).read_text();files=[]
                for name,source in [('old',old),('current',current)]:
                    file=root/(name+'.cpp');file.write_text(re.sub(r'^#include .*\n','',source,flags=re.M));files.append(file)
                for gate in [0,1]:
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
