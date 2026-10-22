// Executes extracted, unchanged production helpers and the actual arena ledger.
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <cmath>
#include <vector>
#include <stdexcept>
#include <sys/mman.h>
#include <unistd.h>
#define RE4DC_MOVIE_WORLD_ARENA 1
#define RE4DC_MOVIE_WORLD_ARENA_S30 1
#define RE4DC_PS2_WORLD_DYNAMIC 1
#define RE4DC_PS2_WORLD_PARTS 1
#define RE4DC_PS2_PASS_MASK 1
#define RE4DC_MESH_FASTPATH 1
#define RE4DC_D349_RENDERER_STACK 1
#define RE4DC_PVR_STREAM 1
#define RE4DC_PVR_PIPELINE 2
#define RE4DC_PVR_RECOVER 1
#define O_RDONLY 0
#include "movie_world_arena.h"
#include "movie_world_arena_lifecycle.inc"
static unsigned checks;
#define CHECK(x) do{++checks;if(!(x)){std::fprintf(stderr,"check failed line %d: %s\n",__LINE__,#x);std::abort();}}while(0)
struct alignas(32) Room4Cell {unsigned magic,generation,bytes,reserved[5];};
constexpr unsigned kRoom4Magic=0x57364834;
struct {bool live;unsigned generation;} room4;
struct HeapInfo {int handle;uintptr_t start,end;} Heap[13];
static bool heap_active=true;
int memCheckHeapActive(unsigned i){return i<13&&heap_active;}
extern "C" void re4dc_log(const char*,...){}
extern "C" void re4dc_missing(const char* s){throw std::runtime_error(s);}
static bool ready=true,direct_open=false,draining_parts=false,source_draws_finished=false,stream_aborted=false,stream_scene=false;
static void* movie_texture=nullptr;
static bool movie_background=false,movie_picture=false;
static unsigned vram_frees=0;
void pvr_mem_free(void* p){CHECK(p);++vram_frees;}
static unsigned present_failures=0;
static bool present_pending=false,hold_present=false,hold_ta=false,hold_render=false;
static unsigned reset_calls=0,discard_calls=0,close_calls=0,fence_calls=0;
struct {bool ta_busy=false,render_busy=false;} pvr_state;
void reset_deferred(){++reset_calls;}
void stream_close(bool shown){CHECK(!shown);++close_calls;stream_scene=false;present_pending=true;}
void present_fence(){++fence_calls;if(!hold_present)present_pending=false;}
bool pvr_present_pending(){return present_pending;}
namespace pvr_ready {
unsigned ta_timeouts=0,render_timeouts=0;
bool wait_clear(bool& busy,const char*,char reason,unsigned&){
    if((reason=='K'&&hold_ta)||(reason=='Q'&&hold_render))return false;
    busy=false;return true;
}
}
extern "C" void re4dc_ps2_world_movie_discard(){++discard_calls;}
static unsigned io_depth=0;
struct Re4dcIoScope{Re4dcIoScope(){++io_depth;}~Re4dcIoScope(){--io_depth;}};
constexpr unsigned kLutBytes=2048,kGatherBytes=3072;
struct Ps2Part{uint32_t crc,fnv;uint16_t width,height;uint8_t pass,cull;uint16_t reserved;};
struct Ps2Placement{uint16_t mesh,placement;float affine[12];};
struct Ps2Head{char magic[4];uint32_t version,placements,parts,meshes,crc,reserved[2];};
namespace re4dc {namespace room{struct CompactVertex12{unsigned char bytes[12];};}
namespace render{bool is_finite(float f){return std::isfinite(f);}}
namespace vp{void build_lut(uint32_t* p){for(unsigned i=0;i<512;++i)p[i]=i;}}}
static bool adopt_fail=false;
struct Package {
    struct Header{unsigned part_count=16,mesh_count=1;} h;
    struct Mesh{unsigned part_count=16,first_part=0;} mesh;
    bool live=false;
    bool adopt(const void* p,unsigned n,bool,bool){CHECK(p&&(n==797056||n==1537920));live=!adopt_fail;return live;}
    void close(){live=false;}
    const Header& header()const{return h;}
    const Mesh* meshes()const{return &mesh;}
};
struct Ps2World {
    Package package;unsigned char* storage=nullptr;unsigned bytes=0;
    const Ps2Part* parts=nullptr;const Ps2Placement* placements=nullptr;unsigned nplacements=0;
    const uint32_t* lut=nullptr;re4dc::room::CompactVertex12* gather=nullptr;
    bool camera=false,attempted=false,masked=false;unsigned room=0x11f,want=0x11f;
    static constexpr unsigned kMaskPlacements=2048;uint8_t pass_mask[kMaskPlacements]{};
}ps2w;
movie_world::Ledger ps2_movie;
struct MovieWorldFiles{unsigned mesh=0,side=0,mesh_crc=0,mesh_fnv=0,side_crc=0,side_fnv=0;}ps2_movie_files;
struct MovieWorldRead{MovieWorldRead(){++ps2_movie.readers;}~MovieWorldRead(){--ps2_movie.readers;}};
namespace dyn {
#include "production_dynamic_types.inc"
unsigned char* block=nullptr;Slot* slots=nullptr;unsigned nslots=0,frame=9,nmoved=3;
uint8_t state[250];
void reset(){block=nullptr;slots=nullptr;nslots=0;}
}
using file_t=int;
constexpr int FILEHND_INVALID=-1;
static std::vector<unsigned char> mesh_file,side_file;
static unsigned reads=0,opens=0,world_frees=0,heap_allocs=0,heap_frees=0;
static int fail_reads=0;
static bool fail_open=false,stale_on_read=false;
static void* region;static size_t region_bytes,rw_bytes;static unsigned char* heap_begin;static unsigned char* saved_world;
int fs_open(const char* p,int){++opens;return fail_open?-1:std::strstr(p,".re4mesh")?1:2;}
ssize_t fs_total(int f){return f==1?ssize_t(mesh_file.size()):ssize_t(side_file.size());}
void fs_close(int){}
bool read_package(file_t f,unsigned char* out,unsigned n,unsigned head){
    CHECK(head==0&&io_depth==1);++reads;
    if(fail_reads){--fail_reads;return false;}
    auto& v=f==1?mesh_file:side_file;CHECK(v.size()==n);std::memcpy(out,v.data(),n);
    if(stale_on_read){++room4.generation;CHECK(mprotect(heap_begin,rw_bytes,PROT_NONE)==0);}
    return true;
}
void re4dc_static_free(void* p){CHECK(p==saved_world);++world_frees;}
static unsigned service_token=0;
extern "C" int re4dc_movie_world_active(){return service_token!=0;}
extern "C" void* re4dc_movie_world_sep_alloc(unsigned n){return re4dc_ps2_mesh_movie_alloc(service_token,n);}
extern "C" int re4dc_movie_world_sep_free(void* p){return re4dc_ps2_mesh_movie_free(service_token,p);}
void* re4dc_ui_stage_alloc(unsigned n){++heap_allocs;return std::malloc(n);}
void re4dc_ui_stage_free(void* p){++heap_frees;std::free(p);}
static void* movie_sep_raw;static void* movie_sep;unsigned re4dc_movie_stream_staged;
#include "production_helpers.inc"

void* cell(unsigned offset,unsigned bytes){
    auto* c=reinterpret_cast<Room4Cell*>(heap_begin+offset);*c={kRoom4Magic,room4.generation,bytes,{}};return c+1;
}
void initialize(unsigned room=0x11f){
    CHECK(mprotect(heap_begin,rw_bytes,PROT_READ|PROT_WRITE)==0);
    room4={true,7};heap_active=true;for(auto& h:Heap)h={-1,0,0};Heap[4]={1,uintptr_t(heap_begin),uintptr_t(heap_begin+rw_bytes)};
    ps2_movie={};ps2w={};ready=true;direct_open=draining_parts=stream_aborted=source_draws_finished=stream_scene=false;
    movie_texture=nullptr;movie_background=movie_picture=false;vram_frees=0;present_pending=hold_present=hold_ta=hold_render=false;present_failures=0;pvr_state={};
    reset_calls=discard_calls=close_calls=fence_calls=reads=opens=world_frees=heap_allocs=heap_frees=0;
    fail_reads=0;fail_open=adopt_fail=stale_on_read=false;service_token=0;movie_sep=movie_sep_raw=nullptr;re4dc_movie_stream_staged=0;
    const unsigned mb=room==0x100?1537920:797056,sb=room==0x100?19612:9076,cap=room==0x100?1562656:811264;
    const unsigned np=room==0x100?304:16,placements=room==0x100?283:169;
    ps2w.room=ps2w.want=room;ps2w.package.h.part_count=np;ps2w.package.mesh.part_count=np;
    saved_world=static_cast<unsigned char*>(cell(0,cap));ps2w.storage=saved_world;ps2w.bytes=cap;
    mesh_file.assign(mb,0x63);side_file.assign(sb,0);
    auto* h=reinterpret_cast<Ps2Head*>(side_file.data());std::memcpy(h->magic,"R4PW",4);h->version=1;h->parts=np;h->meshes=1;h->placements=placements;
    auto* parts=reinterpret_cast<Ps2Part*>(side_file.data()+32);
    for(unsigned i=0;i<np;++i){parts[i].width=parts[i].height=16;parts[i].pass=i%3;parts[i].cull=i%3;}
    h->crc=ps2_crc32(side_file.data()+32,sb-32);
    std::memcpy(saved_world,mesh_file.data(),mesh_file.size());std::memcpy(saved_world+mb,side_file.data(),side_file.size());
    CHECK(ps2_movie.capture(saved_world,cap,7));ps2w.package.live=true;
    ps2w.parts=reinterpret_cast<const Ps2Part*>(saved_world+mb+32);
    ps2w.placements=reinterpret_cast<const Ps2Placement*>(ps2w.parts+np);ps2w.nplacements=placements;ps2w.camera=ps2w.masked=true;
    ps2_movie_files={mb,sb,ps2_crc32(mesh_file.data(),mesh_file.size()),movie_world::fnv(mesh_file.data(),mesh_file.size()),ps2_crc32(side_file.data(),side_file.size()),movie_world::fnv(side_file.data(),side_file.size())};
    dyn::block=static_cast<unsigned char*>(cell(cap+64,64));dyn::nslots=1;
    dyn::slots=static_cast<dyn::Slot*>(cell(cap+160,sizeof(dyn::Slot)));*dyn::slots={};
    dyn::slots->serial=0xabc;dyn::slots->rest[3]=71;dyn::slots->source=true;dyn::slots->nparts=1;dyn::slots->pose_offset=56;
    const unsigned part_bytes=sizeof(dyn::PartPose)+(RE4DC_PS2_WORLD_ROOT_POSE?96U:0U);
    dyn::slots->parts=static_cast<dyn::PartPose*>(cell(cap+416,part_bytes));
    std::memset(dyn::slots->parts,0,part_bytes);dyn::slots->parts->pose[5]=42;
#if RE4DC_PS2_WORLD_ROOT_POSE
    dyn::slots->root_matrix_offset=65;
    auto* root=reinterpret_cast<float*>(dyn::slots->parts+1);
    for(unsigned i=0;i<24;++i)root[i]=float(i+1);
#endif
    dyn::frame=9;dyn::nmoved=3;std::memset(dyn::state,4,sizeof(dyn::state));
}
std::vector<void*> allocate_player(unsigned token){
    const unsigned sizes[]={16416,49152,32768,52,65536,716,55296,13824,13824,55296,13824,13824};
    std::vector<void*> p;
    for(unsigned n:sizes){void* v=re4dc_ps2_mesh_movie_alloc(token,n);CHECK(v);CHECK(!(uintptr_t(v)&31));std::memset(v,0xaa,n);p.push_back(v);}
    return p;
}
void free_player(unsigned token,const std::vector<void*>& p){for(void* v:p)CHECK(re4dc_ps2_mesh_movie_free(token,v));}
void test_dynamic_part_cell_contract(){
    for(unsigned count: {1U,2U,255U}){
        initialize(0x100);
        const unsigned bytes=count*sizeof(dyn::PartPose)+
            ((RE4DC_PS2_WORLD_ROOT_POSE && count==1)?96U:0U);
        // Keep this expected layout independent of the production sizing helper.
        dyn::slots->nparts=count;
        dyn::slots->parts=static_cast<dyn::PartPose*>(cell(1562656+416,bytes));
        std::memset(dyn::slots->parts,0x39,bytes);
        auto* header=reinterpret_cast<Room4Cell*>(dyn::slots->parts)-1;
        CHECK(ps2_movie_dyn_valid());
        --header->bytes;CHECK(!ps2_movie_dyn_valid());++header->bytes;
        ++header->bytes;CHECK(!ps2_movie_dyn_valid());--header->bytes;
        ++header->generation;CHECK(!ps2_movie_dyn_valid());--header->generation;
#if RE4DC_PS2_WORLD_ROOT_POSE
        if(count==1){
            header->bytes-=96;CHECK(!ps2_movie_dyn_valid());header->bytes+=96;
            // A refused/singular witness still owns the same allocation size.
            dyn::slots->root_matrix_offset=~0U;CHECK(ps2_movie_dyn_valid());
        }
#endif
        std::vector<unsigned char> saved(bytes);
        std::memcpy(saved.data(),dyn::slots->parts,bytes);
        const auto slot=*dyn::slots;
        const auto token=re4dc_ps2_mesh_movie_borrow(0x10030);CHECK(token);
        CHECK(re4dc_ps2_mesh_movie_return(token,0)==1);
        CHECK(!std::memcmp(dyn::slots,&slot,sizeof(slot)));
        CHECK(!std::memcmp(dyn::slots->parts,saved.data(),bytes));
    }
}
void test_s30_roundtrip_and_failures(){
    initialize(0x100);
    CHECK(!re4dc_ps2_mesh_movie_borrow(0x10020));CHECK(!re4dc_ps2_mesh_movie_borrow(0x11f10));
    const auto slot=*dyn::slots;const auto pose=*dyn::slots->parts;
    auto token=re4dc_ps2_mesh_movie_borrow(0x10030);CHECK(token);
    auto allocations=allocate_player(token);service_token=token;
    void* sep=re4dc_movie_sep_alloc(32,32768);CHECK(sep&&ps2_movie.live==13);
    free_player(token,allocations);re4dc_movie_sep_free(sep);service_token=0;
    CHECK(re4dc_ps2_mesh_movie_return(token,0)==1);
    CHECK(reads==2&&opens==2&&ps2w.nplacements==283&&ps2w.package.live&&ps2w.masked);
    CHECK(!std::memcmp(saved_world,mesh_file.data(),mesh_file.size()));
    CHECK(!std::memcmp(saved_world+1537920,side_file.data(),side_file.size()));
    CHECK(!std::memcmp(dyn::slots,&slot,sizeof(slot)));CHECK(!std::memcmp(dyn::slots->parts,&pose,sizeof(pose)));
    CHECK(heap_allocs==0&&heap_frees==0&&world_frees==0);
    for(unsigned bad=0;bad<3;++bad){
        initialize(0x100);
        if(bad==0)--ps2_movie_files.side;
        if(bad==1){ps2_movie_files.mesh-=32;ps2_movie_files.side+=32;}
        if(bad==2)ps2w.want=0x101;
        CHECK(!re4dc_ps2_mesh_movie_borrow(0x10030));CHECK(!discard_calls&&!reads);
    }
    for(unsigned fault=0;fault<4;++fault){
        initialize(0x100);token=re4dc_ps2_mesh_movie_borrow(0x10030);CHECK(token);
        if(fault==0)mesh_file[400000]^=1;
        if(fault==1)side_file[9000]^=1;
        if(fault==2)fail_reads=20;
        if(fault==3)stale_on_read=true;
        CHECK(re4dc_ps2_mesh_movie_return(token,0)==-1);
        CHECK(!ps2w.parts&&!ps2w.package.live&&!world_frees);
        CHECK(mprotect(heap_begin,rw_bytes,PROT_READ|PROT_WRITE)==0);
    }
}
void test_roundtrip_and_slots(){
    initialize();stream_scene=true;pvr_state={true,true};
    auto original_slot=*dyn::slots;auto original_pose=*dyn::slots->parts;
    const unsigned token=re4dc_ps2_mesh_movie_borrow(0x11f10);CHECK(token);CHECK(!ps2w.package.live&&!ps2w.parts&&!ps2w.camera);
    CHECK(stream_aborted&&source_draws_finished&&close_calls==1&&fence_calls==1);CHECK(re4dc_ps2_mesh_movie_blocked());
    auto p=allocate_player(token);service_token=token;
    void* sep=re4dc_movie_sep_alloc(32,32768);CHECK(sep);CHECK(re4dc_movie_stream_staged==32800);
    CHECK(ps2_movie.used==363360&&ps2_movie.nslots==13&&ps2_movie.live==13);
    CHECK(!re4dc_ps2_mesh_movie_alloc(token,52));CHECK(!re4dc_ps2_mesh_movie_alloc(token,1));
    CHECK(!re4dc_ps2_mesh_movie_free(token,static_cast<unsigned char*>(p[0])+32));
    CHECK(re4dc_ps2_mesh_movie_return(token,0)==-1);CHECK(reads==0);
    CHECK(!re4dc_movie_sep_alloc(32,32768));re4dc_movie_sep_free(sep);CHECK(!movie_sep&&!re4dc_movie_stream_staged);
    free_player(token,p);CHECK(!re4dc_ps2_mesh_movie_free(token,p[0]));
    ++ps2_movie.readers;CHECK(re4dc_ps2_mesh_movie_return(token,0)==-1);--ps2_movie.readers;
    CHECK(re4dc_ps2_mesh_movie_return(token,0)==1);service_token=0;
    CHECK(reads==2&&opens==2&&ps2w.package.live&&ps2w.parts&&ps2w.masked&&!ps2w.camera);
    CHECK(!std::memcmp(dyn::slots,&original_slot,sizeof(original_slot)));CHECK(!std::memcmp(dyn::slots->parts,&original_pose,sizeof(original_pose)));
    CHECK(dyn::frame==~0u&&dyn::nmoved==0&&dyn::state[0]==0);CHECK(world_frees==0&&heap_allocs==0&&heap_frees==0);
    CHECK(!std::memcmp(saved_world,mesh_file.data(),mesh_file.size()));CHECK(!std::memcmp(saved_world+797056,side_file.data(),side_file.size()));
    const unsigned again=re4dc_ps2_mesh_movie_borrow(0x11f11);CHECK(again&&again!=token);
    CHECK(!re4dc_ps2_mesh_movie_alloc(token,52));CHECK(!re4dc_ps2_mesh_movie_free(token,p[0]));
    CHECK(re4dc_ps2_mesh_movie_return(again,1)==0);CHECK(reads==2&&world_frees==0);
    re4dc_ps2_mesh_retire();CHECK(world_frees==1);re4dc_ps2_mesh_retire();CHECK(world_frees==1);
}
void test_declines(){
    initialize();const unsigned hash=ps2_crc32(saved_world,811264);
    CHECK(!re4dc_ps2_mesh_movie_borrow(0x11f12));CHECK(!re4dc_ps2_mesh_movie_borrow(0x1011f10));
    direct_open=true;CHECK(!re4dc_ps2_mesh_movie_borrow(0x11f10));CHECK(reset_calls==0);direct_open=false;
    draining_parts=true;CHECK(!re4dc_ps2_mesh_movie_borrow(0x11f10));CHECK(reset_calls==0);draining_parts=false;
    ps2_movie.readers=1;CHECK(!re4dc_ps2_mesh_movie_borrow(0x11f10));CHECK(reset_calls==0);ps2_movie.readers=0;
    hold_present=present_pending=true;CHECK(!re4dc_ps2_mesh_movie_borrow(0x11f10));hold_present=present_pending=false;
    hold_ta=true;CHECK(!re4dc_ps2_mesh_movie_borrow(0x11f10));hold_ta=false;
    hold_render=true;CHECK(!re4dc_ps2_mesh_movie_borrow(0x11f10));hold_render=false;
    present_failures=1;CHECK(!re4dc_ps2_mesh_movie_borrow(0x11f10));present_failures=0;
    CHECK(ps2_movie.phase==movie_world::Phase::ready&&ps2w.package.live&&ps2w.parts);
    CHECK(hash==ps2_crc32(saved_world,811264)&&world_frees==0&&reads==0);
    // Equal padded total cannot certify the exact on-disc layout: decline
    // before discarding a frame or overwriting the retained payload.
    for(unsigned variant=0;variant<3;++variant){
        initialize();const unsigned before=ps2_crc32(saved_world,811264);
        if(variant==0){ps2_movie_files.mesh-=32;ps2_movie_files.side+=32;}
        if(variant==1)--ps2_movie_files.side;
        if(variant==2)++ps2_movie_files.side;
        CHECK(!re4dc_ps2_mesh_movie_borrow(0x11f10));
        CHECK(ps2_movie.phase==movie_world::Phase::ready&&ps2w.package.live);
        CHECK(!reset_calls&&!discard_calls&&!fence_calls&&!reads&&!world_frees);
        CHECK(ps2_crc32(saved_world,811264)==before);
    }
    initialize();auto* header=reinterpret_cast<Room4Cell*>(dyn::slots)-1;++header->generation;
    CHECK(!re4dc_ps2_mesh_movie_borrow(0x11f10));
}
void test_restore_faults(){
    initialize();auto token=re4dc_ps2_mesh_movie_borrow(0x11f10);CHECK(token);fail_reads=1;
    CHECK(re4dc_ps2_mesh_movie_return(token,0)==1);CHECK(opens==4&&reads==3); // one resource-only retry
    initialize();token=re4dc_ps2_mesh_movie_borrow(0x11f10);CHECK(token);fail_reads=20;
    CHECK(re4dc_ps2_mesh_movie_return(token,0)==-1);CHECK(opens==4&&reads==2);CHECK(!ps2w.parts&&!ps2w.package.live&&world_frees==0);
    CHECK(ps2_movie.phase==movie_world::Phase::failed&&re4dc_ps2_mesh_movie_blocked());
    bool halted=false;try{re4dc_ps2_mesh_retire();}catch(const std::runtime_error&){halted=true;}CHECK(halted&&world_frees==0);
    initialize();token=re4dc_ps2_mesh_movie_borrow(0x11f11);CHECK(token);mesh_file[400000]^=1;
    CHECK(re4dc_ps2_mesh_movie_return(token,0)==-1);CHECK(opens==4&&reads==4&&!ps2w.parts); // whole-file body identity
    initialize();token=re4dc_ps2_mesh_movie_borrow(0x11f11);CHECK(token);side_file[7000]^=1;
    CHECK(re4dc_ps2_mesh_movie_return(token,0)==-1);CHECK(opens==4&&reads==4&&!ps2w.parts);
    initialize();token=re4dc_ps2_mesh_movie_borrow(0x11f10);CHECK(token);adopt_fail=true;
    CHECK(re4dc_ps2_mesh_movie_return(token,0)==-1);CHECK(opens==4&&!ps2w.package.live);
    initialize();token=re4dc_ps2_mesh_movie_borrow(0x11f10);CHECK(token);fail_open=true;
    CHECK(re4dc_ps2_mesh_movie_return(token,0)==-1);CHECK(opens==4&&reads==0);
}
void test_protected_stale_and_boundaries(){
    initialize();auto token=re4dc_ps2_mesh_movie_borrow(0x11f10);CHECK(token);void* v=re4dc_ps2_mesh_movie_alloc(token,52);CHECK(v);
    ++room4.generation;CHECK(mprotect(heap_begin,rw_bytes,PROT_NONE)==0);
    CHECK(!re4dc_room4_cell_valid(saved_world,811264,7));CHECK(!re4dc_ps2_mesh_movie_valid(token));
    CHECK(!re4dc_ps2_mesh_movie_alloc(token,716));CHECK(!re4dc_ps2_mesh_movie_free(token,v));CHECK(re4dc_ps2_mesh_movie_return(token,0)==-1);
    CHECK(reads==0&&world_frees==0);CHECK(mprotect(heap_begin,rw_bytes,PROT_READ|PROT_WRITE)==0);
    initialize();room4.live=false;CHECK(mprotect(heap_begin,rw_bytes,PROT_NONE)==0);CHECK(!re4dc_room4_cell_valid(saved_world,0,7));
    CHECK(mprotect(heap_begin,rw_bytes,PROT_READ|PROT_WRITE)==0);initialize();Heap[4].handle=-1;
    CHECK(mprotect(heap_begin,rw_bytes,PROT_NONE)==0);CHECK(!re4dc_room4_cell_valid(saved_world,0,7));
    CHECK(mprotect(heap_begin,rw_bytes,PROT_READ|PROT_WRITE)==0);initialize();
    CHECK(!re4dc_room4_cell_valid(heap_begin,1,7));CHECK(!re4dc_room4_cell_valid(heap_begin+rw_bytes,1,7));CHECK(!re4dc_room4_cell_valid(saved_world,0xffffffff,7));
    token=re4dc_ps2_mesh_movie_borrow(0x11f10);CHECK(token);stale_on_read=true;
    CHECK(re4dc_ps2_mesh_movie_return(token,0)==-1);CHECK(reads==1&&world_frees==0&&!ps2w.parts);
    CHECK(mprotect(heap_begin,rw_bytes,PROT_READ|PROT_WRITE)==0);
}
void test_every_partial_allocation_and_service(){
    for(unsigned count=0;count<=12;++count){
        initialize();const unsigned token=re4dc_ps2_mesh_movie_borrow(0x11f10);CHECK(token);
        const unsigned sizes[]={16416,49152,32768,52,65536,716,55296,13824,13824,55296,13824,13824};
        std::vector<void*> p;for(unsigned i=0;i<count;++i){void* v=re4dc_ps2_mesh_movie_alloc(token,sizes[i]);CHECK(v);p.push_back(v);}
        free_player(token,p);CHECK(re4dc_ps2_mesh_movie_return(token,0)==1);CHECK(world_frees==0&&heap_frees==0&&heap_allocs==0);
    }
    initialize();service_token=re4dc_ps2_mesh_movie_borrow(0x11f10);CHECK(service_token);
    CHECK(!re4dc_movie_sep_alloc(64,32768));CHECK(!re4dc_movie_sep_alloc(16,32768));CHECK(!re4dc_movie_sep_alloc(32,1));CHECK(heap_allocs==0);
    bool halted=false;try{re4dc_movie_sep_free(saved_world+32);}catch(const std::runtime_error&){halted=true;}CHECK(halted&&heap_frees==0);
    CHECK(re4dc_ps2_mesh_movie_return(service_token,1)==0);service_token=0;
    void* sep=re4dc_movie_sep_alloc(32,32768);CHECK(sep&&heap_allocs==1);re4dc_movie_sep_free(sep);CHECK(heap_frees==1); // ordinary path unchanged
    movie_world::Ledger l;CHECK(!l.capture(saved_world,363359,7));CHECK(!l.capture(saved_world+1,811264,7));
}
// The real Movie aggregate, common finish, cancellation and pre-retire hook
// execute here; only device calls and unrelated cache-return/logging are adapted.
#define RE4DC_MOVIE_STAGE_ORDER 1
#define RE4DC_MOVIE_HEAP_EVICT 1
#define RE4DC_MOVIE_DISC_QUIET 1
#define RE4DC_ROUTE_MOVIE_DIAG 1
namespace player {
constexpr unsigned MaxAllocs=16,MaxReserve=12;
struct plm_buffer_t{};struct plm_video_t{};struct plm_frame_t{};
using snd_stream_hnd_t=int;
constexpr int RE4DC_MOVIE_EOF=1,RE4DC_MOVIE_SKIP=2,RE4DC_MOVIE_ERROR=3,RE4DC_MOVIE_CANCEL=4;
bool stream_initialized=false,stream_active=false,texture_alive=false,texture_closes=true;
unsigned texture_close_calls=0,shutdown_calls=0,stopped=0,destroyed=0,terminals=0,returned_cache=0;
void (*destroy_yield_hook)()=nullptr;
int re4dc_movie_disc_owner=0;
unsigned re4dc_ui_movie_presented(){return 0;}
unsigned re4dc_movie_stream_active(){return stream_active?1:0;}
int re4dc_movie_stream_initialized(){return stream_initialized;}
void snd_stream_stop(int){++stopped;}
void snd_stream_destroy(int){++destroyed;if(destroy_yield_hook)destroy_yield_hook();stream_active=false;}
void snd_stream_shutdown(){++shutdown_calls;if(movie_sep)re4dc_movie_sep_free(movie_sep);stream_initialized=false;}
int re4dc_ui_movie_close(){++texture_close_calls;if(texture_closes){texture_alive=false;movie_texture=nullptr;return 1;}return 0;}
int re4dc_ui_movie_try_close(){const int ok=::re4dc_ui_movie_try_close();if(ok)texture_alive=false;return ok;}
void thd_sleep(unsigned){}
void release_reserved(unsigned n){CHECK(n==0);}
int return_cache(unsigned* b,unsigned* r){++returned_cache;*b=*r=0;return 0;}
auto re4dc_model_return_retained=&return_cache;
unsigned long long timer_us_gettime64(){return 1000;}
void memory(const char*){}
void movie_state(int,int){++terminals;}
#include "production_player.inc"
void setup(){
    initialize();m=Movie{};movie_world_token=0;movie_scope=0;movie_epoch=1;movie_readers=0;movie_full_call=movie_retiring=movie_finishing=false;destroy_yield_hook=nullptr;
    stream_initialized=stream_active=texture_alive=texture_closes=true;
    texture_close_calls=shutdown_calls=stopped=destroyed=terminals=returned_cache=0;
    const unsigned token=re4dc_ps2_mesh_movie_borrow(0x11f10);CHECK(token);movie_world_token=service_token=token;
    const auto p=allocate_player(token);for(void* v:p)m.allocs[m.nallocs++]=v;
    CHECK(re4dc_movie_sep_alloc(32,32768));m.id=0x11f10;m.entered=10;m.start=11;m.stream=1;m.owns_service=true;m.texture=true;m.file=7;
    movie_scope=0x11f10;re4dc_movie_disc_owner=1;movie_texture=reinterpret_cast<void*>(0x1234);movie_picture=true;
}
void reenter_during_destroy(){
    CHECK(movie_finishing&&movie_world_token&&stream_active&&movie_sep&&ps2_movie.live==13);
    const auto token=movie_world_token;const unsigned stop_before=stopped,destroy_before=destroyed;
    CHECK(!re4dc_movie_world_before_room_retire());
    CHECK(!re4dc_movie_world_before_heap_change(heap_begin,unsigned(rw_bytes)));
    for(unsigned api=0;api<2;++api){
        bool halted=false;try{if(api)re4dc_movie_end();else re4dc_movie_cancel();}
        catch(const std::runtime_error&){halted=true;}
        CHECK(halted&&movie_finishing&&movie_world_token==token);
        CHECK(stopped==stop_before&&destroyed==destroy_before&&ps2_movie.live==13&&world_frees==0&&reads==0);
    }
}
void test_terminals(){
    // The device adapter yields at the actual production finish call-site.
    // All external retirement entries must refuse until its one owner returns.
    for(unsigned entry=0;entry<2;++entry){
        setup();destroy_yield_hook=reenter_during_destroy;
        if(entry)CHECK(re4dc_movie_world_before_room_retire());
        else CHECK(re4dc_movie_cancel()==RE4DC_MOVIE_CANCEL);
        CHECK(!movie_finishing&&!movie_world_token&&destroyed==1&&stopped==1&&shutdown_calls==1);
        CHECK(ps2_movie.phase==(entry?movie_world::Phase::retired:movie_world::Phase::ready));
        service_token=0;destroy_yield_hook=nullptr;
    }
    for(int status:{RE4DC_MOVIE_EOF,RE4DC_MOVIE_SKIP,RE4DC_MOVIE_ERROR,RE4DC_MOVIE_CANCEL}){
        setup();CHECK(finish(status)==status);CHECK(!movie_world_token&&!m.entered&&!m.texture&&!texture_alive);
        CHECK(ps2_movie.phase==movie_world::Phase::ready&&ps2w.package.live&&reads==2);
        CHECK(shutdown_calls==1&&stopped==1&&destroyed==1&&terminals==1&&texture_close_calls==1);
        CHECK(!stream_active&&!stream_initialized&&!movie_sep&&world_frees==0&&heap_frees==0&&heap_allocs==0);
        CHECK(movie_epoch==2&&!re4dc_movie_disc_owner);service_token=0;
    }
    setup();movie_readers=1;CHECK(!re4dc_movie_world_before_room_retire());CHECK(m.nallocs==12&&ps2_movie.live==13&&reads==0);
    bool halted=false;try{re4dc_movie_cancel();}catch(const std::runtime_error&){halted=true;}CHECK(halted&&world_frees==0&&ps2_movie.live==13);
    halted=false;try{re4dc_movie_end();}catch(const std::runtime_error&){halted=true;}CHECK(halted&&ps2_movie.live==13);
    movie_readers=0;CHECK(re4dc_movie_world_before_room_retire());CHECK(!movie_world_token&&!m.entered&&ps2_movie.phase==movie_world::Phase::retired&&reads==0);
    CHECK(re4dc_movie_world_before_room_retire());re4dc_ps2_mesh_retire();CHECK(world_frees==1);service_token=0;
    setup();texture_closes=false;halted=false;
    try{finish(RE4DC_MOVIE_ERROR);}catch(const std::runtime_error&){halted=true;}
    CHECK(halted&&texture_close_calls==101&&movie_world_token&&m.texture&&texture_alive);
    CHECK(m.nallocs==0&&ps2_movie.live==0&&reads==0&&!ps2w.package.live&&world_frees==0);
    texture_closes=true;CHECK(finish(RE4DC_MOVIE_ERROR)==RE4DC_MOVIE_ERROR);CHECK(!movie_world_token&&reads==2);service_token=0;
    setup();fail_reads=20;halted=false;
    try{finish(RE4DC_MOVIE_ERROR);}catch(const std::runtime_error&){halted=true;}
    CHECK(halted&&movie_world_token&&ps2_movie.phase==movie_world::Phase::failed&&reads==2&&world_frees==0);
}
}
#define RE4DC_GAME 1
namespace heap_host {
using u32=uintptr_t;
constexpr unsigned MEM_HEAP_NUM=13;
struct OSHeapCell{};struct OSHeapDescriptor{OSHeapCell* allocated=nullptr;};
OSHeapDescriptor descriptors[13];OSHeapDescriptor* HeapHead=descriptors;
OSHeapCell *cell_main=nullptr,*cell_game=nullptr,*cell_stage=nullptr,*cell_dll=nullptr;
unsigned CurrentHeap=4,destroys=0,creates=0;uintptr_t replacement_start=0;
bool require_world_retired=false;
void OSReport(const char*,...){}
void MemSignalHeap(int){heap_active=true;}
void OSDestroyHeap(int){++destroys;if(require_world_retired)CHECK(world_frees==1);}
int OSCreateHeap(void*,void*){++creates;return 9;}
u32 MemCheckHeapEnd(int){return replacement_start;}
#include "production_heap.inc"
void begin(){initialize();destroys=creates=0;require_world_retired=false;replacement_start=uintptr_t(saved_world)-64;}
void ancestor(unsigned no){Heap[no]={int(no+1),uintptr_t(heap_begin),uintptr_t(heap_begin+rw_bytes)};}
void test_transitions(){
    begin();CHECK(MemDestroyHeap(4)==1);CHECK(world_frees==1&&destroys==1&&!ps2w.storage);
    CHECK(MemDestroyHeap(4)==0);CHECK(world_frees==1&&destroys==1);
    begin();ancestor(1);CHECK(MemDestroyHeap(1)==1);CHECK(world_frees==1&&destroys==1&&Heap[4].handle>=0);
    begin();Heap[2]={2,uintptr_t(heap_begin+850000),uintptr_t(heap_begin+860000)};
    CHECK(MemDestroyHeap(2)==1);CHECK(world_frees==0&&destroys==1&&ps2w.package.live);
    begin();ancestor(3);replacement_start=uintptr_t(heap_begin);CHECK(MemReplaceHeap(3,4)==1);
    CHECK(world_frees==1&&destroys==2&&creates==1&&!ps2w.storage);
    begin();Heap[3].handle=-1;CHECK(MemReplaceHeap(3,4)==1);CHECK(world_frees==1&&destroys==1&&creates==1);
    begin();Heap[3].handle=-1;Heap[4].start=0;CHECK(MemReplaceHeap(3,4)==0);CHECK(world_frees==0&&destroys==0&&creates==0); // unchanged source failure
    begin();ancestor(0);ancestor(1);require_world_retired=true;MemClearAllHeap();CHECK(world_frees==1&&destroys==3);
    MemClearAllHeap();CHECK(world_frees==1&&destroys==3);
    // Execute real cancellation/CPU cleanup before an overlapping ancestor's
    // descriptor changes; the UI adapter must not fence or wait here.
    player::setup();destroys=creates=0;ancestor(0);require_world_retired=true;
    const unsigned fences=fence_calls;CHECK(MemDestroyHeap(0)==1);
    CHECK(world_frees==1&&destroys==1&&!player::movie_world_token&&reads==0&&fence_calls==fences&&vram_frees==1);
    service_token=0;
    // Active decoded/input pointers on a protected page: all three actual
    // transition bodies must stop before touching it or destroying ANY heap.
    for(unsigned transition=0;transition<3;++transition){
        player::setup();destroys=creates=0;require_world_retired=false;ancestor(0);ancestor(3);replacement_start=uintptr_t(heap_begin);
        player::movie_readers=1;ps2_movie.readers=1;CHECK(mprotect(heap_begin,rw_bytes,PROT_NONE)==0);
        bool halted=false;try{if(transition==0)MemDestroyHeap(4);else if(transition==1)MemReplaceHeap(3,4);else MemClearAllHeap();}
        catch(const std::runtime_error&){halted=true;}
        CHECK(halted&&destroys==0&&creates==0&&world_frees==0&&ps2_movie.live==13);
        CHECK(mprotect(heap_begin,rw_bytes,PROT_READ|PROT_WRITE)==0);
    }
    player::setup();destroys=creates=0;ancestor(0);const unsigned before_fence=fence_calls;
    pvr_state.render_busy=true;bool halted=false;
    try{MemClearAllHeap();}catch(const std::runtime_error&){halted=true;}
    CHECK(halted&&destroys==0&&creates==0&&world_frees==0&&fence_calls==before_fence);
    CHECK(player::movie_world_token&&player::m.texture&&ps2_movie.live==0&&reads==0); // no false ownership release
    // Production re4dc_missing is a non-returning halt. Our exception adapter
    // deliberately leaves its interrupted retirement fail-closed. Reset that
    // test-only halted caller before releasing the remaining fixture resources.
    CHECK(player::movie_retiring&&!player::movie_finishing);
    player::movie_retiring=false;pvr_state.render_busy=false;
    CHECK(player::re4dc_movie_world_before_room_retire());
    service_token=0;
}
}
int main(){
    const size_t page=size_t(sysconf(_SC_PAGESIZE));rw_bytes=(1700000+page-1)&~(page-1);region_bytes=rw_bytes+2*page;
    region=mmap(nullptr,region_bytes,PROT_NONE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);CHECK(region!=MAP_FAILED);heap_begin=static_cast<unsigned char*>(region)+page;
    player::re4dc_movie_world_scope(0x10030);CHECK(player::movie_scope==0x10030);
    player::re4dc_movie_world_scope(0x10020);CHECK(player::movie_scope==0);
    test_dynamic_part_cell_contract();test_s30_roundtrip_and_failures();test_roundtrip_and_slots();test_declines();test_restore_faults();test_protected_stale_and_boundaries();test_every_partial_allocation_and_service();player::test_terminals();heap_host::test_transitions();
    CHECK(munmap(region,region_bytes)==0);std::printf("PASS: %u assertions; actual production lifecycle/restore/UI/service helpers; guard pages + UBSan\n",checks);
}
