// platform/native_actor_zam.inc -- CHAR_SH4ZAM (chardraw19.mk; lane character-draw-path, CHARDRAW19-STATUS.md).
// Included by native_actor_fast.cpp inside its anonymous namespace, before re4dc_actor_submit, only when
// RE4DC_CHAR_SH4ZAM is set.
//
// Lighting from a per-part colour table. A fast-lit record's colour is a function of its normal (with the normal's own
// palette entry) and the part's lights and alpha. So the part's normals are lit once per draw call, in index order, by
// today's kernel (pass_lights over synthetic records, 64 at a time), and each meshlet then gathers colour[ni] per
// corner. Parts with per-vertex alpha (e.colors) and small parts keep today's per-record pass.
// The table lives in the per-submit workspace (released by the draw call's guard): no static buffer.

struct ZamTable { const void* key; u32* argb; unsigned count; bool tried; };
ZamTable zam_tab{};
struct ZamStats { unsigned parts, normals, records, fallbacks; } zam_stats;
alignas(32) u16 zam_rec[(64 + 2) * 3];

inline void zam_begin_call() { zam_tab = ZamTable{}; }

bool zam_build(Part& e, const Lights& L, const Records& r) {
    Frame& f = e.f;
    const unsigned count = f.normal_count;
    if (!count || count > 8192U) return false;
    u32* const tab = static_cast<u32*>(scratch(count * 4U));
    u8* const raw = static_cast<u8*>(scratch((64U + 4U) * unsigned(sizeof(pvr_vertex_t)) + 32U));
    if (!tab || !raw) return false;
    pvr_vertex_t* const tmp = reinterpret_cast<pvr_vertex_t*>((reinterpret_cast<uintptr_t>(raw) + 31U) & ~uintptr_t(31));
    pvr_vertex_t* const keep = e.cache.v;
    e.cache.v = tmp;
    for (unsigned base = 0; base < count; base += 64U) {
        const unsigned m = count - base < 64U ? count - base : 64U;
        for (unsigned j = 0; j < m + 2U; ++j) {
            const unsigned ni = base + (j < m ? j : m - 1U);
            zam_rec[j * 3U] = 0; zam_rec[j * 3U + 1U] = u16(ni); zam_rec[j * 3U + 2U] = 0;
        }
        const Records c{zam_rec, 3U, r.color, false};
        pass_lights(e, L, c, m);
        for (unsigned j = 0; j < m; ++j) tab[base + j] = tmp[j].argb;
    }
    e.cache.v = keep;
    zam_tab.argb = tab; zam_tab.count = count;
    ++zam_stats.parts; zam_stats.normals += count;
    if ((zam_stats.parts & 4095U) == 0)
        re4dc_log("char zam: parts=%u normals=%u records=%u fallbacks=%u\n", zam_stats.parts, zam_stats.normals,
                  zam_stats.records, zam_stats.fallbacks);
    return true;
}

void zam_lights(Part& e, const Lights& L, const Records& r, unsigned n) {
    if (e.colors || !n) { pass_lights(e, L, r, n); return; }
    if (!zam_tab.tried) {
        zam_tab.tried = true;
        zam_tab.key = e.f.normals;
        if (!zam_build(e, L, r)) zam_tab.argb = nullptr;
    }
    if (!zam_tab.argb || zam_tab.key != e.f.normals) { ++zam_stats.fallbacks; pass_lights(e, L, r, n); return; }
    const u32* const tab = zam_tab.argb;
    const unsigned count = zam_tab.count;
    pvr_vertex_t* v = e.cache.v;
    for (unsigned i = 0; i < n; ++i) {
        const unsigned ni = r.ni(i);
        v[i].argb = ni < count ? tab[ni] : tab[0];
    }
    zam_stats.records += n;
}
