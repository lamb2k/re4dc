// VRAM_PAGES=1 (default off: this file then compiles to nothing and the image is unchanged).
// Replaces KOS's weak pvr_mem_* allocator (dlmalloc over texture RAM, pvr_mem.c) with an
// allocator whose bookkeeping lives in main RAM, so no block header sits in VRAM.
//
// Why: dlmalloc keeps a 4-byte header in front of each block and rounds blocks to 32 bytes,
// so after any earlier block the next address is 32 bytes past a 2 KiB page. UI_VRAM's
// texture_package allocate_texture() wants a VQ texture (codebook) on a 2 KiB page and a
// texture of at most one page inside one page; it therefore re-allocated every VQ texture
// with 2016 bytes of padding: +2048 bytes per resident texture (r100: ~78 textures, 161 KB
// between the cache's accounted bytes and the physical pool).
//
// Placement here: a request of at least one page starts on a page boundary; a smaller one
// never straddles a page (the same rule allocate_texture() checks, so its first allocation
// is always accepted). Best fit over the free extents (least leftover, then lowest address);
// frees coalesce with both neighbours. Everything outside texture RAM is untouched.
// Render only: game state never reads VRAM addresses.
#if RE4DC_VRAM_PAGES
#include <kos.h>
#include <dc/pvr.h>
#include <cstdint>
#include <cstring>
#include "re4dc_platform.h"

namespace {
constexpr std::uint32_t kGran = 32, kPage = 2048;
constexpr unsigned kMaxFree = 256, kMaxAlloc = 512;
struct Extent { std::uint32_t off, len; };      // offsets from base, both multiples of kGran
Extent free_list[kMaxFree]; unsigned nfree;     // sorted by offset, never adjacent
Extent alloc_list[kMaxAlloc]; unsigned nalloc;  // sorted by offset
std::uintptr_t base; std::uint32_t pool, free_bytes;
#if defined(RE4DC_VRAM_PAGES_VQ_ONLY) && RE4DC_VRAM_PAGES_VQ_ONLY
bool free_place;   // set only inside re4dc_vram_pages_malloc_any: this request needs no page
#endif
unsigned fails, peak_alloc, peak_free;
#if defined(RE4DC_VRAM_ROOM_ARENA) && RE4DC_VRAM_ROOM_ARENA
// VRAM_ROOM_ARENA (Makefile; lane mipmap22): two-ended placement. Class 2 (long-lived: core keys, glyph atlas, overlay
// slab) takes the highest place that fits, class 1 (room-lifetime textures) the lowest; class 0 (dynamic: movie, door,
// lake, probes) keeps best fit in between. native_ui.cpp sets re4dc_vram_arena_class around its allocations.
#if !defined(RE4DC_VRAM_ROOM_ARENA_NO_TOP) || !RE4DC_VRAM_ROOM_ARENA_NO_TOP
// Highest page-rule placement of `len` bytes in extent e, or ~0 if it does not fit.
std::uint32_t place_high(const Extent& e, std::uint32_t len) {
    if(len > e.len) return ~0U;
    std::uintptr_t at = base + e.off + e.len - len;
#if defined(RE4DC_VRAM_PAGES_VQ_ONLY) && RE4DC_VRAM_PAGES_VQ_ONLY
    if(free_place && len > kPage) {}
    else
#endif
    if(len >= kPage) at &= ~std::uintptr_t(kPage - 1);
    else if((at & (kPage - 1)) + len > kPage) at = ((at + len) & ~std::uintptr_t(kPage - 1)) - len;
    if(at < base + e.off) return ~0U;
    return std::uint32_t(at - base);
}
#endif
#endif
#if defined(RE4DC_TEX_CHECK) && RE4DC_TEX_CHECK == 2
// TEX_CHECK=2 (test only): free texture RAM reads magenta (RGB565 0xF81F), so a draw from never-written or
// freed VRAM is visible on Flycast (which zeroes VRAM; a console holds noise there).
void poison(std::uint32_t off, std::uint32_t len) {
    volatile std::uint32_t* p = reinterpret_cast<volatile std::uint32_t*>(base + off);
    for(std::uint32_t i = 0; i < len / 4; ++i) p[i] = 0xF81FF81FU;
}
#define RE4DC_VRAM_POISON(off, len) poison((off), (len))
#else
#define RE4DC_VRAM_POISON(off, len) ((void)0)
#endif

bool insert_at(Extent* list, unsigned& n, unsigned cap, unsigned at, Extent e) {
    if(n >= cap) return false;
    std::memmove(list + at + 1, list + at, (n - at) * sizeof(Extent));
    list[at] = e; ++n; return true;
}
void erase_at(Extent* list, unsigned& n, unsigned at) {
    std::memmove(list + at, list + at + 1, (n - at - 1) * sizeof(Extent)); --n;
}
unsigned lower_bound(const Extent* list, unsigned n, std::uint32_t off) {
    unsigned lo = 0, hi = n;
    while(lo < hi) { const unsigned mid = (lo + hi) / 2; if(list[mid].off < off) lo = mid + 1; else hi = mid; }
    return lo;
}
// Placement offset of `len` bytes in extent e, or ~0 if it does not fit.
std::uint32_t place(const Extent& e, std::uint32_t len) {
    const std::uintptr_t abs = base + e.off;
    std::uintptr_t at = abs;
#if defined(RE4DC_VRAM_PAGES_VQ_ONLY) && RE4DC_VRAM_PAGES_VQ_ONLY
    if(free_place && len > kPage) {}
    else
#endif
    if(len >= kPage) at = (abs + kPage - 1) & ~std::uintptr_t(kPage - 1);
    else if((abs & (kPage - 1)) + len > kPage) at = (abs + kPage - 1) & ~std::uintptr_t(kPage - 1);
    const std::uint32_t off = std::uint32_t(at - base);
    return off + len <= e.off + e.len ? off : ~0U;
}
}

extern "C" {
#if defined(RE4DC_VRAM_ROOM_ARENA) && RE4DC_VRAM_ROOM_ARENA
volatile unsigned re4dc_vram_arena_class;
#endif
#if defined(RE4DC_VRAM_PAGES_VQ_ONLY) && RE4DC_VRAM_PAGES_VQ_ONLY
// VRAM_PAGES_VQ_ONLY (Makefile): texture_package.cpp allocate_texture allocates a non-VQ texture of more than one
// page here; it may start anywhere (32-byte granularity). Every other request keeps the page rule. The flag is set
// and cleared with interrupts off, so no other thread's request can see it.
pvr_ptr_t pvr_mem_malloc(size_t size);
pvr_ptr_t re4dc_vram_pages_malloc_any(size_t size) {
    irq_disable_scoped();
    free_place = true;
    pvr_ptr_t p = pvr_mem_malloc(size);
    free_place = false;
    return p;
}
#endif
void pvr_mem_initialize(pvr_ptr_t texture_base, size_t available) {
    base = reinterpret_cast<std::uintptr_t>(texture_base);
    pool = std::uint32_t(available) & ~(kGran - 1);
    if(!base) pool = 0;
}
void pvr_mem_reset(void) {
    irq_disable_scoped();
    nalloc = 0; nfree = 0; free_bytes = 0;
    if(base && pool) { free_list[0] = {0, pool}; nfree = 1; free_bytes = pool; RE4DC_VRAM_POISON(0, pool); }
}
pvr_ptr_t pvr_mem_malloc(size_t size) {
    if(!base || !size || size > pool) { ++fails; return nullptr; }
    const std::uint32_t len = (std::uint32_t(size) + kGran - 1) & ~(kGran - 1);
    irq_disable_scoped();
    unsigned best = ~0U; std::uint32_t best_at = 0, best_left = ~0U;
#if defined(RE4DC_VRAM_ROOM_ARENA) && RE4DC_VRAM_ROOM_ARENA
    const unsigned cls = re4dc_vram_arena_class;
    if(cls == 1) {          // room: lowest address that fits
        for(unsigned i = 0; i < nfree && best == ~0U; ++i) {
            const std::uint32_t at = place(free_list[i], len);
            if(at != ~0U) { best = i; best_at = at; }
        }
#if !defined(RE4DC_VRAM_ROOM_ARENA_NO_TOP) || !RE4DC_VRAM_ROOM_ARENA_NO_TOP
    } else if(cls == 2) {   // long-lived: highest address that fits
        for(unsigned i = nfree; i-- > 0 && best == ~0U;) {
            const std::uint32_t at = place_high(free_list[i], len);
            if(at != ~0U) { best = i; best_at = at; }
        }
#endif
    } else
#endif
    for(unsigned i = 0; i < nfree; ++i) {
        Extent candidate = free_list[i];
#if defined(RE4DC_VRAM_ROOM_ARENA) && RE4DC_VRAM_ROOM_ARENA && \
    defined(RE4DC_VRAM_ROOM_ARENA_NO_TOP) && RE4DC_VRAM_ROOM_ARENA_NO_TOP
        // Console experiment: keep glyphs, the overlay slab and core keys below
        // a47f2000. Class 1 room placement/retirement and dynamic use are unchanged.
        // Clip only the candidate, never the real free list: other classes may
        // still use the final 56 KiB. Do not fall back into that range on failure.
        if(cls == 2) {
            constexpr std::uintptr_t kLongLivedEnd = 0xa47f2000U;
            const std::uintptr_t start = base + candidate.off;
            if(start >= kLongLivedEnd) continue;
            const std::uintptr_t available = kLongLivedEnd - start;
            if(candidate.len > available) candidate.len = std::uint32_t(available);
        }
#endif
        const std::uint32_t at = place(candidate, len);
        if(at == ~0U) continue;
        const std::uint32_t left = candidate.len - len;
        if(left < best_left) { best = i; best_at = at; best_left = left; if(!left) break; }
    }
    if(best == ~0U || nalloc >= kMaxAlloc) { ++fails; return nullptr; }
    const Extent e = free_list[best];
    const Extent front{e.off, best_at - e.off}, back{best_at + len, e.off + e.len - best_at - len};
    // Replace the extent by its non-empty remainders (at most one extra entry).
    if(front.len && back.len) {
        if(nfree >= kMaxFree) { ++fails; return nullptr; }
        free_list[best] = front; insert_at(free_list, nfree, kMaxFree, best + 1, back);
    }
    else if(front.len) free_list[best] = front;
    else if(back.len) free_list[best] = back;
    else erase_at(free_list, nfree, best);
    insert_at(alloc_list, nalloc, kMaxAlloc, lower_bound(alloc_list, nalloc, best_at), Extent{best_at, len});
    free_bytes -= len;
    if(nalloc > peak_alloc) peak_alloc = nalloc;
    if(nfree > peak_free) peak_free = nfree;
    return reinterpret_cast<pvr_ptr_t>(base + best_at);
}
void pvr_mem_free(pvr_ptr_t chunk) {
    if(!chunk || !base) return;
    const std::uint32_t off = std::uint32_t(reinterpret_cast<std::uintptr_t>(chunk) - base);
    irq_disable_scoped();
    const unsigned a = lower_bound(alloc_list, nalloc, off);
    if(a >= nalloc || alloc_list[a].off != off) {
        re4dc_log("vram pages: free of unknown block %08x\n", unsigned(reinterpret_cast<std::uintptr_t>(chunk)));
        return;
    }
    Extent e = alloc_list[a]; erase_at(alloc_list, nalloc, a);
    RE4DC_VRAM_POISON(e.off, e.len);
    free_bytes += e.len;
    unsigned i = lower_bound(free_list, nfree, e.off);
    if(i && free_list[i - 1].off + free_list[i - 1].len == e.off) { --i; free_list[i].len += e.len; }
    else if(!insert_at(free_list, nfree, kMaxFree, i, e)) {
        // Cannot happen: a free extent sits between two allocations, so nfree <= nalloc + 1.
        re4dc_log("vram pages: free list full, %u bytes lost\n", e.len); free_bytes -= e.len; return;
    }
    if(i + 1 < nfree && free_list[i].off + free_list[i].len == free_list[i + 1].off) {
        free_list[i].len += free_list[i + 1].len; erase_at(free_list, nfree, i + 1);
    }
}
size_t pvr_mem_available(void) { return base ? free_bytes : 0; }
void pvr_mem_print_list(void) {}
void pvr_mem_stats(void) {}

// MOVIE_WINDOW: the allocations (offset, length; sorted by offset), the pool size, and the absolute address
// of offset 0, for native_ui.cpp's targeted claim. Returns the count copied (at most cap).
unsigned re4dc_vram_pages_snapshot(unsigned* off, unsigned* len, unsigned cap, unsigned* base_out, unsigned* pool_out) {
    irq_disable_scoped();
    const unsigned n = nalloc < cap ? nalloc : cap;
    for(unsigned i = 0; i < n; ++i) { off[i] = alloc_list[i].off; len[i] = alloc_list[i].len; }
    *base_out = unsigned(base); *pool_out = pool;
    return n;
}

// VRAM_CENSUS: allocator view for native_ui.cpp.
void re4dc_vram_pages_census(unsigned* out) {
    // out: allocs, alloc_bytes, extents, free_bytes, largest, hist[5] (<2K, <8K, <32K, <128K, >=128K),
    //      fails, peak_alloc, peak_free
    irq_disable_scoped();
    std::uint32_t used = 0, largest = 0; unsigned hist[5] = {0, 0, 0, 0, 0};
    for(unsigned i = 0; i < nalloc; ++i) used += alloc_list[i].len;
    for(unsigned i = 0; i < nfree; ++i) {
        const std::uint32_t l = free_list[i].len;
        if(l > largest) largest = l;
        ++hist[l < 2048 ? 0 : l < 8192 ? 1 : l < 32768 ? 2 : l < 131072 ? 3 : 4];
    }
    out[0] = nalloc; out[1] = used; out[2] = nfree; out[3] = free_bytes; out[4] = largest;
    for(unsigned k = 0; k < 5; ++k) out[5 + k] = hist[k];
    out[10] = fails; out[11] = peak_alloc; out[12] = peak_free;
}
}
#endif
