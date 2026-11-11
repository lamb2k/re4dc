// CHARS31_COUNT=1 (chars31.mk; diagnostic only, default 0 = nothing built; lane chars31, review answer 2 item 1):
// a per-model table of the character path. Every part that reaches re4dc_actor_submit / re4dc_actor_submit_chunks is
// attributed to its source model (cModel*): parts, parts committed with output / committed empty / other results,
// "AL25 flat" lit parts and their flat / multiply vertices, transformed vertices by kernel (s16 / u16 skin, rigid),
// meshlet-culled vertices, emitted triangles, view distance (min/max of the part origins), parts with material alpha
// 0 (hidden). Every 120 UI frames: one "C31W" line (window totals, including the boundary counters) and one "C31"
// line per model, heaviest first. Included inside native_actor_fast.cpp's anonymous namespace (stats, light25_stats).
// Reads only; draws and decides nothing.
extern "C" void re4dc_c31_describe(const void* model, unsigned* key, int* pos);          // model_bridge.cpp
extern "C" void re4dc_c31_model_counts(unsigned* parts, unsigned* other, unsigned* in, unsigned* out);  // native_ui.cpp
extern "C" unsigned re4dc_ui_frame();
extern "C" void re4dc_c31_ra_dump(unsigned frame);  // native_ui.cpp: results outside any guarded part, by caller
namespace c31 {
struct Row {
    const void* model; unsigned key; int pos[3];
    unsigned calls, out_parts, empty_parts, other_parts, al25, flat_v, mult_v, s16_v, u16_v, rig_v, s16_p, u16_p, rig_p,
        cull_v, tris_in, tris_out, hidden, verts;
    float dmin, dmax;
};
constexpr unsigned kRows = 48;
Row rows[kRows + 1];  // the last row collects models past kRows
unsigned nrows, frame0, depth, mp0, mo0, mi0, mt0, al0;
bool started;
Row* cur;
unsigned kern_flags;  // per guarded part: 1 s16, 2 u16, 4 rigid
Row& row_of(const void* model) {
    for (unsigned i = 0; i < nrows; ++i) if (rows[i].model == model) return rows[i];
    Row& r = nrows < kRows ? rows[nrows++] : rows[kRows];
    if (&r != &rows[kRows] || !r.model) {
        r = Row{}; r.model = model; r.dmin = 3.0e38f; r.dmax = 0.0f;
        re4dc_c31_describe(model, &r.key, r.pos);
        if (&r == &rows[kRows]) r.key = 0xFFFFFFFFU;
    }
    return r;
}
void flush(unsigned frame) {
    unsigned mp, mo, mi, mt;
    re4dc_c31_model_counts(&mp, &mo, &mi, &mt);
#if RE4DC_ACTOR_LIGHT_FAST_ONLY
    const unsigned al = light25_stats.parts;
#else
    const unsigned al = 0;
#endif
    const unsigned frames = frame - frame0;
    if (started && frames) {
        unsigned ap = 0;
        for (unsigned i = 0; i <= kRows; ++i) ap += rows[i].out_parts + rows[i].empty_parts;
        re4dc_log("C31W f=%u frames=%u models=%u committed=%u attributed=%u other=%u tris_in=%u tris_out=%u al25=%u\n",
                  frame, frames, nrows, mp - mp0, ap, mo - mo0, mi - mi0, mt - mt0, al - al0);
        for (unsigned n = 0; n <= kRows; ++n) {
            unsigned best = ~0U;
            for (unsigned i = 0; i <= kRows; ++i)
                if (rows[i].calls && (best == ~0U || rows[i].verts > rows[best].verts)) best = i;
            if (best == ~0U) break;
            Row& r = rows[best];
            re4dc_log("C31 f=%u m=%06x key=%08x calls=%u out=%u empty=%u oth=%u al25=%u flat=%u mult=%u s16=%u/%u u16=%u/%u "
                      "rig=%u/%u verts=%u cull=%u tin=%u tout=%u hid=%u d=%d-%d pos=%d,%d,%d\n",
                      frame, unsigned(reinterpret_cast<std::uintptr_t>(r.model)) & 0xFFFFFFU, r.key, r.calls, r.out_parts,
                      r.empty_parts, r.other_parts, r.al25, r.flat_v, r.mult_v, r.s16_p, r.s16_v, r.u16_p, r.u16_v, r.rig_p,
                      r.rig_v, r.verts, r.cull_v, r.tris_in, r.tris_out, r.hidden, r.dmin < 1.0e30f ? int(r.dmin) : -1,
                      int(r.dmax), r.pos[0], r.pos[1], r.pos[2]);
            r.calls = 0;
        }
        re4dc_c31_ra_dump(frame);
    }
    for (Row& r : rows) r = Row{};
    nrows = 0; started = true; frame0 = frame;
    mp0 = mp; mo0 = mo; mi0 = mi; mt0 = mt; al0 = al;
}
// One part (outermost submit only): deltas of the boundary and AL25 counters around it.
struct Guard {
    bool on; Row* prev; unsigned kf_prev, mp, mo, mi, mt, al, fl, mu;
    explicit Guard(const Re4dcModelPart* p) : on(p && depth == 0), prev(cur), kf_prev(kern_flags) {
        ++depth;
        if (!on) return;
        const unsigned frame = re4dc_ui_frame();
        if (!started || frame - frame0 >= 120U) flush(frame);
        Row& r = row_of(p->model);
        cur = &r; kern_flags = 0; ++r.calls;
        const float* m = p->modelview;
        const float d = std::sqrt(m[3] * m[3] + m[7] * m[7] + m[11] * m[11]);
        if (d < r.dmin) r.dmin = d;
        if (d > r.dmax) r.dmax = d;
        if (!(p->alpha_state & 256) && (p->alpha_state & 255) == 0) ++r.hidden;
        re4dc_c31_model_counts(&mp, &mo, &mi, &mt);
#if RE4DC_ACTOR_LIGHT_FAST_ONLY
        al = light25_stats.parts; fl = light25_stats.flat_vertices; mu = light25_stats.multiply_vertices;
#else
        al = fl = mu = 0;
#endif
    }
    ~Guard() {
        --depth;
        if (!on) return;
        Row& r = *cur;
        unsigned mp2, mo2, mi2, mt2;
        re4dc_c31_model_counts(&mp2, &mo2, &mi2, &mt2);
        if (mp2 != mp) { if (mt2 != mt) r.out_parts += mp2 - mp; else r.empty_parts += mp2 - mp; }
        r.other_parts += mo2 - mo; r.tris_in += mi2 - mi; r.tris_out += mt2 - mt;
#if RE4DC_ACTOR_LIGHT_FAST_ONLY
        r.al25 += light25_stats.parts - al; r.flat_v += light25_stats.flat_vertices - fl;
        r.mult_v += light25_stats.multiply_vertices - mu;
#endif
        if (kern_flags & 1U) ++r.s16_p;
        if (kern_flags & 2U) ++r.u16_p;
        if (kern_flags & 4U) ++r.rig_p;
        cur = prev; kern_flags = kf_prev;
    }
};
inline void kern(bool skin, bool s16, unsigned n) {
    if (!cur) return;
    cur->verts += n;
    if (!skin) { cur->rig_v += n; kern_flags |= 4U; }
    else if (s16) { cur->s16_v += n; kern_flags |= 1U; }
    else { cur->u16_v += n; kern_flags |= 2U; }
}
inline void cull(unsigned n) { if (cur) cur->cull_v += n; }
}  // namespace c31
extern "C" unsigned re4dc_c31_depth() { return c31::depth; }
#define C31_GUARD(pp) c31::Guard c31_guard(pp)
#define C31_KERN(skin, s16, n) c31::kern((skin), (s16), (n))
#define C31_CULL(n) c31::cull(n)
