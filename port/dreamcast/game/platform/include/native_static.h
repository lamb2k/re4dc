#pragma once
// Recovered scroll objects -> D349 native static room packages (.re4room v4).
//
// Source authority is unchanged: setObj binds each placed object by its SMD
// owner/work/BIN/common identity, and the object's own draw (every source
// visibility gate, the current part material, blend, cull and alpha) decides
// when a native batch is drawn. A bound part draws the package batches with
// its (texId, alphaTex) key instead of decoding its GX display list. There is
// no second object registry: each package source slot records the one live
// object bound to it, checked against that object's creation serial.
struct Re4dcModelPart;
struct Re4dcStaticStats {
    unsigned owners_open, open_failures, alloc_rejects, package_bytes;
    unsigned binds, bind_misses, bind_conflicts, stale_bindings;
    unsigned parts_native, parts_skipped, parts_fallback, key_misses;
    unsigned groups_visible, groups_culled, batches, strips, strips_culled;
    unsigned strips_clipped, triangles_clipped, vertices, moved_objects;
    unsigned vertex_alpha, reserve_rejects, bind_rejects, aborts;
    unsigned vertex_opaque, vertex_alpha_min, vertex_alpha_unused;
    int heap_before, heap_after;
    unsigned unowned_binds, locate_misses, parts_lit;
    unsigned clusters_visible, clusters_culled, lod_draws[4]; // R4IM v2 (MESH_LOD)
};
extern "C" {
// Called by scroll.cpp setObj after the object's placement matrix is final.
// room is (stage_no << 8) | room_no; block is -1 for the main scenario.
void re4dc_static_bind(const void* object, unsigned room, int block,
                       unsigned work, unsigned bin, unsigned common,
                       unsigned serial, const float world[12]);
// Block/room retirement: the source destroyed every object of this owner.
void re4dc_static_retire_owner(int block);
void re4dc_static_retire_all();
// Returns one when the part was drawn, queued or deliberately skipped
// natively; zero leaves it to the generic ModelPart path.
int re4dc_static_submit(const Re4dcModelPart*);
const Re4dcStaticStats* re4dc_static_stats();
// Existing frame owner's frame number (native_ui.cpp).
unsigned re4dc_ui_frame();
// Guarded heap-4 storage, same reserve policy as retained preparation.
void* re4dc_static_alloc(unsigned bytes);
void re4dc_static_free(void*);
int re4dc_static_heap_free();
// NATIVE_FOG (native_static.cpp): GXSetFog state from gx_stub.cpp, the source
// View far plane from the model bridge, and the frame-start PVR fog table
// update from native_ui.cpp (after the previous render's fence).
void re4dc_fog_capture(int type, float start, float end, unsigned rgba);
unsigned re4dc_fog_enabled();
void re4dc_fog_note_far(float far);
void re4dc_fog_frame();
#if RE4DC_FOG_TA_DOUBLEBUF
int re4dc_fog_frame_pending();  // TA_DOUBLEBUF: a fog change must fence the render in flight
#endif
}

// lane bakeall: one-line hooks used inside native_static.cpp (kept here so no source line moves in the default image).
// R4ID count check (native_static.cpp PS2DYN). WORLD_BAKE (lane bakeall): a baked package keeps each placement's
// SMD row as its field with fewer placements than rows; the ids sidecar is indexed by field, so it must cover every
// placement's field instead of matching the placement count. Default build: unchanged exact-count check.
#if defined(RE4DC_WORLD_BAKE) && RE4DC_WORLD_BAKE
template<class P> static inline bool re4dc_ids_count_ok(unsigned n,unsigned placements,const P* pl) {
    if(n==placements)return true;
    for(unsigned i=0;i<placements;++i)if(pl[i].placement>=n)return false;
    return true;
}
#define RE4DC_IDS_COUNT_OK(n,p,pl) re4dc_ids_count_ok((n),(p),(pl))
#else
#define RE4DC_IDS_COUNT_OK(n,p,pl) ((n)==(p))
#endif
// PS2DYN per-id trace (DYN_ID_TRACE=1, diagnostic builds only): first frame each scroll-bound id is hidden (1), moved (2)
// or drawn from its source hierarchy (3). Proves which bound placements leave rest pose before a bake merges them.
#if defined(RE4DC_DYN_ID_TRACE) && RE4DC_DYN_ID_TRACE
extern "C" void re4dc_log(const char*,...);
static inline void re4dc_dyn_id_trace(unsigned id,unsigned r,unsigned f){
    static unsigned char seen[256][4];
    if(!r || r>3U || id>255U || seen[id][r])return;
    seen[id][r]=1;re4dc_log("PS2DYN id=%02x state=%s frame=%u\n",id,r==1U?"hidden":r==2U?"moved":"source",f);
}
#define RE4DC_DYN_ID_TRACE(id,r,f) re4dc_dyn_id_trace((id),(r),(f))
#else
#define RE4DC_DYN_ID_TRACE(id,r,f) ((void)0)
#endif
