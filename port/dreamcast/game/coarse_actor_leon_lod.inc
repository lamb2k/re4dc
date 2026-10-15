// LEON_LOD=1 (ps2leon.mk; needs PS2_LEON=1 and LEON_HAND_PACK=1; render only). Included by coarse_actor_owner_leon.inc
// before the owner plans. Leon's render mesh rungs (roles 0 body, 1 jacket, 2 knife, 3 face, 4 head, 7 hair, and the
// hair run) come from one disc package, dc/native/pl00/leon_lod.re4lp (tools/d367/leonlod/lod_pack.py), instead of the
// image: the image header (lod_pack.py derive) keeps every other Leon table and leaves those rows null, and one buffer
// the size of the largest rung (arm A, today's Leon) holds the rung drawn now. The hands stay LEON_HAND_PACK's.
//   - Level: re4dc_leon_lod_set(n) (the package's level order: 0 = arm A, the boot default LEON_LOD_LEVEL), applied at
//     the next room enter (re4dc_leon_lod_room_enter, ui_bridge.cpp: a load point, ~0.1 MB read) or, mid-room (the
//     poc101 frozen sweep), at the end of the next actor retirement (coarse_actor_transaction.inc, once a tick, when no
//     owned record is live: one disc read hitch); if no rung is loaded, Leon's owner plan tries once more (up to 3
//     failures). The skeleton, animation, game state and the hands are untouched: only the drawn mesh changes.
//   - A load re-qualifies the six role chunks and the hair run (their immutable IDs are reset, as LEON_HAND_PACK does
//     for a hand slot) and forces the FTRV palette program to be rebuilt from the new weights (skin_state).
//   - A failed read leaves the rows null: the owner plans decline (Leon falls back to the source path, which
//     MCHECK_LEONGC reports) and the next room enter tries again.
#include <kos/fs.h>
#include <fcntl.h>
#include <arch/timer.h>
#include "leon_lod_caps.h"
extern "C" void re4dc_actor_transaction_retire();
#ifndef RE4DC_LEON_LOD_LEVEL
#define RE4DC_LEON_LOD_LEVEL 0
#endif
#pragma GCC push_options
#pragma GCC optimize("Os")  // cold loader code
namespace leon_lod {
struct RoleRec { unsigned role,positions,normals,palettes,triangles,stream_bytes,off[5],size[5]; };
struct LevelRec { char name[8]; unsigned off32,bytes,plan[4],hair[8]; RoleRec roles[6]; };
static_assert(sizeof(LevelRec)==leon_lod_caps::level_record,"leon_lod.re4lp level record layout");
constexpr unsigned kMaxLevels=8,kRoles[6]={0,1,2,3,4,7};
alignas(32) unsigned char buf[leon_lod_caps::buffer_bytes];
unsigned nlevels,file_bytes;
int dir_state;  // 0 not read, 1 ready, 2 failed
unsigned level_req=RE4DC_LEON_LOD_LEVEL,level_cur=~0u,level_tried=~0u,loads,fails,generation;
re4dc_source::ChunkInput input[8];
unsigned plan_palette_bytes,plan_workspace_bytes,pl08_plan_palette_bytes,pl08_plan_workspace_bytes;
unsigned hair_palettes=leon_hair_runs::boot_palette_count;
const unsigned char* hair_uv;unsigned hair_uv_bytes;
const char* package(){return "/cd/dc/native/pl00/leon_lod.re4lp";}
void reset_ids();        // coarse_actor_owner_leon.inc, after coarse_actor_geometry_once.inc
bool owned_live();       // after coarse_actor_transaction.inc
// Read `bytes` at `offset` straight into `to` (as LEON_HAND_PACK's directory read; no shared DVD buffer), one open.
bool read_at(unsigned offset,unsigned char* to,unsigned bytes) {
    file_t f=fs_open(package(),O_RDONLY);
    if(f==FILEHND_INVALID)return false;
    const bool ok=fs_seek(f,offset,SEEK_SET)==off_t(offset) && fs_read(f,to,bytes)==ssize_t(bytes);
    fs_close(f);
    return ok;
}
bool directory() {
    if(dir_state)return dir_state==1;
    dir_state=2;
    unsigned h[16]{};
    unsigned why=1;
    if(read_at(0,reinterpret_cast<unsigned char*>(h),64) && h[0]==leon_lod_caps::magic && h[1]==leon_lod_caps::version) {
        why=2;
        nlevels=h[2];file_bytes=h[5];
        if(nlevels && nlevels<=kMaxLevels && h[3]<=sizeof(buf) && h[4]==64+nlevels*sizeof(LevelRec))why=0;
    }
    re4dc_log("LEONLOD dir levels=%u file=%u buffer=%u why=%u\n",nlevels,file_bytes,unsigned(sizeof(buf)),why);
    if(why)return false;
    dir_state=1;
    return true;
}
void clear() {
    for(unsigned k=0;k<6;++k){const unsigned r=kRoles[k];leon4k::chunks[r]=leon4k::Chunk{r,0,0,0,0,0,nullptr,nullptr,nullptr,nullptr,nullptr};input[r]={};}
    leon_hair_runs::runs[0].stream=nullptr;leon_hair_runs::runs[0].bytes=0;hair_uv=nullptr;hair_uv_bytes=0;
    level_cur=~0u;
}
// Load rung `level` into the buffer and point Leon's rows at it. Callers hold no owned record on the old bytes.
bool load(unsigned level) {
    if(!directory())return false;
    if(level>=nlevels){re4dc_log("LEONLOD level %u not in the package (%u levels): level 0\n",level,nlevels);level=0;}
    clear();
    LevelRec L;   // the level's record, read per load (no resident directory)
    unsigned why=0;
    if(!read_at(64+level*unsigned(sizeof(LevelRec)),reinterpret_cast<unsigned char*>(&L),sizeof(LevelRec)))why=1;
    else if(L.bytes>sizeof(buf) || L.off32*32u+L.bytes>file_bytes || L.hair[4]+L.hair[5]>L.bytes || L.hair[6]+L.hair[7]>L.bytes)why=3;
    else for(unsigned k=0;k<6;++k){const RoleRec& r=L.roles[k];
        if(r.role!=kRoles[k] || r.size[4]!=r.palettes*16u)why=4;
        for(unsigned a=0;a<5;++a)if((r.off[a]&31u) || r.off[a]+r.size[a]>L.bytes)why=5;}
    if(why){++fails;re4dc_log("LEONLOD level %u record bad why=%u\n",level,why);return false;}
    reset_ids();
    skin_state=0;   // the FTRV palette program is rebuilt from the new weights before use
    const unsigned t0=unsigned(timer_us_gettime64());
    if(!read_at(L.off32*32u,buf,L.bytes)){++fails;re4dc_log("LEONLOD read failed level=%u\n",level);return false;}
    for(unsigned k=0;k<6;++k) {
        const RoleRec& r=L.roles[k];const unsigned char* a[5];
        for(unsigned i=0;i<5;++i)a[i]=buf+r.off[i];
        leon4k::chunks[r.role]=leon4k::Chunk{r.role,r.positions,r.normals,r.palettes,r.triangles,r.stream_bytes,a[0],a[1],a[2],a[3],
            reinterpret_cast<const leon4k::Weight*>(a[4])};
        input[r.role]=re4dc_source::ChunkInput{{a[0],r.size[0]},{a[1],r.size[1]},{a[2],r.size[2]},{a[3],r.size[3]},{a[4],r.size[4]},
            r.positions,r.normals,r.palettes,r.triangles,119u};
    }
    plan_palette_bytes=L.plan[0];plan_workspace_bytes=L.plan[1];pl08_plan_palette_bytes=L.plan[2];pl08_plan_workspace_bytes=L.plan[3];
    hair_palettes=L.hair[0];
    auto& run=leon_hair_runs::runs[0];
    run.triangles=L.hair[1];run.material=L.hair[2];run.asset_id=L.hair[3];run.stream=buf+L.hair[6];run.bytes=L.hair[7];
    hair_uv=buf+L.hair[4];hair_uv_bytes=L.hair[5];
    level_cur=level;++loads;++generation;
    re4dc_log("LEONLOD level=%u name=%.8s bytes=%u read_us=%u tris=%u/%u/%u/%u/%u/%u hair=%u\n",level,L.name,L.bytes,
        unsigned(timer_us_gettime64())-t0,L.roles[0].triangles,L.roles[1].triangles,L.roles[2].triangles,L.roles[3].triangles,
        L.roles[4].triangles,L.roles[5].triangles,L.hair[1]);
    return true;
}
// The owner plans' gate: the first plan loads the requested rung (nothing of Leon's owner path is live before it).
bool ready() {
    if(level_cur!=~0u)return true;
    if(dir_state==2 || fails>=3)return false;
    return load(level_req);
}
}
#pragma GCC pop_options
// Run-time level (poc101 rows, warp `leonlod <n>`): applied at the next room enter.
extern "C" void re4dc_leon_lod_set(unsigned level) {leon_lod::level_req=level;}
extern "C" unsigned re4dc_leon_lod_level() {return leon_lod::level_cur;}
extern "C" void re4dc_leon_lod_room_enter() {
    using namespace leon_lod;
    if(level_cur==level_req)return;   // the first room enter loads the boot level; ready() retries a failed load
    if(owned_live())re4dc_actor_transaction_retire();   // (its retired() hook may already load the level)
    if(level_cur==level_req)return;
    fails=0;
    load(level_req);
}
// coarse_actor_transaction.inc re4dc_actor_transaction_retire, after every owned record is revoked: a level change
// asked for since the last load (once per request; the boot level loads at first use).
namespace leon_lod { void retired() {
    if(level_cur==~0u || level_req==level_cur || level_tried==level_req)return;
    level_tried=level_req;fails=0;
    if(load(level_req))level_tried=~0u;
} }
