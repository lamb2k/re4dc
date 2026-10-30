"""EF03 ordinary sprite/RTT/water: actual producer and packet bodies, fake devices.

No asset data or SDK. Host ABI/FP and fake PVR headers do not qualify a console.
"""
import importlib.util
import difflib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('ef03_gate',HERE/'test_fx_r200_entry_cap.py')
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
ROOT,INC=gate.ROOT,gate.INCLUDE
BASE='83148f45e7cc98032c724b0d9309737e16806ae5'


def fixture(base=None):
    source=gate.production(gate.NATIVE,base)
    text=gate.TEST.read_text().split('#include "fx_r200_test_scaffold.inc"')[0]
    body=gate.scaffold(base).replace('culling,fog_type,shading','culling,fog_type,shading,alpha')
    body=body.replace('#include "native_model.h"','#include "native_model.h"\n#include "native_draw_result.hpp"\n#include "subscreen_quad_geometry.hpp"\n#include "water_outcomes03.hpp"')
    stream=gate.extract.function(body,'void stream_send(')
    body=body.replace(stream,r'''unsigned raw_sends=0,abort_send=0;
void stream_send(const void* data,unsigned count){
    ++raw_sends;sent_bytes+=count;gate::Packet p{1,{}};
    const auto* b=static_cast<const unsigned char*>(data);p.bytes.assign(b,b+count);
    gate::packets.push_back(std::move(p));
    if(abort_send && raw_sends==abort_send)stream_aborted=true;
}''')
    support=r'''
#include <cstdlib>
using pvr_ptr_t=void*;
bool rtt_alloc_ok=true;unsigned prim_calls=0;
void* pvr_mem_malloc(unsigned n){return rtt_alloc_ok?std::malloc(n):nullptr;}
void pvr_mem_free(void* p){std::free(p);}
unsigned fb_register=0;struct{unsigned bg_color=0;}pvr_state;
#define PVR_FB_CFG_2 0
#define PVR_GET(x) fb_register
#define PVR_SET(x,v) (fb_register=(v))
int pvr_scene_begin_rtt(void*,unsigned,unsigned,unsigned){return 0;}
int pvr_list_begin(unsigned){return 0;}
void pvr_scene_finish(){} void pvr_list_finish(){} void pvr_wait_render_done(){}
void present_fence(){} std::uint64_t timer_us_gettime64(){return 0;}
float fog_amount=0;
extern "C" float re4dc_fog_amount(float){return fog_amount;}
'''
    start=body.index('extern "C" int re4dc_effect_sprite(')
    includes=gate.production(gate.INCLUDES+'pvr_rtt.inc',base)+'\n'+gate.production(gate.INCLUDES+'native_water_ps2.inc',base)
    if base is None:
        includes+='\n#if RE4DC_NATIVE_DRAW_OUTCOMES\n'+gate.definition(source,'extern "C" re4dc::NativeDrawResult re4dc_effect_sprite_result(')+'\n#endif\n'
    body=body[:start]+support+includes+'\n'+body[start:]
    # Import the production water drain owner, not a fixture implementation.
    begin=source.index('if(deferred_first->lighting==kWaterTag)')
    water=gate.extract.function(source[begin:],'if(deferred_first->lighting==kWaterTag)')
    body=body.replace('    while(deferred_first&&!stream_aborted){','    while(deferred_first&&!stream_aborted){\n'+water)
    text+='#undef CHECK\n#define CHECK(x) gate::check(bool(x), #x, 0)\n#define DFA26_HIT(...)\n'+body
    return text


def source_fixture():
    source=(ROOT/'src/game/esp_sub.cpp').read_text()
    finish=gate.extract.function((ROOT/'src/game/espgen45.cpp').read_text(),'static void Water29Finish(')
    return r'''
using u8=unsigned char;using u32=unsigned;using f32=float;using Mtx=float[3][4];
struct TEXHeader {void* data;unsigned width,height,format;};
struct CLUT {void* data;unsigned format,numEntries;};
struct TEXDescriptor {TEXHeader* textureHeader;CLUT* CLUTHeader;};
struct TEXPalette {unsigned numDescriptors;};
struct EspTexWk {unsigned Owner=0;TEXPalette* pTpl=nullptr;float mtx[3][4]{};};
struct System {EspTexWk Esp_tex_tbl[1];}sys03,*g_pEspSys=&sys03;
struct cEsp {unsigned m_Id=1,m_Tex_id=0,m_Ptn_no=0,m_Tool_flg=0,m_Flg=0,xA5=4,xA6=5;Mtx m_Mat{};};
struct {u8 r=128,g=64,b=32,a=192;}s_effect_col;
TEXHeader tex03{reinterpret_cast<void*>(1),64,64,14};TEXDescriptor desc03{&tex03,nullptr};TEXPalette pal03{1};
TEXDescriptor* TEXGet(TEXPalette*,unsigned){return &desc03;}
bool ortho03=false,bad_view03=false,hide03=false;
void projection03(float* p){const float perspective[]={0,1,0,1,0,-.01f,-1.01f};
    std::memcpy(p,perspective,sizeof perspective);if(ortho03){p[0]=1;p[4]=0;}}
void viewport03(float* p){const float v[]={0,0,640,480,0,1};std::memcpy(p,v,sizeof v);if(bad_view03)p[2]=0;}
#define RE4DC_FX_FLIP_PTN(p,n) (p)
#define RE4DC_GXF_GET_PROJECTION(p) projection03(p)
#define RE4DC_GXF_GET_VIEWPORT(p) viewport03(p)
#define RE4DC_WATER45_NATIVE 1
int re4dc_water45_hides(float (*)[3]){return hide03;}
unsigned bridge_calls03=0;Re4dcEffectSprite source_packet03;
re4dc::NativeDrawResult bridge03(const Re4dcEffectSprite* s){++bridge_calls03;source_packet03=*s;return re4dc_effect_sprite_result(s);}
#define re4dc_effect_sprite_result bridge03
''' + gate.extract.function(source,'static re4dc::NativeDrawResult EspSpriteEmitResult03(')+'\n'+gate.extract.function(source,'static void EspSpriteEmit(')+r'''
#undef re4dc_effect_sprite_result
unsigned G_ROOM_ID=0x10b;
struct {unsigned flag=1;}water45_work03,*g_pWater45=&water45_work03;
unsigned fallback_calls03=0;
void re4dc_water45_draw(decltype(g_pWater45)){++fallback_calls03;}
unsigned re4dc_ui_frame(){return frame;}
enum{WATER29_NOT_ATTEMPTED,WATER29_ADMITTED,WATER29_TOTAL_REFUSAL,WATER29_PARTIAL_REFUSAL};
unsigned s_water29_last_admission=0,s_water29_partial=0,s_water29_admission_refused=0,s_water29_last_log_frame=~0U;
''' + '#if RE4DC_NATIVE_DRAW_OUTCOMES\n' + finish


def water_producer_fixture():
    source=(ROOT/'src/game/espgen45.cpp').read_text()
    def struct(name):
        start=source.index('struct '+name+' {');return source[start:source.index('};',start)+2]
    return '\nusing s32=int;using s16=short;using u16=unsigned short;\n'+struct('WaterPs2Row')+'\n'+struct('WaterPs2ExtRow')+r'''
struct GXColor {u8 r,g,b,a;};
struct {struct {Mtx v_mat{};}Cam;}global03,*pG=&global03;
struct Water29View {const WaterPs2Row* main_rows;unsigned main_count;const WaterPs2ExtRow* ext_rows;unsigned ext_count,ext_index_base;};
WaterPs2Row main_rows03[3];WaterPs2ExtRow ext_rows03[2];
unsigned main_count03=3,ext_count03=2;
enum {WATER29_BOUND};
int Water29Select(unsigned,Water29View* out){*out={main_rows03,main_count03,ext_rows03,ext_count03,0};return WATER29_BOUND;}
int re4dc_water42_live(){return 1;}int re4dc_fx_level_get(){return 0;}
void CameraCurrentProjection(){}void GXGetProjectionv(float* p){projection03(p);}void GXGetViewportv(float* p){viewport03(p);}
void PSMTXInverse(const Mtx&,Mtx& out){std::memset(out,0,sizeof out);}
void PSMTXConcat(const Mtx&,const Mtx& in,Mtx& out){std::memcpy(out,in,sizeof out);out[2][3]=-100;}
unsigned re4dc_vi_retrace_count(){return 0;}int EffIsSetFinalCol(){return 0;}void EffGetFinalCol(GXColor*){}
int EffGetAreaState(int){return 1;}int GetSstDispFlag(unsigned){return 1;}
unsigned WaterPs2Pattern(const WaterPs2Row&,const EspTexWk*,unsigned,unsigned){return 0;}
unsigned s_wps2_frame=~0U;
unsigned water_calls03=0;unsigned refuse_mask03=0,terminal_mask03=0;
std::vector<unsigned> visit03;re4dc::NativeDrawResult finished03{re4dc::NativeDrawOutcome::Culled};
re4dc::NativeDrawResult water_bridge03(const Re4dcWaterLayer* L,int* admitted){
    const unsigned index=water_calls03++;visit03.push_back(unsigned(L->half_x));
    if(terminal_mask03&(1u<<index)){*admitted=0;return {re4dc::NativeDrawOutcome::PartialAbort};}
    if(refuse_mask03&(1u<<index)){*admitted=0;return {re4dc::NativeDrawOutcome::Refused};}
    return re4dc_water_layer_result(L,admitted);
}
void finish_bridge03(unsigned accepted,unsigned refused,const re4dc::NativeDrawResult& output){
    finished03=output;Water29Finish(accepted,refused,output);
}
#define RE4DC_WATER_LAYER29 1
#define RE4DC_WATER_PS2_EXT 1
#define re4dc_water_layer_result water_bridge03
#define Water29Finish finish_bridge03
''' + source[source.index('extern "C" void re4dc_water_ps2_draw(void*)'):source.index('// EspgenTrans (espgen.cpp), once per drawn image:')]+r'''
#undef re4dc_water_layer_result
#undef Water29Finish
void producer_fresh03(){
    reset();model_packets=reinterpret_cast<pvr_vertex_t*>(gate::slab);
    gate::packets.clear();water_calls03=0;visit03.clear();refuse_mask03=terminal_mask03=0;
    for(unsigned i=0;i<3;++i){auto& r=main_rows03[i];r={};r.room=G_ROOM_ID;r.area=-1;
        r.tex=0xf7;r.hx=float(i+1);r.hz=200;r.argb=0xffffffff;r.src=4;r.dst=5;}
    for(unsigned i=0;i<2;++i){auto& r=ext_rows03[i];r={};r.room=G_ROOM_ID;r.area=-1;r.disp=0xff;
        r.tex=0xf7;r.hx=float(i+4);r.hz=200;r.ax[0]=r.az[2]=1;r.argb=0xffffffff;r.src=4;r.dst=5;}
}
'''


CASES=r'''
static void fresh03(){
    reset();model_packets=reinterpret_cast<pvr_vertex_t*>(gate::slab);
    gate::packets.clear();gate::logs.clear();raw_sends=abort_send=0;
    rtt::packet_count=0;rtt::capture_slot=-1;fog_amount=0;fog_far=0;
}
static Re4dcWaterLayer water03(){
    Re4dcWaterLayer w{};w.projection[1]=1;w.projection[5]=-1.0f/999.0f;
    w.projection[6]=-1000.0f/999.0f;w.viewport[2]=640;w.viewport[3]=480;
    w.viewport[4]=0;w.viewport[5]=1;w.half_x=w.half_z=200;w.argb=0xffffffff;
    w.mv[0][0]=w.mv[1][2]=1;w.mv[2][3]=-100;w.src=4;w.dst=5;return w;
}
int main(){using O=re4dc::NativeDrawOutcome;
    CHECK(sizeof(re4dc::NativeDrawResult)==12 && sizeof(WaterOut)==1056);
    fresh03();auto s=sprite();auto r=re4dc_effect_sprite_result(&s);
    CHECK(r.outcome==O::Queued && r.queued==1 && !r.submitted);
    CHECK(raw_sends==0 && deferred_count==1);drain();CHECK(raw_sends>0);
    fresh03();source_draws_finished=true;r=re4dc_effect_sprite_result(&s);
    CHECK(r.outcome==O::Submitted && r.submitted==1 && !r.queued);
    fresh03();source_draws_finished=true;abort_send=1;r=re4dc_effect_sprite_result(&s);
    CHECK(r.outcome==O::PartialAbort && r.published() && !r.fallback_allowed());
    fresh03();stream_aborted=true;r=re4dc_effect_sprite_result(&s);
    CHECK(r.outcome==O::PartialAbort && !r.published() && !r.fallback_allowed());
    CHECK(re4dc_effect_sprite(&s)==0 && !deferred_count && !raw_sends);
    fresh03();s.pad=1;r=re4dc_effect_sprite_result(&s);CHECK(r.outcome==O::Queued && r.queued==1);
    drain();CHECK(raw_sends>0);fresh03();source_draws_finished=true;abort_send=1;
    r=re4dc_effect_sprite_result(&s);CHECK(r.outcome==O::PartialAbort && r.submitted==1);s=sprite();
    fresh03();s.color=0;r=re4dc_effect_sprite_result(&s);CHECK(r.outcome==O::PolicySkip);
    CHECK(re4dc_effect_sprite(&s)==0);s=sprite();s.x[0]=NAN;
    r=re4dc_effect_sprite_result(&s);CHECK(r.outcome==O::UnsupportedBeforePublication);
    fresh03();s=sprite();for(float& x:s.x)x=-100;r=re4dc_effect_sprite_result(&s);CHECK(r.outcome==O::Culled);
    fresh03();s=sprite();texture_missing=true;r=re4dc_effect_sprite_result(&s);CHECK(r.outcome==O::Refused && r.fallback_allowed());
    fresh03();deferred_top=0;model_packets=nullptr;gate::allocation_ok=false;r=re4dc_effect_sprite_result(&s);
    CHECK(r.outcome==O::Refused && !r.published());gate::allocation_ok=true;
    fresh03();re4dc_rtt_want(0);re4dc_rtt_capture_begin(0,32,32,64,64,0);
    r=re4dc_effect_sprite_result(&s);CHECK(r.outcome==O::Queued && r.queued==1 && raw_sends==0);
    CHECK(rtt::packet_count==1);std::vector<unsigned char> copied(rtt::packets[0],rtt::packets[0]+kSpritePacket);
    s.x[0]+=13;CHECK(std::memcmp(copied.data(),rtt::packets[0],kSpritePacket)==0);s=sprite();
    rtt::packet_count=rtt::kMaxSprites;
    r=re4dc_effect_sprite_result(&s);CHECK(r.outcome==O::Refused);re4dc_rtt_room_reset();
    fresh03();re4dc_rtt_want(0);re4dc_rtt_capture_begin(0,32,32,64,64,0);stream_aborted=true;
    r=re4dc_effect_sprite_result(&s);
    CHECK(r.outcome==O::PartialAbort && !r.published() && !r.fallback_allowed() && rtt::packet_count==0);
    // Independent capture retains its existing copy/policy decision. It is not
    // the public sprite entry's already-aborted-stream refusal point.
    r=rtt::capture_result03(&s);
    CHECK(r.outcome==O::PartialAbort && r.queued==1 && rtt::packet_count==1);
    s.color=0;r=rtt::capture_result03(&s);CHECK(r.outcome==O::PolicySkip && !r.published());
    s=sprite();re4dc_rtt_room_reset();
    fresh03();re4dc_rtt_capture_begin(0,32,32,64,64,0);rtt::targets[0].want_frame=0;
    r=re4dc_effect_sprite_result(&s);CHECK(r.outcome==O::PolicySkip);re4dc_rtt_room_reset();
    fresh03();rtt_alloc_ok=false;re4dc_rtt_want(0);re4dc_rtt_capture_begin(0,32,32,64,64,0);
    r=re4dc_effect_sprite_result(&s);CHECK(r.outcome==O::Refused);rtt_alloc_ok=true;re4dc_rtt_room_reset();
    fresh03();re4dc_rtt_want(0);re4dc_rtt_capture_begin(0,15,32,64,64,0);
    r=re4dc_effect_sprite_result(&s);CHECK(r.outcome==O::UnsupportedBeforePublication);re4dc_rtt_room_reset();
    fresh03();re4dc_rtt_want(0);re4dc_rtt_capture_begin(0,32,32,64,64,0);s.x[0]=NAN;
    r=re4dc_effect_sprite_result(&s);CHECK(r.outcome==O::UnsupportedBeforePublication && rtt::packet_count==0);
    s=sprite();texture_missing=true;r=re4dc_effect_sprite_result(&s);CHECK(r.outcome==O::Refused && rtt::packet_count==0);re4dc_rtt_room_reset();
    fresh03();auto w=water03();int admitted=-1;r=re4dc_water_layer_result(&w,&admitted);
    CHECK(admitted==1 && r.outcome==O::Queued && r.queued==1 && !raw_sends);drain();CHECK(raw_sends>0);
    fresh03();stream_aborted=true;r=re4dc_water_layer_result(&w,&admitted);
    CHECK(admitted==0 && r.outcome==O::PartialAbort && !r.published() && !r.fallback_allowed());
    CHECK(re4dc_water_layer(&w)==0 && !deferred_count && !raw_sends);
    fresh03();source_draws_finished=true;w=water03();fog_amount=1;
    r=re4dc_water_layer_result(&w,&admitted);CHECK(admitted==1 && r.outcome==O::Submitted && r.submitted==1);
    CHECK(raw_sends==1 && gate::packets[0].bytes.size()==32 && !r.fallback_allowed());
    fresh03();source_draws_finished=true;w=water03();w.projection[5]=0;
    r=re4dc_water_layer_result(&w,&admitted);CHECK(admitted==1 && r.outcome==O::UnsupportedBeforePublication && !raw_sends);
    CHECK(re4dc_water_layer(&w)==1); // legacy admission is independent of visible output
    fresh03();source_draws_finished=true;w=water03();w.eye_x=1e9f;
    r=re4dc_water_layer_result(&w,&admitted);CHECK(admitted==1 && r.outcome==O::Culled && !raw_sends);
    fresh03();source_draws_finished=true;w=water03();abort_send=1;
    r=re4dc_water_layer_result(&w,&admitted);CHECK(admitted==1 && r.outcome==O::PartialAbort && r.submitted==1 && !r.fallback_allowed());
    fresh03();source_draws_finished=true;w=water03();abort_send=2;
    r=re4dc_water_layer_result(&w,&admitted);CHECK(raw_sends>=2 && r.outcome==O::PartialAbort);
    fresh03();w=water03();w.projection[0]=1;r=re4dc_water_layer_result(&w,&admitted);
    CHECK(admitted==0 && r.outcome==O::UnsupportedBeforePublication && !raw_sends);
    fresh03();w=water03();deferred_top=0;model_packets=nullptr;gate::allocation_ok=false;
    r=re4dc_water_layer_result(&w,&admitted);CHECK(!admitted && r.outcome==O::Refused);
    re4dc::NativeDrawProgress p;re4dc_water03_observe(p,{O::Refused});
    CHECK(p.result.fallback_allowed());re4dc_water03_observe(p,{O::Queued,0,1});
    CHECK(p.result.outcome==O::PartialAbort && p.result.queued==1 && !p.result.fallback_allowed());
    re4dc_water03_observe(p,{O::Submitted,1,0});CHECK(p.result.submitted==1 && p.result.queued==1);
    fresh03();cEsp e;auto& tw=g_pEspSys->Esp_tex_tbl[0];tw.pTpl=&pal03;tw.mtx[0][0]=tw.mtx[1][1]=1;
    e.m_Mat[0][0]=e.m_Mat[1][1]=1;e.m_Mat[2][3]=-10;
    r=EspSpriteEmitResult03(&e);CHECK(r.outcome==O::Queued && bridge_calls03==1);
    CHECK(source_packet03.color==0xc0804020 && source_packet03.src==4 && source_packet03.dst==5);
    CHECK(source_packet03.u[0]==0 && source_packet03.v[0]==0 && source_packet03.z[0]==.1f);
    fresh03();texture_missing=true;r=EspSpriteEmitResult03(&e);CHECK(r.outcome==O::Refused);
    fresh03();bad_view03=true;r=EspSpriteEmitResult03(&e);CHECK(r.outcome==O::UnsupportedBeforePublication);bad_view03=false;
    fresh03();hide03=true;r=EspSpriteEmitResult03(&e);CHECK(r.outcome==O::Culled);hide03=false;
    fresh03();e.m_Mat[2][3]=-.1f;r=EspSpriteEmitResult03(&e);CHECK(r.outcome==O::PolicySkip);e.m_Mat[2][3]=-10;
    fresh03();tw.pTpl=nullptr;r=EspSpriteEmitResult03(&e);CHECK(r.outcome==O::Refused);tw.pTpl=&pal03;
    fresh03();source_draws_finished=true;abort_send=1;r=EspSpriteEmitResult03(&e);CHECK(r.outcome==O::PartialAbort);
    fresh03();EspSpriteEmit(&e);CHECK(deferred_count==1); // existing void caller contract
    fresh03();stream_aborted=true;r=EspSpriteEmitResult03(&e);
    CHECK(r.outcome==O::PartialAbort && !r.published() && !r.fallback_allowed());
    EspSpriteEmit(&e);CHECK(!deferred_count && !raw_sends); // same source void ABI
    Water29Finish(0,1,{O::Refused});CHECK(fallback_calls03==1);
    Water29Finish(0,1,{O::PartialAbort,1,0});CHECK(fallback_calls03==1);
    Water29Finish(1,1,{O::PartialAbort,0,1});CHECK(fallback_calls03==1 && s_water29_partial==1);
    Water29Finish(1,0,{O::Submitted,1,0});CHECK(s_water29_last_admission==WATER29_ADMITTED);
    fresh03();unsigned submitted=99;
    CHECK(re4dc_effect_stage1_batch(nullptr,0,5,&submitted)==1 && submitted==0);
    CHECK(re4dc_effect_haze_batch(nullptr,0,&submitted)==1 && submitted==0);
    s=sprite();s.color=0;CHECK(re4dc_effect_stage1_batch(&s,1,5,&submitted)==1 && submitted==0);
    CHECK(re4dc_effect_haze_batch(&s,1,&submitted)==1 && submitted==0 && deferred_count==0);
    producer_fresh03();refuse_mask03=2;re4dc_water_ps2_draw(nullptr);
    CHECK(visit03==std::vector<unsigned>({1,2,3,4,5}));
    CHECK(finished03.outcome==O::PartialAbort && finished03.queued==4 && deferred_count==4);
    CHECK(s_water29_last_admission==WATER29_PARTIAL_REFUSAL);const auto calls=water_calls03;
    re4dc_water_ps2_draw(nullptr);CHECK(water_calls03==calls); // once per native image
    producer_fresh03();refuse_mask03=31;const auto prior_fallback=fallback_calls03;re4dc_water_ps2_draw(nullptr);
    CHECK(finished03.fallback_allowed() && fallback_calls03==prior_fallback+1 && water_calls03==5);
    producer_fresh03();refuse_mask03=31;terminal_mask03=1;re4dc_water_ps2_draw(nullptr);
    CHECK(finished03.outcome==O::PartialAbort && !finished03.published() && fallback_calls03==prior_fallback+1);
    // Actual native stream state, without the synthetic terminal bridge: every
    // existing layer visit remains, but no legacy generator replay is allowed.
    producer_fresh03();stream_aborted=true;const auto prior_terminal_fallback=fallback_calls03;
    re4dc_water_ps2_draw(nullptr);
    CHECK(visit03==std::vector<unsigned>({1,2,3,4,5}) && water_calls03==5);
    CHECK(finished03.outcome==O::PartialAbort && !finished03.published() && !finished03.fallback_allowed());
    CHECK(s_water29_last_admission==WATER29_TOTAL_REFUSAL && fallback_calls03==prior_terminal_fallback);
    std::printf("EF03 packet boundaries passed: %u assertions\n",gate::assertions);
}
'''


class Outcomes03(unittest.TestCase):
    def test_complete_source_option_absent_zero_preprocessing(self):
        for name in ('esp_sub.cpp','espgen45.cpp'):
            path='src/game/'+name
            old=gate.production(path,BASE);current=gate.production(path)
            for target in (False,True):
                args=['g++','-std=gnu++20','-fpermissive','-w','-E','-P','-DRE4DC_GAME',
                      '-DRE4DC_EFFECT_SPRITES=1','-DRE4DC_EFFECT_LEAN=1','-DRE4DC_FX_STRIP21=1',
                      '-DRE4DC_WATER_PS2=1','-DRE4DC_WATER45_NATIVE=1','-DRE4DC_WATER45_LEAN=1','-DRE4DC_WATER_PS2_EXT=1','-DRE4DC_WATER_LAYER29=1',
                      '-include',str(INC/'re4dc_prelude.h'),'-I'+str(ROOT/'include'),'-I'+str(ROOT/'src'),
                      '-I'+str(INC),'-iquote',str(ROOT/'src/game')]
                if target:args+=['-D__sh__']
                outputs=[]
                for text,defs in ((old,[]),(current,[]),(current,['-DRE4DC_NATIVE_DRAW_OUTCOMES=0'])):
                    run=subprocess.run(args+defs+['-x','c++','-'],input=text,capture_output=True,text=True,cwd=ROOT)
                    self.assertEqual(run.returncode,0,run.stderr);outputs.append(run.stdout)
                self.assertTrue(outputs[0]==outputs[1],name+'\n'+'\n'.join(list(difflib.unified_diff(outputs[0].splitlines(),outputs[1].splitlines()))[:100]))
                self.assertEqual(outputs[0],outputs[2],name)

    def test_native_option_absent_zero_preprocessing_and_objects(self):
        with tempfile.TemporaryDirectory(prefix='ef03-off-') as td:
            tmp=Path(td);(tmp/'dc').mkdir()
            (tmp/'dc/pvr.h').write_text(gate.PVR_STUB.replace('PVR_LIST_OP_POLY=0,','PVR_ALPHA_ENABLE=1,PVR_UVCLAMP_NONE=0,PVR_LIST_OP_POLY=0,'))
            (tmp/'config.h').write_text('\n'.join(f'#define {k} {v}' for k,v in dict(gate.CONFIG,RE4DC_PVR_RTT=1,RE4DC_WATER_PS2=1).items()))
            pp=[];objects=[]
            for name,base,defs in (('base',BASE,[]),('absent',None,[]),('zero',None,['-DRE4DC_NATIVE_DRAW_OUTCOMES=0'])):
                code=fixture(base)
                args=['g++','-std=c++20','-O2','-g0','-ffp-contract=off','-include',str(tmp/'config.h'),
                      '-I'+str(tmp),'-I'+str(INC),'-I'+str(gate.PLATFORM),'-I'+str(ROOT/'port/dreamcast/room'),*defs]
                run=subprocess.run(args+['-E','-P','-x','c++','-'],input=code,capture_output=True,text=True)
                self.assertEqual(run.returncode,0,run.stderr);pp.append(run.stdout)
                obj=tmp/(name+'.o')
                run=subprocess.run(args+['-x','c++','-','-c','-o',str(obj)],input=code,capture_output=True,text=True)
                self.assertEqual(run.returncode,0,run.stderr);objects.append(obj.read_bytes())
            self.assertTrue(pp[0]==pp[1],'\n'.join(list(difflib.unified_diff(pp[0].splitlines(),pp[1].splitlines()))[:100]))
            self.assertEqual(pp[0],pp[2])
            self.assertEqual(objects[0],objects[1]);self.assertEqual(objects[0],objects[2])

    def test_primary_make_exact_existing_selector_consumers(self):
        with tempfile.TemporaryDirectory(prefix='ef03-make-') as td:
            kos=Path(td);(kos/'Makefile.rules').write_text('')
            targets=['obj/src/game/esp_sub.o','obj/src/game/cloth.o','obj/src/game/espgen45.o','obj/platform/native_ui.o','obj/src/game/esp01.o']
            common=['make','--no-print-directory','-f','Makefile','-n','KOS_BASE='+str(kos),*targets,'EFFECT_SPRITES=1','FX_STRIP21=1']
            outputs=[]
            for value in (None,'0','1'):
                run=subprocess.run(common+([] if value is None else ['NATIVE_DRAW_OUTCOMES='+value]),capture_output=True,text=True,cwd=ROOT/'port/dreamcast/game')
                self.assertEqual(run.returncode,0,run.stderr)
                lines=[s for s in run.stdout.splitlines() if s.startswith('kos-c++')];self.assertEqual(len(lines),5);outputs.append(lines)
            self.assertEqual(outputs[0],outputs[1])
            for i,line in enumerate(outputs[2]):self.assertEqual(line.count('-DRE4DC_NATIVE_DRAW_OUTCOMES=1'),int(i<4),line)

    def test_actual_sprite_RTT_water_boundaries_normal_and_sanitized(self):
        with tempfile.TemporaryDirectory(prefix='ef03-packets-') as td:
            tmp=Path(td);(tmp/'dc').mkdir()
            (tmp/'dc/pvr.h').write_text(gate.PVR_STUB.replace('PVR_LIST_OP_POLY=0,','PVR_ALPHA_ENABLE=1,PVR_UVCLAMP_NONE=0,PVR_LIST_OP_POLY=0,'))
            config=dict(gate.CONFIG,RE4DC_NATIVE_DRAW_OUTCOMES=1,RE4DC_PVR_RTT=1,RE4DC_WATER_PS2=1)
            (tmp/'config.h').write_text('\n'.join(f'#define {k} {v}' for k,v in config.items()))
            cpp=tmp/'actual.cpp';cpp.write_text(fixture()+source_fixture()+water_producer_fixture()+CASES)
            for san in (False,True):
                exe=tmp/('san' if san else 'normal')
                args=['g++','-std=c++20','-O2','-fno-pie','-no-pie','-include',str(tmp/'config.h'),
                      '-I'+str(tmp),'-I'+str(INC),'-I'+str(gate.PLATFORM),'-I'+str(ROOT/'port/dreamcast/room')]
                if san:args+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
                run=subprocess.run(args+[str(cpp),str(ROOT/'port/dreamcast/room/pvr_geometry.cpp'),'-o',str(exe)],capture_output=True,text=True)
                self.assertEqual(run.returncode,0,run.stderr)
                run=subprocess.run([str(exe)],capture_output=True,text=True,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'))
                self.assertEqual(run.returncode,0,run.stdout+run.stderr)
                self.assertIn('EF03 packet boundaries passed:',run.stdout)


if __name__=='__main__':unittest.main()
