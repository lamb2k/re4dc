// Synthetic driver around production WP29 loader/runtime and extracted pc core.
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <vector>
#include <cstdio>
#include <cstdarg>
#include "world_portal29.hpp"
#include "pvs23_proof.hpp"
#define RE4DC_WORLD_PORTAL29 1
#define RE4DC_PS2_INTERIOR_CULL 1
#define RE4DC_PS2_INTERIOR_ACTORS 0
#define RE4DC_GC_ASSET_GATE 0
#define RE4DC_SCREEN_WF 640.0f
#define RE4DC_SCREEN_HF 480.0f
#define O_RDONLY 0
using file_t=int;
using ssize_t=long;
constexpr file_t FILEHND_INVALID=-1;
static unsigned frame=1,epoch=1;
static bool scene_ok=true,opaque_ok=true,source_ok=true,heap_ok=true,file_ok=true,short_read=false;
static unsigned allocations=0,frees=0,source_checks=0;
static std::vector<unsigned char> file_bytes;
static unsigned read_offset=0;
unsigned re4dc_ui_frame(){return frame;}
int re4dc_static_heap_free(){return 1000000;}
void* re4dc_static_alloc(unsigned n){if(!heap_ok)return nullptr;++allocations;return std::malloc(n);}
extern "C" void* re4dc_world_portal29_alloc(unsigned n){return re4dc_static_alloc(n);}
void re4dc_static_free(void* p){if(p){++frees;std::free(p);}}
void re4dc_log(const char*,...){}
file_t fs_open(const char*,int){read_offset=0;return file_ok?1:FILEHND_INVALID;}
unsigned fs_total(file_t){return unsigned(file_bytes.size());}
ssize_t fs_read(file_t,void* dst,unsigned n){
    if(short_read)return 0;
    if(read_offset+n>file_bytes.size())return 0;
    std::memcpy(dst,file_bytes.data()+read_offset,n);read_offset+=n;return n;
}
int fs_close(file_t){return 0;}
// Fixtures deliberately use identity rotation, so this exact inverse stub
// isolates cell/portal logic from the unchanged general matrix inverse.
bool inverse(const float* v,float* out){
    for(unsigned r=0;r<3;++r)for(unsigned c=0;c<4;++c)out[4*r+c]=c==3?-v[4*r+3]:float(c==r);
    return v[0]==1 && v[5]==1 && v[10]==1;
}
namespace re4dc::vp { constexpr unsigned kCacheSlots=256; }
namespace pc {
struct Cell {float lo[3],hi[3];std::uint16_t first,count;};
struct Portal {std::uint32_t axis;float plane,u0,u1,v0,v1;};
#include "world_portal29_cells.inc"
constexpr float kSlack=64.0f;constexpr unsigned kMaxFr=24;
struct Plane{float n[3];};
struct Frustum{std::uint32_t axis;float plane;bool beyond_high;Plane edge[4];float an[4][3];};
struct State{
    bool ok=false,active=false;float eye[3]{};int cell=-1;unsigned nfr=0;Frustum* fr=nullptr;
    unsigned frame=~0U,setup_frame=~0U,done_frame=~0U;float corner=0;
    unsigned placements=0,clusters=0,meshlets=0,tests=0,active_frames=0,frames=0;PC_STATE_EXTRA
} st,trans;
struct Data{void* block=nullptr;const Cell* cells=nullptr;const Portal* portals=nullptr;bool lent=false;unsigned loads=0,fails=0,lends=0;}data;
constexpr unsigned kFrBytes=kMaxFr*sizeof(Frustum);
inline State& trans_state(){return trans;}
inline bool eye_of(const float* v,float e[3]){float inv[12];if(!inverse(v,inv))return false;e[0]=inv[3];e[1]=inv[7];e[2]=inv[11];return true;}
#include "portal29_pc_core.inc"
bool load(){return load_cells(data,st,trans,kFrBytes,kMaxFr);}
void unload(){wp29_clear();if(data.block)re4dc_static_free(data.block);data.block=nullptr;data.cells=nullptr;data.portals=nullptr;st.fr=nullptr;trans.fr=nullptr;st.active=trans.active=false;}
}
struct Mesh {unsigned first_part,part_count;float origin[3],step[3];};
struct Meta {unsigned crc,fnv;std::uint16_t width,height;std::uint8_t pass,cull,texture,reserved;};
struct Placement {unsigned mesh,placement;float affine[12];};
struct Head {unsigned part_count=2;};
struct Package{
    Head h;Mesh mesh[2]{{0,1,{0,0,0},{.001f,.001f,.001f}},{1,1,{0,0,0},{.001f,.001f,.001f}}};
    bool has_lod=true;bool lod()const{return has_lod;}const Head& header()const{return h;}const Mesh* meshes()const{return mesh;}
};
Meta meta[2]{{1,2,32,32,0,0,1,0},{3,4,32,32,0,0,1,0}};
Placement placements[2]{{0,0,{1,0,0,0,0,1,0,0,0,0,1,0}},{1,1,{1,0,0,0,0,1,0,0,0,0,1,0}}};
struct World{Package package;const Meta* parts=meta;const Placement* placements=::placements;unsigned nplacements=2,room=0x103;
    void* storage=reinterpret_cast<void*>(1);float view[12]{1,0,0,0,0,1,0,0,0,0,1,0};
    float projection[7]{0,1,0,1,0,-.001f,-10};float viewport[6]{0,0,640,480,0,1};}ps2w;
namespace dyn{constexpr unsigned kIds=16,kNone=255;const std::uint8_t id_data[2]={255,255};const std::uint8_t* ids=id_data;
    unsigned nids=2;std::uint8_t slot_of[kIds]={};}
int re4dc_ps2_placements_intact(unsigned,const unsigned char*,unsigned){++source_checks;return source_ok;}
int re4dc_pvs23_scene(unsigned out[2]){if(!scene_ok)return 0;out[0]=frame;out[1]=epoch;return 1;}
int re4dc_pvs23_opaque_ready(const unsigned* key,unsigned){return opaque_ok && key && !key[4];}
namespace proof23 {unsigned fpscr(){return 0;}}
#include "world_portal29_runtime.inc"

// Compile the production chunk selector twice: its stream and general loops.
// Ordinary view tests accept the synthetic mesh; real pc::grid_hidden supplies
// the portal rejects. This isolates portal composition from unchanged frusta.
namespace re4dc::render {
struct DrawBounds {float lo[3],hi[3];};
bool group_visible(const DrawBounds&,const float*,const float*,const float*,float,float,unsigned){return true;}
}
namespace lean {
constexpr unsigned kMode=0;
struct SgPlane {float a[4];};
struct Counters {unsigned skipped=0,cl_inside=0,sg_tests=0,sg_culled=0,sg_meshlets=0,sg_vskip=0,calls=0;}st,lst;
unsigned box_class(const float*,const float*,const float*,const float*,float,float,const float*){return 1;}
int box_mask(const float*,const float*,const float*,const float*,float,float){return 0;}
int box_mask_lean(const float*,const float*,const float*,const float*,float,float){return 0;}
void sg_coef(const float*,float,float*){}
void sg_coef_lean(const float*,float,SgPlane*){}
unsigned sg_select(const std::uint16_t*,unsigned,const float*,unsigned,std::uint16_t*,std::uint16_t*,unsigned&,unsigned&,unsigned&){return 0;}
unsigned sg_select_lean(const std::uint16_t*,unsigned,const SgPlane*,unsigned,std::uint16_t*,std::uint16_t*,unsigned&,unsigned&,unsigned&){return 0;}
}
static unsigned re4dc_sg_lean_on=1;
struct SelectStats {unsigned clusters_culled=0,clusters_visible=0,groups_culled=0,lod_draws[3]{};}stats;
struct Lod {unsigned first_cluster,cluster_count;};
struct Cluster {std::uint16_t bounds_min[3],bounds_max[3];unsigned first_level,level_count;};
struct Level {unsigned first_meshlet,meshlet_count;float error;};
struct Meshlet {std::uint16_t bounds_min[3],bounds_max[3];unsigned vertex_count;};
struct SelectPackage {
    Lod pl[1]{{0,2}};
    Cluster cl[2]{{{5000,2950,2000},{5100,3050,2100},0,1},{{2800,2800,1900},{5200,3200,2200},1,1}};
    Level lv[2]{{0,1,0},{1,2,0}};
    Meshlet ml[3]{{{5000,2950,2000},{5100,3050,2100},3},{{2900,2900,2000},{3100,3100,2100},3},{{4900,2900,2000},{5100,3100,2100},3}};
    bool lod()const{return true;}const Lod* part_lods()const{return pl;}const Cluster* clusters()const{return cl;}
    const Level* levels()const{return lv;}const Meshlet* meshlets()const{return ml;}
};
struct SelectorBase {
    struct Pick{std::uint16_t let;std::uint8_t nr,gmask,lo,hi,pad[2];};
    SelectPackage package;
    struct Params{float projection[7]{},viewport[6]{};unsigned cull=0;}p;
    float matrix[12]{1,0,0,0,0,1,0,0,0,0,1,0};const float* mvq=matrix;
    float near=10,cull_far=20000,lod_scale=1;
    unsigned part_index=0,sg_groups=0,pc_mode=1;const float* lean_am=nullptr;
    const std::uint8_t* sg=nullptr;const unsigned* ps2=nullptr;const std::uint8_t* pvs_set=nullptr;
    const float* wp29_wq=nullptr;bool lean_inside=true,sg_coef_ok=false,sg_lp_ok=false;
    float sg_coef[40]{};lean::SgPlane sg_lp[5]{};
};
#define RE4DC_PS2_PVS 1
#define RE4DC_SCENERY_STREAM 0
#define RE4DC_SG_SELECT_LEAN 0
struct GeneralSelector:SelectorBase {
#include "scenery_chunk_select.inc"
};
#undef RE4DC_SCENERY_STREAM
#undef RE4DC_SG_SELECT_LEAN
#define RE4DC_SCENERY_STREAM 1
#define RE4DC_SG_SELECT_LEAN 1
struct StreamSelector:SelectorBase {
#include "scenery_chunk_select.inc"
};

template<class Selector> static void selector_checks(){
    Selector s;SelectorBase::Pick picks[8];
    float matrix[21]={1,0,0,-3000,0,1,0,-3000,0,0,1,0};pc::abs_rows(matrix);
    assert(!s.chunk_ok());s.wp29_wq=matrix;assert(s.chunk_ok());
    const unsigned cl0=pc::st.clusters,ml0=pc::st.meshlets;
    assert(s.chunk_select(picks)==1 && picks[0].let==1 && picks[0].nr==255);
    assert(pc::st.clusters==cl0+1 && pc::st.meshlets==ml0+1);
    s.pc_mode=0;s.wp29_wq=nullptr;assert(s.chunk_ok());assert(s.chunk_select(picks)==3);
    s.pc_mode=1;s.wp29_wq=matrix;const std::uint8_t independent_pvs=1;s.pvs_set=&independent_pvs;assert(!s.chunk_ok());
}

static void put(std::vector<unsigned char>& b,unsigned off,unsigned v){std::memcpy(b.data()+off,&v,4);}
static void putf(std::vector<unsigned char>& b,unsigned off,float v){std::memcpy(b.data()+off,&v,4);}
static void checksum(std::vector<unsigned char>& b){
    const unsigned at=re4dc::portal29::word(b.data(),44),n=re4dc::portal29::word(b.data(),48);
    put(b,56,re4dc::portal29::crc(b.data()+at,n*8));put(b,60,0);put(b,60,re4dc::portal29::crc(b.data(),b.size(),true));
}
static std::vector<unsigned char> valid_cell(){
    std::vector<unsigned char>b(64+32+28+24+16,0);std::memcpy(b.data(),"PCL2",4);
    const unsigned w[]={0x103,0x1111,0x2222,4096,1,1,unsigned(b.size())};for(unsigned i=0;i<7;++i)put(b,4+4*i,w[i]);
    putf(b,32,100);put(b,36,1);put(b,40,re4dc::portal29::kMarker);put(b,44,148);put(b,48,2);put(b,52,1);
    const float outer[6]={-1000,-1000,-1000,1000,1000,1000};for(unsigned i=0;i<6;++i)putf(b,64+4*i,outer[i]);
    b[90]=1;for(unsigned i=0;i<3;++i){putf(b,96+4*i,-800);putf(b,108+4*i,800);}b[122]=1;
    put(b,124,2);putf(b,128,1000);putf(b,132,-200);putf(b,136,200);putf(b,140,-200);putf(b,144,200);
    put(b,148,0);put(b,152,0);put(b,156,1);put(b,160,1);checksum(b);return b;
}
static void load_good(){
    pc::unload();file_bytes=valid_cell();pc::st.ok=true;pc::adopt_live(0x103,0x1111,0x2222,4096);
    assert(pc::load());assert(pc::wp29_count==2);
}
static unsigned checks=0;
static void expect(bool value){assert(value);++checks;}
int main(){
    const auto good=valid_cell();re4dc::portal29::Layout h;
    expect(re4dc::portal29::layout(good.data(),good.size(),h));expect(h.witnesses==2 && h.room==0x103);
    for(unsigned n=0;n<good.size();++n)expect(!re4dc::portal29::layout(good.data(),n,h));
    for(unsigned off=0;off<good.size();++off){auto b=good;b[off]^=1;expect(!re4dc::portal29::layout(b.data(),b.size(),h));}
    for(unsigned off:{20U,24U,36U,44U,48U,52U}){auto b=good;put(b,off,0xffffffffU);expect(!re4dc::portal29::layout(b.data(),b.size(),h));}
    for(unsigned off:{32U,64U,96U,128U,132U}){auto b=good;put(b,off,0x7fc00000U);checksum(b);expect(!re4dc::portal29::layout(b.data(),b.size(),h));}
    {auto b=good;put(b,124,3);checksum(b);expect(!re4dc::portal29::layout(b.data(),b.size(),h));}
    {auto b=good;putf(b,96,-900);checksum(b);expect(!re4dc::portal29::layout(b.data(),b.size(),h));}
    {auto b=good;put(b,156,0);put(b,160,0);checksum(b);expect(!re4dc::portal29::layout(b.data(),b.size(),h));}
    {auto b=good;b[90]=2;checksum(b);expect(!re4dc::portal29::layout(b.data(),b.size(),h));}
    load_good();
    pc::setup(ps2w.view,ps2w.projection,10);expect(pc::st.active);
    selector_checks<GeneralSelector>();selector_checks<StreamSelector>();checks+=16;
    float c[3]={0,0,2000},half[3]={20,20,20};expect(pc::hidden(c,half)==0);
    c[0]=2000;expect(pc::hidden(c,half)>0);c[0]=0;c[2]=0;expect(pc::hidden(c,half)<0);
    pc::setup(ps2w.view,ps2w.projection,100);expect(!pc::st.active); // near envelope too large
    pc::trans.ok=true;pc::setup_state(pc::trans,ps2w.view,ps2w.projection,10);expect(!pc::trans.active);
    ps2w.view[3]=-900;pc::setup(ps2w.view,ps2w.projection,10);expect(!pc::st.active);ps2w.view[3]=0;
    const unsigned key[6]={1,2,32,32,0,0};
    wp29::begin(0,ps2w.projection,10,20000);expect(wp29::candidate);wp29::activate();expect(!pc::st.active);
    wp29::finish(0,0,true,key);wp29::activate();expect(!pc::st.active);
    wp29::finish(1,1,false,key);wp29::activate();expect(!pc::st.active);
    opaque_ok=false;wp29::finish(1,1,true,key);wp29::activate();expect(!pc::st.active);opaque_ok=true;
    wp29::finish(1,1,true,key);wp29::activate();expect(pc::st.active && wp29::receipts.count==2);
    wp29::finish(1,1,true,key);expect(wp29::receipts.count==2);
    source_ok=false;wp29::activate();expect(!pc::st.active && !wp29::receipts.count);source_ok=true;
    wp29::begin(0,ps2w.projection,10,20000);wp29::finish(0,0,true,key);wp29::finish(1,1,true,key);++epoch;
    wp29::activate();expect(!pc::st.active);
    wp29::begin(0,ps2w.projection,10,20000);wp29::finish(0,0,true,key);wp29::finish(1,1,true,key);
    ps2w.view[3]=1;wp29::activate();expect(!pc::st.active);ps2w.view[3]=0;
    wp29::begin(0,ps2w.projection,10,20000);wp29::finish(0,0,true,key);wp29::finish(1,1,true,key);
    wp29::begin(1,ps2w.projection,10,19000);wp29::activate();expect(!pc::st.active && !wp29::receipts.count);
    ++frame;wp29::begin(0,ps2w.projection,10,20000);expect(!wp29::receipts.count);
    scene_ok=false;wp29::begin(0,ps2w.projection,10,20000);expect(!pc::st.active && !wp29::candidate);scene_ok=true;
    pc::unload();expect(pc::wp29_count==0 && !pc::st.active);
    for(unsigned mode=0;mode<4;++mode){file_bytes=good;pc::st.ok=true;pc::adopt_live(0x103,0x1111,0x2222,4096);
        if(mode==0)file_ok=false;if(mode==1)heap_ok=false;if(mode==2)short_read=true;if(mode==3)pc::live_sidecar=0x9999;
        expect(!pc::load() && !pc::data.block && !pc::wp29_count);file_ok=heap_ok=true;short_read=false;}
    load_good();const unsigned gen=pc::wp29_generation;pc::unload();load_good();expect(pc::wp29_generation!=gen);
    pc::unload();expect(allocations==frees);
    std::printf("portal29 production loader/runtime: %u checks PASS; allocation balance %u/%u\n",checks,allocations,frees);
}
