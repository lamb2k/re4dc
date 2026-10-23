#!/usr/bin/env python3
"""Host-execute generic proofs and actual runtime guards against private packages.

Target FPSCR read, scene identity and material readiness are controlled stubs;
the latter's exact production body has its separate opaque_checks gate.
"""
import argparse
import hashlib
import re
import tempfile
from pathlib import Path
from host_checks import GAME, NATIVE, compile_run


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--private',type=Path,default=Path('/root/re4data/private/pvs23-20261022-v1'))
    args=ap.parse_args()
    header=args.private/'certificate/pvs23_certificates.inc'
    native=NATIVE.read_text()
    pvs_start=native.index('namespace pvs {\nstruct Head')
    pvs_head=re.search(r'struct Head \{.*?\};',native[pvs_start:],re.S)[0]
    admission=re.search(r'        if\(std::memcmp\(h.magic,"R4PV",4\)\).*?        else why=nullptr;',native[pvs_start:],re.S)[0]
    caller=re.search(r'    pvs::open\(ps2w.room,[^\n]*;',native)[0]
    structs='\n'.join(re.search(r'struct '+name+r' \{[^\n]*',native)[0] for name in ('Ps2Part','Ps2Placement','Ps2Head'))
    eye=native[native.index('bool eye_of(const float* v,float e[3])',native.index('namespace pvs {\nstruct Head')):]
    eye=eye[:eye.index('\nvoid open(')]
    runtime=(GAME/'platform/include/pvs23_runtime.inc').read_text()
    start=runtime.index('unsigned fpscr(){')
    end=runtime.index('\nbool sources()',start)
    runtime=runtime[:start]+'unsigned fpscr(){return test_fpscr;}\n'+runtime[end:]
    prefix=r'''
#include <cassert>
#include <cmath>
#include <cstring>
#include <cstdint>
#include <fstream>
#include <iterator>
#include <vector>
#include <limits>
#include "pvs23_proof.hpp"
#include "pvs23_format.hpp"
#include "instanced_mesh.hpp"
#include "world_rect_provenance.h"
struct pvr_vertex_t {unsigned flags;float x,y,z,u,v;unsigned argb,oargb;};
namespace re4dc::vp {constexpr unsigned kCacheSlots=264;}
namespace re4dc::render {bool is_finite(float x){return re4dc::pvsproof::normal_or_zero(x);}}
unsigned frame_id=1,scene_id=1,test_fpscr=0;
bool live=true,material=true,scene_live=true;
unsigned bad_field=~0U;
unsigned re4dc_ui_frame(){return frame_id;}
extern "C" int re4dc_pvs23_scene(unsigned out[2]){out[0]=frame_id;out[1]=scene_id;return scene_live;}
extern "C" int re4dc_pvs23_opaque_ready(const unsigned*,unsigned){return material;}
extern "C" int re4dc_ps2_placements_intact(unsigned,const unsigned char* b,unsigned n){
 for(unsigned i=0;i<n;++i)if(unsigned(b[2*i])+(unsigned(b[2*i+1])<<8)==bad_field)return 0;
 return live;
}
std::uint32_t ps2_crc32(const unsigned char* p,unsigned n){
 unsigned c=~0U;for(unsigned i=0;i<n;++i){c^=p[i];for(unsigned b=0;b<8;++b)c=(c>>1)^(0xedb88320U&(0U-(c&1U)));}return ~c;
}
std::vector<unsigned char> read(const char* p){std::ifstream f(p,std::ios::binary);return {std::istreambuf_iterator<char>(f),{}};}
''' + structs+r'''
struct World {unsigned room=0,nplacements=0;void* storage=nullptr;re4dc::room::MeshPackage package;const Ps2Part* parts=nullptr;const Ps2Placement* placements=nullptr;} ps2w;
volatile unsigned re4dc_ps2_pvs_on=1;
namespace pvs {unsigned generation=1,pl_skipped=0,cl_skipped=0;unsigned char bit=0;const std::uint8_t* cur=&bit;bool can_cut(unsigned);
''' + eye+'\n}\n'
    call_probe='\nnamespace pvs {\n'+pvs_head+r'''
std::vector<unsigned char> caller_table;
const char* caller_reason="not called";bool caller_ok=false;unsigned caller_policy=0;
void open(unsigned room,std::uint32_t mesh_crc,std::uint32_t mesh_bytes,std::uint32_t side_crc){
    Head h{};const unsigned size=caller_table.size();assert(size>=sizeof(h));
    std::memcpy(&h,caller_table.data(),sizeof(h));const char* why=nullptr;
'''+admission+r'''
    caller_policy=side_crc;caller_reason=why;
    caller_ok=!why && re4dc_pvs23_table_guard(room,caller_table.data(),size,mesh_crc,mesh_bytes,side_crc);
}
}
void invoke_real_ps2_open_call(const Ps2Head& h,unsigned policySourceCrc){
'''+caller+'\n}\n'
    controls=r'''
void generic(){
 using namespace re4dc::pvsproof;
 Panel panel{0,0,0,0,0,{0,1,2,3,2,1}};
 pvr_vertex_t v[5]{};v[0].x=10;v[0].y=10;v[1].x=10;v[1].y=100;v[2].x=100;v[2].y=10;v[3].x=100;v[3].y=100;
 for(auto& x:v)x.z=.001f;
 std::uint8_t codes[5]={0,0x40,0x80,0xc0,0},strip[5]={4,0,1,2,3};
 assert(panel_sent(panel,v,codes,4,strip,5,2,64)); // upper outcode bits are don't-care
 codes[0]=1;assert(panel_sent(panel,v,codes,4,strip,5,2,64));codes[0]=0; // side-straddling strip is unchanged
 for(unsigned i=0;i<4;++i)codes[i]|=1;assert(!panel_sent(panel,v,codes,4,strip,5,2,64));
 for(unsigned i=0;i<4;++i)codes[i]&=0xc0;
 codes[0]=32;assert(!panel_sent(panel,v,codes,4,strip,5,2,64));codes[0]=0;
 strip[4]=0;assert(!panel_sent(panel,v,codes,4,strip,5,2,64));strip[4]=3;
 assert(!panel_sent(panel,v,codes,4,strip,4,2,64));
 assert(!panel_sent(panel,v,codes,4,strip,5,2,3)); // oversized source strip invokes CPU clipper
 std::uint8_t unrelated[9]={4,0,1,2,3,3,4,4,4};codes[4]=32;
 assert(panel_sent(panel,v,codes,5,unrelated,9,2,64));codes[4]=0; // unrelated strip may clip
 std::swap(v[1],v[2]);assert(!panel_sent(panel,v,codes,4,strip,5,2,64));assert(panel_sent(panel,v,codes,4,strip,5,0,64));
 std::swap(v[1],v[2]);v[0].x=std::numeric_limits<float>::quiet_NaN();assert(!panel_sent(panel,v,codes,4,strip,5,2,64));
 Receipts r;float k[27]{};r.sync(1,1,0x100,1,k);r.committed=3;assert(r.complete(2));
 r.sync(1,2,0x100,1,k);assert(!r.complete(2));r.committed=3;k[1]=1;r.sync(1,2,0x100,1,k);assert(!r.complete(2));
 r.committed=3;r.sync(1,2,0x100,2,k);assert(!r.complete(2));r.clear();assert(!r.complete(0));
}
int main(){
 generic();
 for(unsigned room:{0x100U,0x101U}){
  char path[512];std::snprintf(path,sizeof(path),"%s/inputs/r%03x/ps2-world.re4mesh",PRIVATE_ROOT,room);auto mesh=read(path);
  std::snprintf(path,sizeof(path),"%s/inputs/r%03x/ps2-world.r4pw",PRIVATE_ROOT,room);auto policy=read(path);
  std::snprintf(path,sizeof(path),"%s/candidate/dc/native/r%03x/ps2-world.pvs",PRIVATE_ROOT,room);auto table=read(path);
  assert(!mesh.empty() && !policy.empty() && !table.empty());
  assert(ps2w.package.adopt(mesh.data(),mesh.size(),true,true));
  const auto* h=reinterpret_cast<const Ps2Head*>(policy.data());
  ps2w.room=room;ps2w.storage=mesh.data();ps2w.nplacements=h->placements;
  ps2w.parts=reinterpret_cast<const Ps2Part*>(policy.data()+sizeof(Ps2Head));
  ps2w.placements=reinterpret_cast<const Ps2Placement*>(ps2w.parts+h->parts);
  assert(!std::memcmp(h->magic,"R4PW",4) && h->version==1 && !h->reserved[0] && !h->reserved[1]);
  assert(policy.size()==32U+16U*h->parts+52U*h->placements && h->crc==ps2_crc32(policy.data()+32,policy.size()-32));
  assert(h->parts==ps2w.package.header().part_count && h->meshes==ps2w.package.header().mesh_count);
  const unsigned policySourceCrc=re4dc::rect21::provenance::policy_source_crc(room,policy.data(),policy.size(),
      ps2w.package.header().crc,mesh.size(),h->parts,h->meshes);
  assert(policySourceCrc==(room==0x100?0x14118acdU:0x68100b21U) && policySourceCrc!=h->crc);
  pvs::caller_table=table;
  invoke_real_ps2_open_call(*h,policySourceCrc); // extracted production call, not a hand-written physical argument
  assert(pvs::caller_policy==h->crc && !pvs::caller_reason && pvs::caller_ok);
  pvs::open(room,ps2w.package.header().crc,mesh.size(),policySourceCrc);
  assert(!pvs::caller_ok && !std::strcmp(pvs::caller_reason,"physical policy crc"));
  invoke_real_ps2_open_call(*h,policySourceCrc);assert(pvs::caller_ok);
  auto load=[&](){return re4dc_pvs23_table_guard(room,table.data(),table.size(),ps2w.package.header().crc,mesh.size(),h->crc);};
  assert(load());
  table.back()^=1;assert(!load());table.back()^=1;assert(load());
  assert(!re4dc_pvs23_table_guard(room,table.data(),table.size(),1,mesh.size(),h->crc));assert(load());
  assert(!re4dc_pvs23_table_guard(room,table.data(),table.size(),ps2w.package.header().crc,mesh.size(),1));assert(load());
  float view[12]={1,0,0,0,0,1,0,0,0,0,1,0},proj[7]={0,1,0,1,0,1,100000},port[6]={0,0,640,480,0,1};
  assert(re4dc_pvs23_frame_guard(room,view,proj,port,10,100000));
  assert(!pvs::can_cut(ps2w.nplacements-1));
  test_fpscr=1U<<19;assert(!re4dc_pvs23_frame_guard(room,view,proj,port,10,100000));test_fpscr=0;
  assert(re4dc_pvs23_frame_guard(room,view,proj,port,10,100000));
  for(unsigned setting:{2U,3U,1U<<7}){test_fpscr=setting;assert(!re4dc_pvs23_frame_guard(room,view,proj,port,10,100000));}test_fpscr=1;
  assert(re4dc_pvs23_frame_guard(room,view,proj,port,10,100000));test_fpscr=0;
  proj[1]=.01f;assert(!re4dc_pvs23_frame_guard(room,view,proj,port,10,100000));proj[1]=1;
  view[0]=2;assert(!re4dc_pvs23_frame_guard(room,view,proj,port,10,100000));view[0]=1;
  view[3]=std::numeric_limits<float>::infinity();assert(!re4dc_pvs23_frame_guard(room,view,proj,port,10,100000));view[3]=0;
  assert(re4dc_pvs23_frame_guard(room,view,proj,port,10,100000));
  auto cert=proof23::cert;assert(cert && cert->npanels==2);
  for(unsigned q=0;q<cert->npanels;++q){
   const auto& p=cert->panels[q];const auto& l=ps2w.package.meshlets()[p.meshlet];
   std::vector<pvr_vertex_t> cache(l.vertex_count);std::vector<std::uint8_t> codes(l.vertex_count,0xc0);
   const auto* base=ps2w.package.vertices()+l.first_vertex;const auto* offsets=ps2w.package.indexed(l)?ps2w.package.pool_offsets(l):nullptr;
   // Synthetic interior screen transcript over the exact immutable source indices.
   // Choose a nondegenerate axis pair and orientation; this is no captured camera.
   bool found=false;
   for(unsigned axis=0;axis<3 && !found;++axis){
    unsigned ax=axis,ay=(axis+1)%3;double lo[2]={1e9,1e9},hi[2]={-1e9,-1e9};
    for(unsigned j=0;j<l.vertex_count;++j){const auto& c=base[offsets?offsets[j]:j];const unsigned xyz[3]={c.x,c.y,c.z};lo[0]=std::min(lo[0],double(xyz[ax]));hi[0]=std::max(hi[0],double(xyz[ax]));lo[1]=std::min(lo[1],double(xyz[ay]));hi[1]=std::max(hi[1],double(xyz[ay]));}
    if(hi[0]==lo[0] || hi[1]==lo[1])continue;
    for(unsigned j=0;j<l.vertex_count;++j){const auto& c=base[offsets?offsets[j]:j];const unsigned xyz[3]={c.x,c.y,c.z};cache[j].x=10+600*(xyz[ax]-lo[0])/(hi[0]-lo[0]);cache[j].y=10+440*(xyz[ay]-lo[1])/(hi[1]-lo[1]);cache[j].z=.001f;}
    if(!re4dc::pvsproof::panel_sent(p,cache.data(),codes.data(),l.vertex_count,ps2w.package.strip_begin(l),l.strip_bytes,2,64))for(auto& c:cache)c.x=640-c.x;
    found=re4dc::pvsproof::panel_sent(p,cache.data(),codes.data(),l.vertex_count,ps2w.package.strip_begin(l),l.strip_bytes,2,64);
   }
   assert(found);
   unsigned pending[3]={~0U,~0U,0},key[6]={1,2,64,64,0,2};
   re4dc_pvs23_observe(p.placement,p.part,p.meshlet,cache.data(),codes.data(),l.vertex_count,ps2w.package.strip_begin(l),l.strip_bytes,2,64,pending);
   assert((pending[2]>>q)&1U);
   const unsigned before=proof23::receipts.committed;
   material=false;re4dc_pvs23_commit(p.placement,p.part,pending,key);assert(proof23::receipts.committed==before);material=true;
   re4dc_pvs23_commit(p.placement,p.part,pending,key);assert((proof23::receipts.committed>>q)&1U);
  }
  assert(pvs::can_cut(ps2w.nplacements-1));assert(!pvs::can_cut(cert->max_placement));
  bad_field=ps2w.placements[ps2w.nplacements-1].placement;assert(!pvs::can_cut(ps2w.nplacements-1));bad_field=~0U;
  scene_id++;assert(!pvs::can_cut(ps2w.nplacements-1)); // replacement image, same frame
  proof23::receipts.committed=(1U<<cert->npanels)-1U;live=false;assert(!pvs::can_cut(ps2w.nplacements-1));live=true;
  assert(!pvs::can_cut(ps2w.nplacements-1)); // liveness refusal erased receipts
  ++frame_id;++pvs::generation;
 }
}
'''
    with tempfile.TemporaryDirectory(prefix='pvs23-proof-') as td:
        td=Path(td);(td/'kos').mkdir();(td/'kos/fs.h').write_text('#pragma once\ntypedef int file_t;\n#define FILEHND_INVALID (-1)\n')
        flags=['-I'+str(GAME.parent/'room'),'-I'+str(GAME.parent/'tools/d367/texture_rect21'),'-DRE4DC_PVS23_CERTIFICATES="'+str(header)+'"',
               '-DPRIVATE_ROOT="'+str(args.private)+'"','-DRE4DC_MESH_FASTPATH=1','-DRE4DC_MESH_DIRECT=1',
               '-DRE4DC_MESH_VP_SCHED=1','-DRE4DC_HW_LEAN=1','-DRE4DC_SCENERY_CHUNK=1',
               '-DRE4DC_SCREEN_WF=640.0f','-DRE4DC_SCREEN_HF=480.0f']
        compile_run(td,'proof',prefix+runtime+call_probe+controls,flags)
        compile_run(td,'uncertified',prefix+runtime+'\nint main(){unsigned char b[64]{};assert(!re4dc_pvs23_table_guard(0x100,b,64,1,2,3));assert(!pvs::can_cut(999));}\n',
                    [flag for flag in flags if not flag.startswith('-DRE4DC_PVS23_CERTIFICATES=')])
    print('PASS: real private mesh/table admission and actual generic guards/receipts; synthetic screen transcripts; target FPSCR/material/scene stubs')
    print('private_certificate_sha256='+hashlib.sha256(header.read_bytes()).hexdigest())


if __name__=='__main__':main()
