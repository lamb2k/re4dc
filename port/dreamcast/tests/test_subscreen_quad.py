"""Source inventory tiles/lines: clipping, state binding and queue ownership."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[3]

def body(source,signature):
    start=source.index(signature);p=source.index('{',start)+1;depth=1
    while depth:
        depth+=(source[p]=='{')-(source[p]=='}');p+=1
    return source[start:p]

class SubscreenQuad(unittest.TestCase):
    def test_actual_geometry_and_queue(self):
        source=(ROOT/'port/dreamcast/game/platform/native_ui.cpp').read_text()
        native=body(source,'static int subscreen_submit(')+"\n"+body(source,'extern "C" int re4dc_subscreen_quad(')+"\n"+body(source,'extern "C" int re4dc_subscreen_line(')
        stub=r"""
#pragma once
#include <cstddef>
#include <cstdint>
struct pvr_vertex_t{std::uint32_t flags;float x,y,z,u,v;std::uint32_t argb,oargb;};
struct pvr_poly_hdr_t{std::uint32_t words[8];};
enum pvr_blend_mode_t {PVR_BLEND_ZERO=0,PVR_BLEND_ONE=1,PVR_BLEND_SRCALPHA=4,PVR_BLEND_INVSRCALPHA=5};
enum {PVR_LIST_TR_POLY=2,PVR_CULLING_NONE=0,PVR_SHADE_FLAT=0,PVR_FOG_DISABLE=2,PVR_DEPTHCMP_GEQUAL=3,PVR_DEPTHCMP_ALWAYS=7,PVR_DEPTHWRITE_DISABLE=1};
struct pvr_poly_cxt_t{struct{unsigned culling,shading,fog_type;}gen;struct{unsigned comparison,write;}depth;struct{pvr_blend_mode_t src,dst;}blend;};
#define PVR_CMD_VERTEX 0xe0000000U
#define PVR_CMD_VERTEX_EOL 0xf0000000U
inline int pvr_prim(const void*,std::size_t){return 0;}
"""
        code=r"""
#include "subscreen_quad_geometry.hpp"
#include <algorithm>
#include <cassert>
#include <cstring>
#include <limits>
#include <new>
bool frame_ready=true,stream_aborted=false,draining_parts=false,source_draws_finished=false;
unsigned dropped,nquad,deferred_count,frame_queue_peak,frame_queue_drops;
struct DeferredLighting{};
struct DeferredPart{DeferredPart* next;DeferredLighting* lighting;unsigned changed[2];};
DeferredPart* deferred_first=nullptr;DeferredPart* deferred_last=nullptr;
DeferredLighting* const kSubscreenQuadTag=reinterpret_cast<DeferredLighting*>(4);
constexpr unsigned kSubscreenQuadNode=(sizeof(DeferredPart)+31)&~31U;
alignas(32) unsigned char frame_storage[32768],spill[1024],sent[1024];
unsigned deferred_top=sizeof(frame_storage),deferred_spill_top,deferred_spill_capacity,sent_bytes;
unsigned char* deferred_spill=nullptr;bool spill_available=true;
void* re4dc_model_deferred_storage(unsigned* n){*n=spill_available?sizeof(spill):0;return spill_available?spill:nullptr;}
void stream_select(unsigned list){assert(list==PVR_LIST_TR_POLY);}
void stream_send(const void* data,unsigned bytes){assert(bytes<=sizeof(sent));std::memcpy(sent,data,bytes);sent_bytes=bytes;}
void pvr_poly_cxt_col(pvr_poly_cxt_t* c,unsigned list){assert(list==PVR_LIST_TR_POLY);*c={};}
void pvr_poly_compile(pvr_poly_hdr_t* out,const pvr_poly_cxt_t* c){
    *out={};out->words[0]=c->blend.src;out->words[1]=c->blend.dst;
    out->words[2]=c->depth.comparison;out->words[3]=c->depth.write;
    out->words[4]=c->gen.fog_type;out->words[5]=c->gen.culling;
}
"""+native+r"""
Re4dcSubscreenQuad quad(){
    // Source strip: upper right, upper left, lower right, lower left.
    Re4dcSubscreenQuad q{{{1,1,-10},{-1,1,-10},{1,-1,-10},{-1,-1,-10}},
        {0,1,0,1,0,-.01f,-1.01f},{0,0,640,480,0,1},0x4080c060,2,0};
    return q;
}
int main(){
    auto q=quad();pvr_vertex_t v[12];auto n=re4dc::subscreen::vertices(q,v);
    assert(n==6);assert(v[0].x==352 && v[0].y==216 && v[0].z==.1f);
    for(unsigned i=0;i<n;++i){assert(v[i].argb==0x604080c0);assert(v[i].flags==(i%3==2?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX));}
    const unsigned blend_src[]={1,4,4,1},blend_dst[]={0,5,1,1};
    source_draws_finished=true;
    for(unsigned b=0;b<4;++b)for(unsigned z=0;z<2;++z){
        q=quad();q.blend=b;q.depth_test=z;assert(re4dc_subscreen_quad(&q));
        const auto* h=reinterpret_cast<const pvr_poly_hdr_t*>(sent);
        assert(h->words[0]==blend_src[b] && h->words[1]==blend_dst[b]);
        assert(h->words[2]==(z?PVR_DEPTHCMP_GEQUAL:PVR_DEPTHCMP_ALWAYS));
        assert(h->words[3]==PVR_DEPTHWRITE_DISABLE && h->words[4]==PVR_FOG_DISABLE);
    }
    q=quad();q.positions[0][2]=0;q.positions[1][2]=0;
    n=re4dc::subscreen::vertices(q,v);assert(n>0 && n<=12);
    for(unsigned i=0;i<n;++i)assert(std::isfinite(v[i].x) && std::isfinite(v[i].y) && v[i].z>0);
    q=quad();for(auto& p:q.positions)p[2]=1;assert(!re4dc::subscreen::vertices(q,v));
    q=quad();for(auto& p:q.positions)p[0]+=100;assert(!re4dc::subscreen::vertices(q,v));
    q=quad();for(auto& p:q.positions)p[2]=-1000;assert(!re4dc::subscreen::vertices(q,v));
    q=quad();q.positions[0][0]=std::numeric_limits<float>::quiet_NaN();assert(!re4dc::subscreen::vertices(q,v));
    q=quad();q.projection[0]=1;assert(!re4dc::subscreen::vertices(q,v));
    q=quad();q.blend=4;assert(!re4dc_subscreen_quad(&q));
    // Inventory lines reuse the same packet queue and source color/depth.
    q=quad();q.positions[0][1]=q.positions[1][1]=0;
    n=re4dc::subscreen::line_vertices(q,6,v);assert(n==4);
    assert(v[0].x==352 && v[0].y==239.5f && v[1].y==240.5f);
    assert(v[2].x==288 && v[3].flags==PVR_CMD_VERTEX_EOL);
    for(unsigned i=0;i<n;++i)assert(v[i].argb==0x604080c0);
    assert(re4dc_subscreen_line(&q,12));
    assert(sent_bytes==5*sizeof(pvr_vertex_t));
    const auto* line=reinterpret_cast<const pvr_vertex_t*>(sent)+1;
    assert(line[0].y==239 && line[1].y==241);
    assert(!re4dc_subscreen_line(&q,0) && !re4dc_subscreen_line(&q,256));
    q.positions[0][2]=0;assert(re4dc::subscreen::line_vertices(q,6,v)==4);
    for(unsigned i=0;i<4;++i)assert(std::isfinite(v[i].x) && std::isfinite(v[i].y) && v[i].z>0);
    q=quad();q.positions[1][2]=-200;assert(re4dc::subscreen::line_vertices(q,6,v)==4);
    q=quad();for(unsigned i=0;i<2;++i)q.positions[i][2]=1;assert(!re4dc::subscreen::line_vertices(q,6,v));
    q=quad();for(unsigned i=0;i<2;++i)q.positions[i][0]+=100;assert(!re4dc::subscreen::line_vertices(q,6,v));
    q=quad();for(unsigned j=0;j<3;++j)q.positions[1][j]=q.positions[0][j];assert(!re4dc::subscreen::line_vertices(q,6,v));
    q=quad();q.positions[1][0]=std::numeric_limits<float>::infinity();assert(!re4dc::subscreen::line_vertices(q,6,v));
    // Fully copied packet: producer geometry, colour and state can retire.
    source_draws_finished=false;q=quad();assert(re4dc_subscreen_quad(&q));
    auto* first=deferred_first;assert(first && first==deferred_last && deferred_count==1);
    unsigned char copy[1024];unsigned bytes=first->changed[0];
    const auto* data=reinterpret_cast<const unsigned char*>(first)+kSubscreenQuadNode;
    std::memcpy(copy,data,bytes);std::memset(&q,0,sizeof(q));assert(!std::memcmp(copy,data,bytes));
    q=quad();assert(re4dc_subscreen_quad(&q));assert(first->next==deferred_last && deferred_count==2);
    // Existing bounded spill, then explicit refusal when no storage remains.
    deferred_top=0;assert(re4dc_subscreen_quad(&q));assert(deferred_spill==spill);
    deferred_spill_top=0;spill_available=false;auto* tail=deferred_last;
    assert(!re4dc_subscreen_quad(&q));assert(deferred_last==tail && dropped==1);
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'dc').mkdir();(p/'dc/pvr.h').write_text(stub)
            cpp=p/'test.cpp';cpp.write_text(code);exe=p/'test'
            subprocess.run(['g++','-std=c++20','-O1','-fsanitize=address,undefined',
                '-fno-omit-frame-pointer','-I'+str(p),'-I'+str(ROOT/'port/dreamcast/game/platform/include'),
                str(cpp),str(ROOT/'port/dreamcast/room/pvr_geometry.cpp'),'-o',str(exe)],check=True)
            subprocess.run([str(exe)],check=True)


    def test_source_binding_and_powerpc_guard(self):
        rel='src/Sscrn/ss_item_draw.cpp'
        current=(ROOT/rel).read_text()
        baseline=subprocess.check_output(['git','show','c2fd317afbaa82c9430fb1164061c621237b5581:'+rel],cwd=ROOT,text=True)
        signature='void ss_Draw_tile3d_local(Vec* a, Vec* b, Vec* c, Vec* d, Mtx mtx, u32 color, u32 blend, int zupd)\n'
        stub=r"""
#include "native_ui.h"
#include <cassert>
#include <cstring>
#include <iostream>
using u8=unsigned char;using u32=unsigned;using Mtx=float[3][4];
struct Vec{float x,y,z;};
unsigned native_calls,gx_begins,line_calls,line_width;Re4dcSubscreenQuad captured{},captured_line{};
struct SsLinePrim{Vec a,b;unsigned color;int width,blend,zupd;};
struct Global{struct Camera{Mtx v_mat;}Cam;}global;Global* pG=&global;
float proj[7]={0,1.3f,.1f,1.7f,.2f,-.01f,-1.01f};
float viewport[6]={10,20,640,480,0,1};
void PSMTXMultVec(Mtx m,const Vec* p,Vec* v){
    v->x=m[0][0]*p->x+m[0][1]*p->y+m[0][2]*p->z+m[0][3];
    v->y=m[1][0]*p->x+m[1][1]*p->y+m[1][2]*p->z+m[1][3];
    v->z=m[2][0]*p->x+m[2][1]*p->y+m[2][2]*p->z+m[2][3];
}
void GXGetProjectionv(float* p){std::memcpy(p,proj,sizeof(proj));}
void GXGetViewportv(float* p){std::memcpy(p,viewport,sizeof(viewport));}
extern "C" int re4dc_subscreen_quad(const Re4dcSubscreenQuad* q){captured=*q;++native_calls;return 1;}
extern "C" int re4dc_subscreen_line(const Re4dcSubscreenQuad* q,unsigned width){captured_line=*q;line_width=width;++line_calls;return 1;}
template<typename... T>void record(const char* name,T... v){std::cout<<name;((std::cout<<' '<<+v),...);std::cout<<'\n';}
#define GX_STUB(name) template<typename... T>void name(T... v){record(#name,v...);}
GX_STUB(GXSetBlendMode) GX_STUB(CameraCurrentProjection) GX_STUB(GXSetCullMode)
GX_STUB(GXSetNumChans) GX_STUB(GXSetChanCtrl) GX_STUB(GXSetZMode)
GX_STUB(GXSetNumTexGens) GX_STUB(GXSetNumTevStages) GX_STUB(GXSetTevOrder)
GX_STUB(GXSetTevOp) GX_STUB(GXClearVtxDesc) GX_STUB(GXSetVtxDesc)
GX_STUB(GXSetVtxAttrFmt) GX_STUB(GXSetCurrentMtx) GX_STUB(GXPosition3f32) GX_STUB(GXColor4u8)
void GXLoadPosMtxImm(Mtx m,unsigned n){record("GXLoadPosMtxImm",n);for(int i=0;i<3;++i)for(int j=0;j<4;++j)record("matrix",m[i][j]);}
void GXBegin(unsigned a,unsigned b,unsigned c){++gx_begins;record("GXBegin",a,b,c);}
void GXSetLineWidth(u8 width,int offset){record("GXSetLineWidth",width,offset);}
"""
        main=r"""
int main(){
    Vec p[4]={{1,2,3},{-4,5,-6},{7,-8,9},{-10,11,-12}};
    const auto original=p[0];
    Mtx m={{2,3,4,5},{6,7,8,9},{10,11,12,13}};
    for(unsigned blend=0;blend<4;++blend)for(int depth=0;depth<2;++depth){
        ss_Draw_tile3d_local(p,p+1,p+2,p+3,m,0x4080c060,blend,depth);
#if defined(RE4DC_GAME) && !defined(__PPC__)
        assert(native_calls==blend*2+depth+1 && gx_begins==0);
        for(unsigned i=0;i<4;++i){Vec v;PSMTXMultVec(m,p+i,&v);assert(captured.positions[i][0]==v.x && captured.positions[i][1]==v.y && captured.positions[i][2]==v.z);}
        assert(!std::memcmp(captured.projection,proj,sizeof(proj)));
        assert(!std::memcmp(captured.viewport,viewport,sizeof(viewport)));
        assert(captured.color==0x4080c060 && captured.blend==blend && captured.depth_test==unsigned(depth));
#else
        assert(!native_calls && gx_begins==blend*2+depth+1);
#endif
    }
    assert(!std::memcmp(&p[0],&original,sizeof(Vec)));
    std::cout<<"BEGIN_LINES\n";
    std::memcpy(pG->Cam.v_mat,m,sizeof(m));unsigned expected_calls=0;
    for(int width:{0,1,6,12,255,256,-1})for(int blend=0;blend<4;++blend)for(int depth=0;depth<2;++depth){
        SsLinePrim line{p[0],p[1],0x20406080,width,blend,depth};
        ss_Draw_line3d_trans(&line);++expected_calls;
#if defined(RE4DC_GAME) && !defined(__PPC__)
        assert(line_calls==expected_calls && line_width==static_cast<u8>(width));
        for(unsigned i=0;i<2;++i){Vec v;PSMTXMultVec(m,p+i,&v);assert(captured_line.positions[i][0]==v.x && captured_line.positions[i][1]==v.y && captured_line.positions[i][2]==v.z);}
        assert(captured_line.color==line.color && captured_line.blend==unsigned(blend) && captured_line.depth_test==unsigned(depth));
        assert(!std::memcmp(captured_line.projection,proj,sizeof(proj)));
        assert(!std::memcmp(captured_line.viewport,viewport,sizeof(viewport)));
#else
        assert(line_calls==0);
#endif
    }
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);outputs=[]
            for label,source,defines in (
                ('baseline',baseline,[]),('ppc',current,[]),
                ('ppc_game',current,['-DRE4DC_GAME','-D__PPC__']),
                ('dreamcast',current,['-DRE4DC_GAME'])):
                cpp=p/(label+'.cpp')
                line=body(source,'void ss_Draw_line3d_local(Vec* a, Vec* b, Mtx mtx, u32 color, u32 blend, int zupd)\n')
                callback=body(source,'static void ss_Draw_line3d_trans(SsLinePrim* p)\n')
                cpp.write_text(stub+body(source,signature)+line+callback+main);exe=p/label
                subprocess.run(['g++','-std=c++20','-O1','-fsanitize=address,undefined',
                    '-fno-omit-frame-pointer','-I'+str(ROOT/'port/dreamcast/game/platform/include'),
                    *defines,str(cpp),'-o',str(exe)],check=True)
                outputs.append(subprocess.check_output([str(exe)],text=True))
            self.assertEqual(outputs[0],outputs[1]);self.assertEqual(outputs[0],outputs[2])
            tiles,lines=outputs[0].split('BEGIN_LINES\n')
            common='\n'.join(line for line in tiles.splitlines()
                             if not line.startswith(('GXBegin','GXPosition3f32','GXColor4u8')))+'\n'
            self.assertEqual(common+'BEGIN_LINES\n'+lines,outputs[3])


class ExaminePublication(unittest.TestCase):
    def test_reused_examine_texture_buffer_is_rekeyed(self):
        source=(ROOT/'port/dreamcast/game/platform/native_ui.cpp').read_text()
        ss=(ROOT/'src/Sscrn/ss_main.cpp').read_text()
        start=ss.index('    case 4: {',ss.index('void SsItemExamine::move('))
        end=ss.index('        m->modelInit(wk->pItemBin, wk->pItemTpl);',start)+len('        m->modelInit(wk->pItemBin, wk->pItemTpl);')
        publish=ss[start+len('    case 4: {'):end]
        keys=source[source.index('unsigned image_size('):source.index('void close_entry(',source.index('unsigned image_size('))]
        reset=body(source,'inline void sources_reset()')
        invalidate=body(source,'extern "C" void re4dc_ui_invalidate_sources()')
        code=r"""
#include "native_ui.h"
#include <cassert>
#include <cstdint>
#include <type_traits>
struct Key{unsigned crc,fnv;bool operator==(const Key& b)const{return crc==b.crc&&fnv==b.fnv;}};
struct Source{Re4dcUiImage image;Key key;};
constexpr unsigned kSourceCount=128,kTextureCount=448;
Source sources[kSourceCount];unsigned nsource,handle_clock=1,handle_reset=1,plans_reset;
struct Identity{int lookup(const void*,unsigned,unsigned,unsigned,unsigned&,unsigned&,const void*=nullptr,unsigned=0xffffffffU,unsigned=0)const{return 0;}};
Identity room_identities,core_identities,option_identities,player_identities,weapon_identities;
struct EnemyIdentity{void* archive=nullptr;Identity table;};EnemyIdentity enemy_identities[4];
unsigned identity_hits;void re4dc_log(const char*,...){}
void re4dc_model_reset_draw_plans(){++plans_reset;}
""".replace('const void*=','const void* =')+keys+reset+'\n'+invalidate+r"""
struct Vec{float x,y,z;};unsigned init_count;
struct cMap{void* bin;void* tpl;void modelInit(void* b,void* t){bin=b;tpl=t;++init_count;}};
struct SUB_SCREEN{cMap* p_exam_model;void* pItemBin;void* pItemTpl;};
void publish(SUB_SCREEN* wk){
"""+publish+r"""
}
int main(){
 unsigned char pixels[32];for(unsigned i=0;i<32;++i)pixels[i]=i;
 Re4dcUiImage image{pixels,nullptr,8,4,1,0xffffffffU,0};Key first{},stale{},fresh{};
 assert(image_key(image,first));assert(nsource==1);
 // A new item overwrites the same source TPL address and dimensions.
 for(unsigned i=0;i<32;++i)pixels[i]=255-i;
 assert(image_key(image,stale));assert(stale==first); // reproduce old identity
 cMap model{};int bin;SUB_SCREEN wk{&model,&bin,pixels};
 const unsigned old_clock=handle_clock;publish(&wk);
 assert(init_count==1&&model.bin==&bin&&model.tpl==pixels);
#if defined(RE4DC_GAME) && !defined(__PPC__)
 assert(!nsource&&handle_clock==old_clock+1&&handle_reset==handle_clock&&plans_reset==1);
 assert(image_key(image,fresh));assert(!(fresh==first));
 // Subsequent items and repeat examination retain the same lifecycle rule.
 pixels[0]^=0x37;publish(&wk);assert(image_key(image,stale));assert(!(stale==fresh));
 publish(&wk);assert(image_key(image,fresh));assert(stale==fresh&&init_count==3);
#else
 assert(nsource==1&&handle_clock==old_clock&&plans_reset==0); // original PPC call sequence
#endif
}
"""
        with tempfile.TemporaryDirectory() as d:
            path=Path(d);cpp=path/'examine.cpp';cpp.write_text(code);exe=path/'examine'
            for defines in (['-DRE4DC_GAME=1'],['-D__PPC__=1'],['-DRE4DC_GAME=1','-D__PPC__=1']):
                subprocess.run(['g++','-std=c++17','-DRE4DC_COPY_LEAN=1','-fsanitize=address,undefined','-fno-pie','-no-pie',*defines,'-I'+str(ROOT/'port/dreamcast/game/platform/include'),str(cpp),'-o',str(exe)],check=True)
                subprocess.run([str(exe)],check=True)

if __name__=='__main__':unittest.main()
