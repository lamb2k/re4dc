"""Bounded real Esp1b source cells through existing native quad packets.

Synthetic public controls. Device/texture boundaries are host shims, not target
ABI, FP, texture appearance, render cost or console qualification.
"""
import importlib.util
import difflib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('grid03_packets',HERE/'test_effect_outcomes03.py')
packets=importlib.util.module_from_spec(spec);spec.loader.exec_module(packets)
gate=packets.gate
ROOT,INC=gate.ROOT,gate.INCLUDE
BASE='ff5809469d5cc78bd5e24afd8851d23fa2473860' # clean automatic EF03 merge dependency


def source_fixture():
    src=(ROOT/'src/game/esp_sub.cpp').read_text()
    typed=src.index('static int EspSpriteEligible(cEsp* esp,bool')
    start=src.rfind('#if defined(RE4DC_ESP1B_GRID03)',0,typed)
    eligibility=src[start:src.index('#if RE4DC_PS2FX_DRAW',typed)]
    gen=(ROOT/'src/game/esp1b.cpp').read_text()
    def struct(source,name):
        begin=source.index('struct '+name+' {');return source[begin:source.index('};',begin)+2]
    legacy=gate.definition(src,'void Esp1b_SpTrans(cEsp* esp)')
    return r'''
#undef CHECK
#define CHECK(x) gate::check(bool(x),#x,__LINE__)
#include "effect_uv12.hpp"
using u8=unsigned char;using s8=signed char;using u32=unsigned;using f32=float;
using Mtx=float[3][4];struct Vec{float x,y,z;};struct GXColor{u8 r,g,b,a;};
struct TEXHeader{void* data;unsigned width,height,format,wrapS,wrapT;};
struct CLUT{void* data;unsigned format,numEntries;};
struct TEXDescriptor{TEXHeader* textureHeader;CLUT* CLUTHeader;};
struct TEXPalette{unsigned numDescriptors;};
struct EspTexWk{unsigned Owner=0;TEXPalette* pTpl=nullptr;Mtx mtx{};};
struct System{EspTexWk Esp_tex_tbl[1];}sys03,*g_pEspSys=&sys03;
struct Parent03{Mtx mat{};}parent03,*pEffParentWorld=&parent03;
struct cEsp{unsigned m_Id=0x1b,m_Flg=0x10,m_Parts_no=0xff,m_Tool_flg=0,m_Shimmer_type=0,m_Shimmer_pow=0;
 unsigned m_Tex_id=0,m_Ptn_no=0,m_MaskTex_id=0,xA4=1,xA5=4,xA6=5;struct{unsigned owner=0,Core_flg=0;}info;Mtx m_Mat{};
 float m_Size_base_x=1,m_Size_base_y=1,m_Size_mul=1,m_Col_a=192;Vec m_Pos{},m_Ang{};Parent03* parent=&parent03;int ChannelSet();
 alignas(4)u8 pad_EC[64]{};};
void EspCommonTrans(cEsp*);void (*EspTransTbl[256])(cEsp*)={};
TEXHeader header03{reinterpret_cast<void*>(1),64,64,4,0,0};
TEXDescriptor desc03{&header03,nullptr};TEXPalette palette03{1};
TEXDescriptor* TEXGet(TEXPalette*,unsigned){return &desc03;}
GXColor s_effect_col{128,64,32,192};
#define RE4DC_FX_FLIP_PTN(p,n) (p)
void projection03(float* out){const float p[]={0,1,0,1,0,-.01f,-1.01f};std::memcpy(out,p,sizeof p);}
void viewport03(float* out){const float v[]={0,0,640,480,0,1};std::memcpy(out,v,sizeof v);}
#define RE4DC_GXF_GET_PROJECTION(p) projection03(p)
#define RE4DC_GXF_GET_VIEWPORT(p) viewport03(p)
void PSVECSubtract(const Vec* a,const Vec* b,Vec* o){const Vec v{a->x-b->x,a->y-b->y,a->z-b->z};*o=v;}
void PSVECAdd(const Vec* a,const Vec* b,Vec* o){const Vec v{a->x+b->x,a->y+b->y,a->z+b->z};*o=v;}
void PSVECScale(const Vec* a,Vec* o,float s){const Vec v{a->x*s,a->y*s,a->z*s};*o=v;}
void PSMTXMultVec(const Mtx m,const Vec* a,Vec* o){const Vec v{
 m[0][0]*a->x+m[0][1]*a->y+m[0][2]*a->z+m[0][3],
 m[1][0]*a->x+m[1][1]*a->y+m[1][2]*a->z+m[1][3],
 m[2][0]*a->x+m[2][1]*a->y+m[2][2]*a->z+m[2][3]};*o=v;}
''' + eligibility+'\n'+gate.definition(src,'void GetPosXY(')+'\n'+struct(src,'Esp1bSpWork')+r'''
std::vector<Re4dcEffectQuad> observed03;
std::vector<re4dc::NativeDrawResult> children03;
bool oracle_only03=false;unsigned retire_after03=0;
cEsp* poison_after_first03=nullptr;
extern "C" re4dc::NativeDrawResult re4dc_effect_quad_result(const Re4dcEffectQuad* q){
 observed03.push_back(*q);
 auto result=oracle_only03?re4dc::NativeDrawResult{re4dc::NativeDrawOutcome::Culled}:native_quad03(q);
 children03.push_back(result);
 if(retire_after03 && observed03.size()==retire_after03)entries[0].valid=false;
 if(poison_after_first03 && observed03.size()==1){std::memset(poison_after_first03->pad_EC,0,sizeof poison_after_first03->pad_EC);
  for(auto& row:poison_after_first03->m_Mat)for(float& f:row)f=NAN;}
 return result;
}
#include "esp1b_grid03.inc"
struct Raw03{Vec position;float s,t;};std::vector<Raw03> raw03;Vec raw_position03;
void GXClearVtxDesc(){}void GXSetVtxDesc(int,int){}void GXSetVtxAttrFmt(int,int,int,int,int){}
void GXBegin(int primitive,int,unsigned count){CHECK(primitive==0x80);raw03.clear();raw03.reserve(count);}
void GXPosition3f32(float x,float y,float z){raw_position03={x,y,z};}
void GXNormal3s8(int x,int y,int z){CHECK(x==0 && y==1 && z==0);}
void GXTexCoord2f32(float s,float t){raw03.push_back({raw_position03,s,t});}
#undef RE4DC_ESP1B_GRID03
#define RE4DC_ESP1B_GRID03 0
''' + legacy.replace('void Esp1b_SpTrans(', 'void RawEsp1b_SpTrans(')+r'''
#undef RE4DC_ESP1B_GRID03
#define RE4DC_ESP1B_GRID03 1
''' + legacy+'\n'+struct(gen,'Esp1bWork')+r'''
struct EspGenWork{u8 Work8[1];Vec Vec0,Vec1,Vec2;};
struct cEsp1b:cEsp{Esp1bWork m_Free;int SetFreeWork(EspGenWork*,u32*);};
unsigned logged03=0;struct Log03{void err(int,int,const char*,...){++logged03;}}log03,*pLog=&log03;
static float esp1b_scale=.005f;
''' + gate.extract.function(gen,'int cEsp1b::SetFreeWork(')


def routing_fixture():
    src=(ROOT/'src/game/esp_sub.cpp').read_text()
    start=src.index('void EspCommonTrans(cEsp* esp)\n{')
    common=src[start:src.index('// Heat shimmer sprite:',start)]
    start=src.index('extern "C" int re4dc_esp_coarse_sprite_visible(')
    coarse=src[start:src.index('\n#endif\n#endif\n\n// The pulled',start)]
    return r'''
using Mtx44=float[4][4];
struct{struct{Mtx v_mat{};}Cam;unsigned Status_flg[2]{};}global03,*pG=&global03;
unsigned channel_calls03=0,flat_calls03=0;bool channel_ok03=true;
int cEsp::ChannelSet(){++channel_calls03;return channel_ok03;}
void identity03(Mtx m){std::memset(m,0,sizeof(Mtx));for(unsigned i=0;i<3;++i)m[i][i]=1;}
void concat03(const Mtx a,const Mtx b,Mtx out){Mtx t{};
 for(unsigned r=0;r<3;++r){for(unsigned c=0;c<3;++c)for(unsigned k=0;k<3;++k)t[r][c]+=a[r][k]*b[k][c];
  t[r][3]=a[r][0]*b[0][3]+a[r][1]*b[1][3]+a[r][2]*b[2][3]+a[r][3];}std::memcpy(out,t,sizeof t);}
void low_RotMatrix(Mtx m,const Vec* a){CHECK(a->x==0 && a->y==0 && a->z==0);identity03(m);}
void rot03(Mtx m,char axis,float angle){CHECK(axis=='z'||axis=='y');CHECK(angle==0);identity03(m);}
#define RE4DC_RENDER_MTXConcat(a,b,c) concat03(a,b,c)
#define RE4DC_RENDER_MTXMultVec(a,b,c) PSMTXMultVec(a,b,c)
#define RE4DC_RENDER_MTXRotRad(a,b,c) rot03(a,b,c)
#define RE4DC_RENDER_MTXInverse(a,b) (identity03(b),1)
#define ESP_PARTS_SCREEN(e) ((s8)(e)->m_Parts_no>=-8 && (s8)(e)->m_Parts_no<=-3)
#define ESPCT(i) ((void)0)
struct EspAnmData{float Cx=0,Cy=0,Width=64,Height=64;}animation03;
int EspGetAnmAddr(unsigned,EspAnmData** out){*out=&animation03;return 1;}
unsigned OtGetPrevKind(){return 0;}void CameraCurrentProjection(){}
void C_MTXOrtho(Mtx44,float,float,float,float,float,float){}void GXSetProjection(Mtx44,int){}
void EspCommonTransShimmer(cEsp*,int,unsigned){}void EspCommonTransNega(cEsp*,unsigned){}
void EspSpriteEmit(cEsp*){++flat_calls03;}
void PSMTXTranspose(const Mtx m,Mtx out){std::memcpy(out,m,sizeof(Mtx));}void GXLoadNrmMtxImm(Mtx,unsigned){}
EspTexWk* EspGetTexWk(unsigned,int){return &sys03.Esp_tex_tbl[0];}
void GXSetTevColorOp(int,int,int,int,int,int){}void GXSetAlphaUpdate(int){}
void GXSetZMode(int,int,int){}void GXSetDstAlpha(int,int){}void GXSetAlphaCompare(int,int,int,int,int){}
void GXSetNumTevStages(int){}void GXSetNumTexGens(int){}void GXCallDisplayList(const void*,unsigned){}
unsigned g_EspCommonDisplayList[24]{};float EspGetCameraPan(){return 0;}
''' + gate.extract.function(src,'extern "C" int re4dc_esp_strip21_eligible(')+'\n'+gate.extract.function(src,'extern "C" int re4dc_esp_sprite_class(')+r'''
float s_vis_far=0;
''' + coarse+'\n'+common


def legacy_fixture(source):
    fixture=source_fixture()
    prefix=fixture[:fixture.index('#if defined(RE4DC_ESP1B_GRID03)')]
    raw=fixture[fixture.index('struct Raw03{'):fixture.index('#undef RE4DC_ESP1B_GRID03')]
    start=source.index('struct Esp1bSpWork {');work=source[start:source.index('};',start)+2]
    return r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstring>
#include <vector>
namespace gate{void check(bool value,const char*,int){assert(value);}}
''' + prefix+'\n#line 1 "esp1b-legacy-fixture.cpp"\n'+gate.definition(source,'void GetPosXY(')+'\n'+work+'\n'+raw+'\n'+gate.definition(source,'void Esp1b_SpTrans(cEsp* esp)')


CASES=r'''
using O=re4dc::NativeDrawOutcome;
static cEsp fresh03(unsigned div=2){
 reset();model_packets=reinterpret_cast<pvr_vertex_t*>(gate::slab);gate::packets.clear();
 raw_sends=abort_send=0;observed03.clear();children03.clear();raw03.clear();oracle_only03=false;retire_after03=0;poison_after_first03=nullptr;
 rtt::capture_slot=-1;header03={reinterpret_cast<void*>(1),64,64,4,0,0};desc03.CLUTHeader=nullptr;
 s_effect_col={128,64,32,192};auto& tw=sys03.Esp_tex_tbl[0];tw={};tw.pTpl=&palette03;
 tw.mtx[0][0]=tw.mtx[1][1]=tw.mtx[2][2]=1;
 cEsp e;EspTransTbl[e.m_Id]=EspCommonTrans;e.m_Mat[0][0]=e.m_Mat[1][1]=e.m_Mat[2][2]=1;e.m_Mat[2][3]=-10;
 auto* w=reinterpret_cast<Esp1bSpWork*>(e.pad_EC+12);*w={div,{.4f,-.2f,.6f},{.2f,.1f,-.3f},{-.2f,.3f,.2f}};
 return e;
}
static void close03(float a,float b){CHECK(std::isfinite(a) && std::fabs(a-b)<.00001f);}
static void oracle03(cEsp& e){
 const cEsp before=e;RawEsp1b_SpTrans(&e);CHECK(std::memcmp(&before,&e,sizeof e)==0);
 oracle_only03=true;auto r=Esp1bGridDraw03(&e);CHECK(r.outcome==O::Culled && !r.published());
 CHECK(raw03.size()==4*observed03.size());const auto& m=sys03.Esp_tex_tbl[0].mtx;
 for(unsigned cell=0;cell<observed03.size();++cell){const auto& q=observed03[cell];
  CHECK(q.color==0xc0804020 && q.src==4 && q.dst==5 && !q.wrap_s && !q.wrap_t);
  for(unsigned k=0;k<4;++k){const auto& raw=raw03[4*cell+k];Vec view;PSMTXMultVec(e.m_Mat,&raw.position,&view);
   close03(q.positions[k][0],view.x);close03(q.positions[k][1],view.y);close03(q.positions[k][2],view.z);
   const float s=((m[0][0]*raw.s+m[0][1]*raw.t)+m[0][2])+m[0][3];
   const float t=((m[1][0]*raw.s+m[1][1]*raw.t)+m[1][2])+m[1][3];close03(q.u[k],s);close03(q.v[k],t);
  }
 }
 CHECK(std::memcmp(&before,&e,sizeof e)==0);
}
int main(){
 for(unsigned d:{2u,3u,64u}){auto e=fresh03(d);auto& m=sys03.Esp_tex_tbl[0].mtx;
  m[0][0]=-.7f;m[0][1]=.2f;m[0][2]=.4f;m[0][3]=-.1f;m[1][0]=.3f;m[1][1]=1.2f;m[1][2]=-.2f;m[1][3]=.6f;
  e.m_Mat[0][1]=.5f;e.m_Mat[1][2]=.7f;oracle03(e);CHECK(observed03.size()==d*d);
 }
 auto e=fresh03();auto r=Esp1bGridDraw03(&e);CHECK(r.outcome==O::Queued && r.queued==4 && observed03.size()==4);
 const auto accepted=r;std::memset(e.pad_EC,0,sizeof e.pad_EC);drain();CHECK(raw_sends>0 && accepted.queued==4);
 e=fresh03();RawEsp1b_SpTrans(&e);source_draws_finished=true;r=Esp1bGridDraw03(&e);CHECK(r.outcome==O::Submitted && r.submitted==4);
 CHECK(gate::packets.size()==4);constexpr unsigned diagonal[]={0,1,2,0,2,3};
 const auto* verts=reinterpret_cast<const pvr_vertex_t*>(gate::packets[0].bytes.data()+32);
 CHECK(gate::packets[0].bytes.size()==7*sizeof(pvr_vertex_t));
 for(unsigned i=0;i<6;++i){Vec view;PSMTXMultVec(e.m_Mat,&raw03[diagonal[i]].position,&view);
  auto q=observed03[0];re4dc::effect_strip21::project(view.x,view.y,view.z,&q);
  close03(verts[i].x,view.x);close03(verts[i].y,view.y);close03(verts[i].z,view.z);
  close03(verts[i].u,raw03[diagonal[i]].s);close03(verts[i].v,raw03[diagonal[i]].t);CHECK(verts[i].argb==0xc0804020);
 }
 e=fresh03();source_draws_finished=true;abort_send=2;r=Esp1bGridDraw03(&e);
 CHECK(r.outcome==O::PartialAbort && r.submitted==2 && observed03.size()==2 && !r.fallback_allowed());
 e=fresh03();texture_missing=true;r=Esp1bGridDraw03(&e);CHECK(r.outcome==O::Refused && !r.published() && r.fallback_allowed());
 e=fresh03();entries[0].valid=false;r=Esp1bGridDraw03(&e);CHECK(r.outcome==O::Refused && !r.published());
 e=fresh03();retire_after03=1;r=Esp1bGridDraw03(&e);CHECK(r.outcome==O::PartialAbort && r.queued==1 && observed03.size()==2);
 e=fresh03();poison_after_first03=&e;r=Esp1bGridDraw03(&e);CHECK(r.outcome==O::Queued && r.queued==4 && observed03.size()==4);
 drain();CHECK(raw_sends==4); // producer values and queued packets own their copies
 e=fresh03();deferred_top=0;model_packets=nullptr;gate::allocation_ok=false;
 r=Esp1bGridDraw03(&e);CHECK(r.outcome==O::Refused && !r.published());gate::allocation_ok=true;
 e=fresh03();deferred_top=kEffectQuad21Node+7*sizeof(pvr_vertex_t)+16384;model_packets=nullptr;gate::allocation_ok=false;
 r=Esp1bGridDraw03(&e);CHECK(r.outcome==O::PartialAbort && r.queued==1 && observed03.size()==2);gate::allocation_ok=true;
 e=fresh03();r=Esp1bGridDraw03(&e);reset_deferred();drain();CHECK(r.queued==4 && !raw_sends);
 e=fresh03(64);r=Esp1bGridDraw03(&e);
 CHECK(r.outcome==O::PartialAbort && r.queued>0 && r.queued<=RE4DC_EFFECT_SPRITE_MAX && observed03.size()==r.queued+1);
 e=fresh03();rtt::capture_slot=0;r=Esp1bGridDraw03(&e);
 CHECK(r.outcome==O::UnsupportedBeforePublication && !r.published() && raw_sends==0 && deferred_count==0);
 e=fresh03();fx_frame=frame;fx_count=RE4DC_EFFECT_SPRITE_MAX-1;r=Esp1bGridDraw03(&e);
 CHECK(r.outcome==O::PartialAbort && r.queued==1 && observed03.size()==2);
 for(unsigned d:{0u,1u,65u,0xffffffffu}){e=fresh03(d);r=Esp1bGridDraw03(&e);CHECK(r.outcome==O::UnsupportedBeforePublication && observed03.empty());}
 e=fresh03();reinterpret_cast<Esp1bSpWork*>(e.pad_EC+12)->p3.z=NAN;r=Esp1bGridDraw03(&e);
 CHECK(r.outcome==O::UnsupportedBeforePublication && observed03.empty());
 e=fresh03();e.m_Mat[0][0]=NAN;r=Esp1bGridDraw03(&e);CHECK(r.outcome==O::UnsupportedBeforePublication && observed03.empty());
 for(unsigned flag:{0x40u,0x2000u,0x4000u,0x10000u,0x100000u,0x200000u,0x8000u,0x800000u}){
  e=fresh03();e.m_Tool_flg=flag;r=Esp1bGridDraw03(&e);CHECK(r.outcome==O::UnsupportedBeforePublication && observed03.empty());
 }
 e=fresh03();e.info.owner=0x23;r=Esp1bGridDraw03(&e);CHECK(r.outcome==O::UnsupportedBeforePublication && observed03.empty());
 e=fresh03();e.m_Parts_no=0xfd;r=Esp1bGridDraw03(&e);CHECK(r.outcome==O::UnsupportedBeforePublication && observed03.empty());
 for(unsigned fmt:{0u,5u,8u}){e=fresh03();header03.format=fmt;r=Esp1bGridDraw03(&e);CHECK(r.outcome==O::UnsupportedBeforePublication && observed03.empty());}
 e=fresh03();header03.wrapS=1;r=Esp1bGridDraw03(&e);CHECK(r.outcome==O::UnsupportedBeforePublication && observed03.empty());
 e=fresh03();sys03.Esp_tex_tbl[0].mtx[1][2]=NAN;r=Esp1bGridDraw03(&e);CHECK(r.outcome==O::UnsupportedBeforePublication && observed03.empty());
 e=fresh03();sys03.Esp_tex_tbl[0].mtx[0][0]=3e38f;sys03.Esp_tex_tbl[0].mtx[0][3]=1e38f;
 r=Esp1bGridDraw03(&e);CHECK(r.outcome==O::PartialAbort && r.queued==1 && observed03.size()==1 && !r.fallback_allowed());
 e=fresh03();s_effect_col.a=1;r=Esp1bGridDraw03(&e);CHECK(r.outcome==O::PolicySkip && observed03.empty());
 e=fresh03();e.m_Tool_flg=0x20080;s_effect_col={128,64,32,1};r=Esp1bGridDraw03(&e);
 CHECK(r.outcome==O::Queued && observed03[0].color==0x04ffff80);
 e=fresh03();e.m_Mat[0][0]=e.m_Mat[1][1]=0;r=Esp1bGridDraw03(&e);CHECK(r.outcome==O::Culled && !r.published());
 e=fresh03();e.m_Mat[2][3]=-1.95f;r=Esp1bGridDraw03(&e);
 CHECK(r.complete() && r.published() && r.queued<4 && children03.size()==4); // mixed culled/near-clipped cells
 e=fresh03();Esp1b_SpTrans(&e);CHECK(raw03.empty() && deferred_count==4);
 e=fresh03();identity03(parent03.mat);identity03(pG->Cam.v_mat);e.m_Pos.z=-10;
 EspTransTbl[e.m_Id]=EspCommonTrans;CHECK(re4dc_esp_sprite_class(&e)==1);
 e.m_Pos.x=1e6f;CHECK(re4dc_esp_coarse_sprite_visible(&e)==1); // no flat billboard bound
 e.m_Col_a=0;CHECK(re4dc_esp_coarse_sprite_visible(&e)==0);e.m_Col_a=192;e.m_Pos.x=0;
 channel_calls03=flat_calls03=0;EspCommonTrans(&e);
 CHECK(channel_calls03==1 && flat_calls03==0 && observed03.size()==4 && raw03.empty());
 e=fresh03();e.m_Pos.z=-10;channel_calls03=0;channel_ok03=false;EspCommonTrans(&e);
 CHECK(channel_calls03==1 && observed03.empty());channel_ok03=true;
 e=fresh03();e.m_Pos.z=-10;e.m_Tool_flg=0x4000;channel_calls03=0;EspCommonTrans(&e);
 CHECK(channel_calls03==0 && observed03.empty() && re4dc_esp_sprite_class(&e)==0);
 e=fresh03();e.m_Pos.z=-10;source_draws_finished=true;abort_send=2;channel_calls03=flat_calls03=0;EspCommonTrans(&e);
 CHECK(channel_calls03==1 && flat_calls03==0 && observed03.size()==2 && raw03.empty());
 for(unsigned byte=0;byte<256;++byte){cEsp1b generated;EspGenWork gen{};gen.Work8[0]=u8(byte);gen.Vec0={2,-3,4};gen.Vec1={4,5,6};gen.Vec2={-1,2,3};u32 seed=42;
  CHECK(generated.SetFreeWork(&gen,&seed)==1 && seed==42 && (generated.m_Flg&0x10));
  const int n=int(s8(byte))+4;CHECK(generated.m_Free.n==std::max(2,std::min(64,n)));
  close03(generated.m_Free.Vec0.x,.01f);close03(generated.m_Free.Vec1.y,.025f);close03(generated.m_Free.Vec2.z,.015f);
 }
 std::printf("Esp1b actual source/native boundaries passed: %u assertions\n",gate::assertions);
}
'''


class Esp1bGrid03(unittest.TestCase):
    def test_legacy_GetPosXY_SpTrans_absent_zero_host_objects(self):
        old=gate.production('src/game/esp_sub.cpp',BASE);current=gate.production('src/game/esp_sub.cpp')
        with tempfile.TemporaryDirectory(prefix='esp1b-grid-off-') as td:
            tmp=Path(td);outputs=[]
            for name,source,defs in (('base',old,[]),('absent',current,[]),('zero',current,['-DRE4DC_ESP1B_GRID03=0'])):
                obj=tmp/(name+'.o');code=legacy_fixture(source)
                run=subprocess.run(['g++','-std=c++20','-O2','-g0','-ffp-contract=off','-I'+str(INC),*defs,
                    '-x','c++','-','-c','-o',str(obj)],input=code,capture_output=True,text=True)
                self.assertEqual(run.returncode,0,run.stderr);outputs.append(obj.read_bytes())
            self.assertEqual(outputs[0],outputs[1]);self.assertEqual(outputs[0],outputs[2])

    def test_full_source_absent_zero_identity_and_macro_guards(self):
        common=['g++','-std=gnu++20','-fpermissive','-w','-E','-P','-DRE4DC_GAME',
         '-DRE4DC_EFFECT_SPRITES=1','-DRE4DC_EFFECT_LEAN=1','-DRE4DC_FX_STRIP21=1','-DRE4DC_NATIVE_DRAW_OUTCOMES=1',
         '-include',str(INC/'re4dc_prelude.h'),'-I'+str(ROOT/'include'),'-I'+str(ROOT/'src'),'-I'+str(INC),'-iquote',str(ROOT/'src/game')]
        for name in ('esp_sub.cpp','esp1b.cpp'):
            old=gate.production('src/game/'+name,BASE);current=gate.production('src/game/'+name)
            for target in (False,True):
                outputs=[];args=common+(['-D__sh__'] if target else [])
                for source,defs in ((old,[]),(current,[]),(current,['-DRE4DC_ESP1B_GRID03=0'])):
                    run=subprocess.run(args+defs+['-x','c++','-'],input=source,capture_output=True,text=True,cwd=ROOT)
                    self.assertEqual(run.returncode,0,run.stderr);outputs.append(run.stdout)
                self.assertTrue(outputs[0]==outputs[1],name+'\n'+'\n'.join(list(difflib.unified_diff(outputs[0].splitlines(),outputs[1].splitlines()))[:60]))
                self.assertEqual(outputs[0],outputs[2],name)
                if name=='esp_sub.cpp':
                    run=subprocess.run(args+['-DRE4DC_ESP1B_GRID03=1','-x','c++','-'],input=current,capture_output=True,text=True,cwd=ROOT)
                    self.assertEqual(run.returncode,0,run.stderr)
                    self.assertIn('Esp1bGridDraw03',run.stdout)
                    for missing in ('EFFECT_LEAN','EFFECT_SPRITES','FX_STRIP21','NATIVE_DRAW_OUTCOMES'):
                        run=subprocess.run(args+['-DRE4DC_ESP1B_GRID03=1','-DRE4DC_'+missing+'=0','-x','c++','-'],input=current,capture_output=True,text=True,cwd=ROOT)
                        self.assertNotEqual(run.returncode,0,missing)
                        self.assertIn('ESP1B_GRID03 needs',run.stderr)

    def test_primary_make_strict_selector_scope_and_dependencies(self):
        with tempfile.TemporaryDirectory(prefix='esp1b-grid-make-') as td:
            kos=Path(td);(kos/'Makefile.rules').write_text('')
            targets=['obj/src/game/esp_sub.o','obj/src/game/esp1b.o','obj/src/game/cloth.o','obj/platform/native_ui.o','obj/src/game/esp01.o']
            common=['make','--no-print-directory','-f','Makefile','-n','KOS_BASE='+str(kos),*targets,
                    'EFFECT_SPRITES=1','EFFECT_LEAN=1','FX_STRIP21=1','NATIVE_DRAW_OUTCOMES=1']
            outputs=[]
            def run(extra):return subprocess.run(common+extra,capture_output=True,text=True,cwd=ROOT/'port/dreamcast/game')
            for value in (None,'0','1'):
                r=run([] if value is None else ['ESP1B_GRID03='+value]);self.assertEqual(r.returncode,0,r.stderr)
                lines=[s for s in r.stdout.splitlines() if s.startswith('kos-c++')];self.assertEqual(len(lines),5);outputs.append(lines)
            self.assertEqual(outputs[0],outputs[1])
            for i,line in enumerate(outputs[2]):self.assertEqual(line.count('-DRE4DC_ESP1B_GRID03=1'),int(i==0))
            for value in ('','2','-1','%','0%','1%','0 1','1 ','0 ','1\t','$(subst x, ,x)1'):
                r=run(['ESP1B_GRID03='+value]);self.assertNotEqual(r.returncode,0,value);self.assertIn('ESP1B_GRID03',r.stderr)
            for missing in ('EFFECT_SPRITES','EFFECT_LEAN','FX_STRIP21','NATIVE_DRAW_OUTCOMES'):
                r=run(['ESP1B_GRID03=1',missing+'=0']);self.assertNotEqual(r.returncode,0,missing)

    def test_actual_source_GX_oracle_producer_native_packets_and_failures(self):
        with tempfile.TemporaryDirectory(prefix='esp1b-grid03-') as td:
            tmp=Path(td);(tmp/'dc').mkdir()
            (tmp/'dc/pvr.h').write_text(gate.PVR_STUB.replace('PVR_LIST_OP_POLY=0,','PVR_ALPHA_ENABLE=1,PVR_UVCLAMP_NONE=0,PVR_LIST_OP_POLY=0,'))
            defs=dict(gate.CONFIG,RE4DC_NATIVE_DRAW_OUTCOMES=1,RE4DC_PVR_RTT=1,RE4DC_WATER_PS2=1,RE4DC_ESP1B_GRID03=1,RE4DC_EFFECT_LEAN=1)
            (tmp/'config.h').write_text('\n'.join(f'#define {k} {v}' for k,v in defs.items()))
            code=packets.fixture().replace('re4dc_effect_quad_result','native_quad03')+source_fixture()+routing_fixture()+CASES
            cpp=tmp/'actual.cpp';cpp.write_text(code)
            for san in (False,True):
                exe=tmp/('san' if san else 'normal')
                args=['g++','-std=c++20','-O2','-ffp-contract=off','-fno-pie','-no-pie','-include',str(tmp/'config.h'),
                 '-I'+str(tmp),'-I'+str(INC),'-I'+str(gate.PLATFORM),'-I'+str(ROOT/'port/dreamcast/room')]
                if san:args+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
                run=subprocess.run(args+[str(cpp),str(ROOT/'port/dreamcast/room/pvr_geometry.cpp'),'-o',str(exe)],capture_output=True,text=True)
                self.assertEqual(run.returncode,0,run.stderr)
                run=subprocess.run([str(exe)],capture_output=True,text=True,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
                self.assertEqual(run.returncode,0,run.stdout+run.stderr)


if __name__=='__main__':unittest.main()
