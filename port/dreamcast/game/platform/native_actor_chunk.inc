// platform/native_actor_chunk.inc -- CHAR_CHUNK (chardraw19.mk; lane character-draw-path, CHARDRAW19-STATUS.md).
// Included by native_actor_fast.cpp inside its anonymous namespace, after Part / pass_positions, only when
// RE4DC_CHAR_CHUNK is set (knob 0 compiles nothing).
//
// Stage 1 (exact, render only): the character front end of the chunk path.
//   * Position once: a chunk's records are sorted by (position palette, normal palette, vi, ni) by the converter,
//     so records that repeat a skinned point sit next to each other. Each distinct point is skinned and projected
//     once by the same kernel (pass_positions over a compacted record list), then copied to the records that repeat
//     it; a repeat with other texture coordinates gets them from the kernel's own float steps (fmul, then fadd).
//   * Submit: through chunk_sink_* below, an adapter with the shape of chunk_submit.h (begin / points / strips /
//     end) over today's store-queue window (Part::whole / Part::strips, emit_sq and the clipper unchanged). When
//     scenery19's chunk_submit v1 lands, chunk_sink_* forward to re4dc_chunk_* (one switch, CHAR_CHUNK_BACKEND).
// Exactness: the TA words of every vertex are the knob-off path's (same kernel on the same inputs, a copy of its
// output, or the same two float operations for u / v); strip order, culling and clipping are unchanged.

constexpr unsigned kChunkRecPad = 2;  // the kernels read up to two records past the last
alignas(32) u16 chunk_rec[(kMaxVertices + kChunkRecPad) * 3];
u8 chunk_src[kMaxVertices];           // record -> compacted point
struct ChunkStats { unsigned chunks, records, points; } chunk_stats;
unsigned chunk_stats_log = 0;

#if defined(__GNUC__) && !defined(__clang__)
__attribute__((optimize("fp-contract=off")))
#endif
inline void chunk_uv(pvr_vertex_t& d, const u8* uv, unsigned ti, bool s16_uv, const PosConst& k) {
    const u8* t = uv + ti * 4U;
    const float tu = s16_uv ? float(*reinterpret_cast<const short*>(t)) : float(*reinterpret_cast<const u16*>(t));
    const float tv = s16_uv ? float(*reinterpret_cast<const short*>(t + 2)) : float(*reinterpret_cast<const u16*>(t + 2));
    volatile float mu = tu * k.au, mv = tv * k.av;  // two roundings, as the kernel's fmul + fadd
    d.u = mu + k.bu; d.v = mv + k.bv;
}

// pass_positions with each repeated point done once. all / any as pass_positions (repeats add no new outcode).
void chunk_positions(Part& e, const Records& r, unsigned n, const PosConst& k, bool s16_uv, unsigned& all,
                     unsigned& any) {
    unsigned u = 0;
    unsigned prev = ~0U;
    for (unsigned i = 0; i < n; ++i) {
        const unsigned vi = r.vi(i);
        if (vi != prev) {
            u16* d = chunk_rec + u * 3U;
            d[0] = u16(vi); d[1] = u16(r.ni(i)); d[2] = u16(r.ti(i));
            prev = vi; ++u;
        }
        chunk_src[i] = u8(u - 1U);
    }
    ++chunk_stats.chunks; chunk_stats.records += n; chunk_stats.points += u;
    if (frame_serial - chunk_stats_log >= 600U) {
        chunk_stats_log = frame_serial;
        re4dc_log("char chunk: frame=%u chunks=%u records=%u points=%u\n", frame_serial, chunk_stats.chunks,
                  chunk_stats.records, chunk_stats.points);
        void nj_dump(unsigned);
        nj_dump(frame_serial);
    }
    if (u == n) { pass_positions(e, r, n, k, s16_uv, all, any); return; }
    for (unsigned j = 0; j < kChunkRecPad * 3U; ++j) chunk_rec[u * 3U + j] = chunk_rec[(u - 1U) * 3U + j % 3U];
    const Records c{chunk_rec, 3U, r.color, false};
    pass_positions(e, c, u, k, s16_uv, all, any);
    // Expand in place from the back: point chunk_src[i] <= i, and slots above i are already final.
    pvr_vertex_t* v = e.cache.v;
    u8* oc = e.cache.oc;
    for (unsigned i = n; i-- > 0;) {
        const unsigned s = chunk_src[i];
        if (s == i) continue;
        const pvr_vertex_t& from = v[s];
        pvr_vertex_t& to = v[i];
        to.x = from.x; to.y = from.y; to.z = from.z;
        if (r.ti(i) == chunk_rec[s * 3U + 2U]) { to.u = from.u; to.v = from.v; }
        else chunk_uv(to, e.p.uv, r.ti(i), s16_uv, k);
        oc[i] = oc[s];
    }
#if RE4DC_CHAR_CHUNK == 2
    // Check build: the knob-off pass into a side cache, compared word for word (x, y, z, u, v, outcode).
    {
        alignas(32) static pvr_vertex_t ref_v[kMaxVertices + 4];
        alignas(32) static u8 ref_oc[kMaxVertices + 32];
        static unsigned mis[6], checked, logged;
        const Cache keep = e.cache;
        e.cache.v = ref_v; e.cache.oc = ref_oc;
        unsigned a2 = ~0U, o2 = 0;
        pass_positions(e, r, n, k, s16_uv, a2, o2);
        e.cache = keep;
        for (unsigned i = 0; i < n; ++i) {
            const u32* x = reinterpret_cast<const u32*>(&v[i]); const u32* y = reinterpret_cast<const u32*>(&ref_v[i]);
            const unsigned bad = (x[1] != y[1]) | ((x[2] != y[2]) << 1) | ((x[3] != y[3]) << 2) | ((x[4] != y[4]) << 3) |
                                 ((x[5] != y[5]) << 4) | ((oc[i] != ref_oc[i]) << 5);
            for (unsigned b = 0; b < 6; ++b) mis[b] += (bad >> b) & 1U;
            if (bad && logged < 40) {
                ++logged;
                printf("CCHK bad=%x i=%u n=%u u=%u src=%u vi=%u ti=%u srcti=%u U=%08x/%08x V=%08x/%08x X=%08x/%08x\n", bad,
                          i, n, u, chunk_src[i], r.vi(i), r.ti(i), chunk_rec[chunk_src[i] * 3U + 2U], x[4], y[4], x[5], y[5],
                          x[1], y[1]);
            }
        }
        checked += n;
        if ((checked & ~16383U) != ((checked - n) & ~16383U))
            printf("CCHK frame=%u checked=%u x=%u y=%u z=%u u=%u v=%u oc=%u\n", frame_serial, checked, mis[0], mis[1],
                      mis[2], mis[3], mis[4], mis[5]);
    }
#endif
}

// Light once per distinct normal: pass_lights (fast fold) over the chunk's distinct normal indices into a side
// cache, then each record takes its normal's colour word. A record's lit colour is a function of its normal (and
// the normal's palette entry) and the part's alpha only, unless the part has per-vertex alpha (e.colors), which
// keeps today's pass.
u8 chunk_nsrc[kMaxVertices];
u16 chunk_nkey[256];   // open-address table: normal index + 1 (0 = empty)
u8 chunk_nval[256];
unsigned chunk_backend_meshlets, chunk_backend_fallbacks;
struct ChunkLightStats { unsigned records, normals; } chunk_light_stats;
void chunk_lights(Part& e, const Lights& L, const Records& r, unsigned n) {
    if (e.colors || !n) { pass_lights(e, L, r, n); return; }
    std::memset(chunk_nkey, 0, sizeof chunk_nkey);
    unsigned u = 0;
    for (unsigned i = 0; i < n; ++i) {
        const unsigned ni = r.ni(i);
        unsigned h = (ni * 2654435761U) >> 24;
        while (chunk_nkey[h] && chunk_nkey[h] != ni + 1U) h = (h + 1U) & 255U;
        if (!chunk_nkey[h]) {
            chunk_nkey[h] = u16(ni + 1U); chunk_nval[h] = u8(u);
            u16* d = chunk_rec + u * 3U;
            d[0] = u16(r.vi(i)); d[1] = u16(ni); d[2] = u16(r.ti(i));
            ++u;
        }
        chunk_nsrc[i] = chunk_nval[h];
    }
    chunk_light_stats.records += n; chunk_light_stats.normals += u;
    if (u == n) { pass_lights(e, L, r, n); return; }
    for (unsigned j = 0; j < kChunkRecPad * 3U; ++j) chunk_rec[u * 3U + j] = chunk_rec[(u - 1U) * 3U + j % 3U];
    const Records c{chunk_rec, 3U, r.color, false};
    // Side cache from the frame workspace (per submit scratch, released here): no static buffer, KOS untouched.
    const unsigned mark = workspace_top;
    pvr_vertex_t* const lit = static_cast<pvr_vertex_t*>(scratch((u + 4U) * unsigned(sizeof(pvr_vertex_t))));
    if (!lit) { pass_lights(e, L, r, n); return; }
    pvr_vertex_t* const keep = e.cache.v;
    e.cache.v = lit;
    pass_lights(e, L, c, u);
    e.cache.v = keep;
    for (unsigned i = 0; i < n; ++i) keep[i].argb = lit[chunk_nsrc[i]].argb;
    workspace_top = mark;
#if RE4DC_CHAR_CHUNK == 2
    {
        alignas(32) static pvr_vertex_t ref_v[kMaxVertices + 4];
        static unsigned bad, checked, logged;
        e.cache.v = ref_v;
        pass_lights(e, L, r, n);
        e.cache.v = keep;
        for (unsigned i = 0; i < n; ++i)
            if (ref_v[i].argb != keep[i].argb && ++bad && logged < 20) {
                ++logged;
                printf("LCHK i=%u n=%u ni=%u got=%08x want=%08x\n", i, n, r.ni(i), unsigned(keep[i].argb),
                       unsigned(ref_v[i].argb));
            }
        checked += n;
        if ((checked & ~16383U) != ((checked - n) & ~16383U))
            printf("LCHK checked=%u bad=%u normals=%u/%u backend meshlets=%u fallbacks=%u\n", checked, bad,
                   chunk_light_stats.normals, chunk_light_stats.records, chunk_backend_meshlets,
                   chunk_backend_fallbacks);
    }
#endif
}

// The chunk sink: today's store-queue window (adapter) or, with CHUNK_SUBMIT, the shared back end (chunk_submit.h v1).
#if defined(RE4DC_CHAR_CHUNK_BACKEND) && RE4DC_CHAR_CHUNK_BACKEND
}  // namespace
#include "chunk_submit.h"
namespace {
// Actor outcode byte (AVK layout: near 32, far 16, left 8, right 4, top 2, bottom 1) -> the back end's (left 32,
// right 16, top 8, bottom 4, near 2, far 1).
inline u8 chunk_code(unsigned oc) {
    return u8(((oc & (kOcLeft | kOcRight | kOcTop | kOcBottom)) == 0 ? 0U : 0U) |
              ((oc & kOcLeft) ? 32U : 0U) | ((oc & kOcRight) ? 16U : 0U) | ((oc & kOcTop) ? 8U : 0U) |
              ((oc & kOcBottom) ? 4U : 0U) | ((oc & kOcNear) ? 2U : 0U) | ((oc & kOcFar) ? 1U : 0U));
}
// The back end hands every strip with a corner past near or far to the caller. The actor rule is near-only
// clipping (far and the screen edges only cull, the PVR scissors the rest), so the callback applies it: culled when
// every corner shares a screen edge or far, sent as is when no corner is past near, else today's clipper.
struct ChunkClip { Part* e; const Records* r; re4dc_chunk_sink* s; };
int chunk_clip(void* ctx, const uint8_t* idx, unsigned n, unsigned form) {
    (void)form;  // actor form: bit 7 on the strip's last index, as Part::strip / clip_strip take it
    ChunkClip& c = *static_cast<ChunkClip*>(ctx);
    Part& e = *c.e;
    unsigned all = ~0U, any = 0;
    for (unsigned k = 0; k < n; ++k) { const unsigned oc = e.cache.oc[idx[k] & 127U]; all &= oc; any |= oc; }
    if (all & kOcCull) { ++stats.strips_culled; return 1; }
    e.sq = *re4dc_chunk_sq(c.s);
    bool ok = true;
    if (!(any & kOcNear)) { e.strip(idx, n); e.output += n - 2U; }
    else ok = e.clip_strip(*c.r, idx, n);
    *re4dc_chunk_sq(c.s) = e.sq;
    return ok ? 1 : -1;
}
// One meshlet through the back end: points = the records' screen words (already skinned once per distinct point),
// corners = the records (u, v, colour), strips = the meshlet's actor-form index list. false: not taken (caller
// falls back to the adapter, nothing sent).
bool chunk_backend(Part& e, const Records& r, const u8* index, unsigned nv, unsigned ni, unsigned nt, bool& ok) {
    if (!e.direct || nv > RE4DC_CHUNK_MAX_POINTS || e.slots + 6U * nt > 32767U) return false;
    const unsigned mark = workspace_top;
    u8* const work = static_cast<u8*>(scratch(RE4DC_CHUNK_CACHE_BYTES + nv * 28U + 64U));
    if (!work) { ++chunk_backend_fallbacks; return false; }
    float* const xyz = reinterpret_cast<float*>(work + RE4DC_CHUNK_CACHE_BYTES);
    float* const uv = xyz + 3U * nv;
    u32* const argb = reinterpret_cast<u32*>(uv + 2U * nv);
    u8* const codes = reinterpret_cast<u8*>(argb + nv);
    u8* const point = codes + nv;
    for (unsigned i = 0; i < nv; ++i) {
        const pvr_vertex_t& v = e.cache.v[i];
        xyz[3 * i] = v.x; xyz[3 * i + 1] = v.y; xyz[3 * i + 2] = v.z;
        uv[2 * i] = v.u; uv[2 * i + 1] = v.v; argb[i] = v.argb;
        codes[i] = chunk_code(e.cache.oc[i]); point[i] = u8(i);
    }
    re4dc_chunk_sink s;
    ChunkClip cc{&e, &r, &s};
    re4dc_chunk_window_begin(&s, e.sq, work, 255U, chunk_clip, &cc);
    re4dc_chunk_points_screen(&s, xyz, codes, nv);
    re4dc_chunk_corners(&s, point, uv, argb, nv);
    const unsigned out0 = e.output, slots0 = e.slots;
    const int res = re4dc_chunk_strips(&s, index, ni, RE4DC_CHUNK_STRIPS_ACTOR);
    e.sq = re4dc_chunk_window_end(&s);
    // the callback's own sends are already in e.slots / e.output; add the back end's direct strips
    e.slots += s.slots; e.output += s.slots - 2U * s.strips;
    (void)out0; (void)slots0;
    e.input += nt;
    workspace_top = mark;
    ++chunk_backend_meshlets;
    ok = res > 0;
    return true;
}
#endif

// NINJA DIAG (throwaway, lane chardraw19 Ninja guide check; never delivered)
const Re4dcModelPart* nj_part;
struct NjM { const void* model; unsigned char id, typ; unsigned tris, strips, idx; };
NjM nj_rows[64];
struct NjN { const void* arr; const void* model; unsigned bytes, count, shift, stride; };
NjN nj_norm[512]; unsigned nj_nn;
inline NjM& nj_row() {
    const void* m = nj_part ? nj_part->model : nullptr;
    for (auto& x : nj_rows) {
        if (x.model == m) return x;
        if (!x.model) { x.model = m; x.id = m ? static_cast<const unsigned char*>(m)[0x100] : 0xff;
                        x.typ = m ? static_cast<const unsigned char*>(m)[0x101] : 0xff; return x; }
    }
    return nj_rows[63];
}
inline void nj_note(const Re4dcModelPart* p) {
    nj_part = p;
    if (!p->normals) return;
    for (unsigned i = 0; i < nj_nn; ++i) if (nj_norm[i].arr == p->normals) return;
    if (nj_nn < 512) nj_norm[nj_nn++] = {p->normals, p->model, p->normal_count * p->normal_stride, p->normal_count,
                                         p->normal_shift, p->normal_stride};
}
void nj_dump(unsigned frame) {
    for (auto& x : nj_rows) {
        if (!x.model) break;
        unsigned nb = 0, nc = 0, sh = 0, st = 0, arrs = 0;
        for (unsigned i = 0; i < nj_nn; ++i)
            if (nj_norm[i].model == x.model) { nb += nj_norm[i].bytes; nc += nj_norm[i].count; sh = nj_norm[i].shift;
                                               st = nj_norm[i].stride; ++arrs; }
        printf("NJ frame=%u model=%08x id=%02x typ=%02x tris=%u strips=%u idx=%u normals=%u arrays=%u bytes=%u shift=%u stride=%u\n",
               frame, unsigned(reinterpret_cast<uintptr_t>(x.model)), x.id, x.typ, x.tris, x.strips, x.idx, nc, arrs,
               nb, sh, st);
    }
    __builtin_memset(nj_rows, 0, sizeof(nj_rows));
    nj_nn = 0;
}

struct ChunkSink { Part* e; };
inline void chunk_sink_begin(ChunkSink& s, Part& e) { s.e = &e; }
inline bool chunk_sink_strips(ChunkSink& s, const Records& r, const u8* index, unsigned nv, unsigned ni, unsigned nt,
                              unsigned any) {
    Part& e = *s.e;
    {
        NjM& row = nj_row();
        row.tris += nt; row.idx += ni;
        for (unsigned k = 0; k < ni; ++k) row.strips += (index[k] & 0x80U) != 0;
    }
#if defined(RE4DC_CHAR_CHUNK_BACKEND) && RE4DC_CHAR_CHUNK_BACKEND
    bool ok = true;
    if (chunk_backend(e, r, index, nv, ni, nt, ok)) return ok;
#else
    (void)nv;
#endif
    if (!(any & (kOcCull | kOcNear)) && e.fits(ni)) { ++stats.meshlets_whole; return e.whole(index, ni, nt); }
    return e.strips(r, index, ni);
}
inline void chunk_sink_end(ChunkSink&) {}
