// GANADO_LOD=1 (ps2leon.mk; needs PS2_GANADO=1, COARSE_SKIN_FTRV=1, ACTOR_TRANSACTION=1; render only). Included by
// coarse_ganado_cast.cpp after the skin and gate tables. The cast Ganados' body and head meshes (roles 0 / 1 of every
// PS2 appearance) come from one disc package, dc/native/ganado/ganado_lod.re4gl (tools/d367/leonlod/glod_pack.py),
// instead of the image: the image header (glod_pack.py derive) keeps every other table (hands, signatures, bind,
// atlas keys) and leaves those rows null, and one buffer the size of the largest level (level 0, today's meshes) holds
// the level drawn now: memory neutral. Every Ganado draws the loaded level.
//   - Level: re4dc_ganado_lod_set(n) (the package's order: 0 = today, the boot default GANADO_LOD_LEVEL; 1 g85, 2 g70,
//     3 g55). The first owner plan loads the requested level; a later change loads at the end of the next actor
//     retirement (re4dc_actor_transaction_retire, once a tick, when no owned record is live): one ~0.1 MB disc read.
//   - A load re-qualifies the body / head immutable chunks (IDs 9 + 4a + role) and rebuilds the FTRV palette groups and
//     the pregate balls of every appearance from the new weights. Skeleton, motions, hands and game state are untouched.
//   - Cutscenes keep the full models: while an in-engine event holds the game the wanted level is 0 (the switch in and
//     out is a load at the next retirement).
//   - A failed read leaves the rows null: the owner plans decline (the Ganado keeps the source path) and the next
//     request tries again.
#include <fcntl.h>
#include <arch/timer.h>
#include "coarse_actor_preflight.h"
#include "ganado_lod_caps.h"
#ifndef RE4DC_GANADO_LOD_LEVEL
#define RE4DC_GANADO_LOD_LEVEL 0
#endif
extern "C" void re4dc_actor_immutable_chunk_reset(unsigned asset_id);  // coarse_actor_geometry_once.inc
#pragma GCC push_options
#pragma GCC optimize("Os")  // cold loader code
namespace { namespace ganado_lod {
namespace caps = ganado_lod_caps;
static_assert(caps::appearances == kApps, "GANADO_LOD package / bundle appearance count");
struct RoleRec { unsigned role,positions,normals,palettes,triangles,stream_bytes,off[5],size[5]; };
struct LevelRec { char name[8]; unsigned off32,bytes,skin_bytes,reserved; RoleRec roles[kApps*2]; };
static_assert(sizeof(LevelRec)==caps::level_record,"ganado_lod.re4gl level record layout");
constexpr unsigned kMaxLevels=8;
alignas(32) unsigned char buf[caps::buffer_bytes];
unsigned nlevels,file_bytes;
int dir_state;  // 0 not read, 1 ready, 2 failed
unsigned level_req=RE4DC_GANADO_LOD_LEVEL,level_cur=~0u,level_tried=~0u,loads,fails;
re4dc_source::ChunkInput input[kApps][2];
const char* package(){return "/cd/dc/native/ganado/ganado_lod.re4gl";}
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
    if(read_at(0,reinterpret_cast<unsigned char*>(h),64) && h[0]==caps::magic && h[1]==caps::version) {
        why=2;
        nlevels=h[2];file_bytes=h[5];
        if(nlevels && nlevels<=kMaxLevels && h[3]<=sizeof(buf) && h[4]==64+nlevels*sizeof(LevelRec) && h[7]==kApps)why=0;
    }
    re4dc_log("GANADOLOD dir levels=%u file=%u buffer=%u why=%u\n",nlevels,file_bytes,unsigned(sizeof(buf)),why);
    if(why)return false;
    dir_state=1;
    return true;
}
void clear() {
    for(unsigned a=0;a<kApps;++a)for(unsigned r=0;r<2;++r){gc::chunks[a][r]=gc::Chunk{r,0,0,0,0,0,nullptr,nullptr,nullptr,nullptr,nullptr};input[a][r]={};}
    level_cur=~0u;
}
// Everything built from the old weights / positions is rebuilt on the next draw.
void forget() {
    for(unsigned a=0;a<kApps;++a)for(unsigned r=0;r<2;++r)re4dc_actor_immutable_chunk_reset(9u+a*4u+r);
#if RE4DC_COARSE_SKIN_FTRV
    for(auto& s:skin_state)s=0;
    skin_next=0;
#endif
#if RE4DC_COARSE_PREGATE
    for(auto& s:gate_state)s=0;
    gate_next=0;
#endif
}
// Load level `level` into the buffer and point the body / head rows at it. Callers hold no owned record on the old bytes.
bool load(unsigned level) {
    if(!directory())return false;
    if(level>=nlevels){re4dc_log("GANADOLOD level %u not in the package (%u levels): level 0\n",level,nlevels);level=0;}
    clear();
    forget();
    LevelRec L;   // the level's record, read per load (no resident directory)
    unsigned why=0;
    if(!read_at(64+level*unsigned(sizeof(LevelRec)),reinterpret_cast<unsigned char*>(&L),sizeof(LevelRec)))why=1;
    else if(L.bytes>sizeof(buf) || L.off32*32u+L.bytes>file_bytes || L.skin_bytes>gc::skin_stream_bytes)why=3;
    else for(unsigned k=0;k<kApps*2;++k){const RoleRec& r=L.roles[k];
        if(r.role!=k%2u || r.size[4]!=r.palettes*16u || r.palettes>256u)why=4;
        for(unsigned a=0;a<5;++a)if((r.off[a]&31u) || r.off[a]+r.size[a]>L.bytes)why=5;}
    if(why){++fails;re4dc_log("GANADOLOD level %u record bad why=%u\n",level,why);return false;}
    const unsigned t0=unsigned(timer_us_gettime64());
    if(!read_at(L.off32*32u,buf,L.bytes)){++fails;re4dc_log("GANADOLOD read failed level=%u\n",level);return false;}
    unsigned tris=0;
    for(unsigned k=0;k<kApps*2;++k) {
        const RoleRec& r=L.roles[k];const unsigned a=k/2u,role=r.role;const unsigned char* p[5];
        for(unsigned i=0;i<5;++i)p[i]=buf+r.off[i];
        gc::chunks[a][role]=gc::Chunk{role,r.positions,r.normals,r.palettes,r.triangles,r.stream_bytes,p[0],p[1],p[2],
            const_cast<unsigned char*>(p[3]),reinterpret_cast<const gc::Weight*>(p[4])};
        input[a][role]=re4dc_source::ChunkInput{{p[0],r.size[0]},{p[1],r.size[1]},{p[2],r.size[2]},{p[3],r.size[3]},
            {p[4],r.size[4]},r.positions,r.normals,r.palettes,r.triangles,34u};
        tris+=r.triangles;
    }
    level_cur=level;++loads;
    re4dc_log("GANADOLOD level=%u name=%.8s bytes=%u read_us=%u body_head_tris=%u skin=%u\n",level,L.name,L.bytes,
        unsigned(timer_us_gettime64())-t0,tris,L.skin_bytes);
    return true;
}
// The owner plans' gate: the first plan loads the requested level.
// The level drawn now: level 0 (today's full meshes) while an in-engine event / cutscene holds the game (Status_flg[1]
// 0x10000000; user 2026-10-15: cutscenes keep the full models), else the requested gameplay level.
#if defined(RE4DC_GANADO_EVENT_KEEP_LOD) && RE4DC_GANADO_EVENT_KEEP_LOD
// GANADO_EVENT_KEEP_LOD=1 (user 2026-10-22, option 1): events keep the gameplay level, so no package reload at
// event start/end. Render-only approximation.
unsigned want() {return level_req;}
#else
unsigned want() {return (pG && (pG->Status_flg[1]&0x10000000u))?0u:level_req;}
#endif
bool ready() {
    if(level_cur!=~0u)return true;
    if(dir_state==2 || fails>=3)return false;
    return load(want());
}
} }
#pragma GCC pop_options
// Run-time level (poc101 GANADOLOD row, warp `glod <n>`): applied at the next actor retirement.
extern "C" void re4dc_ganado_lod_set(unsigned level) {ganado_lod::level_req=level;}
extern "C" unsigned re4dc_ganado_lod_level() {return ganado_lod::level_cur;}
// coarse_actor_transaction.inc re4dc_actor_transaction_retire, after every owned record is revoked.
extern "C" void re4dc_ganado_lod_retired() {
    using namespace ganado_lod;
    const unsigned w=want();
    if(level_cur==~0u || w==level_cur || level_tried==w)return;  // the boot level loads at first use
    level_tried=w;fails=0;   // one try per wanted level here (a failure leaves the rows null: ready() retries)
    if(load(w))level_tried=~0u;
}
