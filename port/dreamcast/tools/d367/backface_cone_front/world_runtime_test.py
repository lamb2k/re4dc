#!/usr/bin/env python3
"""World caller and metadata gates, using extracted production function bodies.

The host fixture controls transform/certificate/SQ/clip boundaries to exercise
dispatch and bookkeeping; it is not execution of the renderer or SH4 assembly.
Optional --sh4-cxx/--kos-root/--sdk-root compile the complete native_static.cpp
translation unit against real headers and compare absent/0 objects to baseline.
"""
import argparse
import ctypes
import hashlib
import importlib.util
import json
import re
import struct
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
SOURCE = DC / "game/platform/native_static.cpp"


def function(text, signature):
    start = text.index(signature)
    begin = text.index("{", start)
    depth = 0
    tokens = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]')
    for match in tokens.finditer(text, begin):
        token = match.group()
        if token == "{":
            depth += 1
        elif token == "}":
            depth -= 1
            if not depth:
                return text[start:match.end()]
    raise ValueError("unclosed production function: " + signature)


def run(command, cwd, path, input=None):
    result = subprocess.run(command, cwd=cwd, input=input,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    path.write_bytes(result.stdout)
    if result.returncode:
        raise RuntimeError("%s failed (%s):\n%s" % (command[0], result.returncode, result.stdout.decode()))
    return result.stdout.decode()


HEADER = r'''
#include <algorithm>
#include <array>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <tuple>
#include <vector>
#include <dc/pvr.h>
#include "backface_emit.hpp"
#define RE4DC_CPU_BACKFACE 2
#define RE4DC_SCENERY_CONE 1
#define RE4DC_SCENERY_CONE_SIGN 1
using std::uint8_t;
static unsigned log_calls;
template<class... T> void re4dc_log(const char*,T...){++log_calls;}
namespace re4dc::room {
struct CompactVertex12 {std::uint16_t x,y,z,u,v,color;};
struct CompactBatch {float uv_bias[2],uv_scale[2];};
struct Meshlet {std::uint32_t first_vertex,first_strip,strip_bytes;std::uint16_t vertex_count,strip_count,bounds_min[3],bounds_max[3];};
struct MeshPartLod {unsigned first_cluster,cluster_count;};
struct MeshCluster {std::uint16_t bounds_min[3],bounds_max[3];unsigned first_level,level_count;};
struct MeshLevel {unsigned first_meshlet,meshlet_count;float error;};
}
namespace re4dc::render {
struct DrawBounds {float lo[3],hi[3];};
template<class... T> bool group_visible(T...){return true;}
}
struct Counts {
 unsigned input,output,vertices,strips,strips_culled,slots;
 bool operator==(const Counts&)const=default;
};
struct Statistics {
 unsigned vertices=0,strips=0,strips_culled=0,groups_visible=0,bind_rejects=0,batches=0,reserve_rejects=0;
 unsigned clusters_culled=0,clusters_visible=0,groups_culled=0,lod_draws[4]{};
} stats;
namespace lean {
constexpr unsigned kMode=2;
struct Stats {unsigned skipped=0,cl_inside=0,sg_tests=0,sg_culled=0,sg_meshlets=0,sg_vskip=0;} st;
static pvr_vertex_t* prime_at=nullptr;static unsigned primed=0;
template<class... T> unsigned box_class(T...){return 2;}
template<class... T> int box_mask(T...){return 0;}
template<class... T> void sg_coef(T...){}
template<class... T> unsigned sg_select(T...){assert(false);return 0;}
}
namespace re4dc::bf::certificate {
struct Context {bool valid;};
struct Cone {float center[3],radius,extent[3],axis[3],cos_lower,sin_upper,min_normal;};
struct Proof {bool valid;};
enum Outcome {Uncertain,Back,FrontCandidate};
@WORTH_FRONT@
@EXACT_ZERO@
@FLAT_DEPTH@
static unsigned prepares=0,classifies=0,scans=0,strict_calls=0;
static bool prepare_ok=true,projection_ok=true,strict_ok=true;
static const float* matrix_seen=nullptr;
bool prepare(Context& c,const float* m,float n){++prepares;matrix_seen=m;return c.valid=prepare_ok&&m&&n>0;}
Outcome classify(const Context&,const Cone& c,unsigned,Proof& p){++classifies;p.valid=true;return c.min_normal==1.0f?FrontCandidate:Uncertain;}
bool projected_front(const Proof&,const void*,unsigned){++scans;return projection_ok;}
bool strict_front(const void* c,const std::uint8_t* ix,unsigned n,unsigned mask,unsigned cull){
 ++strict_calls;if(!strict_ok)return false;
 auto* v=static_cast<const pvr_vertex_t*>(c);
 for(unsigned i=0;i+2<n;++i){
  const auto &a=v[ix[i]&mask],&b=v[ix[i+1]&mask],&z=v[ix[i+2]&mask];
  float area=std::fma(b.x-a.x,z.y-a.y,-((b.y-a.y)*(z.x-a.x)));
  if(i&1)area=-area;
  if(!(cull==1?area>0:area<0))return false;
 }
 return n>=3;
}
}
static const std::uint8_t* stream_start;
static std::vector<std::tuple<bool,unsigned,unsigned>> walk_calls;
static unsigned transformed;
namespace re4dc::vp {
using Vertex12=re4dc::room::CompactVertex12;
struct Constants {};
constexpr unsigned kChecksAll=3;
static const Vertex12* raw_start;
static pvr_vertex_t projected[256];static std::uint8_t projected_codes[256];
struct StripCodes {unsigned all,any;};
StripCodes codes(const std::uint8_t* oc,const std::uint8_t* ix,unsigned n){
 assert(n);unsigned all=255,any=0;for(unsigned j=0;j<n;++j){all&=oc[ix[j]];any|=oc[ix[j]];}return {all,any};
}
void prime(pvr_vertex_t* c,unsigned n){for(unsigned j=0;j<n;++j){c[j].flags=0xe0000000;c[j].oargb=0;}}
template<unsigned Checks> void transform_sched(const Vertex12* in,unsigned n,pvr_vertex_t* cache,std::uint8_t* oc,const Constants&){
 transformed+=n;const unsigned first=unsigned(in-raw_start);for(unsigned j=0;j<n;++j){cache[j]=projected[first+j];oc[j]=projected_codes[first+j];}
}
void copy(std::uint32_t*& q,const pvr_vertex_t* cache,const std::uint8_t* ix,unsigned n){
 for(unsigned j=0;j<n;++j){std::memcpy(q,cache+ix[j],32);q[0]=j+1==n?0xf0000000:0xe0000000;q+=8;}
}
const std::uint8_t* boundary_walk(bool front,const std::uint8_t* s,const std::uint8_t* end,const std::uint8_t* oc,
 const pvr_vertex_t* cache,unsigned limit,unsigned cull,std::uint32_t*& q,unsigned& culled,unsigned& emitted,unsigned& triangles){
 walk_calls.emplace_back(front,unsigned(s-stream_start),unsigned(end-stream_start));
 while(s<end){const unsigned n=*s;assert(n&&n+1<=unsigned(end-s));const auto c=codes(oc,s+1,n);
  if(c.all&3){++culled;s+=n+1;continue;}
  if((c.any&3)||n>limit)return s;
  if(c.all&0x3c)++culled;
  else{++emitted;triangles+=n-2;
   if(front)copy(q,cache,s+1,n);
   else re4dc::bf::strip(cache,s+1,n,255,cull,[&](const std::uint8_t* ix,unsigned count){copy(q,cache,ix,count);});
  }
  s+=n+1;
 }
 return s;
}
const std::uint8_t* walk_lean(const std::uint8_t* s,const std::uint8_t* end,const std::uint8_t* oc,const pvr_vertex_t* cache,
 unsigned lim,std::uint32_t*& q,unsigned& culled,unsigned& emitted){unsigned tri=0;return boundary_walk(true,s,end,oc,cache,lim,0,q,culled,emitted,tri);}
const std::uint8_t* walk_lean_sq(const std::uint8_t* s,const std::uint8_t* end,const std::uint8_t* oc,const pvr_vertex_t* cache,
 unsigned lim,unsigned cull,std::uint32_t*& q,unsigned& culled,unsigned& emitted,unsigned& tri){return boundary_walk(false,s,end,oc,cache,lim,cull,q,culled,emitted,tri);}
}
namespace cone {
static const void* pkg=nullptr;static const std::uint8_t* rec=nullptr;static const float* tab2=nullptr;
static const float* front_angles=nullptr;static const float* front_normals=nullptr;
static const std::uint16_t* front_counts=nullptr;
static unsigned tests=0,rejects=0,vskip=0,picks_dropped=0;
static unsigned front_tests=0,front_candidates=0,front_groups=0,front_vertices=0,front_bad=0;
@TRAILER@
}
extern "C" bool test_trailer(const std::uint8_t* sec,unsigned len,unsigned crc,unsigned bytes,unsigned lets,unsigned groups,unsigned sg,
 const std::uint8_t* group_records){
 const float* a=reinterpret_cast<const float*>(1);const float* n=a;
 const std::uint16_t* counts=reinterpret_cast<const std::uint16_t*>(1);
 const bool ok=cone::front_trailer(sec,len,crc,bytes,lets,groups,sg,group_records,a,n,counts);
 assert(ok?(a&&n&&counts):(!a&&!n&&!counts));return ok;
}
struct Package {
 re4dc::room::Meshlet ml[2]{};re4dc::room::MeshPartLod pl[1]{{0,1}};
 re4dc::room::MeshCluster cl[1]{{{0,0,0},{40,40,0},0,1}};
 re4dc::room::MeshLevel lv[1]{{0,1,0}};
 re4dc::room::CompactVertex12 raw[256]{};std::vector<std::uint8_t> stream;
 const auto* meshlets()const{return ml;}const auto* part_lods()const{return pl;}
 const auto* clusters()const{return cl;}const auto* levels()const{return lv;}
 const auto* strip_begin(const re4dc::room::Meshlet& l)const{return stream.data()+l.first_strip;}
};
struct Part {unsigned cull=1,material_flags=0,depth_mode=0;float projection[7]{},viewport[6]{};};
static float loaded_matrix[16];static const float* bf_loaded_screen=loaded_matrix;
static unsigned result_calls;
int re4dc_model_packet_streaming(){return 0;}
void re4dc_model_packet_commit(unsigned){}
void re4dc_model_result(unsigned,unsigned,unsigned){++result_calls;}
struct Draw {
 Part& p;Package& package;
 const unsigned* ps2=nullptr;const std::uint8_t* sg=nullptr;unsigned sg_groups=0;
 float mvq[12]{1,0,0,0,0,1,0,0,0,0,1,100},near=1,cull_far=1000,lod_scale=1;
 bool lean_inside=true,lean_part=false,sg_coef_ok=false;const float* lean_am=nullptr;float sg_coef[40]{};
 unsigned part_index=0,primed=0,limit=255,input=0,output=0,slots=0,used=0;
 bool submitted=false,streaming=false,bind_ok=true,borrow_ok=true,gather_ok=true;
 void* palette=nullptr;
 struct {float uv_bias[2]{},uv_scale[2]{};}part;
 re4dc::room::CompactBatch batch{};re4dc::vp::Constants k;
 pvr_vertex_t cache_data[256]{};std::uint8_t code_data[256]{};
 pvr_vertex_t* cache=cache_data;std::uint8_t* outcodes=code_data;
 std::uint32_t buffer[65536]{};std::uint32_t* sq=buffer;
 re4dc::bf::certificate::Context* front_context=nullptr;bool front_prepared=false,front_valid=false;
 std::vector<std::pair<unsigned,Counts>> clips;int clip_result=1;
 bool bind(){return bind_ok;}bool borrow(){return borrow_ok;}bool borrow_gather(){return gather_ok;}
 const auto* corners(const re4dc::room::Meshlet& l){return package.raw+l.first_vertex;}
 void set_clip(){}
 Counts counts()const{return {input,output,stats.vertices,stats.strips,stats.strips_culled,slots};}
 int clip_strip(const re4dc::room::CompactVertex12*,const re4dc::room::CompactBatch&,const std::uint8_t* s,unsigned n){
  clips.emplace_back(unsigned(s-stream_start),counts());if(clip_result<=0)return clip_result;
  re4dc::vp::copy(sq,cache,s,n);slots+=n;output+=n-2;++stats.strips;return 1;
 }
 @PICK@;
 @BF_ON@
 @BF_SQ@
 @LEAN_FLUSH@
 @STRIPS_LEAN@
 @SELECT@
 @FRONT_MASK@
 @EMIT_PICK@
 @CHUNK_EMIT@
};
'''

TESTS = r'''
namespace cert=re4dc::bf::certificate;
struct Fixture {
 Package package;Part part;std::uint16_t groups[32]{};std::uint8_t cones[32]{};
 std::uint16_t counts[8]{};
 float minima[4]{1,1,1,1},angles[128]{},table[64]{};Draw draw;
 static constexpr unsigned repeats=96,group_bytes=4*repeats;
 Fixture(unsigned count=4,unsigned strips=repeats,unsigned strip_length=3,unsigned range=3):draw{part,package}{
  assert(count*range<=256U&&strip_length<=255U);
  stats={};lean::st={};walk_calls.clear();transformed=0;result_calls=0;log_calls=0;
  std::fill(std::begin(loaded_matrix),std::end(loaded_matrix),0.0f);
  cert::prepares=cert::classifies=cert::scans=cert::strict_calls=0;cert::prepare_ok=cert::projection_ok=cert::strict_ok=true;
  cone::front_tests=cone::front_candidates=cone::front_groups=cone::front_vertices=cone::front_bad=0;
  for(unsigned q=0;q<count;++q){
   const unsigned v=q*range;
   for(unsigned r=0;r<strips;++r){package.stream.push_back(strip_length);
    for(unsigned j=0;j<strip_length;++j)package.stream.push_back(v+(r*strip_length+j)%range);}
   auto* g=groups+q*8;g[0]=g[1]=g[2]=0;g[3]=g[4]=40;g[5]=0;
   g[6]=(q+1)*strips*(strip_length+1);g[7]=v|((v+range-1)<<8);
   counts[2*q]=strips*strip_length;counts[2*q+1]=strips;
   cones[q*8+2]=127;cones[q*8+3]=1;
   for(unsigned k=0;k<range;++k){const unsigned i=v+k;
    re4dc::vp::projected[i]={0xe0000000U,float(q*100+(k==1?40:0)),float(k==2?40:0),1,
                           float(i+1),float(i+2),0xff112200U+i,0};
    re4dc::vp::projected_codes[i]=0;
   }
  }
  package.ml[0]={0,0,count*strips*(strip_length+1),std::uint16_t(count*range),std::uint16_t(count*strips),{0,0,0},{40,40,0}};
  draw.sg=reinterpret_cast<const std::uint8_t*>(groups);draw.sg_groups=count;
  cone::pkg=&package;cone::rec=cones;cone::front_angles=angles;cone::front_normals=minima;cone::front_counts=counts;cone::tab2=table;
  stream_start=package.stream.data();re4dc::vp::raw_start=package.raw;bf_loaded_screen=loaded_matrix;
 }
 Draw::Pick whole()const{return {0,255,0,0,0,{0,0}};}
};
struct Result {std::vector<std::uint32_t> words;Counts counts;std::vector<std::pair<unsigned,Counts>> clips;int result;};
Result execute(Fixture& f,const Draw::Pick& pk,bool proof){
 if(!proof)cone::front_normals=nullptr;
 const int result=f.draw.chunk_emit(&pk,1);
 return {{f.draw.buffer,f.draw.sq},f.draw.counts(),f.draw.clips,result};
}
void equal(const Result& a,const Result& b){assert(a.words==b.words);assert(a.counts==b.counts);assert(a.clips==b.clips);assert(a.result==b.result);}
using Setup=void(*)(Fixture&);
void compare(const char* label,Setup setup,Draw::Pick pick={0,255,0,0,0,{0,0}},int expected=1){
 Fixture baseline;setup(baseline);const auto old=execute(baseline,pick,false);
 Fixture candidate;setup(candidate);const auto now=execute(candidate,pick,true);
 equal(old,now);assert(now.result==expected);std::cout<<label<<" PASS\n";
}
void none(Fixture&){}
void output_tests(){
 compare("whole all-front",none);
 compare("whole mixed group routes",[](Fixture& f){f.minima[1]=f.minima[2]=2;});
 compare("whole all uncertain",[](Fixture& f){for(auto& n:f.minima)n=2;});
 compare("partial alternating groups",none,{0,2,5,0,8,{0,0}});
 compare("partial empty pick",none,{0,0,0,0,0,{0,0}});
 compare("all-depth cull before limit",[](Fixture& f){f.draw.limit=2;for(auto& code:re4dc::vp::projected_codes)code=1;});
 compare("depth crossing clip",[](Fixture&){re4dc::vp::projected_codes[3]=1;});
 compare("oversize before screen cull",[](Fixture& f){f.draw.limit=2;for(auto& code:re4dc::vp::projected_codes)code=4;});
 compare("all-screen cull",[](Fixture&){for(auto& code:re4dc::vp::projected_codes)code=4;});
 compare("clip failure stops later groups",[](Fixture& f){f.minima[1]=2;re4dc::vp::projected_codes[3]=1;f.draw.clip_result=-1;},{0,255,0,0,0,{0,0}},-1);
 compare("bind failure",[](Fixture& f){f.draw.bind_ok=false;},{0,255,0,0,0,{0,0}},0);
 compare("borrow failure",[](Fixture& f){f.draw.borrow_ok=false;},{0,255,0,0,0,{0,0}},0);
 compare("gather failure after submit",[](Fixture& f){f.draw.gather_ok=false;f.draw.submitted=true;},{0,255,0,0,0,{0,0}},-1);
 compare("cull none",[](Fixture& f){f.part.cull=0;});
 compare("alpha-mask guard",[](Fixture& f){f.part.material_flags=4;});
 compare("no-depth-write guard",[](Fixture& f){f.part.depth_mode=1;});
 compare("unknown projection",[](Fixture&){cert::projection_ok=false;});
 compare("unsupported transform",[](Fixture&){cert::prepare_ok=false;});
 compare("depth-varying group",[](Fixture&){loaded_matrix[3]=0.1f;});
 compare("missing loaded matrix",[](Fixture&){bf_loaded_screen=nullptr;});
 compare("uncertain group backface",[](Fixture& f){f.minima[1]=2;std::swap(re4dc::vp::projected[4],re4dc::vp::projected[5]);});
 {
  Fixture f;f.minima[1]=f.minima[2]=2;execute(f,f.whole(),true);
  constexpr unsigned B=Fixture::group_bytes;
  const std::vector<std::tuple<bool,unsigned,unsigned>> expected={{true,0,B},{false,B,3*B},{true,3*B,4*B}};
  assert(walk_calls==expected);assert(cert::prepares==1&&cert::matrix_seen==loaded_matrix);assert(transformed==12);
  assert(cone::front_groups==2&&cone::front_tests==4&&cone::front_candidates==2&&cone::front_vertices==6);
 }
 {
  Fixture f;execute(f,{0,2,5,0,8,{0,0}},true);
  constexpr unsigned B=Fixture::group_bytes;
  const std::vector<std::tuple<bool,unsigned,unsigned>> expected={{true,0,B},{true,2*B,3*B}};
  assert(walk_calls==expected);assert(transformed==9&&cone::front_groups==2&&cone::front_vertices==6);
 }
 {
  Fixture f;Draw::Pick picks[]={f.whole(),f.whole()};assert(f.draw.chunk_emit(picks,2)==1);
  assert(cert::prepares==1&&cert::classifies==8&&result_calls==1);
 }
#if RE4DC_BACKFACE_CONE_FRONT == 2
 compare("mode2 failed strict check falls back",[](Fixture&){cert::strict_ok=false;});
 {
  Fixture f;cert::strict_ok=false;execute(f,f.whole(),true);
  assert(cone::front_bad==4&&cone::front_groups==0&&log_calls==4);
  assert(std::get<0>(walk_calls.front())==false);
 }
 {
  Fixture f;f.draw.limit=2;cert::strict_ok=false;execute(f,f.whole(),true);
  assert(cert::strict_calls==0&&cone::front_bad==0); // clipping still owns oversize strips
 }
#else
 {Fixture f;execute(f,f.whole(),true);assert(cert::strict_calls==0);}
#endif
}
void metadata_tests(){
 auto rejected=[](Setup mutate){Fixture f;mutate(f);re4dc::bf::certificate::Context context{true};
  f.draw.front_context=&context;f.draw.front_valid=true;unsigned keep=0;
  assert(f.draw.front_mask(f.whole(),f.package.ml[0],f.package.stream.data(),keep)==0);};
 rejected([](Fixture&){cone::front_normals=nullptr;});
 rejected([](Fixture&){cone::front_angles=nullptr;});
 rejected([](Fixture&){cone::front_counts=nullptr;});
 rejected([](Fixture&){cone::pkg=nullptr;});
 rejected([](Fixture& f){f.draw.sg=nullptr;});
 rejected([](Fixture& f){f.draw.sg_groups=0;});
 rejected([](Fixture& f){f.draw.sg_groups=9;});
 rejected([](Fixture& f){for(unsigned i=0;i<4;++i)f.minima[i]=0;});
 rejected([](Fixture& f){for(unsigned i=0;i<4;++i)f.cones[i*8+3]=64;});
 rejected([](Fixture& f){for(unsigned i=0;i<4;++i)f.groups[i*8+7]=0xff00;});
 rejected([](Fixture& f){for(unsigned i=0;i<4;++i)f.groups[i*8]=41;});
 rejected([](Fixture& f){f.groups[6]=4*Fixture::group_bytes+1;});
 rejected([](Fixture& f){f.groups[14]=1;});
 rejected([](Fixture& f){f.groups[30]=4*Fixture::group_bytes-1;});
 std::cout<<"metadata controls PASS\n";
}
void admission_tests(){
 // These gates execute the shared header helpers and real production routing,
 // while certificate arithmetic remains a controlled boundary in this test.
 assert(cert::worth_front(64,256,64));
 assert(!cert::worth_front(2,256,64));assert(!cert::worth_front(64,255,64));
 assert(!cert::worth_front(65,256,64));assert(!cert::worth_front(64,256,63));
 auto rejected=[](unsigned strips,unsigned length,unsigned range){
  Fixture old(1,strips,length,range);const auto baseline=execute(old,old.whole(),false);
  Fixture now(1,strips,length,range);const auto candidate=execute(now,now.whole(),true);
  equal(baseline,candidate);assert(cert::prepares==0&&cert::classifies==0&&cert::scans==0);
 };
 rejected(85,3,3);    // 255 indices: insufficient work to repay setup
 rejected(63,5,3);    // 315 indices, but too few strips
 rejected(96,3,128);  // 288 indices, but cache span has insufficient reuse
 rejected(1,240,240); // a long low-reuse strip stays on the original walker
 {
  Fixture f;loaded_matrix[3]=0.1f;execute(f,f.whole(),true);
  assert(cert::prepares==0&&cert::classifies==0&&cert::scans==0);
 }
 {
  Fixture f;loaded_matrix[11]=1.0f;execute(f,f.whole(),true);
  assert(cert::prepares==1&&cone::front_groups==4); // Z extent is exactly zero
 }
 {
  Fixture f;loaded_matrix[3]=-0.0f;execute(f,f.whole(),true);
  assert(cert::prepares==1&&cone::front_groups==4);
 }
 {
  Fixture f;const std::uint32_t subnormal=1;std::memcpy(loaded_matrix+3,&subnormal,4);
  execute(f,f.whole(),true);assert(cert::prepares==0&&cert::classifies==0);
 }
 {
  Fixture f;for(unsigned q=0;q<4;++q)f.minima[q]=0;
  execute(f,f.whole(),true);assert(cert::prepares==0);
 }
 {
  Fixture f;f.draw.borrow_ok=false;execute(f,f.whole(),true);assert(cert::prepares==0);
 }
 std::cout<<"count reuse and flat-depth admission before lazy prepare PASS\n";
}
void cull_after_flush(){
 // Execute the production flush assignment for a full 48-entry queue, then
 // the complete production selector with the current key and stale record.
 for(unsigned current:{1U,2U}){
  Fixture f(1);unsigned key[6]={0,0,0,0,0,current};f.draw.ps2=key;
  for(unsigned j=0;j<48;++j){struct {unsigned cull;}x{j==47?3U-current:current};auto& part=f.part;@FLUSH_CULL@}
  assert(f.part.cull==3U-current);Draw::Pick selected[2]{};
  const unsigned count=f.draw.chunk_select(selected);
  assert(count==(current==1?0U:1U));
  // Non-PS2 callers continue to read their own part cull.
  f.draw.ps2=nullptr;f.part.cull=current;assert(f.draw.chunk_select(selected)==count);
 }
 std::cout<<"alternating cull across full shared-record flush PASS\n";
}
int main(){output_tests();metadata_tests();admission_tests();cull_after_flush();std::cout<<"world production-body host fixture PASS\n";}
'''


def host_fixture(output, source):
    out = output / "host"
    out.mkdir()
    (out / "dc").mkdir()
    (out / "dc/pvr.h").write_text("#pragma once\n#include <cstdint>\nstruct pvr_vertex_t {std::uint32_t flags;float x,y,z,u,v;std::uint32_t argb,oargb;};\nstatic_assert(sizeof(pvr_vertex_t)==32);\n")
    start = source.index("    const std::uint8_t* strips_lean(")
    start = source.rfind("#if defined(RE4DC_BACKFACE_CONE_FRONT)", 0, start)
    end = source.index("\n#endif\n#if RE4DC_MESH_STRIP_LEAN==2", start)
    helper_header = (DC / "room/backface_certificate.hpp").read_text()
    replacements = {
        "WORTH_FRONT": function(helper_header, "inline bool worth_front("),
        "EXACT_ZERO": function(helper_header, "inline bool exact_zero("),
        "FLAT_DEPTH": function(helper_header, "inline bool flat_depth("),
        "TRAILER": function(source, "bool front_trailer("),
        "PICK": function(source, "struct Pick {"),
        "BF_ON": function(source, "bool bf_on()const"),
        "BF_SQ": function(source, "const std::uint8_t* strips_bf_sq("),
        "LEAN_FLUSH": function(source, "void lean_flush("),
        "STRIPS_LEAN": source[start:end],
        "SELECT": function(source, "__attribute__((noinline)) unsigned chunk_select("),
        "FRONT_MASK": function(source, "unsigned front_mask("),
        "EMIT_PICK": function(source, "int emit_pick("),
        "CHUNK_EMIT": function(source, "__attribute__((noinline)) int chunk_emit("),
        "FLUSH_CULL": re.search(r"part\.cull=x\.cull;", source).group(),
    }
    text = HEADER + TESTS
    for name, value in replacements.items():
        text = text.replace("@" + name + "@", value)
    path = out / "world.cpp"
    path.write_text(text)
    results = []
    for mode in (1, 2):
        binary = out / ("world-mode%d" % mode)
        cmd = ["g++", "-std=c++20", "-O2", "-fno-fast-math", "-ffp-contract=off", "-Wall", "-Wextra",
               "-DRE4DC_BACKFACE_CONE_FRONT=%d" % mode, "-I" + str(out), "-I" + str(DC / "room"),
               str(path), "-o", str(binary)]
        run(cmd, ROOT, out / ("compile%d.log" % mode))
        result = run([str(binary)], ROOT, out / ("mode%d.log" % mode))
        results.append(dict(mode=mode, result=result.strip().splitlines()))
    shared = out / "world.so"
    run(["g++", "-std=c++20", "-O2", "-fPIC", "-shared", "-DRE4DC_BACKFACE_CONE_FRONT=1",
         "-I" + str(out), "-I" + str(DC / "room"), str(path), "-o", str(shared)], ROOT, out / "shared.log")
    return shared, results, {key: hashlib.sha256(value.encode()).hexdigest() for key, value in replacements.items()}


def trailer_fixture(shared, output):
    spec = importlib.util.spec_from_file_location("world_producer_fixture", HERE / "world_test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    producer = module.load_source("world_runtime_producer", module.SOURCE.read_text())
    out = output / "metadata"
    out.mkdir()
    positions = [(100, 100, 100), (140, 100, 100), (100, 140, 100)]
    paths = module.fixture(out, [(positions, [[0, 1, 2]])])
    _, r4sg, sccn, _, _, _ = producer.build_room(*paths, 1, False, front_proof=True)
    crc, size, lets, groups = struct.unpack_from("<4I", sccn)
    sg_crc, = struct.unpack_from("<I", r4sg, 28)
    base = (272 + 8 * lets * groups + 15) & ~15
    library = ctypes.CDLL(str(shared))
    check = library.test_trailer
    check.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint,
                      ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p]
    check.restype = ctypes.c_bool
    records = []

    def verify(name, data, expected=False, ids=None, group_data=r4sg[32:]):
        actual = check(data, len(data) if data is not None else 0,
                       *(ids or (crc, size, lets, groups, sg_crc)), group_data)
        assert actual == expected, (name, actual, expected)
        records.append(dict(case=name, accepted=actual))

    verify("valid producer trailer", sccn, True)
    verify("null section", None)
    verify("null group records", sccn, group_data=None)
    verify("legacy only", sccn[:base])
    for length in (0, 15, base - 1, base + 31, len(sccn) - 1):
        verify("truncated-%d" % length, sccn[:length])
    for name, offset, value in (
            ("tag", base, 0), ("version", base + 4, 2), ("length", base + 8, 0),
            ("r4sg identity", base + 12, sg_crc ^ 1), ("mesh identity", base + 16, crc ^ 1),
            ("mesh size", base + 20, size + 16), ("meshlet count", base + 24, lets + 1),
            ("group count", base + 28, groups + 1), ("prefix identity", 0, crc ^ 1),
            ("negative cosine", base + 40, 0xbf000000), ("nan sine", base + 44, 0x7fc00000),
            ("cosine one", base + 40, 0x3f800000), ("subnormal cosine", base + 40, 1),
            ("normal nonpower", base + 544, 0x3fc00000), ("negative normal", base + 544, 0xbf800000),
            ("subunit normal", base + 544, 0x3f000000), ("excess normal", base + 544, 0x50000000)):
        damaged = bytearray(sccn)
        struct.pack_into("<I", damaged, offset, value)
        verify(name, bytes(damaged))
    verify("extra trailing bytes", sccn + b"\0" * 16)
    for name, ids in (("zero groups", (crc, size, lets, 0, sg_crc)),
                      ("excess groups", (crc, size, lets, 9, sg_crc)),
                      ("overflow meshlets", (crc, size, 0xffffffff, groups, sg_crc))):
        verify(name, sccn, ids=ids)
    zero = bytearray(sccn)
    struct.pack_into("<I", zero, base + 544, 0)
    verify("disabled normal is valid metadata", bytes(zero), True)
    count_offset = base + 544 + 4 * lets * groups
    for name, indices, strips in (("count byte span mismatch", 4, 1),
                                  ("certified short strips", 2, 2),
                                  ("indices with zero strips", 4, 0),
                                  ("missing count record", 0, 0),
                                  ("zero-length strips", 0, 4)):
        damaged = bytearray(sccn)
        struct.pack_into("<HH", damaged, count_offset, indices, strips)
        verify(name, bytes(damaged))
    short = bytearray(zero)
    struct.pack_into("<HH", short, count_offset, 2, 2)
    verify("uncertified short strips retain fallback metadata", bytes(short), True)
    long_strip = bytearray(sccn)
    struct.pack_into("<HH", long_strip, count_offset, 299, 1)
    long_group = bytearray(r4sg[32:])
    struct.pack_into("<H", long_group, 12, 300)
    verify("strip count exceeds byte-count limit", bytes(long_strip), group_data=bytes(long_group))
    # The unpublished earlier SCCF draft had padding where counts now live.
    no_counts = bytearray(sccn)
    no_counts[count_offset:] = bytes(len(sccn) - count_offset)
    verify("earlier trailer without nonempty counts", bytes(no_counts))
    _, r4sg2, sccn2, _, _, _ = producer.build_room(*paths, 2, False, front_proof=True)
    crc2, size2, lets2, groups2 = struct.unpack_from("<4I", sccn2)
    sg_crc2, = struct.unpack_from("<I", r4sg2, 28)
    ids2 = (crc2, size2, lets2, groups2, sg_crc2)
    verify("empty group with zero counts", sccn2, True, ids2, r4sg2[32:])
    decreasing = bytearray(r4sg2[32:])
    struct.pack_into("<H", decreasing, 28, 3)
    verify("decreasing group end", sccn2, ids=ids2, group_data=bytes(decreasing))
    certified_empty = bytearray(sccn2)
    base2 = (272 + 8 * lets2 * groups2 + 15) & ~15
    struct.pack_into("<I", certified_empty, base2 + 548, 0x3f800000)
    verify("certified empty group", bytes(certified_empty), ids=ids2, group_data=r4sg2[32:])
    (out / "front.sccn").write_bytes(sccn)
    return records


def target_fixture(args, output):
    if not any((args.sh4_cxx, args.kos_root, args.sdk_root)):
        return dict(status="not requested")
    if not all((args.sh4_cxx, args.kos_root, args.sdk_root)):
        raise ValueError("full target TU gate needs --sh4-cxx, --kos-root and --sdk-root together")
    out = output / "target"
    out.mkdir()
    kos = args.kos_root.resolve()
    flags = ["-std=gnu++20", "-Wall", "-Wextra", "-Os", "-fno-PIC", "-fno-PIE", "-fomit-frame-pointer",
             "-m4-single", "-ml", "-mfsrra", "-mfsca", "-ffunction-sections", "-fdata-sections",
             "-matomic-model=soft-gusa", "-ftls-model=local-exec", "-fno-exceptions", "-fno-unwind-tables",
             "-fno-asynchronous-unwind-tables", "-fno-threadsafe-statics", "-D__DREAMCAST__",
             "-D_arch_dreamcast=1", "-D_arch_sub_pristine=1", "-DRE4DC_GAME"]
    for path in (kos / "include", kos / "kernel/arch/dreamcast/include", kos / "addons/include"):
        flags += ["-isystem", str(path)]
    flags += ["-I" + str(DC / "game/platform/include"), "-I" + str(args.sdk_root.resolve() / "include")]
    macros = dict(NATIVE_STATIC=1, NATIVE_MESH=1, D349_RENDERER_STACK=1, PS2_WORLD_DRAW=1,
                  PS2_WORLD_MESH=1, PS2_WORLD_ROOMS=1, MESH_LOD=1, MESH_FASTPATH=1, MESH_DIRECT=1,
                  PS2_WORLD_LEAN=2, PS2_STRIP_GROUPS=1, MESH_PRIME_LAZY=1, MESH_VP_SCHED=1,
                  MESH_STRIP_LEAN=1, HW_LEAN=1, SCENERY_CHUNK=1, SCENERY_CONE=1, SCENERY_CONE_SIGN=1,
                  CPU_BACKFACE=2, GAME_SH4ZAM=1, TA_DIRECT=1)
    flags += ["-DRE4DC_%s=%s" % pair for pair in macros.items()]
    old = subprocess.check_output(["git", "show", args.baseline + ":" + str(SOURCE.relative_to(ROOT))], cwd=ROOT)
    current = SOURCE.read_bytes()
    receipts = {}
    for label, source, extra in (("base", old, []), ("absent", current, []),
                                 ("zero", current, ["-DRE4DC_BACKFACE_CONE_FRONT=0"]),
                                 ("on1", current, ["-DRE4DC_BACKFACE_CONE_FRONT=1"]),
                                 ("on2", current, ["-DRE4DC_BACKFACE_CONE_FRONT=2"])):
        for extension, phase in (("ii", ["-E", "-P"]), ("o", ["-c"])):
            if label.startswith("on") and extension == "ii":
                continue
            destination = out / (label + "." + extension)
            command = [str(args.sh4_cxx.resolve()), *flags, *extra, "-x", "c++", "-", *phase, "-o", str(destination)]
            run(command, SOURCE.parent, out / (label + "-" + extension + ".log"), source)
            receipts[label + "." + extension] = dict(bytes=destination.stat().st_size,
                                                      sha256=hashlib.sha256(destination.read_bytes()).hexdigest())
    for extension in ("ii", "o"):
        for label in ("absent", "zero"):
            assert (out / ("base." + extension)).read_bytes() == (out / (label + "." + extension)).read_bytes()
    recipe = dict(compiler=str(args.sh4_cxx.resolve()), flags=flags, cwd=str(SOURCE.parent), baseline=args.baseline)
    (out / "recipe.json").write_text(json.dumps(recipe, indent=2) + "\n")
    return dict(status="PASS", receipts=receipts, scope="Complete native_static.cpp target translation unit, real KOS/SDK headers, no debug records; no renderer link or execution.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline", default="d1bc83cff32217a659f93acd5837a1ecc96ff6c3")
    parser.add_argument("--sh4-cxx", type=Path)
    parser.add_argument("--kos-root", type=Path)
    parser.add_argument("--sdk-root", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    output = args.output.resolve()
    source = SOURCE.read_text()
    shared, host, identities = host_fixture(output, source)
    metadata = trailer_fixture(shared, output)
    target = target_fixture(args, output)
    report = dict(source_sha256=hashlib.sha256(source.encode()).hexdigest(), extracted_sha256=identities,
                  host=host, metadata=metadata, target=target,
                  limits="Host boundary-controlled production caller bodies and actual metadata reader; math helper and SH4 SQ implementation have separate gates. Full TU compile is optional, no whole-renderer execution or timing.")
    (output / "world-runtime-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS world runtime: modes 1/2 caller routing, counters, clipping, cull-after-flush; %d metadata cases; target %s" % (len(metadata), target["status"]))


if __name__ == "__main__":
    main()
