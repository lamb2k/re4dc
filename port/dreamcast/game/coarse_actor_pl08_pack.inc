// ACTOR_PL08_PACK=1 (crowd.mk, default 0; needs ACTOR_PL08=1 and NATIVE_STATIC=1): the three pl08-only immutable chunks
// (roles 0 / 1 / 8) live in a heap-4 room cell loaded from dc/native/pl08/leon_pl08.re4cp (tools/d367/pl08_pack.py)
// only while the bound player archive is pl08, instead of 33,916 B of static arrays in every room. Included once by
// coarse_actor_owner_leon.inc after coarse_actor_geometry_once.inc and before coarse_actor_owner_pl08.inc. The rules
// (validation, publish / unpublish / retire, same-address reload) are actor_pl08_pack_check.inc, shared with the host
// test. Hooks: ReadPlayerData (read.cpp, after the player archive bind) and the room enter / leave (ui_bridge.cpp).
// Not published: re4dc_actor_plan_pl08 declines and the whole pl08 model keeps the source path, as before ACTOR_PL08.
#include <kos/fs.h>
#include <fcntl.h>
extern "C" void* re4dc_static_alloc(unsigned);
extern "C" void re4dc_static_free(void*);
extern "C" int re4dc_static_heap_free();
extern "C" void re4dc_actor_transaction_retire();
namespace {
file_t pl08_pack_file=FILEHND_INVALID;
#if RE4DC_GC_ASSET_GATE
re4dc_gcasset::PayloadProof gcasset_pl08;
#endif
leon4k::Chunk pl08_pack_chunks[3];  // the published descriptors (zero when unpublished)
struct Pl08ChunkView;
int pl08_hook_open();
bool pl08_hook_read(unsigned char*,unsigned);
void pl08_hook_close();
unsigned char* pl08_hook_alloc(unsigned bytes) {return static_cast<unsigned char*>(re4dc_static_alloc(bytes));}
void pl08_hook_free(unsigned char* cell) {
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::payload_retire(gcasset_pl08);
#endif
    re4dc_static_free(cell);
}
bool pl08_hook_preflight(const Pl08ChunkView&,unsigned&);
unsigned pl08_hook_reset() {
#if defined(RE4DC_LEON_ATLAS_SPLIT) && RE4DC_LEON_ATLAS_SPLIT
    re4dc_atlas_retire_pl08(); // revoke borrowed source spans BEFORE reset/free/republication
#endif
    unsigned n=actor_immutable_reset_pl08();
    if(skin_costume==1u && skin_state){skin_state=0;++n;}  // the costume-1 skin program is rebuilt from the new bytes
    return n;
}
void pl08_hook_published(const Pl08ChunkView*);
bool pl08_pack_owned_live();  // defined after coarse_actor_transaction.inc (coarse_actor_owner_leon.inc)
void pl08_hook_retire_owned() {if(pl08_pack_owned_live())re4dc_actor_transaction_retire();}
#define P8LOG(...) re4dc_log(__VA_ARGS__)
#include "actor_pl08_pack_check.inc"
#undef P8LOG
#if RE4DC_GC_ASSET_GATE
extern Pl08PackLife pl08_pack;
#endif
int pl08_hook_open() {
    pl08_hook_close();
#if defined(RE4DC_PS2_LEON_PL08) && RE4DC_PS2_LEON_PL08
    pl08_pack_file=fs_open("/cd/dc/native/pl08/leon_pl08_ps2.re4cp",O_RDONLY);  // PS2_LEON=1: the PS2 pl08 body
#else
    pl08_pack_file=fs_open("/cd/dc/native/pl08/leon_pl08.re4cp",O_RDONLY);
#endif
    if(pl08_pack_file==FILEHND_INVALID)return -1;
    return int(fs_total(pl08_pack_file));
}
bool pl08_hook_read(unsigned char* to,unsigned bytes) {
    if(pl08_pack_file==FILEHND_INVALID)return false;
    const bool ok=fs_read(pl08_pack_file,to,bytes)==ssize_t(bytes);
    fs_close(pl08_pack_file);pl08_pack_file=FILEHND_INVALID;
    return ok;
}
void pl08_hook_close() {if(pl08_pack_file!=FILEHND_INVALID){fs_close(pl08_pack_file);pl08_pack_file=FILEHND_INVALID;}}
re4dc_source::ChunkInput pl08_view_input(const Pl08ChunkView& v) {
    return re4dc_source::ChunkInput{{v.array[0],v.bytes[0]},{v.array[1],v.bytes[1]},{v.array[2],v.bytes[2]},{v.array[3],v.bytes[3]},
        {v.array[4],v.bytes[4]},v.position_count,v.normal_count,v.palette_count,v.triangles,119u};
}
bool pl08_hook_preflight(const Pl08ChunkView& v,unsigned& detail) {
    re4dc_source::ChunkProof proof{};
    const auto e=re4dc_source::preflight_chunk(pl08_view_input(v),proof);
    detail=unsigned(e);return e==re4dc_source::BlobError::None;
}
void pl08_hook_published(const Pl08ChunkView* v) {
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::payload_retire(gcasset_pl08);
    if(v && pl08_pack.base && re4dc_gcasset::ensure_disc_catalog())
        (void)re4dc_gcasset::payload_capture(gcasset_pl08,&pl08_pack,pl08_pack.base,kPl08PackBytes);
#endif
    for(unsigned k=0;k<3;++k)pl08_pack_chunks[k]=v?leon4k::Chunk{v[k].source_info,v[k].position_count,v[k].normal_count,
        v[k].palette_count,v[k].triangles,v[k].bytes[3],v[k].array[0],v[k].array[1],v[k].array[2],v[k].array[3],
        reinterpret_cast<const leon4k::Weight*>(v[k].array[4])}:leon4k::Chunk{};
}
Pl08PackLife pl08_pack{};
// The owner's input of package chunk k (published only).
re4dc_source::ChunkInput pl08_pack_input(unsigned k) {return pl08_view_input(pl08_pack.view[k]);}
void pl08_pack_note(const char* what,bool before_pub,const unsigned char* before_cell) {
    if(before_pub!=pl08_pack.published || before_cell!=pl08_pack.cell)
        re4dc_log("P8PACK %s file=%02x published=%u cell=%p heap4_free=%d generation=%u\n",what,pl08_pack.player_file,
            unsigned(pl08_pack.published),static_cast<const void*>(pl08_pack.cell),re4dc_static_heap_free(),pl08_pack.generation);
}
}
extern "C" void re4dc_pl08_pack_player(unsigned file) {
    const bool p=pl08_pack.published;const unsigned char* c=pl08_pack.cell;
    pl08_life_player(pl08_pack,file);pl08_pack_note("bind",p,c);
}
extern "C" void re4dc_pl08_pack_room_enter() {
    const bool p=pl08_pack.published;const unsigned char* c=pl08_pack.cell;
    pl08_life_room_enter(pl08_pack);pl08_pack_note("enter",p,c);
}
extern "C" void re4dc_pl08_pack_room_leave() {
    const bool p=pl08_pack.published;const unsigned char* c=pl08_pack.cell;
    pl08_life_room_leave(pl08_pack,"leave");pl08_pack_note("leave",p,c);
}
#if defined(RE4DC_RESET_MEM_FIX) && RE4DC_RESET_MEM_FIX
// RESET_MEM_FIX (game30.mk): systemResetCommon released the player archive. Forget the bound file as a fresh boot
// has it (0), so the next room enter does not reload the 61 KB pl08 cell into heap 4 for a New Game's Leon
// (the cell itself goes with the reset's room leave).
extern "C" void re4dc_pl08_pack_forget() {
    if(pl08_pack.player_file)re4dc_log("P8PACK forget file=%02x at reset\n",pl08_pack.player_file);
    pl08_pack.player_file=0;
}
#endif
