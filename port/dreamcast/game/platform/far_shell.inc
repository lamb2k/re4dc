// FAR_SHELL (game30.mk; default 0 = no code; render only; lane farshell16, proof of concept 2026-10-16).
// Included twice by native_static.cpp (PS2_WORLD_MESH builds): RE4DC_FAR_SHELL_PART 1 inside the PS2 world's anonymous
// namespace (the package block; ps2_open / re4dc_ps2_mesh_retire open and free it with the world package), part 2 at
// file scope (the C entry points).
//
// What it does: with the Options View distance at Near / Short (VIEW_DIST_OPTION), the PS2 world's OPAQUE pass stops at
// the cut as before, but the fog, the punch-through / translucent world passes, actors and objects keep Full's far
// (25 m), and the room's far shell is drawn in the opaque list instead of the opaque world beyond the cut. The shell
// (tools/d367/farshell, far-shell.fsh per room) is the opaque world surfaces seen beyond the cut from the room's
// reachable positions, simplified offline (collapse decimation, small parts and spikes dropped), each triangle textured
// with the world texture under it (UVs extended from the source triangle, the prelit colour sampled per corner): no new
// textures, so no VRAM. Groups = (level, material, 12 m XZ cell); a group is drawn when its box reaches beyond the cut and
// is in the view before Full's far. Version 2 files carry two levels per cell (fine, and a coarse one beyond the split
// halfway between the cut and Full: 18.75 m at Short); both levels of a cell share the cell's box, so one decision picks one. Its depth is pushed back by kBias (z = 1/w x kBias), so where a straddling group overlaps
// the near world, the real world wins the depth test. The game camera, View._zfar and all logic are untouched.
// Runtime mode (warp line `farshell 0|1|2`): 0 = VIEW_DIST_OPTION as before (every pass and the fog cut), 1 = shell
// (default), 2 = the opaque cut with Full fog / PT / TR and no shell (the pricing arm that isolates the shell's cost).
//
// Residency (lane farshell17, 2026-10-16; test 16 blocker: the shell sat in heap 4 at every View distance and r100's
// after-ambush Ganados could not get heap 4, "Em set failed, Id = 12" x2). The shell is in heap 4 only while it can be
// drawn: mode 1, View distance Short, no route movie running, and heap 4 not short.
// - sync() (every ps2_open, i.e. each world draw and room entry) loads it when it is wanted and not resident, and frees
//   it when it is not wanted. View distance Full / Near: never read, 0 B. Changing the option to Short reads it at the
//   next world draw; changing away frees it there.
// - A route movie borrows it (native_movie.cpp open, as the PCCULL cell): freed before heap_before, read again at the
//   first world draw after the movie.
// - Heap 4 short: a failed heap-4 allocation (main_mem.cpp mem_alloc) or a native static package refused for its reserve
//   (ui_bridge.cpp re4dc_static_alloc) frees the shell and retries once. The room is then marked yielded and the shell
//   is not read there again (its next entries included) until the View distance option changes; that room shows the
//   plain Short cut meanwhile. Other homes measured and rejected (docs/lanes/farshell17.md): VRAM (r100 after the ambush
//   115 KB free, largest 7 KB; r101 largest 10 KB), sound RAM (95 KB free, G2 reads), KOS (the tight one).
#if RE4DC_FAR_SHELL_PART == 1
extern "C" int re4dc_view_dist_get(void);   // option_rows.cpp (VIEW_DIST_OPTION)
#ifndef RE4DC_FAR_SHELL_MODE
#define RE4DC_FAR_SHELL_MODE 1
#endif
namespace farshell {
int mode = RE4DC_FAR_SHELL_MODE;
struct Head { char magic[4]; std::uint32_t version, groups, materials, vertices, strip_bytes, crc, room; };
struct Mat { std::uint32_t crc, fnv; std::uint16_t w, h; std::uint32_t reserved; };
struct Group { float lo[3], hi[3], origin[3], scale, ub, vb; std::uint32_t first_vertex; std::uint16_t vcount, material;
               std::uint32_t first_strip, strip_bytes; };
struct Vert { std::int16_t x, y, z; std::uint16_t rgb; std::int16_t u, v; };
static_assert(sizeof(Head) == 32 && sizeof(Mat) == 16 && sizeof(Group) == 64 && sizeof(Vert) == 12, "far-shell.fsh");
struct State {
    unsigned char* block = nullptr; unsigned bytes = 0, room = 0;
    const Head* h = nullptr; const Mat* mats = nullptr; const Group* groups = nullptr; const Vert* verts = nullptr;
    const std::uint8_t* strips = nullptr;
    const std::uint32_t* lut = nullptr;   // RGB565 -> ARGB8888 by byte: [0,256) high byte, [256,512) low byte (OR them)
    const float* tight = nullptr;         // version 2: per group its own vertex box (lo[3], hi[3]); the file box is the cell's
    // per 120 frames
    unsigned frames = 0, shown = 0, groups_drawn = 0, vtx = 0, strip_verts = 0, strips_cut = 0, headers = 0, refused = 0;
    bool drawing = false;                 // re4dc_far_shell_draw holds pointers into block: a shortfall may not free it
};
State st;
#if RE4DC_GC_ASSET_GATE
// State is reset wholesale; this registered stable record must survive it.
re4dc_gcasset::PayloadProof asset_proof;
#endif
// Residency policy (survives close()).
struct Policy {
    unsigned room = ~0U;    // the room sync() last saw
    bool tried = false;     // this world package: the file was read (or found absent) once; no retry each frame
    bool movie = false;     // a route movie borrowed the shell (or ran with the option at Short): no read until it ends
    unsigned yielded[4] = {~0U, ~0U, ~0U, ~0U};   // rooms where heap 4 ran short with the shell resident
    unsigned loads = 0, frees = 0, lends = 0, yields = 0;
};
Policy pol;
bool yielded(unsigned room) {
    for (unsigned r : pol.yielded) if (r == room) return true;
    return false;
}
void close() {
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    if(st.block)++wc24_generation;
#endif
#if RE4DC_GC_ASSET_GATE
    if(asset_proof.owner)re4dc_gcasset::payload_invalidate(asset_proof,&st);
#endif
    if (st.block) re4dc_static_free(st.block);
    st = State{};
}
void open(unsigned room) {
    close();
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::payload_retire(asset_proof); // cold; close/shortfall itself never logs/hashes/reads catalog
#endif
    char path[48];
    snprintf(path, sizeof(path), "/cd/dc/native/r%03x/far-shell.fsh", room);
    const int before = re4dc_static_heap_free();
    const file_t f = fs_open(path, O_RDONLY);
    const unsigned size = f != FILEHND_INVALID ? unsigned(fs_total(f)) : 0U;
    const char* why = f == FILEHND_INVALID ? "absent" : nullptr;
    if (!why && (size < 32U || size > 524288U)) why = "size";
    // version 2 files need a per-group box table after the colour table: peek at the header for the group count
    Head peek{};
    if (!why && fs_read(f, &peek, sizeof(peek)) != ssize_t(sizeof(peek))) why = "read";
    if (!why && fs_seek(f, 0, SEEK_SET) != 0) why = "seek";
    const unsigned extra = !why && peek.version == 2U && peek.groups <= 8192U ? 24U * peek.groups : 0U;
    if (!why && !(st.block = static_cast<unsigned char*>(re4dc_static_alloc(((size + 31U) & ~31U) + 2048U + extra))))
        why = "heap";
    if (!why && fs_read(f, st.block, size) != ssize_t(size)) why = "read";
    if (f != FILEHND_INVALID) fs_close(f);
    if (!why) {
        const Head* h = reinterpret_cast<const Head*>(st.block);
        if (std::memcmp(h->magic, "FSH1", 4) || (h->version != 1U && h->version != 2U) || h->room != room || !h->groups ||
            !h->materials || (h->version == 2U && 24U * h->groups != extra) ||
            32U + 16U * h->materials + 64U * h->groups + 12U * h->vertices + h->strip_bytes != size ||
            ps2_crc32(st.block + 32, size - 32U) != h->crc)
            why = "header";
        else {
            st.h = h;
            st.mats = reinterpret_cast<const Mat*>(st.block + 32);
            st.groups = reinterpret_cast<const Group*>(st.block + 32 + 16 * h->materials);
            st.verts = reinterpret_cast<const Vert*>(st.block + 32 + 16 * h->materials + 64 * h->groups);
            st.strips = st.block + 32 + 16 * h->materials + 64 * h->groups + 12 * h->vertices;
            // colour table after the file (2 KiB): every ARGB8888 bit is a copy of one RGB565 bit, so the two byte halves
            // expand independently (r8 = r5 << 3 | r5 >> 2 etc.) and OR together
            std::uint32_t* lut = reinterpret_cast<std::uint32_t*>(st.block + ((size + 31U) & ~31U));
            for (unsigned b = 0; b < 256U; ++b) {
                const unsigned r5 = b >> 3, gh = b & 7U, gl = b >> 5, b5 = b & 31U;
                lut[b] = 0xff000000U | ((r5 << 3) | (r5 >> 2)) << 16 | ((gh << 5) | (gh >> 1)) << 8;
                lut[256U + b] = (gl << 2) << 8 | (b5 << 3) | (b5 >> 2);
            }
            st.lut = lut;
            float* tight = h->version == 2U ? reinterpret_cast<float*>(lut + 512) : nullptr;
            for (unsigned g = 0; g < h->groups && !why; ++g) {
                const Group& q = st.groups[g];
                if ((q.material & 0x3fffU) >= h->materials || (h->version == 1U && q.material >= h->materials) || !q.vcount || q.vcount > 256U || q.first_vertex + q.vcount > h->vertices ||
                    q.first_strip + q.strip_bytes > h->strip_bytes)
                    why = "group";
                else if (tight) {   // the group's own box from its i16 grid: culling stays as tight as version 1
                    float* t = tight + 6 * g;
                    for (unsigned a = 0; a < 3; ++a) { t[a] = 3.0e38f; t[3 + a] = -3.0e38f; }
                    for (unsigned i = 0; i < q.vcount; ++i) {
                        const Vert& v = st.verts[q.first_vertex + i];
                        const float p[3] = {q.origin[0] + v.x * q.scale, q.origin[1] + v.y * q.scale, q.origin[2] + v.z * q.scale};
                        for (unsigned a = 0; a < 3; ++a) { t[a] = p[a] < t[a] ? p[a] : t[a]; t[3 + a] = p[a] > t[3 + a] ? p[a] : t[3 + a]; }
                    }
                }
            }
            st.tight = tight;
        }
    }
    if (why) {
        if (st.block) re4dc_static_free(st.block);
        st = State{};
    } else {
        st.bytes = size; st.room = room;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        ++wc24_generation;
#endif
#if RE4DC_GC_ASSET_GATE
        re4dc_gcasset::StaticManifest source;
        re4dc_gcasset::static_manifest_begin(source,re4dc_gcasset::StaticShell,room,gcasset_static_profile(),st.block,size);
        for(unsigned i=0;i<re4dc_gcasset::StaticRoleCount;++i)
            re4dc_gcasset::static_manifest_note(source,re4dc_gcasset::StaticRole(i),re4dc_gcasset::NotApplicable);
        re4dc_gcasset::payload_capture_composite(asset_proof,&st,st.block,size,nullptr,0,source);
#endif
    }
    re4dc_log("FARSHELL room=%03x open=%s bytes=%u groups=%u materials=%u vertices=%u heap=%d->%d\n", room, why ? why : "ok",
              size, st.h ? unsigned(st.h->groups) : 0U, st.h ? unsigned(st.h->materials) : 0U,
              st.h ? unsigned(st.h->vertices) : 0U, before, re4dc_static_heap_free());
}
void release(const char* why) {
    if (!st.block) return;
    const unsigned room = st.room, bytes = st.bytes;
    close();
    ++pol.frees;
    re4dc_log("FARSHELL room=%03x freed bytes=%u (%s) heap=%d\n", room, bytes, why, re4dc_static_heap_free());
}
// ps2_open (world package open, and every world draw while it is open): the shell resident exactly while it is wanted.
void sync() {
    if (pol.room != ps2w.room) { pol.room = ps2w.room; pol.tried = false; pol.movie = false; }   // another room: no movie holds it
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
    // WORLD_METER: the QA row "Far shell" On keeps it resident at any View distance (Off only skips its draw, so the fog
    // and the translucent far stay as the View distance sets them).
    const bool want = mode == 1 && (re4dc_view_dist_get() == 2 || ::re4dc_qa_wshell == 1U) && !pol.movie &&
                      !yielded(ps2w.room);
#else
    const bool want = mode == 1 && re4dc_view_dist_get() == 2 && !pol.movie && !yielded(ps2w.room);
#endif
    if (!want) { release(pol.movie ? "movie" : "not Short"); return; }
    if (st.h || pol.tried) return;
    pol.tried = true;
    open(ps2w.room);
    if (st.h) ++pol.loads;
}
}  // namespace farshell
#elif RE4DC_FAR_SHELL_PART == 2
namespace {
int& far_shell_mode = farshell::mode;
float far_shell_noted = 0.0f;
constexpr float kBias = 0.97f;   // the shell's 1/w scale: 3 % deeper than its surface (the near world wins overlaps)
// Only at Short (user 10-16: "short shell + half vertices"; Near keeps its plain cut: fog and every pass at 18.75 m) and
// only in a room whose shell is loaded: elsewhere (no file, e.g. r103) the cut stays as it was, so no room shows an
// unfogged hole beyond the cut.
bool far_shell_cut_on() {
    return far_shell_mode && re4dc_view_dist_get() == 2 && farshell::st.h && farshell::st.room == ps2w.room;
}
}  // namespace
// Warp line `farshell <mode>` (dbgwarp_bridge.cpp) and benchmark rows.
extern "C" void re4dc_far_shell_set(int mode, const char* why) {
    far_shell_mode = mode < 0 || mode > 2 ? 1 : mode;
    farshell::pol.tried = false;   // the next sync() reads or frees the shell for the new mode
    re4dc_log("far shell: mode %d (%s)\n", far_shell_mode, why);
}
// option_rows.cpp re4dc_view_dist_set (Options View distance, warp line `view`): the next world draw reads the shell
// (Short) or frees it (Full / Near). A change of the option also forgets the rooms where heap 4 ran short.
extern "C" void re4dc_far_shell_view_changed(int level) {
    using namespace farshell;
    pol.tried = false;
    for (unsigned& r : pol.yielded) r = ~0U;
    (void)level;
}
// native_movie.cpp open (before heap_before, as the PCCULL cell): a route movie borrows the shell; no read until it ends.
extern "C" unsigned re4dc_far_shell_movie_release() {
    using namespace farshell;
    pol.movie = true;
    if (!st.block) return 0;
    const unsigned bytes = st.bytes;
    release("lent to a movie");
    ++pol.lends;
    pol.tried = false;   // read again at the first world draw after the movie
    return bytes;
}
// route_movie_bridge.cpp after the movie (beside re4dc_ps2_interior_movie_restore).
extern "C" void re4dc_far_shell_movie_restore() { farshell::pol.movie = false; }
// Heap 4 short (main_mem.cpp mem_alloc after a failed heap-4 allocation, ui_bridge.cpp re4dc_static_alloc before a
// refusal): free the shell so the caller can retry; the room is marked yielded. 1 when bytes were freed.
extern "C" int re4dc_far_shell_shortfall(unsigned need, const char* site) {
    using namespace farshell;
    if (!st.block || st.drawing) return 0;
    const unsigned room = st.room;
    unsigned k = 0;
    while (k < 3U && pol.yielded[k] != ~0U && pol.yielded[k] != room) ++k;
    pol.yielded[k] = room;
    ++pol.yields;
    re4dc_log("FARSHELL room=%03x yields to heap 4: need=%u at %s heap=%d\n", room, need, site ? site : "-",
              re4dc_static_heap_free());
    release("heap 4 short");
    return 1;
}
// native_static.cpp fog: 1 while the shell mode keeps Full's fog (the View distance cut applies to the opaque world only).
extern "C" int re4dc_far_shell_keeps_fog(void) { return far_shell_cut_on(); }
// re4dc_fog_note_far: the far plane before the View distance cut.
extern "C" void re4dc_far_shell_note_far(float far) { far_shell_noted = far; }
// native_ps2_world.cpp: the far for the PT / TR passes and the shell's outer bound (Full's, while the shell mode is on).
extern "C" float re4dc_far_shell_full(float cut) {
    if (!far_shell_cut_on()) return cut;
    return far_shell_noted > cut ? far_shell_noted : cut;
}
// After the PS2 world's opaque pass (native_ps2_world.cpp re4dc_ps2_world_draw): the shell between cut and full.
extern "C" int re4dc_far_shell_draw(float cut, float full) {
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
    re4dc::dsa24::Scope dsa_shell(re4dc::dsa24::Shell);
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    re4dc::wc24::Scope wc_phase(re4dc::wc24::FarOP,re4dc::wc24::Other);
    Wc24PassResult wc_result;
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    wc_result.why.tag(re4dc::wc24::ErrorFarShell,re4dc::wc24::ErrorShellUnavailable,farshell::st.room,ps2w.room);
#endif
    wc_result.complete=far_shell_mode!=1; // an explicitly disabled shell is an option, not a failed draw
    const unsigned wc_refused=farshell::st.refused;
#endif
    using namespace farshell;
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    if(far_shell_mode!=1)return 0;
    if(!st.h || st.room!=ps2w.room){wc_result.why.first(re4dc::wc24::ErrorShellUnavailable,st.room,ps2w.room);return 0;}
    if(!ps2w.camera){wc_result.why.first(re4dc::wc24::ErrorCameraUnavailable,st.room);return 0;}
#else
    if (far_shell_mode != 1 || !st.h || st.room != ps2w.room || !ps2w.camera) return 0;
#endif
#if RE4DC_GC_ASSET_GATE
    GcStaticSourceScope gcasset_source_scope(asset_proof,&st);
#endif
    const float* P = ps2w.projection;
    const float* V = ps2w.viewport;
    const float* v = ps2w.view;
    float vw[12];
    for (unsigned k = 0; k < 12; ++k) vw[k] = v[k];
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    if(P[0]!=0 || V[2]<=0 || V[3]<=0){
        wc_result.why.first(re4dc::wc24::ErrorProjection,0,unsigned(P[0]!=0)|(unsigned(V[2]<=0)<<1)|(unsigned(V[3]<=0)<<2));return 0;
    }
#else
    if (P[0] != 0 || V[2] <= 0 || V[3] <= 0) return 0;
#endif
    const float near = P[6] / (P[5] - 1);
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    if(!re4dc::render::is_finite(near) || near<=0 || !(full>cut)){
        uint32_t bits;std::memcpy(&bits,&near,4);
        wc_result.why.first(re4dc::wc24::ErrorDepth,bits,unsigned(!re4dc::render::is_finite(near))|(unsigned(near<=0)<<1)|(unsigned(!(full>cut))<<2));return 0;
    }
#else
    if (!re4dc::render::is_finite(near) || near <= 0 || !(full > cut)) return 0;
#endif
    const float near_w = near * 1.01f;
    const float sx = V[2] * .5f * RE4DC_SCREEN_WF / V[2], sy = -V[3] * .5f * RE4DC_SCREEN_HF / V[3];
    const float ox = (V[0] + V[2] * .5f) * RE4DC_SCREEN_WF / V[2], oy = (V[1] + V[3] * .5f) * RE4DC_SCREEN_HF / V[3];
    const unsigned ng = st.h->groups;
    Re4dcModelDirect out{};
    std::uint32_t* sq = nullptr;
    unsigned slots = 0, open_mat = ~0U, drawn = 0;
    float us = 1, vs = 1;
    const float az0 = v[8], az1 = v[9], az2 = v[10], az3 = v[11];
    const float fz0 = az0 < 0 ? -az0 : az0, fz1 = az1 < 0 ? -az1 : az1, fz2 = az2 < 0 ? -az2 : az2;
    const std::uint32_t* const lut = st.lut;
    const float split = .5f * (cut + full);   // fine / coarse level split (version 2 files): 18.75 m at Short
    struct Busy { Busy() { st.drawing = true; } ~Busy() { st.drawing = false; } } busy;   // no shortfall free mid-draw
    for (unsigned gi = 0; gi < ng; ++gi) {
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
        dsa_shell.phase(re4dc::dsa24::Work);
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        wc_phase.phase(re4dc::wc24::Selection);
#endif
        const Group& g = st.groups[gi];
        // depth range of the box (view space looks down -z): centre depth +- the half extents on |view z row| (the
        // same range as the 8 corners), then the frustum test to Full's far
        const float* lo = g.lo;
        const float* hi = g.hi;
        if (const unsigned level = g.material >> 14) {
            // version 2 levels: the file box is the cell's box over both levels, so one decision per cell picks one
            // level (fine while the cell's nearest point is closer than the split, coarse beyond it); culling then
            // uses the group's own box
            const float ex = .5f * (hi[0] - lo[0]), ey = .5f * (hi[1] - lo[1]), ez = .5f * (hi[2] - lo[2]);
            const float d = -(az0 * (lo[0] + ex) + az1 * (lo[1] + ey) + az2 * (lo[2] + ez) + az3);
            const float r = fz0 * ex + fz1 * ey + fz2 * ez;
            if ((level == 1U) != (d - r < split)) continue;
        }
        if (st.tight) { lo = st.tight + 6 * gi; hi = lo + 3; }
        {
            const float ex = .5f * (hi[0] - lo[0]), ey = .5f * (hi[1] - lo[1]), ez = .5f * (hi[2] - lo[2]);
            const float d = -(az0 * (lo[0] + ex) + az1 * (lo[1] + ey) + az2 * (lo[2] + ez) + az3);
            const float r = fz0 * ex + fz1 * ey + fz2 * ez;
            if (d + r <= cut || d - r >= full) continue;
        }
        const re4dc::render::DrawBounds b{{lo[0], lo[1], lo[2]}, {hi[0], hi[1], hi[2]}};
        if (!re4dc::render::group_visible(b, v, P, V, near, full, 0)) continue;
        const unsigned mat = g.material & 0x3fffU;
        if (mat != open_mat) {
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
            wc_phase.phase(re4dc::wc24::HeaderMaterial);
#endif
            if (sq) { re4dc_model_direct_end(slots); sq = nullptr; }
            const Mat& m = st.mats[mat];
            const unsigned key[6] = {m.crc, m.fnv, m.w, m.h, 0U, 0U};
            open_mat = mat;
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
            if(!re4dc_ps2_world_direct_begin(key,&out)){
                wc_result.why.first(re4dc::wc24::ErrorShellBindRefusal,gi,mat);++st.refused;continue;
            }
#else
            if (!re4dc_ps2_world_direct_begin(key, &out)) { ++st.refused; continue; }
#endif
            sq = out.sq; slots = 0; us = out.u_scale; vs = out.v_scale; ++st.headers;
        }
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
        if(!sq || out.scratch_capacity<g.vcount){
            wc_result.why.first(re4dc::wc24::ErrorShellScratchRefusal,out.scratch_capacity,g.vcount);++st.refused;continue;
        }
#else
        if (!sq || out.scratch_capacity < g.vcount) { ++st.refused; continue; }
#endif
        ++drawn;
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
        re4dc::dsa24::count(re4dc::dsa24::Parts);
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        wc_phase.phase(re4dc::wc24::Transform);
        re4dc::wc24::count(re4dc::wc24::Transformed,g.vcount);
#endif
        // transform once: screen x, y, 1/w (biased), u, v, argb; flags 0 = behind the near plane. One 3x4 per group maps
        // the group's i16 grid straight to (x', y', w) (view, projection, viewport, origin and scale folded in), so a
        // corner is 3 int->float, one ftrv and one divide; colours expand through a 2 x 256 table. Strips then copy the
        // prepared 32-byte vertices to the store queue by index (measured 10-16 on the hw model: the first C loop cost
        // 2.31 ms / 505k instructions per frame at the r101 cross, mostly coefficient reloads and per-field copies).
        auto* buf = static_cast<pvr_vertex_t*>(out.scratch);
        const Vert* src = st.verts + g.first_vertex;
        float m[12];
        {
            const float s0 = g.scale;
            float rx[4], ry[4], rw[4];
            for (unsigned c = 0; c < 4; ++c) {   // rows on world coordinates: x' = A.p, y' = B.p, w = -vz
                rx[c] = sx * P[1] * vw[c] + (sx * P[2] - ox) * vw[8 + c];
                ry[c] = sy * P[3] * vw[4 + c] + (sy * P[4] - oy) * vw[8 + c];
                rw[c] = -vw[8 + c];
            }
            const float* r[3] = {rx, ry, rw};
            for (unsigned k = 0; k < 3; ++k) {
                m[4 * k + 0] = r[k][0] * s0; m[4 * k + 1] = r[k][1] * s0; m[4 * k + 2] = r[k][2] * s0;
                m[4 * k + 3] = r[k][0] * g.origin[0] + r[k][1] * g.origin[1] + r[k][2] * g.origin[2] + r[k][3];
            }
        }
        const float su = us * (1.0f / 2048.0f), sv = vs * (1.0f / 2048.0f), bu = g.ub * us, bv = g.vb * vs, nw = near_w;
#if defined(__sh__)
        // XMTRX = the folded 3x4 (rows x', y', w, w): one ftrv per corner (KOS mat_trans_nodiv), as native_actor.cpp does
        {
            alignas(32) matrix_t xm;
            for (unsigned c = 0; c < 4; ++c) { xm[c][0] = m[c]; xm[c][1] = m[4 + c]; xm[c][2] = m[8 + c]; xm[c][3] = m[8 + c]; }
            mat_load(&xm);
        }
#endif
        for (unsigned i = 0, n = g.vcount; i < n; ++i) {
            const Vert& q = src[i];
            float x = float(q.x), y = float(q.y), z = float(q.z), w = 1.0f;
#if defined(__sh__)
            mat_trans_nodiv(x, y, z, w);
#else
            {
                const float tx = m[0] * x + m[1] * y + m[2] * z + m[3], ty = m[4] * x + m[5] * y + m[6] * z + m[7];
                w = m[8] * x + m[9] * y + m[10] * z + m[11];
                x = tx; y = ty;
            }
#endif
            std::uint32_t* o = reinterpret_cast<std::uint32_t*>(buf + i);
            if (!(w > nw)) { o[0] = 0; continue; }
            const float inv = 1.0f / w;
            float* of = reinterpret_cast<float*>(o);
            o[0] = PVR_CMD_VERTEX;
            of[1] = x * inv;
            of[2] = y * inv;
            of[3] = inv * kBias;
            of[4] = float(q.u) * su + bu;
            of[5] = float(q.v) * sv + bv;
            o[6] = lut[q.rgb >> 8] | lut[256U + (q.rgb & 255U)];
            o[7] = 0;
        }
        st.vtx += g.vcount;
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
        dsa_shell.phase(re4dc::dsa24::Submit);
        unsigned dsa_in=0,dsa_out=0;
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        wc_phase.phase(re4dc::wc24::Submit);
        unsigned wc_strip_inputs=0;
#endif
        const std::uint8_t* p = st.strips + g.first_strip;
        const std::uint8_t* const e = p + g.strip_bytes;
        const std::uint32_t* const b32 = reinterpret_cast<const std::uint32_t*>(buf);
        while (p < e) {
            const unsigned n = *p++;
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
            dsa_in+=n-2U;
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
            wc_strip_inputs+=n;
#endif
            unsigned ok = ~0U;
            for (unsigned k = 0; k < n; ++k) ok &= b32[8U * p[k]];   // flags word: 0 = behind the near plane
            if (ok) {
                // copy the prepared 32-byte vertices into the store queue (flags word rewritten for the strip end)
                for (unsigned k = 0; k < n; ++k) {
                    const std::uint32_t* s = b32 + 8U * p[k];
#if RE4DC_TA_HASH
                    const float* f = reinterpret_cast<const float*>(s);
                    sq = re4dc_ta_vertex(sq, k + 1 == n ? PVR_CMD_VERTEX_EOL : PVR_CMD_VERTEX, f[1], f[2], f[3], f[4], f[5], s[6]);
#else
                    const std::uint32_t s1 = s[1], s2 = s[2], s3 = s[3], s4 = s[4], s5 = s[5], s6 = s[6];
                    sq[0] = k + 1 == n ? PVR_CMD_VERTEX_EOL : PVR_CMD_VERTEX;
                    sq[1] = s1; sq[2] = s2; sq[3] = s3; sq[4] = s4; sq[5] = s5; sq[6] = s6; sq[7] = 0;
                    sq_flush(sq);
                    sq += 8;
#endif
                }
                slots += n;
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
                dsa_out+=n-2U;
#endif
                st.strip_verts += n;
            } else
                ++st.strips_cut;
            p += n;
        }
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
        re4dc::dsa24::count(re4dc::dsa24::TrianglesIn,dsa_in);
        re4dc::dsa24::count(re4dc::dsa24::TrianglesOut,dsa_out);
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        re4dc::wc24::count(re4dc::wc24::StripInputs,wc_strip_inputs);
#endif
    }
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    wc_phase.phase(re4dc::wc24::Submit);
#endif
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
    dsa_shell.phase(re4dc::dsa24::Submit);
#endif
    if (sq) re4dc_model_direct_end(slots);
    st.groups_drawn += drawn;
    ++st.shown;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    wc_result.complete=st.refused==wc_refused;
#endif
    return 1;
}
// Once per frame from re4dc_ps2_mesh_log's caller (every 120 frames: the counters since the last line).
extern "C" void re4dc_far_shell_log(unsigned frame) {
    using namespace farshell;
    if (frame % 120U) return;
    re4dc_log("FARSHELL frame=%u mode=%d view=%d room=%03x loaded=%u shown=%u groups=%u verts=%u strip_verts=%u strips_cut=%u "
              "headers=%u refused=%u bytes=%u loads=%u frees=%u lends=%u yields=%u\n", frame, far_shell_mode,
              re4dc_view_dist_get(), ps2w.room, st.h ? 1U : 0U, st.shown, st.groups_drawn, st.vtx, st.strip_verts,
              st.strips_cut, st.headers, st.refused, st.block ? st.bytes : 0U, pol.loads, pol.frees, pol.lends, pol.yields);
    st.shown = st.groups_drawn = st.vtx = st.strip_verts = st.strips_cut = st.headers = st.refused = 0;
}
#endif
