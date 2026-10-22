#include "include/actor_visibility23.h"
#if RE4DC_ACTOR_VISIBILITY23
#include <cstring>
#include <cstdint>
extern "C" {unsigned re4dc_actor_visibility23_mode=0;}
namespace {
Re4dcActorVisibility23Stats stats{};
using namespace actor_visibility23;
struct Entry {Key key;Group group[8];unsigned stamp;unsigned char groups;};
Entry cache[32]{};unsigned clock23;
struct View {float words[12];shz_interval_t inverse[12];bool seen,ok;} view23{};
bool equal(const Key&a,const Key&b) {
 return a.positions==b.positions&&a.blob==b.blob&&a.records==b.records&&a.epoch==b.epoch&&
 a.position_count==b.position_count&&a.stream_bytes==b.stream_bytes&&a.meshlet==b.meshlet&&
 a.vertices==b.vertices&&a.stride==b.stride&&a.record_words==b.record_words;
}
}
extern "C" const Re4dcActorVisibility23Stats* re4dc_actor_visibility23_stats(){return &stats;}
extern "C" int re4dc_actor_visibility23_set(unsigned mode){if(mode>2)return 0;re4dc_actor_visibility23_reset();re4dc_actor_visibility23_mode=mode;return 1;}
extern "C" void re4dc_actor_visibility23_reset(){std::memset(cache,0,sizeof(cache));view23={};clock23=0;++stats.resets;}
namespace actor_visibility23 {
const Group* acquire(const Key& key,unsigned* count) {
 *count=0;if(!key.epoch||!key.positions||!key.blob||!key.records||key.stride!=8||
 !key.vertices||key.vertices>128||key.record_words<3||key.record_words>5){++stats.identity_draw;return nullptr;}
 if(++clock23==0){re4dc_actor_visibility23_reset();++clock23;}
 unsigned victim=0;
 for(unsigned i=0;i<32;i++) {
  if(cache[i].stamp&&equal(key,cache[i].key)){++stats.cache_hits;cache[i].stamp=clock23;*count=cache[i].groups;return *count?cache[i].group:nullptr;}
  if(cache[i].stamp<cache[victim].stamp)victim=i;
 }
 ++stats.cache_misses;Entry& e=cache[victim];e={};e.key=key;e.stamp=clock23;
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
                        const shz_interval_t world[3],shz_interval_t padded[3]) {
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
  if(!(total.hi>=0 && total.hi<=50))return false;
  c={-total.hi,total.hi};if(!shz_bounds_add(world[j],c,padded+j))return false;
 }return true;
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
 }
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
  if(!numeric_pad(pm,mv,src,projection,viewport,world,padded))return false;
  for(unsigned a=0;a<3;a++){if(!g||padded[a].lo<lo[a])lo[a]=padded[a].lo;if(!g||padded[a].hi>hi[a])hi[a]=padded[a].hi;}
  ++stats.bound_groups;
 }return true;
}
}
#endif
