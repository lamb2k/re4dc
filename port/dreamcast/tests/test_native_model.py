"""Source primitive transport: endian, source pose/camera, cull, clipping,
whole-part rollback and copied-packet ownership. Does not accept appearance."""
from pathlib import Path
import shutil,subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[3]
@unittest.skipUnless(shutil.which("g++"),"host compiler required")
class NativeModel(unittest.TestCase):
 def test_source_pose_packet_boundary(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/"dc").mkdir()
   (root/"dc/pvr.h").write_text("#pragma once\n#include <cstddef>\n#include <cstdint>\nstruct pvr_vertex_t{std::uint32_t flags;float x,y,z,u,v;std::uint32_t argb,oargb;};\nstruct pvr_poly_hdr_t{std::uint32_t words[8];};\n#define PVR_CMD_VERTEX 0xe0000000U\n#define PVR_CMD_VERTEX_EOL 0xf0000000U\nint pvr_prim(const void*,std::size_t);\n")
   code=r"""
#include "native_model.h"
#include "pvr_geometry.hpp"
#include "native_draw_plan.hpp"
#include <cassert>
#include <cmath>
#include <cstring>
#include <vector>
#include <random>
extern "C" void re4dc_model_submit_reference(const Re4dcModelPart*);
extern "C" void re4dc_model_test_serial(unsigned);
std::vector<std::uint32_t> plan_storage,local_storage;
std::vector<unsigned char> prepared_source;
const re4dc::render::DrawLocalPlan* local_plan=nullptr;
bool reference_spans=false;
extern "C" const re4dc::render::NativeDrawPlan* re4dc_model_acquire_draw_plan(const Re4dcModelPart* p,int* invalid){
 re4dc::render::DrawPlanRequirements r;
 const std::vector<unsigned char> current(p->stream,p->stream+p->stream_bytes);
 if(current!=prepared_source){re4dc_model_preparation_frame();prepared_source=current;}
 *invalid=!re4dc::render::inspect_draw_plan(p->stream,p->stream_bytes,p->flags&0x80000000U,p->position_count,p->normal_count,r);
 if(*invalid)return nullptr;
 plan_storage.resize((r.bytes+3)/4);
 auto* result=re4dc::render::prepare_draw_plan(plan_storage.data(),plan_storage.size()*4,p->stream,p->stream_bytes,p->flags&0x80000000U,r);
 const unsigned bytes=re4dc::render::prepare_draw_locals(nullptr,0,*result,p->stream,p->flags&0x80000000U);
 local_storage.resize((bytes+3)/4);local_plan=nullptr;
 if(bytes && re4dc::render::prepare_draw_locals(local_storage.data(),bytes,*result,p->stream,p->flags&0x80000000U))local_plan=(const re4dc::render::DrawLocalPlan*)local_storage.data();
 return result;
}
extern "C" const re4dc::render::DrawPlanBounds* re4dc_model_acquired_bounds(){return nullptr;}
extern "C" const re4dc::render::DrawLocalPlan* re4dc_model_acquired_locals(){return reference_spans?nullptr:local_plan;}
extern "C" void re4dc_model_release_draw_plan(){}
extern "C" void* re4dc_model_static_lighting_storage(unsigned* bytes){*bytes=0;return nullptr;}
#ifndef RE4DC_TEST_RETAINED
#define RE4DC_TEST_RETAINED 0
#endif
alignas(32) unsigned char retained_scratch[131072];
bool retained_available=true;
extern "C" void* re4dc_model_retained_storage(unsigned* bytes){*bytes=RE4DC_TEST_RETAINED && retained_available?sizeof(retained_scratch):0;return *bytes?retained_scratch:nullptr;}
alignas(32) unsigned char preparation_scratch[12288];
extern "C" void* re4dc_model_preparation_storage(unsigned* bytes){*bytes=sizeof(preparation_scratch);return preparation_scratch;}
extern "C" int re4dc_model_defer_part(const Re4dcModelPart*){return 0;}
unsigned raster_cull=0;
unsigned status=99,capacity=100,committed=0,input,output,binds=0;float uscale=1,vscale=1,predicted_u=1,predicted_v=1;bool bind_fails=false,streaming=false,aborted=false;
std::vector<pvr_vertex_t> all_chunks;
pvr_vertex_t pending[4098],owned[4098];
extern "C" int re4dc_model_diagnostic_enabled(){return 1;}
extern "C" int re4dc_model_packet_reserve(const Re4dcModelPart*,Re4dcModelPacket* p){*p={pending,capacity,predicted_u,predicted_v};return 1;}
extern "C" int re4dc_model_packet_begin(const Re4dcModelPart*,Re4dcModelPacket* p){++binds;*p={pending,capacity,uscale,vscale};return !bind_fails;}
extern "C" void re4dc_model_packet_commit(unsigned n){memcpy(owned,pending,n*32);committed=n;if(streaming)all_chunks.insert(all_chunks.end(),pending,pending+n);}
extern "C" int re4dc_model_packet_streaming(){return streaming;}
extern "C" void re4dc_model_packet_abort(){aborted=true;all_chunks.clear();}
extern "C" void re4dc_model_result(unsigned r,unsigned i,unsigned o){status=r;input=i;output=o;}
int pvr_prim(const void*,std::size_t){assert(false);return -1;}
std::vector<unsigned char> stream(unsigned op,std::initializer_list<unsigned> ids,bool color=false){
 std::vector<unsigned char> result{(unsigned char)op,0,(unsigned char)ids.size()};
 for(unsigned id:ids){result.push_back(id>>8);result.push_back(id);result.push_back(0);result.push_back(0);
  if(color){result.push_back(0);result.push_back(0);} result.push_back(0);result.push_back(id);}
 return result;
}
// Expand actual emitted strips back into the exact triangle order consumed by
// PVR. This catches parity, seam, clipping and rejected-triangle bridging bugs.
std::vector<pvr_vertex_t> expanded(){
 std::vector<pvr_vertex_t> result;unsigned start=0;
 for(unsigned i=0;i<committed;++i){
  const unsigned local=i-start;
  if(local>=2){
   const unsigned a=i-2+(local&1),b=i-1-(local&1);
   if(re4dc::render::triangle_visible_xy(owned[a],owned[b],owned[i],raster_cull,640,480))
    for(unsigned id:{a,b,i}){auto v=owned[id];v.flags=0;result.push_back(v);}
  }
  if(owned[i].flags==PVR_CMD_VERTEX_EOL)start=i+1;
 }
 assert(!committed || owned[committed-1].flags==PVR_CMD_VERTEX_EOL);return result;
}
int main(){
 short pos[4][4]={{-2,-2,0,9},{2,-2,0,9},{2,2,0,9},{-2,2,0,9}};
 unsigned short uv[4][2]={{0,0},{32768,0},{32768,32768},{0,32768}};
 Re4dcModelPart p{};p.positions=(unsigned char*)pos;p.position_count=4;p.normal_count=1;p.position_stride=8;
 p.uv=(unsigned char*)uv;p.modelview[0]=p.modelview[5]=p.modelview[10]=1;p.modelview[11]=-10;
 p.projection[1]=p.projection[3]=1;p.projection[5]=-1.f/99;p.projection[6]=-100.f/99;
 p.viewport[2]=640;p.viewport[3]=480;p.viewport[5]=1;
 auto run=[&](std::vector<unsigned char>& data){p.stream=data.data();p.stream_bytes=data.size();status=99;committed=0;raster_cull=p.cull;re4dc_model_preparation_frame();re4dc_model_submit(&p);};
 auto q=stream(0x80,{0,1,2,3});run(q);
 assert(status==0 && committed==6 && input==2 && output==2);
 assert(fabs(owned[0].x-256)<.001 && fabs(owned[0].y-288)<.001 && fabs(owned[0].z-.1)<.00001);
 assert(owned[1].u==1 && owned[2].v==1);
#if RE4DC_D349_RENDERER_STACK
 // Actual packet RGB is driven by source channel selection, not white shading.
 re4dc::render::SourceLighting lighting;lighting.enable=1;lighting.mask=128;lighting.diffuse=0;
 lighting.normal_matrix[0]=lighting.normal_matrix[5]=lighting.normal_matrix[10]=1;
 auto& light=lighting.lights[7];light.a[0]=light.k[0]=1;light.color[0]=255;
 signed char normal8[]={0,0,64,0};p.normals=(const unsigned char*)normal8;
 p.normal_stride=4;p.normal_shift=6;p.lighting=&lighting;
 run(q);assert(status==0 && committed && owned[0].argb==0xffff0000U);
 const auto red_triangle=expanded();
#if RE4DC_TEST_RETAINED
 // Inventory swaps out the room heap while the renderer still has a batch.
 // Detach without freeing: the old cell is now source inventory/model bytes.
 for(unsigned cycle=0;cycle<3;++cycle){
  re4dc_model_detach_retained_storage();retained_available=false;
  std::memset(retained_scratch,0xA5,sizeof(retained_scratch));
  for(unsigned draw=0;draw<3;++draw){
   run(q);const auto fallback=expanded();
   assert(status==0 && fallback.size()==red_triangle.size());
   assert(!memcmp(fallback.data(),red_triangle.data(),fallback.size()*32));
   for(unsigned char byte:retained_scratch)assert(byte==0xA5);
  }
  // Restoring the room makes the same owned cell available again. Acquisition
  // must initialize it and preserve the source packet output.
  retained_available=true;run(q);const auto restored=expanded();
  assert(status==0 && restored.size()==red_triangle.size());
  assert(!memcmp(restored.data(),red_triangle.data(),restored.size()*32));
  bool touched=false;for(unsigned char byte:retained_scratch)touched|=byte!=0xA5;
  assert(touched);
 }
#endif
 auto litstrip=stream(0x98,{0,1,2});run(litstrip);assert(status==0 && owned[0].argb==0xffff0000U);
 lighting.lights[7].color[0]=0;lighting.lights[7].color[1]=255;
 run(q);assert(status==0 && owned[0].argb==0xff00ff00U);
 lighting.mask=0;run(q);assert(status==0 && owned[0].argb==0xff000000U);
 lighting.enable=0;lighting.material[0]=64;lighting.material[1]=128;lighting.material[2]=255;
 run(q);assert(status==0 && owned[0].argb==0xff4080ffU);
 // Shared model/frame lifetime: material parts borrow the same pose; changes
 // to source lights/channels/normals invalidate only their actual dependents.
 lighting.enable=1;lighting.mask=128;lighting.diffuse=0;lighting.attenuation=2;
 lighting.material[0]=lighting.material[1]=lighting.material[2]=255;
 lighting.lights[7].color[0]=255;lighting.lights[7].color[1]=0;
 run(q);const auto before_wrap=expanded();
 // Counter wrap in any of prepare/activate's increments must never turn an
 // invalid slot into a hit at serial zero, including later assignments.
 for(unsigned distance=0;distance<7;++distance){
  re4dc_model_test_serial(~0U-distance);re4dc_model_preparation_frame();
  const auto work=*re4dc_model_work_stats();re4dc_model_submit(&p);auto after_wrap=expanded();
  assert(after_wrap.size()==before_wrap.size() && !memcmp(after_wrap.data(),before_wrap.data(),before_wrap.size()*32));
  assert(re4dc_model_work_stats()->position_transforms==work.position_transforms+4);
  assert(re4dc_model_work_stats()->normal_transforms==work.normal_transforms+1);
 }
 re4dc_model_test_serial(1000);re4dc_model_preparation_frame();re4dc_model_submit(&p);
 const auto first=*re4dc_model_work_stats();const auto prep_first=*re4dc_model_preparation_stats();
 const auto same_part=owned[0];p.part=(const void*)16;
 re4dc_model_submit(&p);assert(owned[0].argb==same_part.argb);
 assert(re4dc_model_work_stats()->position_transforms==first.position_transforms);
 assert(re4dc_model_work_stats()->normal_transforms==first.normal_transforms);
 assert(re4dc_model_work_stats()->light_evaluations==first.light_evaluations);
 assert(re4dc_model_preparation_stats()->light_builds==prep_first.light_builds);
 p.uv_offset[0]=.25f;re4dc_model_submit(&p);assert(owned[0].u==same_part.u+.25f);
 assert(re4dc_model_work_stats()->light_evaluations==first.light_evaluations);p.uv_offset[0]=0;
 p.modelview[3]=1;re4dc_model_submit(&p);
 assert(re4dc_model_work_stats()->position_transforms==first.position_transforms+4);
 assert(re4dc_model_work_stats()->normal_transforms==first.normal_transforms);
 lighting.normal_matrix[10]=-1;re4dc_model_submit(&p);
 assert(re4dc_model_work_stats()->normal_transforms==first.normal_transforms+1);
 lighting.lights[7].color[0]=0;lighting.lights[7].color[1]=255;
 re4dc_model_submit(&p);assert(owned[0].argb==0xff00ff00U);
 lighting.tev_scale=.5f;re4dc_model_submit(&p);assert(owned[0].argb==0xff007f00U);
 p.alpha_state=128;re4dc_model_submit(&p);assert(owned[0].argb==0x80007f00U);
 unsigned char dynamic_color[4]={255,255,255,255};
 p.flags=0x80000000U;p.colors=dynamic_color;lighting.material_vertex=1;lighting.tev_scale=1;
 auto source_color=stream(0x90,{0,1,2},true);p.stream=source_color.data();p.stream_bytes=source_color.size();
 re4dc_model_submit(&p);assert(owned[0].argb==0x8000ff00U);
 dynamic_color[1]=64;re4dc_model_submit(&p);assert(owned[0].argb==0x80004000U);
 // A reused pose pointer is invalidated at the source frame boundary.
 re4dc_model_preparation_frame();pos[0][0]=0;re4dc_model_submit(&p);assert(owned[0].x==352);pos[0][0]=-2;

 // Independently sparse source channels, normal/color seams and both shade
 // qualification modes must emit the same triangles as reference fallback.
 {
  auto saved=p;auto saved_lighting=lighting;
  short span_positions[201][4]{};signed char span_normals[201][4]{};
  unsigned char span_colors[3][4]={{255,64,32,255},{32,255,64,128},{64,32,255,64}};
  for(unsigned i=0;i<201;++i){std::memcpy(span_positions[i],pos[i%4],8);span_normals[i][2]=(i%2)?-64:64;}
  std::memcpy(span_positions[100],pos[1],8);std::memcpy(span_positions[200],pos[2],8);
  p.positions=(unsigned char*)span_positions;p.position_count=201;p.position_stride=8;
  p.normals=(unsigned char*)span_normals;p.normal_count=201;p.normal_stride=4;p.normal_shift=6;
  p.colors=(unsigned char*)span_colors;p.flags=0x80000000U;p.alpha_state=256;
  lighting.material_vertex=1;lighting.diffuse=1;lighting.normal_matrix[10]=1;
  for(unsigned variant=0;variant<4;++variant){
   auto data=stream(variant>=2?0x98:0x90,{0,1,2,0,1,2},true);
   for(unsigned i=0;i<6;++i){
    const unsigned vi=variant==0?(i%3)*100:i%3;
    const unsigned ni=variant==1?(i%3)*100:variant==2?i%2:i%3;
    const unsigned ci=variant==2?i%3:variant==3?i/3:i%3;
    auto* c=data.data()+3+i*8;c[0]=vi>>8;c[1]=vi;c[2]=ni>>8;c[3]=ni;c[4]=ci>>8;c[5]=ci;
   }
   reference_spans=true;run(data);auto expected=expanded();assert(status==0 && !expected.empty());
   reference_spans=false;auto before=*re4dc_model_work_stats();auto prep=*re4dc_model_preparation_stats();
   run(data);auto actual=expanded();assert(status==0);
   assert(actual.size()==expected.size() && !memcmp(actual.data(),expected.data(),expected.size()*32));
   auto after=*re4dc_model_work_stats();auto prepared=*re4dc_model_preparation_stats();
   assert(after.local_position_references-before.local_position_references==(variant==0?0U:6U));
   assert(prepared.normal_dense_references-prep.normal_dense_references==(variant==1?0U:6U));
   assert(prepared.shade_dense_references-prep.shade_dense_references==(variant>=2?0U:6U));
  }
  p=saved;lighting=saved_lighting;
 }
 p.modelview[3]=0;p.part=nullptr;p.alpha_state=255;p.flags=0;p.colors=nullptr;
 p.lighting=nullptr;p.normals=nullptr;p.normal_stride=p.normal_shift=0;
#endif

 p.cull=2;run(q);assert(committed==6);p.cull=1;run(q);assert(committed==0);p.cull=0;
 auto strips=stream(0x98,{0,1,3,2});p.cull=2;
 const auto strip_before=*re4dc_model_work_stats();
 run(strips);assert(committed==4 && output==2);p.cull=0;
 const auto strip_after=*re4dc_model_work_stats();
#if RE4DC_MODEL_ROOM_STRIPS
 assert(strip_after.room_prepared_strips-strip_before.room_prepared_strips==1);
 assert(strip_after.room_prepared_corners-strip_before.room_prepared_corners==4);
 assert(strip_after.position_references-strip_before.position_references==4);
#else
 assert(strip_after.room_prepared_strips==strip_before.room_prepared_strips);
 assert(strip_after.room_prepared_corners==strip_before.room_prepared_corners);
 assert(strip_after.position_references-strip_before.position_references==6);
#endif
 auto fan=stream(0xa0,{0,1,2,3});run(fan);assert(committed==6);
 // Captured native packet survives source preparation storage being overwritten.
 auto before=owned[0];pos[0][0]=0;assert(!memcmp(&before,&owned[0],32));run(q);assert(owned[0].x==320);pos[0][0]=-2;
 // Source skinned arrays use six-byte stride, not the rigid palette-id stride.
 short skin[4][3]={{-2,-2,0},{2,-2,0},{2,2,0},{-2,2,0}};
 p.positions=(unsigned char*)skin;p.position_stride=6;run(q);assert(fabs(owned[0].x-256)<.001);
 // Crossing the actual source near plane invokes the shared clipper.
 skin[0][2]=10;run(q);assert(status==0 && committed>0);skin[0][2]=0;
 // Whole-part rollback even if the first triangle fit; no partial part published.
 unsigned old_binds=binds;capacity=3;run(q);assert(status==3 && committed==0 && binds==old_binds);capacity=100;
 auto invalid=q;invalid[4]=8;run(invalid);assert(status==1 && committed==0);
 auto trunc=q;trunc.pop_back();run(trunc);assert(status==1);
 auto badop=q;badop[0]=0x61;run(badop);assert(status==1);
 auto badquad=stream(0x80,{0,1,2});run(badquad);assert(status==1);
 // Colored-corner identity adds a BE index; UV CPU values are signed Q8.
 short signeduv[4][2]={{-256,0},{256,0},{256,256},{-256,256}};
 p.flags=0x80000000;p.uv=(unsigned char*)signeduv;auto colored=stream(0x90,{0,1,2},true);run(colored);
 assert(status==0 && owned[0].u==-1 && owned[1].u==1);
 p.projection[0]=1;run(colored);assert(status==1); // unsupported ortho is explicit
 p.projection[0]=0;p.flags=0;p.shift=0;p.uv_offset[0]=p.uv_offset[1]=0;
 short many[66][3];unsigned short manyuv[66][2];
 for(unsigned i=0;i<66;++i){many[i][0]=int(i)-32;many[i][1]=(i&1)?-2:2;many[i][2]=0;manyuv[i][0]=i*128;manyuv[i][1]=(i&1)?32768:0;}
 p.positions=(unsigned char*)many;p.position_count=66;p.position_stride=6;p.uv=(unsigned char*)manyuv;
 p.modelview[11]=-128;p.projection[5]=-1.f/399;p.projection[6]=-400.f/399;
 std::vector<unsigned char> longstrip{0x98,0,66};
 for(unsigned i=0;i<66;++i)for(unsigned byte:{0U,i,0U,0U,0U,i})longstrip.push_back(byte);
 capacity=2048;p.stream=longstrip.data();p.stream_bytes=longstrip.size();committed=0;raster_cull=p.cull;re4dc_model_submit_reference(&p);
 assert(status==0 && committed==192 && output==64);auto baseline=expanded();
 run(longstrip);assert(status==0 && committed==66 && output==64);auto candidate=expanded();
 assert(candidate.size()==baseline.size() && !memcmp(candidate.data(),baseline.data(),baseline.size()*32));
 // Former overflow now fits; one byte of unrelated capacity is not borrowed.
 capacity=66;run(longstrip);assert(status==0 && committed==66);capacity=65;old_binds=binds;run(longstrip);assert(status==3 && !committed && binds==old_binds);
 capacity=2048;
 // Real previous implementation as oracle, randomized depth/cull/seam cases.
 std::mt19937 rng(335);
 unsigned savings=0;
 for(unsigned trial=0;trial<600;++trial){
  for(unsigned i=0;i<66;++i){
   many[i][0]=int(rng()%81)-40;many[i][1]=int(rng()%61)-30;
   many[i][2]=trial%3==0?int(rng()%261)-130:0;
   manyuv[i][0]=rng();manyuv[i][1]=rng();
  }
  p.cull=trial%4;uscale=trial%2?.75f:1.f;vscale=trial%2?.625f:1.f;
  predicted_u=trial%7?uscale:1;predicted_v=trial%7?vscale:1; // exact fallback for alternate native dimensions
  // A split keeps primitive order; UV changes across it must prevent reuse.
  auto data=longstrip;
  if(trial%5==0){auto seam=stream(0x90,{63,64,65});seam[8]=0;seam[14]=1;data.insert(data.end(),seam.begin(),seam.end());}
  p.stream=data.data();p.stream_bytes=data.size();committed=0;raster_cull=p.cull;raster_cull=p.cull;re4dc_model_submit_reference(&p);
  assert(status==0);auto old_count=committed,old_input=input,old_output=output;auto old=expanded();
  run(data);
#if RE4DC_D349_RENDERER_STACK
  assert(status==0 && (p.cull==3 || input==old_input));
#else
  assert(status==0 && (p.cull==3 || input==old_input) && output==old_output && committed<=old_count);
#endif
  auto now=expanded();assert(now.size()==old.size());
  assert(old.empty() || !memcmp(now.data(),old.data(),old.size()*32));if(old_count>committed)savings+=old_count-committed;
 }
 assert(savings);
 // Binding failure discards all successfully prepared vertices, no partial draw.
 p.cull=0;p.modelview[11]=-128;for(auto& vertex:many)vertex[2]=0;
 bind_fails=true;run(longstrip);assert(status==2 && !committed);bind_fails=false;
 // A completely rejected part consumes no texture handle, including cull-all.
 p.cull=3;unsigned before_binds=binds;run(longstrip);assert(status==0 && output==0 && binds==before_binds);
 p.cull=0;p.modelview[11]=1000;run(longstrip);assert(status==0 && !output && binds==before_binds);

 // Real material alpha, independent of texture data. Opaque legacy packets
 // still compare against the old oracle above; every uniform alpha survives.
 p.positions=(unsigned char*)skin;p.position_count=4;p.position_stride=6;
 p.modelview[11]=-10;p.cull=0;uscale=vscale=predicted_u=predicted_v=1;
 p.flags=0;p.uv=(unsigned char*)uv;capacity=2048;
 for(unsigned alpha=0;alpha<256;++alpha){
  p.alpha_state=alpha;run(q);assert(status==0 && committed==6);
  for(unsigned n=0;n<committed;++n)assert((owned[n].argb>>24)==alpha);
 }
 // Independent color identities, rather than position/normal/UV IDs.
 unsigned char colors[3][4]={{17,29,53,0},{61,79,101,64},{103,127,149,255}};
 p.flags=0x80000000;p.uv=(unsigned char*)signeduv;p.colors=(unsigned char*)colors;p.alpha_state=256|13;
 for(unsigned i=0;i<3;++i)colored[3+i*8+5]=2-i;
 run(colored);assert(status==0 && committed==3);
 assert((owned[0].argb>>24)==255 && (owned[1].argb>>24)==64 && (owned[2].argb>>24)==0);
 // Near-plane clipping interpolates alpha. It must not restore 255 or retain
 // an endpoint's alpha across newly inserted vertices.
 p.modelview[11]=-2;skin[0][2]=2;run(colored);assert(status==0 && committed==6);
 unsigned fractional=0;
 for(unsigned i=0;i<committed;++i){auto a=owned[i].argb>>24;if(a>=126 && a<=160)++fractional;}
 assert(fractional>=2);skin[0][2]=0;p.modelview[11]=-10;
 p.alpha_state=512;run(colored);assert(status==1 && !committed);
 p.alpha_state=256;p.colors=nullptr;run(colored);assert(status==1 && !committed);
 p.alpha_state=255;p.flags=0;p.uv=(unsigned char*)manyuv;

 // Source SDK cull boundary, independently checked in clip space. The SDK
 // flips FRONT/BACK hardware fields and stores a negative viewport Y scale.
 // For all-positive W, GX FRONT rejects non-positive projected XY determinant;
 // that becomes positive screen area. Do not use the viewer enum as the oracle.
 p.positions=(unsigned char*)many;p.position_count=66;p.modelview[11]=-128;
 uscale=vscale=predicted_u=predicted_v=1;capacity=2048;
 for(unsigned trial=0;trial<200;++trial){
  for(unsigned i=0;i<3;++i){many[i][0]=int(rng()%61)-30;many[i][1]=int(rng()%61)-30;many[i][2]=0;}
  const long area=(long(many[1][0])-many[0][0])*(long(many[2][1])-many[0][1])-(long(many[1][1])-many[0][1])*(long(many[2][0])-many[0][0]);
  if(!area)continue;
  auto triangle=stream(0x90,{0,1,2});
  for(unsigned mode=0;mode<3;++mode)for(bool force:{false,true}){
   p.cull=re4dc_model_cull(mode,force);run(triangle);
   const bool rejected=(force || mode==0)?area<=0:mode==1?area>=0:false;
   assert(status==0 && output==(rejected?0U:1U));
  }
 }
 p.cull=re4dc_model_cull(2,false);assert(p.cull==0);
 // Stream across small artificial boundaries and compare exact expanded
 // triangles against the existing unbounded oracle, including seams/clipping.
 p.modelview[11]=-128;p.cull=0;streaming=true;
 for(unsigned trial=0;trial<120;++trial){
  for(unsigned i=0;i<66;++i){many[i][0]=int(rng()%81)-40;many[i][1]=int(rng()%61)-30;many[i][2]=trial%3?0:int(rng()%261)-130;}
  uscale=trial%2?.75f:1.f;vscale=trial%2?.625f:1.f;predicted_u=predicted_v=1;
  capacity=2048;p.stream=longstrip.data();p.stream_bytes=longstrip.size();committed=0;
  raster_cull=p.cull;re4dc_model_submit_reference(&p);auto baseline=expanded();auto refinput=input,refoutput=output;
  capacity=3+trial%19;all_chunks.clear();aborted=false;auto prior=binds;
  run(longstrip);assert(status==0 && !aborted && input==refinput);
#if !RE4DC_D349_RENDERER_STACK
  assert(output==refoutput);
#endif
  assert(binds==prior+1);assert(all_chunks.size()<4098);
  memcpy(owned,all_chunks.data(),all_chunks.size()*32);committed=all_chunks.size();auto emitted=expanded();
  assert(emitted.size()==baseline.size() && !memcmp(emitted.data(),baseline.data(),baseline.size()*32));
 }
 // Over 64KiB of independent geometry uses bounded scratch. No reference and
 // candidate are retained simultaneously by the real owner (only this fixture).
 for(auto& v:many)v[2]=0;uscale=vscale=predicted_u=predicted_v=1;
 auto tri=stream(0x90,{0,1,2});std::vector<unsigned char> large;
 for(unsigned n=0;n<1800;++n)large.insert(large.end(),tri.begin(),tri.end());
 // Ensure a nondegenerate visible triangle.
 many[0][0]=-2;many[0][1]=-2;many[1][0]=2;many[1][1]=-2;many[2][0]=2;many[2][1]=2;
 const auto work_before=*re4dc_model_work_stats();
 capacity=2047;all_chunks.clear();aborted=false;run(large);
 const auto work_after=*re4dc_model_work_stats();
 assert(work_after.position_references-work_before.position_references==5400);
#if RE4DC_MODEL_POSITION_CACHE
 assert(work_after.position_transforms-work_before.position_transforms==3);
 assert(work_after.position_hits-work_before.position_hits==5397);
#else
 assert(work_after.position_transforms-work_before.position_transforms==5400);
 assert(work_after.position_hits==0);
#endif
 assert(status==0 && !aborted && input==1800 && output==1800 && all_chunks.size()==5400);
 // A late nonfinite projection must invalidate previously transferred chunks.
 // Valid source indices pass preflight; overflow appears only during transform.
 many[0][0]=many[1][0]=many[2][0]=0;
 many[0][1]=-2;many[0][2]=0;many[1][1]=2;many[1][2]=0;many[2][1]=0;many[2][2]=2;
 p.modelview[0]=3e38f;p.modelview[2]=1;many[3][0]=32767;
 auto invalid_late=stream(0x90,{0,1,3});large.insert(large.end(),invalid_late.begin(),invalid_late.end());
 all_chunks.clear();aborted=false;run(large);assert(status==3 && aborted && all_chunks.empty());
 // First-chunk binding failure never publishes or repeatedly retries I/O.
 p.modelview[0]=1;p.modelview[2]=0;bind_fails=true;all_chunks.clear();aborted=false;
 run(longstrip);assert(status==2 && all_chunks.empty() && !aborted);



}
"""
   (root/"fixture.cpp").write_text(code)
   game=ROOT/"port/dreamcast/game";room=ROOT/"port/dreamcast/room"
   reference=subprocess.check_output(["git","show","c45c0cf433c1b1fe5ae7595b1bccf29b29a0ed96:port/dreamcast/game/platform/native_model.cpp"],cwd=ROOT,text=True)
   reference=reference.replace('"../../room/pvr_geometry.hpp"','"pvr_geometry.hpp"').replace('void re4dc_model_submit(', 'void re4dc_model_submit_reference(')
   (root/"reference.cpp").write_text(reference)
   exe=root/"check"
   for cache,strips,plans,stack,retained in ((0,0,0,0,0),(0,1,0,0,0),(1,0,0,0,0),(1,1,0,0,0),(0,0,1,0,0),(0,1,1,0,0),(1,0,1,0,0),(1,1,1,0,0),(1,1,1,1,0),(1,1,1,1,1)):
    subprocess.run(["g++","-std=c++20","-O2","-DRE4DC_TEST_GENERATIONS=1","-DRE4DC_TEST_RETAINED="+str(retained),"-DRE4DC_D349_RENDERER_STACK="+str(stack),"-DRE4DC_MODEL_DRAW_PLANS="+str(plans),"-DRE4DC_MODEL_ROOM_STRIPS="+str(strips),"-DRE4DC_MODEL_POSITION_CACHE="+str(cache),"-fsanitize=address,undefined","-fno-omit-frame-pointer",
    "-I"+str(root),"-I"+str(game/"platform/include"),"-I"+str(room),str(root/"fixture.cpp"),str(root/"reference.cpp"),
    str(game/"platform/native_model.cpp"),str(room/"pvr_geometry.cpp"),str(room/"native_draw_plan.cpp"),str(room/"source_lighting.cpp"),"-o",str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
if __name__=="__main__":unittest.main()
