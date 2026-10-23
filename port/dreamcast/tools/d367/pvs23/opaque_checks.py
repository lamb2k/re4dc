#!/usr/bin/env python3
"""Execute the exact read-only native_ui PVS prerequisite with cache/state stubs."""
from pathlib import Path
import tempfile
from host_checks import GAME, compile_run


def main():
    text=(GAME/'platform/native_ui.cpp').read_text()
    start=text.index('extern "C" int re4dc_pvs23_opaque_ready(')
    end=text.index('\n}\n#endif',start)+2
    body=text[start:end]
    prefix=r'''
#include <cassert>
#include <cstdint>
#include <cstring>
using pvr_ptr_t=void*;
enum {PVR_LIST_OP_POLY=0,PVR_LIST_PT_POLY=2,PVR_LIST_TR_POLY=4};
enum {PVR_FILTER_BILINEAR=1,PVR_CULLING_CW=2,PVR_CULLING_NONE=0,
PVR_DEPTHCMP_GEQUAL=6,PVR_DEPTHWRITE_ENABLE=1,PVR_BLEND_ONE=1,PVR_BLEND_ZERO=0,
PVR_TXRENV_MODULATEALPHA=2,PVR_TXRALPHA_DISABLE=0,PVR_UVCLAMP_NONE=0,PVR_FOG_TABLE=1,PVR_FOG_DISABLE=0};
struct Key {unsigned crc,fnv;bool operator==(const Key& b)const{return crc==b.crc && fnv==b.fnv;}};
struct Texture {unsigned width=64,height=64,format=0,flags=0;};
namespace re4dc::texture {constexpr unsigned kRgb565=0,kAlpha=1,kBinaryAlpha=2,kTopDrop=4;
unsigned pvr_format(const Texture& t){return t.format;}}
struct Package {
 struct H {unsigned texture_count=1;} h;
 Texture t;bool uploaded=true;pvr_ptr_t address=reinterpret_cast<void*>(32);
 bool upload_complete()const{return uploaded;}
 const H& header()const{return h;}
 const Texture* textures()const{return &t;}
 pvr_ptr_t pvr_texture(unsigned)const{return address;}
};
struct Entry {Package package;Key key{11,22};unsigned frame=10;bool valid=false;};
Entry entries[3];
bool frame_ready=true,stream_aborted=false,direct_open=false,draining_parts=false,source_draws_finished=false;
bool stream_scene=false,ui_order=false,source_binding=true,r11f_binding=true;
unsigned re4dc_ps2_sky_header=0,re4dc_ps2_check_header=0;
unsigned stream_list=0,desired_list=0,stream_closed_lists=0,model_used=0,frame=10;
void* model_packets=reinterpret_cast<void*>(32);
constexpr unsigned kModelPacketBytes=65536;
bool re4dc_source_world_binding_valid(){return source_binding;}
bool re4dc_r11f_binding_valid(){return r11f_binding;}
unsigned re4dc_ps2_world_fog(){return 1;}
struct pvr_poly_cxt_t {
 struct {unsigned culling=0,fog_type=0;} gen;
 struct {unsigned comparison=0,write=0;} depth;
 struct {unsigned src=0,dst=0;} blend;
 struct {unsigned env=0,alpha=0,uv_clamp=0;} txr;
};
struct pvr_poly_hdr_t {unsigned words[8]{};};
pvr_poly_hdr_t observed;
void pvr_poly_cxt_txr(pvr_poly_cxt_t* c,unsigned,unsigned,unsigned,unsigned,void*,unsigned){*c={};}
void pvr_poly_compile(pvr_poly_hdr_t* h,const pvr_poly_cxt_t* c){
 h->words[0]=c->gen.culling|c->gen.fog_type<<4;
 h->words[1]=c->depth.comparison|c->depth.write<<4;
 h->words[2]=c->blend.src|c->blend.dst<<4;
 h->words[3]=c->txr.env|c->txr.alpha<<4|c->txr.uv_clamp<<8;observed=*h;
}
#define RE4DC_TSP_W(t) ((t).width)
#define RE4DC_TSP_H(t) ((t).height)
constexpr unsigned kPs2HdrSets=4;
struct Slot {unsigned mode=0,crc=0,fnv=0,size=0;const Entry* entry=nullptr;void* texture=nullptr;unsigned words[4]{};};
Slot ps2_hdr[kPs2HdrSets][2];
#define RE4DC_PS2_HDR_ON true
'''
    tests=r'''
unsigned key[6]={11,22,64,64,0,2};
void reset(){
 for(auto& e:entries)e=Entry{};entries[0].valid=true;
 frame_ready=true;stream_aborted=direct_open=draining_parts=source_draws_finished=stream_scene=ui_order=false;
 stream_list=desired_list=stream_closed_lists=model_used=0;model_packets=reinterpret_cast<void*>(32);
 source_binding=r11f_binding=true;key[4]=0;key[5]=2;
 re4dc_ps2_sky_header=re4dc_ps2_check_header=0;
 for(auto& row:ps2_hdr)for(auto& slot:row)slot=Slot{};
}
int ready(){return re4dc_pvs23_opaque_ready(key,328);}
int main(){
 reset();assert(ready());Entry before=entries[0];assert(ready());assert(!std::memcmp(&before,&entries[0],sizeof(before)));
 for(unsigned i=0;i<6;++i){
  reset();bool* flags[]={&stream_aborted,&direct_open,&draining_parts,&source_draws_finished,&ui_order};
  if(i<5)*flags[i]=true;else frame_ready=false;
  assert(!ready());
 }
 reset();model_packets=nullptr;assert(!ready());
 reset();model_used=2047;assert(!ready());
 reset();assert(!re4dc_pvs23_opaque_ready(key,2048));assert(!re4dc_pvs23_opaque_ready(key,0));
 reset();desired_list=4;assert(!ready());
 reset();stream_scene=true;stream_list=4;assert(!ready());
 reset();stream_scene=true;stream_closed_lists=1;assert(!ready());
 reset();source_binding=false;assert(!ready());
 reset();r11f_binding=false;assert(!ready());
 reset();re4dc_ps2_sky_header=1;assert(!ready());
 reset();re4dc_ps2_check_header=1;assert(!ready());
 reset();entries[0].frame=9;assert(!ready());
 reset();entries[0].package.uploaded=false;assert(!ready());
 reset();entries[0].package.h.texture_count=0;assert(!ready());
 reset();entries[0].package.address=nullptr;assert(!ready());
 reset();entries[0].package.t.width=128;assert(!ready());
 reset();entries[0].package.t.format=1;assert(!ready());
 for(unsigned flag=1;flag<=4;flag<<=1){reset();entries[0].package.t.flags=flag;assert(!ready());}
 reset();entries[1].valid=true;assert(!ready());
 reset();key[4]=1;assert(!ready());
 reset();key[5]=1;assert(!ready());
#if RE4DC_PS2_WORLD_HDR_CACHE
 reset();assert(ready());
 unsigned set=(11U^(22U>>7)^(22U<<3)^(2U*0x3c1U))&(kPs2HdrSets-1U);
 Slot& slot=ps2_hdr[set][0];slot.mode=(2U<<2)|(1U<<4)|0x100U;slot.crc=11;slot.fnv=22;slot.size=64U|(64U<<16);
 slot.entry=&entries[0];slot.texture=entries[0].package.address;std::memcpy(slot.words,&observed,16);
 Slot before_slot=slot;assert(ready());assert(!std::memcmp(&before_slot,&slot,sizeof(slot)));
 slot.words[1]^=16;assert(!ready()); // depth-write mismatch
 slot.words[1]^=16;slot.entry=&entries[1];assert(!ready());
#endif
}
'''
    flags=['-DRE4DC_TA_DIRECT=1','-DRE4DC_D349_RENDERER_STACK=1','-DRE4DC_PVR_STREAM=1',
        '-DRE4DC_UI_POLY_ORDER=1','-DRE4DC_PS2_WORLD_TRANSITION_OWNER=1','-DRE4DC_PS2_WORLD_R11F_OWNER=1',
        '-DRE4DC_NATIVE_FOG=1','-DRE4DC_PS2_WORLD_FOG_SOURCE=1','-DRE4DC_LOOK_TOGGLE=1','-DRE4DC_PS2_INTERIOR_CULL=2']
    with tempfile.TemporaryDirectory(prefix='pvs23-opaque-') as td:
        for cache in (0,1):
            compile_run(Path(td),'opaque'+str(cache),prefix+body+tests,(*flags,'-DRE4DC_PS2_WORLD_HDR_CACHE='+str(cache)))
        compile_run(Path(td),'piece_state',prefix+body+'\nint main(){unsigned k[6]={11,22,64,64,0,2};assert(!re4dc_pvs23_opaque_ready(k,328));}\n',
            (*flags,'-DRE4DC_PS2_WORLD_HDR_CACHE=1','-DRE4DC_SCENERY_PIECE_STATE=1'))
    print('PASS: exact native_ui read-only eligibility body; cached/cold header controls; ASan/UBSan host only')


if __name__=='__main__':
    main()
