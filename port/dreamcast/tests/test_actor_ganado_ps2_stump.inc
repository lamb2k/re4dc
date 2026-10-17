// Host seams and assertions for test_actor_ganado_ps2_stump.py.
// Every source identity, owner and gate consumer is inserted from the checkout.
#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iterator>
#include <vector>
#define RE4DC_ACTOR_TRANSACTION 1
#define RE4DC_ACTOR_GANADO_PS2_STUMP 1
#define RE4DC_ACTOR_GANADO_APP0_GRIP 1
#define RE4DC_ACTOR_LEON_NATIVE_LOOK 0
#define RE4DC_ACTOR_APPEARANCE_ALIAS 2
#define RE4DC_COARSE_SKIN_FTRV 1
#define RE4DC_COARSE_GANADO_LIMIT 0
#define RE4DC_COARSE_PREGATE 1
#define RE4DC_COARSE_GATE_ONCE 2
#define RE4DC_ACTOR_EARLY_COARSE 1
#define RE4DC_SCREEN_WF 640.0f
#define RE4DC_SCREEN_HF 480.0f
#define RE4DC_SCREEN_HALF_WF 320.0f
#define RE4DC_SCREEN_HALF_HF 240.0f
using Mtx=float[3][4];
static std::vector<unsigned char> arena;
struct Ptr32 {
    std::uint32_t at;
    const void* get()const{return at && at<arena.size()?arena.data()+at:nullptr;}
    operator const void*()const{return get();}
};
struct ModelData {
    Ptr32 pHead; unsigned pad4,pad8; Ptr32 pClr,pTex,pWeight;
    unsigned char weight_palette_num,nParts; unsigned short displist_num;
    Ptr32 pParts;unsigned flags,nTex;unsigned char shift,pad41;unsigned short weight_ext_num;
    unsigned shape;Ptr32 vtxOrig,nrmOrig;unsigned short nVtx,nNrm;unsigned version;
};
static_assert(sizeof(ModelData)==64 && offsetof(ModelData,pParts)==28 && offsetof(ModelData,vtxOrig)==48,"BIN ABI");
struct cCoord {};
struct cParts: cCoord {cParts* pList;const cCoord* pParent;Mtx mat,lt_inv_mat;};
class cModelInfo {
public:
    ModelData* pData=nullptr;void* tpl_addr=nullptr;cModelInfo* pList=nullptr;
    unsigned be_flag=9;float invisible_factor=1;Mtx mat{};
    unsigned blend_mode=0,colorWord=~0u,flagsDC=0,nAddTex=0,blendRatio=0,blendType=0;
    unsigned char color2[4]{};void *pAddTpl=nullptr,*texBlendTbl=nullptr,*pTexAnim=nullptr,*pShape=nullptr;
    float uvU=0,uvV=0,uvScrollU=0,uvScrollV=0;
    struct Shape {float rate=0;void* data=nullptr;} shape[2];
};
class cModel: public cCoord {
public:
    unsigned id=0x13,type=3,serial=1,nParts=34,be_flag=0;
    cParts *pList=nullptr,*pParts=nullptr;cModelInfo* pModelInfo=nullptr;
};
static cModel model;
static cModelInfo infos[4];
static cParts parts[34];
static unsigned checks,posed_vertices,output_triangles,cull_cases;
static void check_at(bool b,unsigned line) {++checks;if(!b){std::fprintf(stderr,"FAIL check=%u line=%u\n",checks,line);std::abort();}}
#define check(b) check_at(bool(b),__LINE__)
static bool inside(const void* base,std::size_t size,const void* p,unsigned n) {
    auto a=reinterpret_cast<std::uintptr_t>(base),b=reinterpret_cast<std::uintptr_t>(p);
    return b>=a && b-a<=size && n<=size-(b-a);
}
static bool host_readable(const void* p,unsigned n) {
    return inside(arena.data(),arena.size(),p,n) || inside(infos,sizeof(infos),p,n) || inside(&model,sizeof(model),p,n);
}
static void identity(Mtx m) {std::memset(m,0,sizeof(Mtx));for(unsigned i=0;i<3;++i)m[i][i]=1;}
static void PSMTXConcat(const float a[3][4],const float b[3][4],float out[3][4]) {
    Mtx t{};
    for(unsigned r=0;r<3;++r)for(unsigned c=0;c<4;++c) {
        for(unsigned k=0;k<3;++k)t[r][c]+=a[r][k]*b[k][c];
        if(c==3)t[r][c]+=a[r][3];
    }
    std::memcpy(out,t,sizeof(t));
}
static int PSMTXInverse(const float a[3][4],float out[3][4]) {
    const float d=a[0][0]*(a[1][1]*a[2][2]-a[1][2]*a[2][1])-a[0][1]*(a[1][0]*a[2][2]-a[1][2]*a[2][0])+a[0][2]*(a[1][0]*a[2][1]-a[1][1]*a[2][0]);
    if(!std::isfinite(d) || std::fabs(d)<1e-10f)return 0;
    Mtx t{};
    for(unsigned r=0;r<3;++r)for(unsigned c=0;c<3;++c)
        t[r][c]=(a[(c+1)%3][(r+1)%3]*a[(c+2)%3][(r+2)%3]-a[(c+1)%3][(r+2)%3]*a[(c+2)%3][(r+1)%3])/d;
    for(unsigned r=0;r<3;++r)for(unsigned k=0;k<3;++k)t[r][3]-=t[r][k]*a[k][3];
    std::memcpy(out,t,sizeof(t));return 1;
}
extern "C" void re4dc_log(const char*,...){}
static float projection[7]={0,1,0,1,0,-0.001001001f,-1.001001001f};
static float viewport[6]={0,0,640,480,0,1};
extern "C" void GXGetProjectionv(float* p){std::memcpy(p,projection,sizeof(projection));}
extern "C" void GXGetViewportv(float* p){std::memcpy(p,viewport,sizeof(viewport));}
struct Global {struct Camera {Mtx v_mat;} Cam;unsigned Frame_cnt=0;} global;
static Global* pG=&global;
#include "coarse_skin.h"
extern "C" void re4dc_coarse_skin_bones(const float* inv,const CoarseBoneJob* jobs,unsigned n) {
    Mtx root{};for(unsigned r=0;r<3;++r)for(unsigned c=0;c<4;++c)root[r][c]=inv[c*4+r];
    for(unsigned i=0;i<n;++i) {
        const auto& j=jobs[i];Mtx a,b,t;
        std::memcpy(a,j.P,sizeof(a));std::memcpy(b,j.B,sizeof(b));PSMTXConcat(a,b,t);PSMTXConcat(root,t,a);
        for(unsigned r=0;r<3;++r)for(unsigned c=0;c<4;++c)j.T[c*3+r]=a[r][c];
    }
}
extern "C" void re4dc_coarse_skin_groups(const void* stream,unsigned groups,const float* T,float* out,unsigned entries) {
    std::fill(out,out+entries*12,0.0f);const auto* p=static_cast<const unsigned char*>(stream);
    for(unsigned g=0;g<groups;++g) {
        const auto* h=reinterpret_cast<const CoarseGroupHeader*>(p);p+=sizeof(*h);
        for(unsigned i=0;i<h->n;++i) {
            const auto* e=reinterpret_cast<const CoarseGroupEntry*>(p);p+=sizeof(*e);
            for(unsigned j=0;j<12;++j)for(unsigned k=0;k<h->count;++k)out[e->out/4+j]+=T[h->offset[k]/4+j]*e->w[k];
        }
    }
}
#include "coarse_actor_transaction.h"
#include "actor_lifetime.h"
#include "ganado_cast_runtime.h"
#include "ganado_ps2_stump_runtime.h"
// Host seams of the variant package loader: heap 4 (malloc, counted), the transaction (no owned records live here).
const char* host_package;
static unsigned host_allocs,host_frees;
extern "C" void* re4dc_static_alloc(unsigned n){++host_allocs;return std::malloc(n);}
extern "C" void re4dc_static_free(void* p){++host_frees;std::free(p);}
extern "C" int re4dc_static_heap_free(){return 1<<20;}
extern "C" void re4dc_actor_transaction_retire(){}
extern "C" int re4dc_actor_owned_live(){return 0;}
extern "C" unsigned re4dc_ui_frame(){return 1;}
#if RE4DC_CROWD_FAR
#include "ganado_far_runtime.h"
static bool far_request;
extern "C" int re4dc_crowd_far(cModel*){return far_request;}
#endif
extern "C" {unsigned re4dc_actor_tx_serial=1;}
// Host seams for consumers that moved on after 10-13 (lane stump17 10-17): the render matrix concat, GANADO_LOD
// (off: always ready) and the em3c / em25 armour material rows (off).
#define RE4DC_RENDER_MTXConcat PSMTXConcat
#define RE4DC_GANADO_LOD_READY() true
namespace re4dc_material { constexpr bool armor_rows=false; }
// INSERT ACTUAL CONSUMERS HERE

static unsigned word(unsigned at) {unsigned x;std::memcpy(&x,arena.data()+at,4);return x;}
static void word(unsigned at,unsigned x){std::memcpy(arena.data()+at,&x,4);}
static unsigned offset(unsigned no){return word(16+(no-4)*4);}
static ModelData* data(unsigned no){return reinterpret_cast<ModelData*>(arena.data()+offset(no));}
static void setup(const char* fixture,unsigned id=0x13) {
    re4dc_actor_forget_all();
    std::ifstream f(fixture,std::ios::binary);arena.assign(std::istreambuf_iterator<char>(f),{});check(!arena.empty());
    re4dc_actor_archive_adopt(arena.data(),arena.data(),unsigned(arena.size()),2);
    for(unsigned no:{448u,450u,453u,454u,476u,478u,479u})for(unsigned field:{0u,12u,16u,20u,28u,48u,52u}) {
        const unsigned at=offset(no)+field;word(at,offset(no)+word(at));
    }
    model={};model.id=id;model.pList=model.pParts=parts;model.pModelInfo=infos;
    for(unsigned i=0;i<34;++i) {
        parts[i]={};parts[i].pList=i<33?&parts[i+1]:nullptr;
        parts[i].pParent=gc::parents[i]<0?static_cast<cCoord*>(&model):static_cast<cCoord*>(&parts[gc::parents[i]]);
        std::memcpy(parts[i].lt_inv_mat,gc::bind[2][i],sizeof(Mtx));check(PSMTXInverse(parts[i].lt_inv_mat,parts[i].mat));
    }
    const unsigned bins[4]={476,478,448,453};
    for(unsigned k=0;k<4;++k) {
        infos[k]={};infos[k].pData=data(bins[k]);infos[k].tpl_addr=arena.data()+offset(477);
        infos[k].pList=k<3?&infos[k+1]:nullptr;identity(infos[k].mat);re4dc_actor_info_adopt(&infos[k]);
    }
    identity(global.Cam.v_mat);global.Cam.v_mat[1][3]=-1600;global.Cam.v_mat[2][3]=-6000;
    projection[5]=-0.000100010f;projection[6]=-1.00010001f;
    check(re4dc_material::source_appearance_type(2,id,3));
    check(re4dc_actor_role_source_bin(&model,&infos[1],2,1)==478);
}
static void swap_info(unsigned k,unsigned bin) {
    re4dc_actor_info_retire(&infos[k]);re4dc_actor_model_changed(&model);
    infos[k].pData=data(bin);re4dc_actor_info_adopt(&infos[k]);++re4dc_actor_tx_serial;
}
static void swap_head(unsigned bin) {swap_info(1,bin);}
static re4dc_material::Error live_head() {
    auto* row=actor_current_role(&model,&infos[1],2,1);check(row);
    re4dc_material::Result r{};return re4dc_material::info(&infos[1],*row,r,false);
}
static float storage[4][256*12];
static float* output[4]={storage[0],storage[1],storage[2],storage[3]};
static Re4dcActorPlan plan() {Re4dcActorPlan p;check(re4dc_actor_plan_ganado(&model,&p));return p;}
static void skin_check(const Re4dcActorPlan& p) {
    check(owner_ganado_palettes(&model,p,output));
    const auto& c=ganado_var::chunk[2];Mtx inv;check(PSMTXInverse(parts[0].mat,inv));
    for(unsigned v=0;v<c.position_count;++v) {
        short s[4];std::memcpy(s,c.positions+v*8,8);const auto& w=c.weights[unsigned(s[3])];
        double expected[3]={};float x[3]={s[0]/16.0f,s[1]/16.0f,s[2]/16.0f};
        for(unsigned k=0;k<w.count;++k) {
            const unsigned b=w.bone[k];float local[3],world[3],relative[3];
            gate_local(gc::bind[2][b],x,local);gate_local(&parts[b].mat[0][0],local,world);gate_local(&inv[0][0],world,relative);
            for(unsigned a=0;a<3;++a)expected[a]+=double(relative[a])*w.value[k];
        }
        for(unsigned a=0;a<3;++a) {
            const float* m=output[1]+unsigned(s[3])*12;double got=m[9+a];for(unsigned k=0;k<3;++k)got+=double(m[k*3+a])*x[k];
            check(std::fabs(got-expected[a])<0.002); // host float matrix reassociation bound, model mm
        }
        ++posed_vertices;
    }
    // Decode the actual plan's FE strips; every corner names a tested source
    // vertex, a valid source normal and the unchanged atlas-remapped UV array.
    const auto* s=p.runs[1].stream.data;const unsigned rec=re4dc_source::pre_u16(s+8)*4,idx=re4dc_source::pre_u16(s+10)*4;
    unsigned triangles=0;
    for(unsigned m=0;m<re4dc_source::pre_u16(s+4);++m) {
        const auto* t=s+32+m*8;const unsigned counts=re4dc_source::pre_u32(t),nv=counts&255,ni=(counts>>8)&4095;
        const unsigned first=re4dc_source::pre_u16(t+4),indices=re4dc_source::pre_u16(t+6);unsigned len=0;
        for(unsigned i=0;i<ni;++i) {
            const unsigned vi=s[idx+indices+i];check((vi&127)<nv);const auto* r=s+rec+(first+(vi&127))*6;
            check(re4dc_source::pre_u16(r)<c.position_count);check(re4dc_source::pre_u16(r+2)<c.normal_count);
            check(re4dc_source::pre_u16(r+4)*4+4<=p.input[1].uv.size);
            if(++len>=3)++triangles;if(vi&128)len=0;
        }
        check(!len);
    }
    check(triangles==90);output_triangles+=triangles;
}
static void cull_check() {
    check(gate_init((kStumpGateApp+2)));check(gate_count[(kStumpGateApp+2)][1]==3);
    const auto& c=ganado_var::chunk[2];
    for(unsigned v=0;v<c.position_count;++v) {
        short s[4];std::memcpy(s,c.positions+v*8,8);const auto& w=c.weights[unsigned(s[3])];float x[3]={s[0]/16.0f,s[1]/16.0f,s[2]/16.0f};
        for(unsigned k=0;k<w.count;++k)if(w.value[k]>0) {
            bool found=false;
            for(unsigned j=0;j<gate_count[(kStumpGateApp+2)][1];++j) {
                const unsigned n=gate_first[(kStumpGateApp+2)][1]+j;if(gate_bone[n]!=w.bone[k])continue;
                float q[3];gate_local(gc::bind[2][w.bone[k]],x,q);double d2=0;
                for(unsigned a=0;a<3;++a)d2+=(q[a]-gate_ball[n].c[a])*(q[a]-gate_ball[n].c[a]);
                check(d2<=double(gate_ball[n].r+0.001f)*(gate_ball[n].r+0.001f));found=true;
            }
            check(found);
        }
    }
    cModelInfo* iv[4]={infos,infos+1,infos+2,infos+3};cParts* pv[34];for(unsigned b=0;b<34;++b)pv[b]=parts+b;
    Mtx inv,mv[4];check(PSMTXInverse(parts[0].mat,inv));
    for(float x:{0.0f,8000.0f,-8000.0f})for(float y:{-1600.0f,8000.0f,-8000.0f})for(float z:{-6000.0f,-20000.0f}) {
        global.Cam.v_mat[0][3]=x;global.Cam.v_mat[1][3]=y;global.Cam.v_mat[2][3]=z;
        const unsigned skip=gate_cull_checked(&model,(kStumpGateApp+2),iv,pv,inv,mv);
        bool any=false;
        for(unsigned v=0;v<c.position_count;++v) {
            short s[4];std::memcpy(s,c.positions+v*8,8);const float* p=output[1]+unsigned(s[3])*12;
            float local[3],world[3],view[3];for(unsigned a=0;a<3;++a)local[a]=p[9+a]+p[a]*s[0]/16+p[3+a]*s[1]/16+p[6+a]*s[2]/16;
            gate_local(&parts[0].mat[0][0],local,world);gate_local(&global.Cam.v_mat[0][0],world,view);
            const float depth=-view[2],px=320*view[0]+320*depth,py=-240*view[1]+240*depth;
            any|=depth>1 && depth<10000 && px>=0 && px<=640*depth && py>=0 && py<=480*depth;
        }
        if(any)check(!(skip&2));++cull_cases;
    }
    check(!g1_mask_mismatch && !g1_visible_mismatch && !g1_mv_mismatch && !g1_g_mismatch && !g1_scale_mismatch);
    infos[1].be_flag=1;check(!visible(&infos[1]));gate_cull_checked(&model,(kStumpGateApp+2),iv,pv,inv,mv);check(!(gate_visible&2));
    infos[1].be_flag=9;
}
// Hand poses: em10HandSet / cEm10::setHand swap role 2 (448 -> 450) and role 3 (453 -> 454) in place.
static void hand_check() {
    swap_info(2,450);swap_info(3,454);
    check(re4dc_actor_role_source_bin(&model,&infos[2],2,2)==450 && re4dc_actor_role_source_bin(&model,&infos[3],2,3)==454);
    auto hands=plan();
    check(hands.immutable_asset_id[2]==kRe4dcGanadoStumpAsset+6 && hands.immutable_asset_id[3]==kRe4dcGanadoStumpAsset+7);
    check(hands.input[2].triangles==97 && hands.input[3].triangles==97 && hands.input[2].stream.data==ganado_var::input[6].stream.data);
    check(owner_ganado_palettes(&model,hands,output));
    for(unsigned r=2;r<4;++r)for(unsigned i=0;i<hands.input[r].palette_count*12;++i)check(std::isfinite(output[r][i]));
    swap_info(2,448);swap_info(3,453);
}
// Package refusals, room leave and the movie loan (the plan declines while the cell is gone, reads it again after).
extern "C" void re4dc_ganado_var_room_leave();
extern "C" unsigned re4dc_ganado_var_lend();
extern "C" void re4dc_ganado_var_return();
static void package_check(const char* good,const char* bad) {
    Re4dcActorPlan declined{};
    re4dc_ganado_var_room_leave();check(!ganado_var::cell);
    const unsigned fails=ganado_var::fails;
    host_package=bad;check(!re4dc_actor_plan_ganado(&model,&declined));check(ganado_var::fails==fails+1 && !ganado_var::cell);
    host_package="/nonexistent/ganado_var.re4gv";check(!re4dc_actor_plan_ganado(&model,&declined));check(ganado_var::fails==fails+2);
    re4dc_ganado_var_room_leave();check(!ganado_var::fails);  // room leave clears the refusal count
    host_package=good;const unsigned loads=ganado_var::loads;check(re4dc_actor_plan_ganado(&model,&declined));
    check(ganado_var::cell && ganado_var::loads==loads+1);
    check(re4dc_ganado_var_lend()==ganado_ps2_stump::file_bytes+ganado_ps2_stump::skin_total+32u && !ganado_var::cell);
    check(!re4dc_actor_plan_ganado(&model,&declined));check(!ganado_var::cell);  // lent: no read during the movie
    re4dc_ganado_var_return();check(re4dc_actor_plan_ganado(&model,&declined) && ganado_var::cell);
    check(host_allocs==host_frees+1);
}
static void run(const char* file,unsigned id) {
    setup(file,id);auto normal=plan();check(normal.immutable_asset_id[1]==18);check(normal.input[1].triangles==gc::chunks[2][1].triangles);
    check(owner_ganado_palettes(&model,normal,output));float original[4][256*12];std::memcpy(original,storage,sizeof(storage));
    Mtx original_pose[34];for(unsigned b=0;b<34;++b)std::memcpy(original_pose[b],parts[b].mat,sizeof(Mtx));
    swap_head(479);check(re4dc_actor_role_source_bin(&model,&infos[1],2,1)==479);auto stump=plan();
    check(stump.immutable_asset_id[1]==(kRe4dcGanadoStumpAsset+2) && stump.immutable_asset_id[0]==17);
    check(stump.input[1].triangles==90 && stump.input[1].palette_count==6 && stump.material_count==1 && stump.runs[1].material==0);
    check(ganado_var::cell && stump.input[1].uv.data==ganado_var::input[2].uv.data && owner_plan_app==(kStumpGateApp+2));
    check(stump.crc==0x65c6fe5a && stump.fnv==0x2593694e);check(live_head()==re4dc_material::Error::None);
    hand_check();
    check(!re4dc_ganado_early_ready(&model));check(!owner_ganado_palettes(&model,normal,output));
#if RE4DC_CROWD_FAR
    far_request=true;auto distant=plan();check(distant.immutable_asset_id[0]==17 && distant.immutable_asset_id[1]==(kRe4dcGanadoStumpAsset+2));far_request=false;
#endif
    for(unsigned pose=0;pose<4;++pose) {
        for(unsigned b=2;b<=4;++b){parts[b].mat[0][3]+=float(pose*13*b);parts[b].mat[1][3]-=float(pose*7);parts[b].mat[2][3]+=float(pose*11);}
        skin_check(stump);cull_check();
    }
    infos[1].be_flag=1;check(live_head()==re4dc_material::Error::None);infos[1].be_flag=11;check(live_head()==re4dc_material::Error::PassGroup);infos[1].be_flag=9;
    infos[1].uvU=1;check(live_head()==re4dc_material::Error::LiveModifier);infos[1].uvU=0;
    check(!actor_current_role(&model,&infos[1],2,0));check(!actor_current_role(&model,&infos[1],1,1));
    re4dc_actor_info_retire(&infos[1]);infos[1].tpl_addr=arena.data()+offset(445);re4dc_actor_info_adopt(&infos[1]);
    Re4dcActorPlan declined{};check(!re4dc_actor_plan_ganado(&model,&declined));
    infos[1].tpl_addr=arena.data()+offset(477);re4dc_actor_info_adopt(&infos[1]);check(re4dc_actor_plan_ganado(&model,&declined));
    swap_head(476);check(!re4dc_actor_plan_ganado(&model,&declined));
    for(unsigned b=0;b<34;++b)std::memcpy(parts[b].mat,original_pose[b],sizeof(Mtx));
    swap_head(478);auto restored=plan();check(restored.immutable_asset_id[1]==normal.immutable_asset_id[1]);
    check(restored.input[1].positions.data==normal.input[1].positions.data && restored.input[1].stream.data==normal.input[1].stream.data);
    check(!owner_ganado_palettes(&model,stump,output));check(owner_ganado_palettes(&model,restored,output));
    for(unsigned r=0;r<4;++r)check(!std::memcmp(original[r],storage[r],restored.input[r].palette_count*48));
    infos[1].pData=data(476);check(!re4dc_actor_plan_ganado(&model,&declined));infos[1].pData=data(478);
    swap_head(479);re4dc_actor_archive_retire(arena.data());check(!re4dc_actor_plan_ganado(&model,&declined));
    // A single unapproved normalized BIN byte fails at adoption, before relocation.
    setup(file,id);re4dc_actor_forget_all();
    std::ifstream f(file,std::ios::binary);arena.assign(std::istreambuf_iterator<char>(f),{});arena[offset(479)+100]^=1;
    re4dc_actor_archive_adopt(arena.data(),arena.data(),unsigned(arena.size()),2);
    bool admitted=false;for(const auto& a:re4dc_material::life::assets)admitted|=a.data==data(479);check(!admitted);
}
int main(int argc,char** argv) {
    check(argc==5);host_package=argv[3];run(argv[1],0x13);run(argv[2],0x15);
    setup(argv[2],0x15);swap_head(479);package_check(argv[3],argv[4]);
#if RE4DC_ACTOR_BIND_REUSE == 2
    check(abr_calls && abr_hits && !abr_bad);
#endif
    std::printf("PASS actual consumers: checks=%u posed_vertices=%u output_triangles=%u cull_cases=%u far=%u reuse=%u\n",checks,posed_vertices,output_triangles,cull_cases,RE4DC_CROWD_FAR,RE4DC_ACTOR_BIND_REUSE);
}
