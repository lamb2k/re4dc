#ifndef RE4DC_WATER_LAYER29_H
#define RE4DC_WATER_LAYER29_H

// EF13's bounded in-memory layer definition. A source owner supplies the
// readable row spans and its incarnation; the loader verifies every row
// pointer, count, alignment and byte extent against those spans before reading.
// The owner keeps its spans alive until publication returns. Water29Store then
// copies the rows, so no borrowed row pointer survives into the deferred draw.
#include <stdint.h>
#include <string.h>

enum Water29Result {
    WATER29_UNBOUND = 0,
    WATER29_NO_WATER = 1,
    WATER29_BOUND = 2,
    WATER29_REFUSED = 3
};
// Native re4dc_water_layer returns queue/immediate-admission status. An
// admitted deferred node can still fail later, so this is not a draw-complete
// result or a replacement for the native renderer's completion counters.
enum Water29Admission {
    WATER29_NOT_ATTEMPTED = 0,
    WATER29_ADMITTED = 1,
    WATER29_PARTIAL_REFUSAL = 2,
    WATER29_TOTAL_REFUSAL = 3
};
enum { WATER29_MAGIC = 0x5732394cU, WATER29_VERSION = 1, WATER29_MAX_ROWS = 32 };

struct Water29Definition {
    uint32_t magic, version, extent;
    uint32_t room, source_key, owner, incarnation;
    uint32_t result;
    uint32_t main_count, main_bytes, ext_count, ext_bytes, ext_index_base;
    const WaterPs2Row* main_rows;
#if defined(RE4DC_WATER_PS2_EXT) && RE4DC_WATER_PS2_EXT
    const WaterPs2ExtRow* ext_rows;
#else
    const void* ext_rows;
#endif
};
struct Water29SourceBytes {
    const void* begin;
    uint32_t bytes, owner, incarnation;
};
struct Water29View {
    Water29Result result;
    const WaterPs2Row* main_rows;
    unsigned main_count;
#if defined(RE4DC_WATER_PS2_EXT) && RE4DC_WATER_PS2_EXT
    const WaterPs2ExtRow* ext_rows;
#else
    const void* ext_rows;
#endif
    unsigned ext_count;
    unsigned ext_index_base;
    uint32_t room, source_key, owner, incarnation;
};
struct Water29Store {
    Water29Definition definition;
    WaterPs2Row main_rows[WATER29_MAX_ROWS];
#if defined(RE4DC_WATER_PS2_EXT) && RE4DC_WATER_PS2_EXT
    WaterPs2ExtRow ext_rows[WATER29_MAX_ROWS];
#endif
    int valid;
};

static inline int water29MainValid(const WaterPs2Row& r)
{
    const float f[] = {r.x, r.y, r.z, r.hx, r.hz, r.ry, r.ru, r.rv, r.su, r.sv};
    for (unsigned i = 0; i < sizeof(f) / sizeof(f[0]); ++i) {
        if (!__builtin_isfinite(f[i])) return 0;
    }
    return r.hx > 0.0f && r.hz > 0.0f;
}
#if defined(RE4DC_WATER_PS2_EXT) && RE4DC_WATER_PS2_EXT
static inline int water29ExtValid(const WaterPs2ExtRow& r)
{
    const float f[] = {r.p[0], r.p[1], r.p[2], r.ax[0], r.ax[1], r.ax[2],
                       r.az[0], r.az[1], r.az[2], r.hx, r.hz, r.ru, r.rv, r.su, r.sv};
    for (unsigned i = 0; i < sizeof(f) / sizeof(f[0]); ++i) {
        if (!__builtin_isfinite(f[i])) return 0;
    }
    return r.hx > 0.0f && r.hz > 0.0f;
}
#endif

static inline int water29Within(const void* ptr, uint32_t bytes, unsigned alignment,
                                const Water29SourceBytes* source, uint32_t owner, uint32_t incarnation)
{
    if (!ptr || !source || !source->begin || source->owner != owner ||
        source->incarnation != incarnation) return 0;
    const uintptr_t p = (uintptr_t) ptr, b = (uintptr_t) source->begin;
    if (p < b || p % alignment || p - b > source->bytes) return 0;
    return bytes <= source->bytes - (p - b);
}

// The caller supplies the expected room and exact source provenance, so a
// same-address replacement from a different room or source cannot qualify.
static inline Water29Result water29Load(const Water29Definition* d, unsigned available,
                                        const Water29SourceBytes* main_source,
                                        const Water29SourceBytes* ext_source,
                                        uint32_t room, uint32_t source_key, Water29View* out)
{
    memset(out, 0, sizeof(*out));
    out->result = WATER29_UNBOUND;
    if (!d) {
        return WATER29_UNBOUND;
    }
    out->result = WATER29_REFUSED;
    if (available < sizeof(*d) || (uintptr_t) d % alignof(Water29Definition) ||
        d->extent != sizeof(*d) || d->magic != WATER29_MAGIC ||
        d->version != WATER29_VERSION || d->room != room || d->source_key != source_key ||
        d->owner == 0 || d->incarnation == 0 || d->main_count > WATER29_MAX_ROWS ||
        d->ext_count > WATER29_MAX_ROWS || d->main_count + d->ext_count > WATER29_MAX_ROWS ||
        d->ext_index_base > 31 || d->ext_count > 32 - d->ext_index_base ||
        d->main_bytes != d->main_count * sizeof(WaterPs2Row)) {
        return WATER29_REFUSED;
    }
#if defined(RE4DC_WATER_PS2_EXT) && RE4DC_WATER_PS2_EXT
    if (d->ext_bytes != d->ext_count * sizeof(WaterPs2ExtRow)) {
        return WATER29_REFUSED;
    }
#else
    (void) ext_source;
    if (d->ext_count != 0 || d->ext_bytes != 0 || d->ext_rows != 0) {
        return WATER29_REFUSED;
    }
#endif
    if (d->result == WATER29_NO_WATER) {
        if (d->main_count || d->ext_count || d->main_rows || d->ext_rows) {
            return WATER29_REFUSED;
        }
    } else if (d->result == WATER29_BOUND) {
        if ((!d->main_count && !d->ext_count) || (d->main_count && !d->main_rows) ||
            (!d->main_count && d->main_rows) || (d->ext_count && !d->ext_rows) ||
            (!d->ext_count && d->ext_rows)) {
            return WATER29_REFUSED;
        }
        if (d->main_count && !water29Within(d->main_rows, d->main_bytes, alignof(WaterPs2Row),
                                             main_source, d->owner, d->incarnation)) {
            return WATER29_REFUSED;
        }
#if defined(RE4DC_WATER_PS2_EXT) && RE4DC_WATER_PS2_EXT
        if (d->ext_count && !water29Within(d->ext_rows, d->ext_bytes, alignof(WaterPs2ExtRow),
                                            ext_source, d->owner, d->incarnation)) {
            return WATER29_REFUSED;
        }
#endif
        for (unsigned i = 0; i < d->main_count; ++i) {
            if (d->main_rows[i].room != room || !water29MainValid(d->main_rows[i])) {
                return WATER29_REFUSED;
            }
        }
#if defined(RE4DC_WATER_PS2_EXT) && RE4DC_WATER_PS2_EXT
        for (unsigned i = 0; i < d->ext_count; ++i) {
            if (d->ext_rows[i].room != room || !water29ExtValid(d->ext_rows[i])) {
                return WATER29_REFUSED;
            }
        }
#endif
    } else {
        return WATER29_REFUSED;
    }
    out->result = (Water29Result) d->result;
    out->main_rows = d->main_rows;
    out->main_count = d->main_count;
    out->ext_rows = d->ext_rows;
    out->ext_count = d->ext_count;
    out->ext_index_base = d->ext_index_base;
    out->room = d->room;
    out->source_key = d->source_key;
    out->owner = d->owner;
    out->incarnation = d->incarnation;
    return out->result;
}

// Validate before changing the active binding. A malformed replacement leaves
// the previous qualified owner and the compiled-table fallback available.
static inline Water29Result water29Publish(Water29Store* dst, const Water29Definition* d,
                                           unsigned available, const Water29SourceBytes* main_source,
                                           const Water29SourceBytes* ext_source,
                                           uint32_t room, uint32_t source_key, Water29View* published_view)
{
    Water29View view;
    const Water29Result r = water29Load(d, available, main_source, ext_source, room, source_key, &view);
    if (r != WATER29_BOUND && r != WATER29_NO_WATER) {
        return r;
    }
    const Water29Definition header = *d;  // d may alias storage changed by the row moves
    if (view.main_count) {
        memmove(dst->main_rows, view.main_rows, view.main_count * sizeof(WaterPs2Row));
    }
#if defined(RE4DC_WATER_PS2_EXT) && RE4DC_WATER_PS2_EXT
    if (view.ext_count) {
        memmove(dst->ext_rows, view.ext_rows, view.ext_count * sizeof(WaterPs2ExtRow));
    }
#endif
    dst->definition = header;
    dst->definition.main_rows = view.main_count ? dst->main_rows : 0;
#if defined(RE4DC_WATER_PS2_EXT) && RE4DC_WATER_PS2_EXT
    dst->definition.ext_rows = view.ext_count ? dst->ext_rows : 0;
#else
    dst->definition.ext_rows = 0;
#endif
    dst->valid = 1;
    if (published_view) {
        *published_view = view;
        published_view->main_rows = view.main_count ? dst->main_rows : 0;
#if defined(RE4DC_WATER_PS2_EXT) && RE4DC_WATER_PS2_EXT
        published_view->ext_rows = view.ext_count ? dst->ext_rows : 0;
#else
        published_view->ext_rows = 0;
#endif
    }
    return r;
}

#endif
