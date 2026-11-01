"""Compare the adapter to the actual recovered GX strip function, not a copied oracle."""
from pathlib import Path
import re,subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]

class EffectStrip21(unittest.TestCase):
    def test_UV_and_corner_order_match_actual_source_all_mirrors_slices_and_signed_cast(self):
        source=(REPO/'src/game/esp01.cpp').read_text();start=source.index('void EspStrip_draw_poly(');stop=source.index('\n// Segment count',start);function=source[start:stop]
        prefix=r'''#include <cassert>
#include <cstring>
#include <cstdio>
#include "effect_strip_uv21.hpp"
using f32=float;using u8=unsigned char;using s16=short;
struct Vec {float x,y,z;};struct EspAnmData {};
struct cEsp {int m_Tex_id;unsigned m_Tool_flg;};
struct Log {void err(int,int,const char*,int){assert(false);}} log_value,*pLog=&log_value;
struct Captured {Vec p;float u,v;} captured[4];unsigned cursor;
bool EspGetAnmAddr(int,EspAnmData**){return true;}
void GXBegin(int primitive,int,unsigned n){assert(primitive==0x80&&n==4);cursor=0;}
void GXMatrixIndex1u8(int i){assert(i==0);}
void GXPosition3f32(float x,float y,float z){captured[cursor].p={x,y,z};}
void GXTexCoord2f32(float u,float v){captured[cursor].u=u;captured[cursor].v=v;++cursor;}
'''
        main=r'''
int main(){Vec corners[]={{1,2,-10},{3,4,-20},{5,6,-30},{7,8,-40}};unsigned count=0;
 for(unsigned repeat=1;repeat<=255;++repeat)for(int no=0;no<int(repeat);++no)
 for(unsigned flag=0;flag<2;++flag)for(unsigned mirror=0;mirror<4;++mirror){
  cEsp esp{0,mirror*2};EspStrip_draw_poly(&esp,no,corners,(u8)repeat,flag);
  re4dc::effect_strip21::UV uv[4];assert(re4dc::effect_strip21::source_uv(no,(u8)repeat,flag,esp.m_Tool_flg,uv));
  constexpr unsigned order[]={0,1,3,2};assert(cursor==4);
  for(unsigned i=0;i<4;++i){assert(!memcmp(&captured[i].p,&corners[order[i]],sizeof(Vec)));
   assert(!memcmp(&captured[i].u,&uv[i].u,sizeof(float)));assert(!memcmp(&captured[i].v,&uv[i].v,sizeof(float)));}++count;
 }
 re4dc::effect_strip21::UV uv[4];assert(!re4dc::effect_strip21::source_uv(0,0,0,0,uv));
 assert(count==261120);printf("%u source comparisons\n",count);
}
'''
        with tempfile.TemporaryDirectory(prefix='re4dc-strip21-') as temp:
            temp=Path(temp);cpp=temp/'oracle.cpp';cpp.write_text(prefix+function+main);exe=temp/'oracle'
            build=subprocess.run(['g++','-std=c++17','-O2','-ffp-contract=off','-I'+str(ROOT/'game/platform/include'),str(cpp),'-o',str(exe)],capture_output=True,text=True)
            self.assertEqual(build.returncode,0,build.stderr)
            run=subprocess.run([str(exe)],capture_output=True,text=True);self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertIn('261120 source comparisons',run.stdout)

    def test_actual_clipper_packet_FIFO_failure_and_fence_pins(self):
        native=(ROOT/'game/platform/native_ui.cpp').read_text();start=native.index('        if(deferred_first->lighting==kEffectQuad21Tag)');end=native.index('{',start)+1;depth=1
        while depth:depth+=(native[end]=='{')-(native[end]=='}');end+=1
        drain=native[start:end]
        stub=r'''#pragma once
#include <cstdint>
#include <cstddef>
struct pvr_vertex_t{std::uint32_t flags;float x,y,z,u,v;std::uint32_t argb,oargb;};
struct pvr_poly_hdr_t{std::uint32_t words[8];};
enum pvr_blend_mode_t{PVR_BLEND_ZERO=0,PVR_BLEND_ONE=1,PVR_BLEND_SRCALPHA=4,PVR_BLEND_INVSRCALPHA=5};
using pvr_uv_clamp_t=unsigned;
enum {PVR_LIST_TR_POLY=2,PVR_CULLING_NONE=0,PVR_DEPTHCMP_GEQUAL=3,PVR_DEPTHWRITE_DISABLE=1,
 PVR_TXRENV_MODULATEALPHA=1,PVR_TXRALPHA_ENABLE=1,PVR_UVCLAMP_U=1,PVR_UVCLAMP_V=2,PVR_FILTER_BILINEAR=1};
struct pvr_poly_cxt_t{struct{unsigned culling,fog_type;}gen;struct{unsigned comparison,write;}depth;
 struct{pvr_blend_mode_t src,dst;}blend;struct{unsigned env,alpha,uv_clamp;}txr;};
#define PVR_CMD_VERTEX 0xe0000000U
#define PVR_CMD_VERTEX_EOL 0xf0000000U
inline int pvr_prim(const void*,std::size_t){return 0;}
'''
        code=r'''
#include <algorithm>
#include <cassert>
#include <cstring>
#include <limits>
#include <new>
#include <vector>
#include "native_ui.h"
#include <dc/pvr.h>
bool frame_ready=true,stream_aborted=false,draining_parts=false,direct_open=false,source_draws_finished=false;
unsigned frame=71,fx_frame=0,fx_count=0,fx_capped=0,fx_missing=0,fx_direct=0,fx_queued=0,fx_peak=0,fx_dropped=0;
unsigned nquad=0,deferred_count=0,frame_queue_peak=0,drops=0,opens=0;
struct DeferredLighting{};struct DeferredPart{DeferredPart* next;DeferredLighting* lighting;unsigned changed[2];};
DeferredPart* deferred_first=nullptr;DeferredPart* deferred_last=nullptr;
alignas(32) unsigned char frame_storage[32768],spill[2048],sent[2048];
unsigned deferred_top=sizeof(frame_storage),deferred_spill_top=0,deferred_spill_capacity=0,sent_bytes=0;
unsigned char* deferred_spill=nullptr;bool spill_available=true,missing=false;std::vector<unsigned> sent_colors;
struct Texture{unsigned width=64,height=64;};
struct Package{Texture value;const Texture* textures(){return &value;}void* pvr_texture(unsigned){return spill;}};
struct Entry{Package package;unsigned frame=0;} entry;
namespace re4dc::texture {unsigned pvr_format(const Texture&){return 0x40000000;}}
#define RE4DC_COVER_W(p,w) (w)
#define RE4DC_COVER_H(p,h) (h)
#define RE4DC_TSP_W(t) ((t).width)
#define RE4DC_TSP_H(t) ((t).height)
#define RE4DC_FX_QUEUE_MARGIN 8192
#define RE4DC_FQ_DROP(a,b) (++drops)
Entry* resolve(const Re4dcUiImage&,const void* mask,bool pin){assert(!mask&&pin);++opens;return missing?nullptr:&entry;}
void* re4dc_model_deferred_storage(unsigned* n){*n=spill_available?sizeof(spill):0;return spill_available?spill:nullptr;}
void stream_select(unsigned list){assert(list==PVR_LIST_TR_POLY);}
void stream_send(const void* data,unsigned bytes){assert(bytes<=sizeof(sent));std::memcpy(sent,data,bytes);sent_bytes=bytes;sent_colors.push_back(reinterpret_cast<const pvr_vertex_t*>(data)[1].argb);}
void gcasset_fx_stream_send(const void* p,unsigned n){stream_send(p,n);}
void pvr_poly_cxt_txr(pvr_poly_cxt_t* c,unsigned list,unsigned fmt,unsigned w,unsigned h,const void* ptr,unsigned filter){
 assert(list==PVR_LIST_TR_POLY&&fmt==0x40000000&&w==64&&h==64&&ptr==spill&&filter==PVR_FILTER_BILINEAR);*c={};}
void pvr_poly_compile(pvr_poly_hdr_t* p,const pvr_poly_cxt_t* c){*p={};p->words[0]=c->blend.src;p->words[1]=c->blend.dst;
 p->words[2]=c->depth.comparison;p->words[3]=c->depth.write;p->words[4]=c->txr.uv_clamp;p->words[5]=c->txr.alpha;p->words[6]=c->txr.env;}
#include "native_effect_strip21.inc"
Re4dcEffectQuad quad(){Re4dcEffectQuad q{};q.image={spill,nullptr,64,64,14,0xffffffffU,0};
 const float p[4][3]={{-1,1,-10},{1,1,-20},{1,-1,-30},{-1,-1,-40}};std::memcpy(q.positions,p,sizeof p);
 for(unsigned i=0;i<4;++i){q.u[i]=float(i)*.2f;q.v[i]=float(i)*.3f;}
 const float projection[]={0,1,0,1,0,-.01f,-1.01f},viewport[]={0,0,640,480,0,1};
 std::memcpy(q.projection,projection,sizeof projection);std::memcpy(q.viewport,viewport,sizeof viewport);
 q.color=0x8197a3bc;q.src=4;q.dst=5;q.wrap_s=1;q.wrap_t=0;return q;}
void reset(){deferred_top=sizeof frame_storage;deferred_first=deferred_last=nullptr;deferred_count=0;
 deferred_spill=nullptr;deferred_spill_top=deferred_spill_capacity=0;sent_bytes=0;fx_count=0;entry.frame=0;}
int main(){auto q=quad();pvr_vertex_t v[12];unsigned n=re4dc::effect_strip21::vertices(q,v);assert(n==6);
 constexpr unsigned order[]={0,1,2,0,2,3};for(unsigned i=0;i<6;++i){const unsigned k=order[i];assert(v[i].z==1.0f/-q.positions[k][2]);
 assert(v[i].u==q.u[k]&&v[i].v==q.v[k]&&v[i].argb==q.color);}
 assert(re4dc_effect_quad(&q));auto* first=deferred_first;assert(first&&first==deferred_last&&entry.frame==frame&&deferred_count==1);
 q.color=0x91827364;assert(re4dc_effect_quad(&q));assert(first->next==deferred_last&&deferred_count==2);
 const auto* bytes=reinterpret_cast<const unsigned char*>(first)+kEffectQuad21Node;
 const auto* header=reinterpret_cast<const pvr_poly_hdr_t*>(bytes);assert(header->words[0]==4&&header->words[1]==5);
 assert(header->words[2]==PVR_DEPTHCMP_GEQUAL&&header->words[3]==PVR_DEPTHWRITE_DISABLE);
 assert(header->words[4]==PVR_UVCLAMP_V&&header->words[5]==1&&header->words[6]==PVR_TXRENV_MODULATEALPHA);
 auto* vertices=reinterpret_cast<const pvr_vertex_t*>(bytes+32);assert(vertices[0].argb==0x8197a3bc);
 drain();assert(sent_colors.size()==2&&sent_colors[0]==0x8197a3bc&&sent_colors[1]==0x91827364);
 q.positions[0][2]=-.5f;n=re4dc::effect_strip21::vertices(q,v);assert(n>0&&n<=12);for(unsigned i=0;i<n;++i)assert(v[i].z>0&&v[i].argb==q.color);
 reset();q=quad();source_draws_finished=true;assert(re4dc_effect_quad(&q));assert(sent_bytes==7*32&&entry.frame==frame&&!deferred_count);
 reset();source_draws_finished=false;deferred_top=8192;spill_available=false;unsigned dropped=fx_dropped;
 assert(!re4dc_effect_quad(&q));assert(fx_dropped==dropped+1&&drops==1&&!deferred_count&&!stream_aborted&&!sent_bytes);
 reset();spill_available=true;deferred_top=8192;assert(re4dc_effect_quad(&q));assert(deferred_first>=reinterpret_cast<DeferredPart*>(spill)&&deferred_first<reinterpret_cast<DeferredPart*>(spill+sizeof spill));
 reset();missing=true;assert(!re4dc_effect_quad(&q)&&!deferred_count&&!stream_aborted);missing=false;
 reset();entry.package.value.width=128;assert(!re4dc_effect_quad(&q)&&!deferred_count);entry.package.value.width=64;
 reset();q.u[0]=std::numeric_limits<float>::quiet_NaN();unsigned oldopens=opens;assert(re4dc_effect_quad(&q)&&opens==oldopens&&!deferred_count);
 reset();q=quad();direct_open=true;assert(!re4dc_effect_quad(&q)&&!deferred_count);direct_open=false;
 q.positions[0][2]=q.positions[1][2]=q.positions[2][2]=q.positions[3][2]=1;assert(re4dc_effect_quad(&q)&&!deferred_count);
}
'''
        code=code.replace('Re4dcEffectQuad quad(){','void drain(){while(deferred_first){'+drain+'}}\nRe4dcEffectQuad quad(){')
        with tempfile.TemporaryDirectory(prefix='re4dc-strip21-packet-') as temp:
            temp=Path(temp);(temp/'dc').mkdir();(temp/'dc/pvr.h').write_text(stub);cpp=temp/'packet.cpp';cpp.write_text(code);exe=temp/'packet'
            args=['g++','-std=c++20','-DRE4DC_FX_STRIP21=1','-DRE4DC_TA_DIRECT=1','-DRE4DC_UI_HANDLES=1','-DRE4DC_EFFECT_SPRITE_MAX=64','-fsanitize=address,undefined','-fno-pie','-no-pie','-I'+str(temp),'-I'+str(ROOT/'game/platform/include'),'-I'+str(ROOT/'room'),str(cpp),str(ROOT/'room/pvr_geometry.cpp'),'-o',str(exe)]
            build=subprocess.run(args,capture_output=True,text=True);self.assertEqual(build.returncode,0,build.stderr)
            run=subprocess.run([str(exe)],capture_output=True,text=True);self.assertEqual(run.returncode,0,run.stdout+run.stderr)

    def test_actual_source_coarse_dispatch_keeps_strip_callback_and_rejects_special_state(self):
        def body(source,signature):
            start=source.index(signature);i=source.index('{',start)+1;depth=1
            while depth:depth+=(source[i]=='{')-(source[i]=='}');i+=1
            return source[start:i]
        source=(REPO/'src/game/esp_sub.cpp').read_text()
        eligible=body(source,'extern "C" int re4dc_esp_strip21_eligible(')
        classify=body(source,'extern "C" int re4dc_esp_sprite_class(')
        dispatch=body((REPO/'src/game/esp.cpp').read_text(),'        if (spriteEntry) {')
        code=r'''#include <cassert>
using s8=signed char;
struct cEsp{unsigned char m_Id,m_Parts_no;unsigned m_Tool_flg,m_Flg,xA4;};
void EspCommonTrans(cEsp*){}void strip01(cEsp*){}void strip02(cEsp*){};
using Callback=void(*)(cEsp*);Callback EspTransTbl[256];
bool EspSpriteEligible(cEsp*){return false;}
int visible_calls=0;bool re4dc_esp_coarse_sprite_visible(cEsp*){++visible_calls;return false;}
'''+eligible+classify+'''\nCallback dispatch(cEsp* esp){Callback trans=EspTransTbl[esp->m_Id];bool spriteEntry=true;for(unsigned once=0;once<1;++once){\n'''+dispatch+'''\nreturn trans;}return nullptr;}\n'''+r'''
int main(){cEsp esp{1,255,0,0,1};EspTransTbl[1]=strip01;EspTransTbl[2]=strip02;
 for(unsigned id:{1U,2U}){esp.m_Id=id;
#if RE4DC_FX_STRIP21
 assert(re4dc_esp_sprite_class(&esp));assert(dispatch(&esp)==EspTransTbl[id]);assert(!visible_calls);
#else
 assert(!re4dc_esp_sprite_class(&esp));assert(!dispatch(&esp));
#endif
 }
#if RE4DC_FX_STRIP21
 esp.m_Tool_flg=0x40;assert(!re4dc_esp_sprite_class(&esp));assert(!dispatch(&esp));esp.m_Tool_flg=0x10000;assert(!re4dc_esp_sprite_class(&esp));
 esp.m_Tool_flg=0;esp.m_Parts_no=0xf8;assert(!re4dc_esp_sprite_class(&esp));esp.m_Parts_no=255;esp.xA4=2;assert(!re4dc_esp_sprite_class(&esp));
#endif
}
'''
        code=code.replace('#include <cassert>','#include <cassert>\n#include <initializer_list>')
        with tempfile.TemporaryDirectory(prefix='re4dc-strip21-dispatch-') as temp:
            temp=Path(temp);cpp=temp/'dispatch.cpp';cpp.write_text(code);exe=temp/'dispatch'
            for enabled in (0,1):
                build=subprocess.run(['g++','-std=c++17','-DRE4DC_FX_STRIP21='+str(enabled),str(cpp),'-o',str(exe)],capture_output=True,text=True)
                self.assertEqual(build.returncode,0,build.stderr)
                run=subprocess.run([str(exe)],capture_output=True,text=True);self.assertEqual(run.returncode,0,run.stdout+run.stderr)

    def test_deferred_tag_is_unique_in_native_UI_and_all_owned_includes(self):
        files=[ROOT/'game/platform/native_ui.cpp',*list((ROOT/'game/platform/include').glob('*.inc'))]
        hits=[(p.name,m.group(1)) for p in files for m in re.finditer(r'(\w+)\s*=\s*reinterpret_cast<DeferredLighting\*>\(0x5354\)',p.read_text())]
        self.assertEqual(hits,[('native_effect_strip21.inc','kEffectQuad21Tag')])

if __name__=='__main__':unittest.main()
