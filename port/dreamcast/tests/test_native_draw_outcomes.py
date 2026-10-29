"""EF03: compile actual FIFO/mesh code, source adapters and real strip caller.

Reuse the existing PVR fixture's stub/driver literals so both tests stay bound to
one packet harness. Production code is included/extracted unchanged, never a
copied outcome implementation. Public fixture input only.
"""
import ast
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
INCLUDE=ROOT/'game/platform/include'


def harness():
    tree=ast.parse((ROOT/'tests/test_effect_strip21.py').read_text())
    method=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='test_actual_clipper_packet_FIFO_failure_and_fence_pins')
    values={}
    for node in method.body:
        if isinstance(node,ast.Assign) and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str):
            for name in node.targets:
                if isinstance(name,ast.Name): values[name.id]=node.value.value
    return values['stub'],values['code'].split('int main(){',1)[0]


def function(text,signature):
    start=text.index(signature); end=text.index('{',start)+1; depth=1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}'); end+=1
    return text[start:end]


class NativeDrawOutcomes(unittest.TestCase):
    def compile_run(self,stub,code,extra=()):
        with tempfile.TemporaryDirectory(prefix='re4dc-outcomes-') as td:
            temp=Path(td); (temp/'dc').mkdir(); (temp/'dc/pvr.h').write_text(stub)
            cpp=temp/'actual.cpp'; cpp.write_text(code); exe=temp/'actual'
            args=['g++','-std=c++20','-DRE4DC_FX_STRIP21=1','-DRE4DC_CLOTH_NATIVE=1',
                  '-DRE4DC_NATIVE_DRAW_OUTCOMES=1','-DRE4DC_TA_DIRECT=1','-DRE4DC_UI_HANDLES=1',
                  '-DRE4DC_EFFECT_SPRITE_MAX=64','-fsanitize=address,undefined','-fno-pie','-no-pie',
                  '-I'+str(temp),'-I'+str(INCLUDE),'-I'+str(ROOT/'room'),*extra,
                  str(cpp),str(ROOT/'room/pvr_geometry.cpp'),'-o',str(exe)]
            build=subprocess.run(args,capture_output=True,text=True)
            self.assertEqual(build.returncode,0,build.stderr)
            run=subprocess.run([str(exe)],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)

    def test_make_control_is_strict_default_off_and_reaches_all_consumers(self):
        with tempfile.TemporaryDirectory(prefix='re4dc-outcome-make-') as td:
            temp=Path(td);mk=temp/'fixture.mk'
            targets=['obj/src/game/esp_sub.o','obj/src/game/cloth.o','obj/platform/native_ui.o']
            mk.write_text('OBJDIR := obj\ninclude '+str(ROOT/'game/effects30.mk')+'\n'+
                          '\n'.join(t+':\n\t@echo FLAGS $(GAME_CPPFLAGS) $(PLATFORM_CPPFLAGS)' for t in targets)+'\n')
            for value in (None,'0','1','2','-1'):
                args=['make','--no-print-directory','-f',str(mk),*targets,'EFFECT_SPRITES=1','FX_STRIP21=1']
                if value is not None:args+=['NATIVE_DRAW_OUTCOMES='+value]
                run=subprocess.run(args,capture_output=True,text=True,cwd=temp)
                if value in ('2','-1'):
                    self.assertNotEqual(run.returncode,0);self.assertIn('NATIVE_DRAW_OUTCOMES is 0 or 1',run.stderr)
                else:
                    self.assertEqual(run.returncode,0,run.stderr)
                    self.assertEqual(run.stdout.count('-DRE4DC_NATIVE_DRAW_OUTCOMES=1'),3 if value=='1' else 0)
            run=subprocess.run(['make','--no-print-directory','-f',str(mk),targets[0],
                                'NATIVE_DRAW_OUTCOMES=1','FX_STRIP21=0'],capture_output=True,text=True,cwd=temp)
            self.assertNotEqual(run.returncode,0);self.assertIn('NATIVE_DRAW_OUTCOMES needs FX_STRIP21=1',run.stderr)

    def test_disabled_actual_emitter_objects_match_parent_and_explicit_zero(self):
        stub,code=harness()
        # Match the production fixture without instantiating game-owned light work.
        code=code.replace('#include "native_effect_strip21.inc"', 'extern "C" void re4dc_log(const char*,...){}\n#include "native_effect_strip21.inc"')
        old=subprocess.check_output(['git','show','9ee386e3ef8d46bcd7ae8586d2064cd1ae22864e:port/dreamcast/game/platform/include/native_effect_strip21.inc'],cwd=REPO,text=True)
        with tempfile.TemporaryDirectory(prefix='re4dc-outcomes-off-') as td:
            temp=Path(td);(temp/'dc').mkdir();(temp/'dc/pvr.h').write_text(stub)
            old_dir=temp/'parent';old_dir.mkdir();(old_dir/'native_effect_strip21.inc').write_text(old)
            objects=[]
            for name,defs,first in [('parent',[],old_dir),('absent',[],INCLUDE),('zero',['-DRE4DC_NATIVE_DRAW_OUTCOMES=0'],INCLUDE)]:
                destination=temp/(name+'.o')
                command=['g++','-std=c++20','-O2','-g0','-DRE4DC_FX_STRIP21=1','-DRE4DC_CLOTH_NATIVE=1',
                         '-DRE4DC_TA_DIRECT=1','-DRE4DC_UI_HANDLES=1','-DRE4DC_EFFECT_SPRITE_MAX=64',*defs,
                         '-I'+str(temp),'-I'+str(first),'-I'+str(INCLUDE),'-I'+str(ROOT/'room'),
                         '-x','c++','-','-c','-o',str(destination)]
                build=subprocess.run(command,input=code,capture_output=True,text=True,cwd=INCLUDE)
                self.assertEqual(build.returncode,0,build.stderr);objects.append(destination.read_bytes())
            self.assertEqual(objects[0],objects[1]);self.assertEqual(objects[0],objects[2])

    def test_actual_packets_all_outcomes_and_partial_publication(self):
        stub,code=harness()
        code=code.replace('bool frame_ready=true,','bool abort_on_select=false,abort_after_send=false;\nbool frame_ready=true,')
        code=code.replace('assert(list==PVR_LIST_TR_POLY);}', 'assert(list==PVR_LIST_TR_POLY);if(abort_on_select)stream_aborted=true;}')
        code=code.replace('sent_bytes=bytes;sent_colors.push_back(', 'sent_bytes=bytes;if(abort_after_send)stream_aborted=true;sent_colors.push_back(')
        code=code.replace('#include "native_effect_strip21.inc"', r'''
extern "C" void re4dc_log(const char*,...){}
alignas(32) unsigned char tail21[2048];unsigned tail21_top=0;
bool fx_r200_tail_select(unsigned required,unsigned char*& storage,unsigned*& top){
 if(required>tail21_top)return false;storage=tail21;top=&tail21_top;return true;}
#include "native_effect_strip21.inc"
''')
        code+=r'''
using Outcome=re4dc::NativeDrawOutcome;
void fresh(){reset();sent_colors.clear();source_draws_finished=false;stream_aborted=false;direct_open=false;
 frame_ready=true;draining_parts=false;missing=false;spill_available=true;abort_on_select=abort_after_send=false;tail21_top=0;}
void expect(re4dc::NativeDrawResult r,Outcome expected,unsigned sent=0,unsigned queued=0){
 assert(r.outcome==expected && r.submitted==sent && r.queued==queued);
 assert(r.fallback_allowed()==(!r.published()&&(expected==Outcome::UnsupportedBeforePublication||expected==Outcome::Refused)));
}
Re4dcEffectMesh21 mesh(float* p,unsigned cols,unsigned rows){auto q=quad();Re4dcEffectMesh21 m{};
 m.image=q.image;m.positions=p;m.cols=cols;m.rows=rows;m.v_top=0;m.v_step=.5f;
 std::memcpy(m.projection,q.projection,sizeof m.projection);std::memcpy(m.viewport,q.viewport,sizeof m.viewport);
 m.color=q.color;m.src=q.src;m.dst=q.dst;return m;}
int main(){
 fresh();auto q=quad();expect(re4dc_effect_quad_result(&q),Outcome::Queued,0,1);
 auto* first=deferred_first;q.color=0x91827364;expect(re4dc_effect_quad_result(&q),Outcome::Queued,0,1);
 assert(deferred_count==2 && first->next==deferred_last && entry.frame==frame);
 auto* a=reinterpret_cast<pvr_vertex_t*>(reinterpret_cast<unsigned char*>(first)+kEffectQuad21Node);
 auto* b=reinterpret_cast<pvr_vertex_t*>(reinterpret_cast<unsigned char*>(first->next)+kEffectQuad21Node);
 assert(a[1].argb==0x8197a3bc && b[1].argb==0x91827364);
 fresh();q=quad();source_draws_finished=true;expect(re4dc_effect_quad_result(&q),Outcome::Submitted,1);
 assert(sent_bytes==7*32 && sent_colors.size()==1 && !deferred_count);
 fresh();q=quad();q.color=0;expect(re4dc_effect_quad_result(&q),Outcome::PolicySkip);assert(!deferred_count);
 fresh();q=quad();for(auto& p:q.positions)p[2]=1;expect(re4dc_effect_quad_result(&q),Outcome::Culled);assert(!deferred_count);
 fresh();q=quad();q.u[0]=std::numeric_limits<float>::quiet_NaN();expect(re4dc_effect_quad_result(&q),Outcome::UnsupportedBeforePublication);
 fresh();q=quad();direct_open=true;expect(re4dc_effect_quad_result(&q),Outcome::UnsupportedBeforePublication);
 fresh();q=quad();missing=true;expect(re4dc_effect_quad_result(&q),Outcome::Refused);assert(!deferred_count);
 fresh();q=quad();fx_frame=frame;fx_count=64;expect(re4dc_effect_quad_result(&q),Outcome::Refused);assert(!deferred_count);
 fresh();q=quad();deferred_top=8192;spill_available=false;expect(re4dc_effect_quad_result(&q),Outcome::Refused);assert(!deferred_count);
 fresh();q=quad();entry.package.value.width=128;expect(re4dc_effect_quad_result(&q),Outcome::UnsupportedBeforePublication);entry.package.value.width=64;
 fresh();q=quad();source_draws_finished=true;abort_on_select=true;expect(re4dc_effect_quad_result(&q),Outcome::Refused);assert(!sent_bytes);
 fresh();q=quad();source_draws_finished=true;abort_after_send=true;expect(re4dc_effect_quad_result(&q),Outcome::PartialAbort,1);assert(sent_bytes);
 // Two intact rows queue exactly once each, in source order; material and EOL stay intact.
 float p[]={-1,1,-10,1,1,-10, -1,0,-10,1,0,-10, -1,-1,-10,1,-1,-10};
 fresh();auto m=mesh(p,2,3);expect(re4dc_effect_mesh21_result(&m),Outcome::Queued,0,2);
 assert(deferred_count==2 && entry.frame==frame);
 a=reinterpret_cast<pvr_vertex_t*>(reinterpret_cast<unsigned char*>(deferred_first)+kEffectQuad21Node);
 b=reinterpret_cast<pvr_vertex_t*>(reinterpret_cast<unsigned char*>(deferred_last)+kEffectQuad21Node);
 assert(a[4].flags==PVR_CMD_VERTEX_EOL && b[4].flags==PVR_CMD_VERTEX_EOL);
 assert(a[1].v==0 && a[2].v==.5f && b[1].v==.5f && b[2].v==1);
 assert(a[0].flags==4 && a[1].argb==m.color); // header src alpha
 fresh();m=mesh(p,2,3);const unsigned rowbytes=5*32,required=kEffectQuad21Node+rowbytes;
 deferred_top=16384+required;spill_available=false;
 expect(re4dc_effect_mesh21_result(&m),Outcome::PartialAbort,0,1);
 assert(deferred_count==1 && deferred_first==deferred_last && entry.frame==frame);
 fresh();m=mesh(p,2,3);deferred_top=8192;spill_available=false;
 expect(re4dc_effect_mesh21_result(&m),Outcome::Refused);assert(!deferred_count);
 fresh();m=mesh(p,2,3);p[12]=std::numeric_limits<float>::quiet_NaN();
 expect(re4dc_effect_mesh21_result(&m),Outcome::PartialAbort,0,1);assert(deferred_count==1);p[12]=-1;
 fresh();m=mesh(p,2,3);source_draws_finished=true;abort_after_send=true;
 expect(re4dc_effect_mesh21_result(&m),Outcome::PartialAbort,1);assert(sent_colors.size()==1 && entry.frame==frame);
 fresh();m=mesh(p,2,3);m.color=0;expect(re4dc_effect_mesh21_result(&m),Outcome::PolicySkip);
 fresh();m=mesh(p,2,3);for(unsigned i=0;i<6;++i)p[3*i+2]=1;expect(re4dc_effect_mesh21_result(&m),Outcome::Culled);
 for(unsigned i=0;i<6;++i)p[3*i+2]=-10;
 // A near-clipped band publishes cells through the same quad producer. Exhaust
 // its second cell: the mesh must report partial instead of silently continuing.
 float c[]={-1,1,-.5f,0,1,-10,1,1,-10, -1,-1,-.5f,0,-1,-10,1,-1,-10};
 fresh();m=mesh(c,3,2);expect(re4dc_effect_mesh21_result(&m),Outcome::Queued,0,2);assert(deferred_count==2);
 const unsigned cellbytes=deferred_first->changed[0];
 fresh();m=mesh(c,3,2);deferred_top=16384+kEffectQuad21Node+cellbytes;spill_available=false;
 expect(re4dc_effect_mesh21_result(&m),Outcome::PartialAbort,0,1);assert(deferred_count==1 && entry.frame==frame);
 fresh();m=mesh(c,3,2);deferred_top=8192;spill_available=false;expect(re4dc_effect_mesh21_result(&m),Outcome::Refused);assert(!deferred_count);
#if defined(RE4DC_FX_R200_ENTRY_CAP) && RE4DC_FX_R200_ENTRY_CAP
 fresh();m=mesh(p,2,3);deferred_top=8192;spill_available=false;tail21_top=required;
 expect(re4dc_effect_mesh21_result(&m),Outcome::PartialAbort,0,1);
 assert(deferred_count==1 && reinterpret_cast<unsigned char*>(deferred_first)==tail21 && entry.frame==frame);
#endif
 // An accepted child followed by refusal forbids fallback even across bands.
 re4dc::NativeDrawProgress progress;assert(progress.add({Outcome::Queued,0,1}));
 assert(!progress.add({Outcome::Refused}));expect(progress.result,Outcome::PartialAbort,0,1);
}
'''
        self.compile_run(stub,code)
        self.compile_run(stub,code,('-DRE4DC_FX_R200_ENTRY_CAP=1',))

    def test_actual_strip_adapter_propagates_refusal_to_real_source_caller(self):
        source=(REPO/'src/game/esp_sub.cpp').read_text()
        start=source.index('#if defined(RE4DC_NATIVE_DRAW_OUTCOMES)',source.index('re4dc_fx_essential_strip_cut'))
        end=source.index('\n#if defined(RE4DC_EFFECT_TORCH)',start)
        adapter=source[start:end].removesuffix('#endif\n')
        eligible=function(source,'extern "C" int re4dc_esp_strip21_eligible(')
        caller_source=(REPO/'src/game/esp01.cpp').read_text()
        caller=caller_source[caller_source.index('void EspStrip_draw_poly('):caller_source.index('\n// Segment count',caller_source.index('void EspStrip_draw_poly('))]
        stub,unused=harness()
        code=r'''
#include <cassert>
#include <cstring>
#include "native_ui.h"
#include "native_draw_result.hpp"
#include "effect_strip_uv21.hpp"
using u8=unsigned char;using s8=signed char;using s16=short;using f32=float;
struct Vec{float x,y,z;};struct GXColor{u8 r,g,b,a;};GXColor s_effect_col{128,64,32,192};
struct cEsp{u8 m_Id=1,m_Parts_no=255;unsigned m_Tool_flg=0,m_Flg=0,xA4=1;
 unsigned m_Tex_id=0,m_Ptn_no=0,xA5=4,xA6=5;};
struct TEXHeader{void* data;unsigned width,height,format,wrapS,wrapT;};
struct CLUT{void* data;unsigned format,numEntries;};struct TEXDescriptor{TEXHeader* textureHeader;CLUT* CLUTHeader;};
struct Tpl{unsigned numDescriptors;};struct EspTexWk{unsigned Owner;Tpl* pTpl;float mtx[3][4];};
struct System{EspTexWk Esp_tex_tbl[1];} system_value,*g_pEspSys=&system_value;
TEXHeader header{nullptr,64,64,14,0,0};TEXDescriptor descriptor{&header,nullptr};Tpl tpl{1};
const TEXDescriptor* TEXGet(Tpl*,unsigned){return &descriptor;}
void projection(float* p){const float a[]={0,1,0,1,0,-.01f,-1.01f};std::memcpy(p,a,sizeof a);}
void viewport(float* p){const float a[]={0,0,640,480,0,1};std::memcpy(p,a,sizeof a);}
#define RE4DC_GXF_GET_PROJECTION(p) projection(p)
#define RE4DC_GXF_GET_VIEWPORT(p) viewport(p)
bool trim=false;extern "C" int re4dc_fx_essential_strip_cut(const cEsp*){return trim;}
re4dc::NativeDrawResult next_result{re4dc::NativeDrawOutcome::Queued,0,1};unsigned native_calls=0,legacy_calls=0;
Re4dcEffectQuad captured{};
extern "C" re4dc::NativeDrawResult re4dc_effect_quad_result(const Re4dcEffectQuad* q){++native_calls;captured=*q;return next_result;}
struct EspAnmData{};bool EspGetAnmAddr(unsigned,EspAnmData**){return true;}
struct Log{void err(int,int,const char*,unsigned){assert(false);}} log_value,*pLog=&log_value;
void GXBegin(unsigned,unsigned,unsigned count){assert(count==4);++legacy_calls;}
void GXMatrixIndex1u8(unsigned){}void GXPosition3f32(float,float,float){}void GXTexCoord2f32(float,float){}
'''+eligible+'\n'+adapter+caller+r'''
int main(){using Outcome=re4dc::NativeDrawOutcome;auto& w=system_value.Esp_tex_tbl[0];w.pTpl=&tpl;
 for(unsigned i=0;i<3;++i)w.mtx[i][i]=1;
 cEsp esp;Vec p[]={{-1,1,-10},{1,1,-10},{-1,-1,-10},{1,-1,-10}};
 for(auto outcome:{Outcome::Submitted,Outcome::Queued,Outcome::Culled,Outcome::PolicySkip,Outcome::PartialAbort}){
  next_result={outcome,outcome==Outcome::Submitted?1U:0U,outcome==Outcome::Queued||outcome==Outcome::PartialAbort?1U:0U};
  unsigned before=legacy_calls;EspStrip_draw_poly(&esp,0,p,2,0);assert(legacy_calls==before);
 }
 assert(captured.positions[2][0]==p[3].x&&captured.positions[3][0]==p[2].x&&captured.color==0xc0804020);
 for(auto outcome:{Outcome::Refused,Outcome::UnsupportedBeforePublication}){
  next_result={outcome};unsigned before=legacy_calls;EspStrip_draw_poly(&esp,0,p,2,0);assert(legacy_calls==before+1);
  auto result=re4dc_esp_strip21_draw_result(&esp,0,p,2,0);assert(result.outcome==outcome&&result.fallback_allowed());
 }
 unsigned before=native_calls;trim=true;auto result=re4dc_esp_strip21_draw_result(&esp,0,p,2,0);
 assert(result.outcome==Outcome::PolicySkip&&native_calls==before);trim=false;
 w.mtx[0][1]=1;result=re4dc_esp_strip21_draw_result(&esp,0,p,2,0);
 assert(result.outcome==Outcome::UnsupportedBeforePublication&&native_calls==before);
}
'''
        code=code.replace('#include <cassert>','#include <cassert>\n#include <initializer_list>')
        self.compile_run(stub,code,('-DRE4DC_FX_TRIM=1',))

    def test_actual_cloth_source_aggregates_bands_and_stops_after_failure(self):
        source=(REPO/'src/game/cloth.cpp').read_text()
        start=source.index('#if defined(RE4DC_NATIVE_DRAW_OUTCOMES)',source.index('static int re4dc_cloth_visible'))
        end=source.index('\n#endif\n\n// clothTrans builds',start)
        adapter=source[start:end]
        stub,unused=harness()
        code=r'''
#include <cassert>
#include <cstring>
#include "native_ui.h"
#include "native_draw_result.hpp"
using u32=unsigned;using f32=float;using Mtx=float[3][4];struct Vec{float x,y,z;};
struct Color{unsigned char r,g,b,a;};
struct cLight{Color DispCol;unsigned xD;float Radius;Vec World;};
struct Env{Color AmbientScr{255,255,255,255};};struct LightManager{Env e;Env* getEnvPtr(){return &e;}} LightMgr;
struct Global{struct{Mtx v_mat;}Cam;}global_value,*pG=&global_value;
struct Cloth{void* tex;void* pTobjA;unsigned divH,divV;void* tlut;unsigned x74;Color color;float Scale;Mtx mat;Vec* pVer;};
void PSMTXScale(Mtx,float,float,float){}void PSMTXConcat(const Mtx,const Mtx,Mtx){}
void PSMTXMultVec(const Mtx,const Vec* p,Vec* out){*out=*p;}
float GetDistance3(Vec*,Vec*){return 0;}
#define RE4DC_GXF_GET_PROJECTION(p) ((void)0)
#define RE4DC_GXF_GET_VIEWPORT(p) ((void)0)
using Outcome=re4dc::NativeDrawOutcome;
re4dc::NativeDrawResult results[3];unsigned calls=0;
extern "C" re4dc::NativeDrawResult re4dc_effect_mesh21_result(const Re4dcEffectMesh21* m){
 assert(m->cols==2&&m->rows==2);assert(m->v_top==calls*(1.f/3));
 assert(m->positions[0]==float(calls*2));return results[calls++];}
'''+adapter+r'''
int main(){unsigned tex[]={1,(64<<16)|64,14,0};Vec p[8];for(unsigned i=0;i<8;++i)p[i]={float(i),0,-10};
 Cloth c{};c.tex=tex;c.divH=2;c.divV=4;c.color={128,64,32,192};c.Scale=1;c.pVer=p;cLight* lights[8]{};Vec pos{};
 results[0]={Outcome::Queued,0,1};results[1]={Outcome::Refused};results[2]={Outcome::Queued,0,1};
 auto r=re4dc_cloth_native(&c,lights,&pos,1);assert(r.outcome==Outcome::PartialAbort&&r.queued==1&&!r.fallback_allowed()&&calls==2);
 calls=0;results[0]={Outcome::Refused};r=re4dc_cloth_native(&c,lights,&pos,1);
 assert(r.outcome==Outcome::Refused&&r.fallback_allowed()&&calls==1);
 calls=0;results[0]={Outcome::Culled};results[1]={Outcome::Queued,0,1};results[2]={Outcome::Queued,0,1};
 r=re4dc_cloth_native(&c,lights,&pos,1);assert(r.outcome==Outcome::Queued&&r.queued==2&&calls==3);
 calls=0;c.pTobjA=&c;r=re4dc_cloth_native(&c,lights,&pos,1);assert(r.outcome==Outcome::UnsupportedBeforePublication&&calls==0);
}
'''
        self.compile_run(stub,code)

if __name__=='__main__':unittest.main()
