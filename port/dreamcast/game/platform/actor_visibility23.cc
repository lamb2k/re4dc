#include "include/actor_visibility23.h"
#if RE4DC_ACTOR_VISIBILITY23
#include <cstring>
#include <cstdint>
#include "include/actor_visibility23_window.h"
extern "C" void re4dc_log(const char*,...);
extern "C" {unsigned re4dc_actor_visibility23_mode=0;}
namespace {
Re4dcActorVisibility23Stats stats{};
using namespace actor_visibility23;
struct Entry {Key key;Group group[8];unsigned stamp;unsigned char groups;};
Entry cache[32]{};unsigned cache_epoch23;
struct View {float words[12];shz_interval_t inverse[12],eye_error[3];bool seen,ok;} view23{};
bool equal(const Key&a,const Key&b) {
 return a.positions==b.positions&&a.blob==b.blob&&a.records==b.records&&a.epoch==b.epoch&&
 a.position_count==b.position_count&&a.stream_bytes==b.stream_bytes&&a.meshlet==b.meshlet&&
 a.vertices==b.vertices&&a.stride==b.stride&&a.record_words==b.record_words;
}
}
extern "C" int re4dc_actor_visibility23_receipt(int ready){if(ready)++stats.world_receipt_ready;else ++stats.world_receipt_draw;return ready;}
extern "C" const Re4dcActorVisibility23Stats* re4dc_actor_visibility23_stats(){return &stats;}
extern "C" int re4dc_actor_visibility23_set(unsigned mode){if(mode>2)return 0;re4dc_actor_visibility23_reset();re4dc_actor_visibility23_mode=mode;return 1;}
extern "C" void re4dc_actor_visibility23_reset(){std::memset(cache,0,sizeof(cache));view23={};cache_epoch23=0;++stats.resets;}
namespace actor_visibility23 {
const Group* acquire(const Key& key,unsigned* count) {
 *count=0;if(!key.epoch||!key.positions||!key.blob||!key.records||key.stride!=8||
 !key.vertices||key.vertices>128||key.record_words<3||key.record_words>5){++stats.identity_draw;return nullptr;}
 if(cache_epoch23!=key.epoch){re4dc_actor_visibility23_reset();cache_epoch23=key.epoch;}
 unsigned victim=32;
 for(unsigned i=0;i<32;i++) {
  if(cache[i].stamp&&equal(key,cache[i].key)){++stats.cache_hits;*count=cache[i].groups;return *count?cache[i].group:nullptr;}
  if(!cache[i].stamp && victim==32)victim=i;
 }
 if(victim==32){++stats.capacity_draw;return nullptr;}
 ++stats.cache_misses;Entry& e=cache[victim];e={};e.key=key;e.stamp=1;
 const auto* rec=static_cast<const unsigned short*>(key.records);
 for(unsigned i=0;i<key.vertices;i++) {
  const unsigned vi=rec[i*key.record_words];if(vi>=key.position_count){++stats.identity_draw;e.groups=0;return nullptr;}
  const auto* pos=reinterpret_cast<const short*>(static_cast<const unsigned char*>(key.positions)+vi*8);
  const unsigned pal=static_cast<unsigned short>(pos[3]);unsigned g=0;
  while(g<e.groups&&e.group[g].palette!=pal)++g;
  if(g==e.groups){if(g==8){++stats.capacity_draw;e.groups=0;return nullptr;}++e.groups;e.group[g].palette=pal;for(unsigned a=0;a<3;a++)e.group[g].lo[a]=e.group[g].hi[a]=pos[a];}
  for(unsigned a=0;a<3;a++){if(pos[a]<e.group[g].lo[a])e.group[g].lo[a]=pos[a];if(pos[a]>e.group[g].hi[a])e.group[g].hi[a]=pos[a];}
  ++stats.source_records;
 }
 *count=e.groups;return e.group;
}
// Private QA numeric envelope, not universal SH7091 formal verification.
// See actor_visibility23/README.md for actual research/manual conditions.
static bool numeric_pad(const shz_interval_t pm[12],const shz_interval_t mv[12],
                        const shz_interval_t src[3],const float* p,const float* v,
                        const shz_interval_t world[3],float near,shz_interval_t padded[3],bool add_eye_lever=true) {
 using I=shz_interval_t;
 auto point=[](float x){return I{x,x};};
 auto absolute=[](I x){float a=__builtin_fabsf(x.lo),b=__builtin_fabsf(x.hi);return I{0,a>b?a:b};};
 I am[12],av[12],raw[3],sk[3],H[3];
 for(unsigned a=0;a<12;a++){am[a]=absolute(pm[a]);av[a]=absolute(mv[a]);}
 for(unsigned a=0;a<3;a++)raw[a]=absolute(src[a]);
 if(!shz_bounds_affine(am,raw,sk)||!shz_bounds_affine(av,sk,H))return false;
 // Upper float strictly above gamma128 = (128*2^-23)/(1-128*2^-23).
 const I gamma=point(0x1.000102p-16f),rho=point(0x1p-18f),u=point(0x1p-23f),one=point(1);
 I ax,ay,sx,sy,kx,ky,cx,cy,half,p2,p4,X,Y,eX,eY,eW,EW,E[3],a,b,c,den;
 if(!shz_bounds_mul(point(320),point(p[1]),&ax)||!shz_bounds_mul(point(-240),point(p[3]),&ay)||
    !shz_bounds_div(point(640),point(v[2]),&sx)||!shz_bounds_div(point(480),point(v[3]),&sy))return false;
 if(!shz_bounds_mul(point(v[2]),point(.5f),&half)||!shz_bounds_add(point(v[0]),half,&a)||
    !shz_bounds_mul(sx,a,&a)||!shz_bounds_mul(point(320),point(p[2]),&p2)||
    !shz_bounds_neg(p2,&b)||!shz_bounds_add(a,b,&cx))return false;
 if(!shz_bounds_mul(point(v[3]),point(.5f),&half)||!shz_bounds_add(point(v[1]),half,&a)||
    !shz_bounds_mul(sy,a,&a)||!shz_bounds_mul(point(240),point(p[4]),&p4)||!shz_bounds_add(a,p4,&cy))return false;
 // Absolute construction operands, including cancellation in cx/cy.
 if(!shz_bounds_mul(point(.5f),absolute(point(v[2])),&half)||!shz_bounds_add(absolute(point(v[0])),half,&a)||
    !shz_bounds_mul(absolute(sx),a,&a)||!shz_bounds_add(absolute(p2),a,&kx))return false;
 if(!shz_bounds_mul(point(.5f),absolute(point(v[3])),&half)||!shz_bounds_add(absolute(point(v[1])),half,&a)||
    !shz_bounds_mul(absolute(sy),a,&a)||!shz_bounds_add(absolute(p4),a,&ky))return false;
 if(!shz_bounds_mul(absolute(ax),H[0],&a)||!shz_bounds_mul(kx,H[2],&b)||!shz_bounds_add(a,b,&X)||
    !shz_bounds_mul(absolute(ay),H[1],&a)||!shz_bounds_mul(ky,H[2],&b)||!shz_bounds_add(a,b,&Y)||
    !shz_bounds_mul(gamma,X,&eX)||!shz_bounds_mul(gamma,Y,&eY)||!shz_bounds_mul(gamma,H[2],&eW))return false;
 if(!shz_bounds_add(H[2],eW,&a)||!shz_bounds_mul(rho,a,&a)||!shz_bounds_neg(rho,&b)||
    !shz_bounds_add(one,b,&den)||!shz_bounds_div(a,den,&a)||!shz_bounds_add(eW,a,&EW))return false;
 if(EW.hi>50)return false;
 I numer[2]={X,Y},error[2]={eX,eY},offset[2]={cx,cy},focal[2]={ax,ay};
 for(unsigned j=0;j<2;j++) {
  I f=absolute(focal[j]);f.lo=__builtin_fabsf(focal[j].lo)<__builtin_fabsf(focal[j].hi)?__builtin_fabsf(focal[j].lo):__builtin_fabsf(focal[j].hi);
  if(focal[j].lo<=0&&focal[j].hi>=0)return false;
  if(!shz_bounds_add(numer[j],error[j],&a)||!shz_bounds_mul(u,a,&a)||!shz_bounds_add(error[j],a,&a)||
     !shz_bounds_mul(absolute(offset[j]),EW,&b)||!shz_bounds_add(a,b,&a)||!shz_bounds_div(a,f,&E[j]))return false;
 }E[2]=EW;
 for(unsigned j=0;j<3;j++) {
  I total=point(0);
  for(unsigned k=0;k<3;k++)if(!shz_bounds_mul(absolute(view23.inverse[j*4+k]),E[k],&a)||!shz_bounds_add(total,a,&total))return false;
  // room_occl uses transpose eye, while bounds use inverse view. A ray
  // meeting either slab face at fraction lambda can be represented from
  // the transpose eye by x'=x+delta*(1/lambda-1). All slab corners are at
  // depth>=near+10; reserve that10mm and bound 1/lambda<=25050/near.
  // 25050 includes the <=50mm effective-depth envelope below. Thus test
  // the WHOLE enlarged box; no unqualified rigidity epsilon substitutes.
  I lever;
  if(add_eye_lever && (!shz_bounds_div(point(25050),point(near),&lever)||!shz_bounds_add(lever,one,&lever)||
     !shz_bounds_mul(view23.eye_error[j],lever,&a)||!shz_bounds_add(total,a,&total)))return false;
  // Coverage/cost cap only: a larger tested box is more conservative.
  // EW<=50, eye L1<=1 and actual target depth<=25050 stay unchanged.
  if(!(total.hi>=0 && total.hi<=512))return false;
  c={-total.hi,total.hi};if(!shz_bounds_add(world[j],c,padded+j))return false;
 }return true;
}
// Wall coordinates use the same gamma/rho envelope, but the target box has
// already paid the eye-lever uncertainty. This bounds each opaque vertex's
// effective world displacement, not its location or an occlusion decision.
bool opaque_world_error(const float view[12],const float P[7],const float V[6],
                        float near,const float operands[3],float maximum) {
 struct Cached {float words[30];bool seen,ok;};static Cached cached{};
 if(!view23.ok||std::memcmp(view23.words,view,48)||!(maximum>0&&maximum<=50))return false;
 float words[30];std::memcpy(words,view,48);std::memcpy(words+12,P,28);std::memcpy(words+19,V,24);
 std::memcpy(words+25,operands,12);words[28]=near;words[29]=maximum;
 if(cached.seen&&!std::memcmp(cached.words,words,sizeof(words)))return cached.ok;
 std::memcpy(cached.words,words,sizeof(words));cached.seen=true;cached.ok=false;
 shz_interval_t pm[12]{},mv[12],src[3],world[3]{},padded[3];
 pm[0]=pm[5]=pm[10]={1,1};
 for(unsigned i=0;i<12;i++)if(!shz_bounds_point(view[i],mv+i))return false;
 for(unsigned a=0;a<3;a++){
  shz_interval_t k;if(!shz_bounds_point(operands[a],&k)||!(operands[a]>0))return false;
  src[a]={-operands[a],operands[a]};
 }
 if(!numeric_pad(pm,mv,src,P,V,world,near,padded,false))return false;
 for(unsigned a=0;a<3;a++)if(padded[a].lo< -maximum||padded[a].hi>maximum)return false;
 cached.ok=true;return true;
}
bool camera_bounds(const Group* groups,unsigned count,const float* palette,unsigned entries,float q,const float modelview[12],const float view[12],const float projection[7],const float viewport[6],float near,float far,float lo[3],float hi[3]) {
 unsigned fpscr=0;
#if defined(__sh__)
 __asm__ volatile("sts fpscr,%0":"=r"(fpscr));
#endif
 if(!shz_bounds_mode_supported(fpscr))return false;
 // Bound actual camera/operand cohort. A discontinuity, tiny focal length,
 // non-rigid camera, huge range or unsupported arithmetic draws.
 if(!projection||!viewport||projection[0]!=0||near<1||far<=near||far>1000000)return false;
 for(unsigned i=0;i<7;i++){shz_interval_t t;if(!shz_bounds_point(projection[i],&t))return false;}
 for(unsigned i=0;i<6;i++){shz_interval_t t;if(!shz_bounds_point(viewport[i],&t))return false;}
 if(__builtin_fabsf(projection[1])<.25f||__builtin_fabsf(projection[1])>10||
    __builtin_fabsf(projection[3])<.25f||__builtin_fabsf(projection[3])>10||
    __builtin_fabsf(projection[2])>2||__builtin_fabsf(projection[4])>2||
    viewport[2]<1||viewport[2]>2048||viewport[3]<1||viewport[3]>2048||
    __builtin_fabsf(viewport[0])>2048||__builtin_fabsf(viewport[1])>2048)return false;
 for(unsigned r=0;r<3;r++)for(unsigned c=0;c<4;c++) {
  shz_interval_t t;if(!shz_bounds_point(view[r*4+c],&t)||__builtin_fabsf(view[r*4+c])>(c==3?500000.0f:1.001f))return false;
 }
 for(unsigned r=0;r<3;r++)for(unsigned t=0;t<3;t++) {
  float dot=0;for(unsigned c=0;c<3;c++)dot+=view[r*4+c]*view[t*4+c];
  if(__builtin_fabsf(dot-(r==t?1.0f:0.0f))>.005f)return false;
 }

 if(!view23.seen||std::memcmp(view23.words,view,sizeof(view23.words))) {
  std::memcpy(view23.words,view,sizeof(view23.words));view23.seen=true;view23.ok=shz_bounds_inverse(view,view23.inverse)!=0;
  for(unsigned a=0;view23.ok&&a<3;a++) {
   shz_interval_t eye{0,0},x,y,z;
   for(unsigned c=0;c<3;c++) {
    if(!shz_bounds_point(view[c*4+a],&x)||!shz_bounds_point(view[c*4+3],&y)||
       !shz_bounds_mul(x,y,&z)||!shz_bounds_add(eye,z,&eye)){view23.ok=false;break;}
   }
   if(!view23.ok)break;
   if(!shz_bounds_neg(eye,&eye)||!shz_bounds_neg(view23.inverse[a*4+3],&x)||
      !shz_bounds_add(eye,x,&z)){view23.ok=false;break;}
   const float l=__builtin_fabsf(z.lo),h=__builtin_fabsf(z.hi);
   view23.eye_error[a]={0,l>h?l:h};
  }
 }
 shz_interval_t eye_sum{0,0};
 for(unsigned a=0;view23.ok&&a<3;a++)if(!shz_bounds_add(eye_sum,view23.eye_error[a],&eye_sum))view23.ok=false;
 if(eye_sum.hi>1.0f)return false; // true eye remains within1mm of OCCL eye, front margin50mm
 if(!view23.ok||!groups||!count||count>8||!palette)return false;
 shz_interval_t scale,mv[12];if(!shz_bounds_point(q,&scale)||q<=0)return false;
 for(unsigned i=0;i<12;i++)if(!shz_bounds_point(modelview[i],mv+i))return false;
 for(unsigned g=0;g<count;g++) {
  if(groups[g].palette>=entries)return false;
  const float* P=palette+groups[g].palette*12;shz_interval_t pm[12],src[3],sk[3],cam[3],world[3];
  for(unsigned r=0;r<3;r++) {
   for(unsigned c=0;c<4;c++)if(!shz_bounds_point(P[c*3+r],pm+r*4+c))return false;
   src[r].lo=groups[g].lo[r];src[r].hi=groups[g].hi[r];if(!shz_bounds_mul(src[r],scale,src+r))return false;
  }
  if(!shz_bounds_affine(pm,src,sk)||!shz_bounds_affine(mv,sk,cam)||!shz_bounds_affine(view23.inverse,cam,world))return false;
  if(cam[2].hi>=-near || cam[2].lo < -25000.0f)return false;
  shz_interval_t padded[3];
  if(!numeric_pad(pm,mv,src,projection,viewport,world,near,padded))return false;
  for(unsigned a=0;a<3;a++){if(!g||padded[a].lo<lo[a])lo[a]=padded[a].lo;if(!g||padded[a].hi>hi[a])hi[a]=padded[a].hi;}
  ++stats.bound_groups;
 }return true;
}
}
#endif

#if RE4DC_ACTOR_VISIBILITY23
namespace {
actor_visibility23::Window fixture23;
Re4dcActorVisibility23Stats previous23{};
unsigned previous_xf23,previous_render23,previous_mode23,previous_n23;
bool pending23;
}
extern "C" void re4dc_actor_visibility23_frame(unsigned render,unsigned open,unsigned mask,unsigned transformed) {
 if(fixture23.seen&&fixture23.last==render)return;
 // No live source actor consumer exists at this workspace-rebind boundary.
 // Counters are actual pass_positions work (chunk repeats already compacted),
 // including diagnostic reference work if a check kernel is explicitly used.
 if(pending23) {
  const auto& now=*re4dc_actor_visibility23_stats();const auto& old=previous23;
  re4dc_log("AV23 frame=%u mode=%u n=%u query=%u sections=%u wall=%u hidden=%u bound=%u would=%u skip=%u tri=%u xf=%u\n",
    previous_render23,previous_mode23,previous_n23,now.queries-old.queries,now.bounded_sections-old.bounded_sections,now.wall_tests-old.wall_tests,now.hidden_sections-old.hidden_sections,now.bounded_records-old.bounded_records,
    now.potential_records-old.potential_records,now.positions_avoided-old.positions_avoided,
    now.triangles_avoided-old.triangles_avoided,transformed-previous_xf23);
  re4dc_log("AV23WORK frame=%u groups=%u hit=%u miss=%u scan=%u material=%u identity=%u numeric=%u capacity=%u reset=%u world_ok=%u world_draw=%u\n",
    previous_render23,now.bound_groups-old.bound_groups,now.cache_hits-old.cache_hits,now.cache_misses-old.cache_misses,
    now.source_records-old.source_records,now.material_draw-old.material_draw,now.identity_draw-old.identity_draw,
    now.numeric_draw-old.numeric_draw,now.capacity_draw-old.capacity_draw,now.resets-old.resets,now.world_receipt_ready-old.world_receipt_ready,now.world_receipt_draw-old.world_receipt_draw);
  pending23=false;
 }
 const auto event=fixture23.begin(render,open!=0,mask);
 if(event==actor_visibility23::Window::Start || event==actor_visibility23::Window::Complete ||
    event==actor_visibility23::Window::Cancel || event==actor_visibility23::Window::Invalid) {
  re4dc_actor_visibility23_set(fixture23.active?fixture23.mode:0);
  re4dc_log("AV23WINDOW event=%u frame=%u mode=%u mask=%x left=%u once=1\n",
    unsigned(event),render,re4dc_actor_visibility23_mode,mask,fixture23.left);
 }
 if(fixture23.active){
  previous23=*re4dc_actor_visibility23_stats();previous_xf23=transformed;
  previous_render23=render;previous_mode23=fixture23.mode;previous_n23=fixture23.frames;pending23=true;
 }
}
#endif
