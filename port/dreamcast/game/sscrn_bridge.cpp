// D367 W11: the sub screen's memory backing (SUBSCREEN=1) and the W11 test instrumentation
// (W11_FIXTURE=1). Game side; the KOS half is platform/subscreen_backing.cpp.
//
// The GameCube swaps 3 MiB at pG->pStFnt with ARAM 0xD00000 while the sub screen is open
// (sscrn.cpp SubScreenExec / SubScreenExitCore): the game's bytes there (heap 2's stage data,
// the room REL heap 3, the first ~2.8 MiB of the room heap 4) wait in ARAM, and the ARAM copy of
// the sub screen (Sscrn.rel, ss_cmmn.dat, ss_pzzl.dat, read once at game start) comes in. The
// Dreamcast has no ARAM, so:
//  - open: the live bytes of the area (every byte except the payload of free heap cells) go to
//    the VRAM backing store, then the area is cleared and filled the way the ARAM copy would
//    fill it: a 0x40-byte module descriptor in place of Sscrn.rel (the module is in the image),
//    ss_cmmn.dat and ss_pzzl.dat read from disc (every screen type uses both);
//  - close: the live bytes come back and are checked against the hash taken at open.
// The heap lists are not touched: the kept/skipped split is taken from the free lists at open
// and reused at close, when heap 4 has been signalled back unchanged.
#include "types.h"
#include "global.h"
#include "main_mem.h"
#include "sscrn.h"
#include "item.h"
#include "player.h"
#include "emhit.h"
#include "mes.h"
#include "card.h"
#if RE4DC_W11_FIXTURE
#include "sce.h"
#endif
#include "re4dc_platform.h"
#include <stdio.h>
#include <string.h>

extern "C" {
int OSCheckHeap(int heap);
void OSReport(const char* fmt, ...);
void re4dc_ui_invalidate_sources();
void re4dc_model_detach_retained_storage();
unsigned re4dc_vram_free();
void re4dc_kos_heap_state(unsigned* free_chunks, unsigned* used, unsigned* break_room);
int re4dc_fixture_read(const char* path, char* buffer, unsigned size);
int re4dc_ssb_open(unsigned bytes, unsigned* bank_bytes, unsigned* pool_bytes);
void re4dc_ssb_rewind();
void re4dc_ssb_put(const void* src, unsigned bytes);
void re4dc_ssb_get(void* dst, unsigned bytes);
void re4dc_ssb_close();
void re4dc_ssb_stats(unsigned* blocks, unsigned* reclaimed_uploads, unsigned* reclaimed_bytes);
unsigned re4dc_ssb_pool_free();
unsigned re4dc_ssb_bank_bytes();
unsigned long long re4dc_ssb_us();
long re4dc_ssb_file_size(const char* name);
long re4dc_ssb_file_read(const char* name, void* dst, unsigned capacity);
u32 re4dc_vi_retrace_count(void);
void re4dc_fixture_state(const char* name, int a, int b);
void re4dc_motion_hold(int on);
unsigned re4dc_motion_forget_dead_heaps();
unsigned re4dc_parts_freeze(u32 lo, u32 hi);  // parts_bridge.cpp
void re4dc_parts_thaw();
#if RE4DC_SUBSCREEN_OVL
long re4dc_ssb_overlay_read(void* dst, unsigned capacity);
void re4dc_ssb_code_sync(void* p, unsigned bytes);
void re4dc_module_overlay(u32 id, void (*prolog)(void), void (*epilog)(void), char* data, char* data_end, char* bss,
                          char* bss_end, char* pristine);  // platform/modules.cpp
#endif
#if RE4DC_SS_PACK
int re4dc_ssb_open_grow();
unsigned re4dc_ssb_cursor();
unsigned re4dc_ssb_pack_scratch_bytes();
unsigned re4dc_ssb_put_packed(const void* src, unsigned n, void* scratch);
int re4dc_ssb_get_packed(void* dst, unsigned n);
#endif
}

namespace {
constexpr u32 kSsAramSize = 0x300000;  // sscrn.cpp SS_ARAM_SIZE
constexpr u32 kDescriptorBytes = 0x40;  // OSModuleHeader up to the prolog/epilog words
constexpr u32 kSscrnModuleId = 71;      // config/G4BE08/modules/Sscrn/rel.json
constexpr u32 kCompactDescriptor = 0xDC000001;  // platform/modules.cpp compact header marker
inline u32 align32(u32 v) { return (v + 31) & ~31U; }

// The OSAlloc heap descriptors: SystemMemInit hands the aligned arena start to OSInitAlloc,
// which puts HeapDesc[MEM_HEAP_NUM] there (main_mem.cpp HeapHead).
const OSHeapDescriptor* heap_descriptor(int h)
{
    if (h < 0 || h >= MEM_HEAP_NUM || Heap[h].handle < 0) return 0;
    const OSHeapDescriptor* head = reinterpret_cast<const OSHeapDescriptor*>((u32(re4dc_mem.heap) + 0x1F) & ~0x1FU);
    return head + Heap[h].handle;
}

// Free bytes and largest free cell of a live heap (-1: none or suspended).
int heap_free(int h, u32* largest)
{
    *largest = 0;
    const OSHeapDescriptor* d = heap_descriptor(h);
    if (!d || Heap[h].status) return -1;
    int total = 0;
    unsigned guard = 0;
    for (const OSHeapCell* c = d->free; c && guard < 100000; c = c->next, ++guard) {
        total += c->size;
        if (u32(c->size) > *largest) *largest = u32(c->size);
    }
    return total;
}
}  // namespace

#if RE4DC_SS_PACK
// Free bytes and largest free cell of the current heap (route movie heap lines, platform/native_movie.cpp).
extern "C" unsigned re4dc_heap_largest_current(unsigned* free_bytes)
{
    u32 largest;
    const int total = heap_free(MemGetCurrentHeap(), &largest);
    *free_bytes = total < 0 ? 0 : unsigned(total);
    return largest;
}
#endif

#if RE4DC_W11_FIXTURE
// Image code integrity (W11 test builds): 64 KiB chunk hashes of [_start, _etext), logged when
// a chunk differs from the first check (the image is never written after boot).
extern "C" char start[] asm("_start");
extern "C" char etext[] asm("_etext");
namespace {
constexpr unsigned kTextChunk = 0x10000, kTextChunks = 64;
u32 text_hash[kTextChunks];
bool text_have;
}
void w11_text_check(const char* when)
{
    const u32 lo = u32(start), hi = u32(etext) & ~3U;
    unsigned bad = 0;
    for (unsigned c = 0; c < kTextChunks && lo + c * kTextChunk < hi; ++c) {
        const u32 a = lo + c * kTextChunk, b = a + kTextChunk < hi ? a + kTextChunk : hi;
        u32 h = 2166136261U;
        for (const u32* w = reinterpret_cast<const u32*>(a); u32(w) < b; ++w) h = (h ^ *w) * 16777619U;
        if (!text_have) text_hash[c] = h;
        else if (h != text_hash[c]) {
            ++bad;
            if (c == 33) {  // the image's writable tail inside [_start, _etext): changes every frame
                text_hash[c] = h;
                --bad;
                continue;
            }
            re4dc_log("w11 text: %s chunk %u [%08x,%08x) changed %08x -> %08x\n", when, c, a, b, text_hash[c], h);
            // First nonzero run of words that look like heap cell headers in the chunk: none known;
            // print the first 8 words at every 0x20 step whose second word is 0 and third is small.
            for (u32 q = a; q + 32 <= b; q += 0x20) {
                const u32* w = reinterpret_cast<const u32*>(q);
                if (w[0] == 0 && w[1] == 0 && w[2] && w[2] < 0x100000 && !(w[2] & 0x1F)) {
                    re4dc_log("w11 text:   cell-like @%08x: %08x %08x %08x %08x %08x %08x %08x %08x\n", q, w[0], w[1],
                              w[2], w[3], w[4], w[5], w[6], w[7]);
                    break;
                }
            }
            text_hash[c] = h;
        }
    }
    if (!text_have) re4dc_log("w11 text: baseline %s [%08x,%08x)\n", when, lo, hi);
    (void) bad;
    text_have = true;
}
#else
static inline void w11_text_check(const char*) {}
#endif

// ------------------------------------------------------------------------------------ backing
#if RE4DC_SUBSCREEN
namespace {
struct Span { u32 start, bytes; };
constexpr unsigned kMaxSpans = 1024;
Span spans[kMaxSpans];
unsigned nspan;
u32 live_bytes, skipped_bytes, open_hash, cmmn_bytes, pzzl_bytes;
bool swapped;
#if RE4DC_SS_PACK
bool packed;  // the open stored the area packed (SS_PACK)
u32 packed_bytes;
#endif
u32 area_lo, area_hi;  // the window while swapped

// Message state that the sub screen points into its own area data (MesData tables: ss_term's
// op messages in slot 2, ss_file/ss_pzzl/ss_shop's ss_cmmn text in slot 0; cMes slots showing
// them). SubScreenExit re-binds only slots 0/1 (cMes.roomInit) and only several frames after
// the area holds the game's bytes again, so a pointer left into the restored area makes the
// message system walk game data as text (Message::WidthCk "no end code", then runaway pMes).
// The ARAM swap leaves the same pointers on the GameCube; there the stale bytes are never
// read before roomInit. Close puts back what the game had at open instead.
constexpr int kMesTypes = sizeof(MesData.ptr) / sizeof(MesData.ptr[0]);
constexpr int kMesSlots = sizeof(cMes.mes) / sizeof(cMes.mes[0]);
u8* mes_ptr_open[kMesTypes];
u32 mes_active_open;

bool in_area(const void* p, u32 lo, u32 hi) { return u32(p) >= lo && u32(p) < hi; }

void save_message_state()
{
    for (int t = 0; t < kMesTypes; ++t) mes_ptr_open[t] = MesData.ptr[t];
    mes_active_open = 0;
    for (int i = 0; i < kMesSlots; ++i)
        if (cMes.mes[i].flags2 & 1) mes_active_open |= 1U << i;
}

void restore_message_state(u32 lo, u32 hi)
{
    for (int t = 0; t < kMesTypes; ++t) {
        if (MesData.ptr[t] != mes_ptr_open[t] && in_area(MesData.ptr[t], lo, hi)) {
            re4dc_log("subscreen backing: message table %d %p -> %p (set inside the area while open)\n", t,
                      MesData.ptr[t], mes_ptr_open[t]);
            MesData.ptr[t] = mes_ptr_open[t];
        }
    }
    // Every live slot whose text cursor is in the area (sub screen text, now game bytes) or not in
    // main RAM at all (a NULL table + offset) is deleted, whatever it showed before the open: the
    // area held sub screen data while open, so no slot can have kept a valid cursor there.
    for (int i = 0; i < kMesSlots; ++i) {
        Message& m = cMes.mes[i];
        if (!((m.flags2 | m.be_flag) & 1)) continue;
        const bool stale = in_area(m.m_pMes, lo, hi) || u32(m.m_pMes) < 0x8C000000U || u32(m.m_pMes) >= 0x8D000000U;
        re4dc_log("subscreen backing: message slot %d be=%x flags2=%x pMes %p%s%s\n", i, unsigned(m.be_flag),
                  unsigned(m.flags2), m.m_pMes, (mes_active_open & (1U << i)) ? " (live at open)" : "",
                  stale ? " stale, deleted" : "");
        if (stale) cMes.Delete(i);
    }
}

u32 hash_words(const void* p, u32 bytes, u32 h)
{
    const u32* w = static_cast<const u32*>(p);
    for (u32 n = bytes / 4; n; --n) h = (h ^ *w++) * 16777619U;
    return h;
}

// The live spans of [lo, hi): the area minus the payload of every free cell of every live heap
// (a free cell keeps its 0x20-byte header, which the heap lists need).
void build_spans(u32 lo, u32 hi)
{
    struct Hole { u32 a, b; };
    static Hole holes[kMaxSpans];
    unsigned nhole = 0;
    for (int h = 0; h < MEM_HEAP_NUM; ++h) {
        const OSHeapDescriptor* d = heap_descriptor(h);
        if (!d || Heap[h].status) continue;
        unsigned guard = 0;
        for (const OSHeapCell* c = d->free; c && guard < 100000; c = c->next, ++guard) {
            u32 a = u32(c) + 0x20, b = u32(c) + u32(c->size);
            if (b <= lo || a >= hi || b <= a) continue;
            if (a < lo) a = lo;
            if (b > hi) b = hi;
            if (nhole < kMaxSpans) holes[nhole++] = {a, b};
        }
    }
    for (unsigned i = 1; i < nhole; ++i) {  // insertion sort by address (a few hundred at most)
        Hole x = holes[i];
        unsigned j = i;
        for (; j && holes[j - 1].a > x.a; --j) holes[j] = holes[j - 1];
        holes[j] = x;
    }
    nspan = 0;
    live_bytes = skipped_bytes = 0;
    u32 at = lo;
    for (unsigned i = 0; i <= nhole; ++i) {
        const u32 end = i < nhole ? holes[i].a : hi;
        if (end > at) {
            if (nspan == kMaxSpans) {  // cannot describe more: keep the rest whole
                spans[nspan - 1].bytes = hi - spans[nspan - 1].start;
                live_bytes += hi - at;
                return;
            }
            spans[nspan++] = {at, end - at};
            live_bytes += end - at;
        }
        if (i < nhole) {
            if (holes[i].b > at) {
                const u32 a = holes[i].a > at ? holes[i].a : at;
                skipped_bytes += holes[i].b - a;
                at = holes[i].b;
            }
        }
    }
}

#if RE4DC_SS_CERT
// SS_CERT (actor_swap_park.inc): every byte of [p, p+n) inside the window lies in a span the open saved, none in a
// skipped free cell (those payloads are not put back at close). Spans are ascending and disjoint.
int span_saved(const void* p, unsigned n)
{
    u32 a = u32(p), b = a + n;
    if (b < a) return 0;
    if (a < area_lo) a = area_lo;
    if (b > area_hi) b = area_hi;
    for (unsigned i = 0; i < nspan && a < b; ++i) {
        const u32 s = spans[i].start, e = s + spans[i].bytes;
        if (e <= a) continue;
        if (s > a) return 0;
        a = e;
    }
    return a >= b;
}
#endif
}  // namespace

#if RE4DC_SUBSCREEN_OVL
// SUBSCREEN_OVL=1: the Sscrn module is not in the image. /cd/dc/sscrn.ovl (tools/gen_overlay.py)
// is a 64-byte header, the module bytes as linked at `base`, and the offsets of the words to
// relocate. Each open reads it to the start of the area, where the GameCube's Sscrn.rel sat: the
// header lands on the descriptor slot and the module right after it, at kDescriptorBytes.
namespace {
struct OverlayHeader {
    u32 magic, version, image_bytes, relocs, base;
    u32 prolog, epilog, data, data_end, bss, bss_end, pristine;  // offsets from base
    u32 image_hash, reloc_hash, pad[2];
};
static_assert(sizeof(OverlayHeader) == kDescriptorBytes, "overlay header fills the descriptor slot");
constexpr u32 kOverlayMagic = 0x4F344552;  // "RE4O"
u32 ovl_image_bytes, ovl_file_bytes;
}

// Game start: the overlay's size, for the area layout.
static void overlay_size()
{
    OverlayHeader h;
    if (re4dc_ssb_overlay_read(&h, sizeof(h)) != long(sizeof(h)) || h.magic != kOverlayMagic || h.version != 1)
        re4dc_missing("sub screen overlay /cd/dc/sscrn.ovl missing or not version 1");
    ovl_image_bytes = h.image_bytes;
    ovl_file_bytes = u32(sizeof(h)) + h.image_bytes + h.relocs * 4;
}

// swap_open, on the cleared area: read, check, relocate; bind the module table entry to it.
static void overlay_load(u32 lo, u32 limit, unsigned* reloc_us)
{
    if (ovl_file_bytes > limit) re4dc_missing("sub screen overlay larger than its area slot");
    if (re4dc_ssb_overlay_read(reinterpret_cast<void*>(lo), ovl_file_bytes) != long(ovl_file_bytes))
        re4dc_missing("sub screen overlay read failed");
    const unsigned long long t0 = re4dc_ssb_us();
    const OverlayHeader h = *reinterpret_cast<const OverlayHeader*>(lo);
    u8* image = reinterpret_cast<u8*>(lo + kDescriptorBytes);
    u32* reloc = reinterpret_cast<u32*>(image + h.image_bytes);
    if (h.magic != kOverlayMagic || h.image_bytes != ovl_image_bytes ||
        hash_words(image, h.image_bytes, 2166136261U) != h.image_hash ||
        hash_words(reloc, h.relocs * 4, 2166136261U) != h.reloc_hash)
        re4dc_missing("sub screen overlay corrupt (hash)");
    const u32 delta = u32(image) - h.base;
    for (u32 i = 0; i < h.relocs; ++i) {
        const u32 at = reloc[i];
        if (at + 4 > h.image_bytes || (at & 3)) re4dc_missing("sub screen overlay relocation out of range");
        *reinterpret_cast<u32*>(image + at) += delta;
    }
    memset(reloc, 0, h.relocs * 4);  // the area is clear past the module, as before
    re4dc_ssb_code_sync(image, h.image_bytes);
    re4dc_module_overlay(kSscrnModuleId, reinterpret_cast<void (*)(void)>(image + h.prolog),
                         reinterpret_cast<void (*)(void)>(image + h.epilog), reinterpret_cast<char*>(image + h.data),
                         reinterpret_cast<char*>(image + h.data_end), reinterpret_cast<char*>(image + h.bss),
                         reinterpret_cast<char*>(image + h.bss_end), reinterpret_cast<char*>(image + h.pristine));
    *reloc_us = unsigned(re4dc_ssb_us() - t0);
}
#endif

#if RE4DC_SS_UI_ORDER
// Same owner that fences/saves/restores the area. The model/UI compositor borrows
// its current frame state only; no second subscreen lifetime or state cache.
extern "C" int re4dc_ss_ui_order() { return swapped ? 1 : 0; }
#endif

// SubScreenAramRead replacement (game start): the area layout, from the disc file sizes.
extern "C" void re4dc_subscreen_aram_init(SubScreenWork* wk)
{
    wk->p_module = 0;
    wk->pPreplfOffs = 0;
    wk->aramSize = kDescriptorBytes;
#if RE4DC_SUBSCREEN_OVL
    overlay_size();
    wk->aramSize += align32(ovl_image_bytes);
    OSReport("Native subscreen area: Sscrn overlay %u B (%u B file) @%x\n", ovl_image_bytes, ovl_file_bytes,
             kDescriptorBytes);
#endif
    sscrnDataFilename(wk, "ss_cmmn.dat");
    long size = re4dc_ssb_file_size(wk->path);
    cmmn_bytes = size > 0 ? u32(size) : 0;
    wk->pCommonOffs = wk->aramSize;
    wk->aramSize += align32(cmmn_bytes);
    sscrnDataFilename(wk, "ss_pzzl.dat");
    size = re4dc_ssb_file_size(wk->path);
    pzzl_bytes = size > 0 ? u32(size) : 0;
    wk->pzzlOfs = wk->aramSize;
    wk->aramSize += align32(pzzl_bytes);
    OSReport("Native subscreen area: descriptor 0x%x + ss_cmmn %u @%x + ss_pzzl %u @%x (read at open, no ARAM)\n",
             kDescriptorBytes, cmmn_bytes, wk->pCommonOffs, pzzl_bytes, wk->pzzlOfs);
    OSReport("SubScrn Data: 0x%08x\n", wk->aramSize);
    OSReport("SubScrn Free: 0x%08x\n", kSsAramSize - wk->aramSize);
    if (!cmmn_bytes || !pzzl_bytes) re4dc_missing("sub screen files (ss_cmmn.dat / ss_pzzl.dat) not on disc");
}


#if RE4DC_SS_POOL_HIGH
#include "light.h"
// Room effect pools above the sub screen window (subscreen.mk SS_POOL_HIGH): a first-fit
// allocation that lands in [pStFnt, +3 MiB) is held while the next fit is tried, then every
// held cell is released, so the pool gets the lowest fitting cell above the window. Falls back
// to the plain allocation when nothing fits above it.
// C++ linkage and no header declaration: the callers declare it inside their own knob blocks (a
// declaration in main_mem.h alone changed the code GCC emitted for cModel::matBlend).
void* re4dc_ss_alloc_above(u32 size, const char* file, int line)
{
    const u32 lo = u32(pG->pStFnt), hi = lo + kSsAramSize;
    void* held[256];
    unsigned n = 0;
    void* p = nullptr;
    for (;;) {
        p = mem_alloc(size, file, line, 0, 0xD);
        if (!p || !lo || u32(p) >= hi || u32(p) + size <= lo || n == 256) break;
        held[n++] = p;
    }
    for (unsigned i = 0; i < n; ++i) Mem_free(held[i]);
    if (!p || (lo && u32(p) < hi && u32(p) + size > lo)) {
        if (p) Mem_free(p);
        p = mem_alloc(size, file, line, 1, 0xD);
        re4dc_log("sub screen: pool %s(%d) %u B not above the window (%08x-%08x): %p held=%u\n", file, line,
                  unsigned(size), lo, hi, p, n);
    }
    return p;
}

// game.cpp gameRoomInit, right after LightMgr.arrayAlloc: the light works move above the window
// too (the sub screen loop runs LightMgr.move(), whose virtual calls went through the sub screen's
// bytes when the array sat inside it). No light exists yet: the new array is only cleared.
void re4dc_ss_light_array_high()
{
    const u32 lo = u32(pG->pStFnt), hi = lo + kSsAramSize;
    const u32 a = u32(LightMgr.pArray), bytes = LightMgr.size * LightMgr.nArray;
    if (!lo || !a || !bytes || a >= hi || a + bytes <= lo) return;
    void* p = re4dc_ss_alloc_above(bytes, "light.h", 285);
    if (!p) return;
    if (u32(p) < hi && u32(p) + bytes > lo) {
        Mem_free(p);
        return;
    }
    LightMgr.memClear(static_cast<cLight*>(p), bytes);
    LightMgr.memFree(LightMgr.pArray);
    LightMgr.pArray = static_cast<cLight*>(p);
}
#endif

#if defined(RE4DC_LOGIC_TRACE_SWAPPED) && RE4DC_LOGIC_TRACE_SWAPPED
extern "C" void re4dc_logic_trace_swap_open(void*,unsigned,unsigned);
extern "C" void re4dc_logic_trace_swap_close();
#endif
#if RE4DC_SS_CERT
extern "C" void re4dc_actor_swap_park(const void*, unsigned, int (*)(const void*, unsigned));
extern "C" void re4dc_actor_swap_unpark(int);
#endif
extern "C" void re4dc_subscreen_swap_open(SubScreenWork* wk)
{
    if (swapped) re4dc_missing("sub screen area swapped twice");
    const unsigned long long t0 = re4dc_ssb_us();
    const u32 lo = u32(wk->pBuf), hi = lo + kSsAramSize;
    // The room cache may lie in this window. Drop the renderer's borrow before
    // packing/reusing it; heap 4 keeps ownership and its bytes are restored at
    // close. Inventory draws on heap 12 cannot reacquire the room cache.
    re4dc_model_detach_retained_storage();
    build_spans(lo, hi);
    unsigned bank = 0, pool = 0;
    const unsigned pool_before = re4dc_ssb_pool_free();
    u32 h = 2166136261U;
#if RE4DC_SS_PACK
    // SS_PACK=1: the live bytes go LZ4-packed into bank 1, with pool blocks only for what does not fit
    // (platform/subscreen_backing.cpp). The encoder's table and staging use the first bytes of the
    // area, which go raw first and are put back right after, before anything else reads the area.
    const u32 scratch = re4dc_ssb_pack_scratch_bytes();
    packed = nspan && spans[0].start == lo && spans[0].bytes >= scratch + 64;
    if (packed) {
        for (unsigned i = 0; i < nspan; ++i) h = hash_words(reinterpret_cast<const void*>(spans[i].start), spans[i].bytes, h);
        if (!re4dc_ssb_open_grow()) re4dc_missing("sub screen backing: open failed");
        re4dc_ssb_rewind();
        re4dc_ssb_put(reinterpret_cast<const void*>(lo), scratch);
        for (unsigned i = 0; i < nspan; ++i) {
            const u32 a = i ? spans[i].start : lo + scratch, b = spans[i].start + spans[i].bytes;
            re4dc_ssb_put_packed(reinterpret_cast<const void*>(a), b - a, reinterpret_cast<void*>(lo));
        }
        packed_bytes = re4dc_ssb_cursor();
        re4dc_ssb_rewind();
        re4dc_ssb_get(reinterpret_cast<void*>(lo), scratch);
        bank = re4dc_ssb_bank_bytes();
        pool = packed_bytes > bank ? packed_bytes - bank : 0;
    } else
#endif
    {
        if (!re4dc_ssb_open(live_bytes, &bank, &pool)) {
            re4dc_log("subscreen backing: live=%u bank=%u pool_free=%u\n", live_bytes, re4dc_ssb_bank_bytes(), pool_before);
            re4dc_missing("sub screen backing: no VRAM for the swapped area");
        }
        re4dc_ssb_rewind();
        for (unsigned i = 0; i < nspan; ++i) {
            re4dc_ssb_put(reinterpret_cast<const void*>(spans[i].start), spans[i].bytes);
            h = hash_words(reinterpret_cast<const void*>(spans[i].start), spans[i].bytes, h);
        }
    }
    open_hash = h;
#if defined(RE4DC_LOGIC_TRACE_SWAPPED) && RE4DC_LOGIC_TRACE_SWAPPED
    // SS_PACK has restored its temporary scratch bytes. The source region is still intact here.
    re4dc_logic_trace_swap_open(wk->pBuf,kSsAramSize,packed?packed_bytes:live_bytes);
#endif
    swapped = true;
    area_lo = lo;
    area_hi = hi;
#if RE4DC_SS_CERT
    // The room's bytes are saved and still intact: its certificates leave the live tables until close.
    re4dc_actor_swap_park(reinterpret_cast<const void*>(lo), kSsAramSize, span_saved);
#endif
    save_message_state();
    re4dc_motion_hold(1);
    // Room demand pools (the cEm one, for one) whose slot tables live in the window.
    const unsigned frozen_pools = re4dc_parts_freeze(lo, hi);
    w11_text_check("after-open");
    const unsigned long long t1 = re4dc_ssb_us();
    // What the ARAM copy would bring in.
    memset(wk->pBuf, 0, kSsAramSize);
#if RE4DC_SUBSCREEN_OVL
    const unsigned long long to0 = re4dc_ssb_us();
    unsigned reloc_us = 0;
    overlay_load(lo, kSsAramSize, &reloc_us);
    re4dc_log("subscreen backing: overlay %u B at %08x read_us=%u reloc_us=%u\n", ovl_image_bytes,
              lo + kDescriptorBytes, unsigned(re4dc_ssb_us() - to0) - reloc_us, reloc_us);
    for (u32 i = 0; i < kDescriptorBytes / 4; ++i) reinterpret_cast<u32*>(lo)[i] = 0;
#endif
    u32* d = reinterpret_cast<u32*>(lo + wk->pPreplfOffs);
    d[0] = kSscrnModuleId;
    d[0x1c / 4] = kCompactDescriptor;
    sscrnDataFilename(wk, "ss_cmmn.dat");
    const long cmmn = re4dc_ssb_file_read(wk->path, reinterpret_cast<void*>(lo + wk->pCommonOffs), cmmn_bytes);
    // ss_pzzl.dat for every type: besides the puzzles it holds the item BIN / TPL pairs that the
    // inventory, examine and shop screens draw (read fresh each open: the pristine copy that
    // SubScreenExit re-read into ARAM after a puzzle).
    sscrnDataFilename(wk, "ss_pzzl.dat");
    const long pzzl = re4dc_ssb_file_read(wk->path, reinterpret_cast<void*>(lo + wk->pzzlOfs), pzzl_bytes);
    if (cmmn != long(cmmn_bytes) || pzzl != long(pzzl_bytes)) re4dc_missing("sub screen file read failed");
    // Source-image pointer keys cached by the native UI named the game's bytes at these addresses.
    re4dc_ui_invalidate_sources();
    const unsigned long long t2 = re4dc_ssb_us();
    unsigned blocks = 0, reclaimed = 0, reclaimed_bytes = 0;
    re4dc_ssb_stats(&blocks, &reclaimed, &reclaimed_bytes);
    re4dc_log("subscreen backing: open type=%x area=%08x+%x live=%u skipped_free=%u spans=%u bank=%u pool=%u "
              "blocks=%u ui_released=%u/%uB pool_free=%u->%u save_us=%u read_us=%u cmmn=%ld pzzl=%ld frozen_pools=%u "
              "hash=%08x\n",
              unsigned(wk->type), lo, kSsAramSize, live_bytes, skipped_bytes, nspan, bank, pool, blocks, reclaimed,
              reclaimed_bytes, pool_before, re4dc_ssb_pool_free(), unsigned(t1 - t0), unsigned(t2 - t1), cmmn, pzzl,
              frozen_pools, open_hash);
#if RE4DC_SS_PACK
    if (packed)
        re4dc_log("subscreen backing: packed %u -> %u B (bank %u, pool %u B)\n", live_bytes, packed_bytes, bank, pool);
#endif
}

extern "C" void re4dc_subscreen_swap_close(SubScreenWork* wk)
{
    w11_text_check("before-close");
    if (!swapped) re4dc_missing("sub screen area restored without a swap");
    const unsigned long long t0 = re4dc_ssb_us();
    re4dc_ssb_rewind();
    u32 h = 2166136261U;
#if RE4DC_SS_PACK
    if (packed) {
        const u32 lo = u32(wk->pBuf), scratch = re4dc_ssb_pack_scratch_bytes();
        re4dc_ssb_get(reinterpret_cast<void*>(lo), scratch);
        for (unsigned i = 0; i < nspan; ++i) {
            const u32 a = i ? spans[i].start : lo + scratch, b = spans[i].start + spans[i].bytes;
            if (!re4dc_ssb_get_packed(reinterpret_cast<void*>(a), b - a))
                re4dc_missing("sub screen backing: a packed span did not decode");
        }
        for (unsigned i = 0; i < nspan; ++i) h = hash_words(reinterpret_cast<const void*>(spans[i].start), spans[i].bytes, h);
        packed = false;
    } else
#endif
    for (unsigned i = 0; i < nspan; ++i) {
        re4dc_ssb_get(reinterpret_cast<void*>(spans[i].start), spans[i].bytes);
        h = hash_words(reinterpret_cast<const void*>(spans[i].start), spans[i].bytes, h);
    }
#if defined(RE4DC_LOGIC_TRACE_SWAPPED) && RE4DC_LOGIC_TRACE_SWAPPED
    re4dc_logic_trace_swap_close();
#endif
    re4dc_ssb_close();
    swapped = false;
    re4dc_parts_thaw();
    restore_message_state(u32(wk->pBuf), u32(wk->pBuf) + kSsAramSize);
    // Motion clips the screen loaded came from heap 12 (gone now); room tables are back as at open.
    const unsigned motions = re4dc_motion_forget_dead_heaps();
    if (motions) re4dc_log("subscreen backing: %u motion residency slots from the sub screen heap dropped\n", motions);
    re4dc_ui_invalidate_sources();
#if RE4DC_SS_CERT
    // Heap 12 is destroyed (SubScreenExitCore) and the room's bytes are back: parked certificates whose bytes hash
    // as at open are published again; a failed restore publishes none.
    re4dc_actor_swap_unpark(h == open_hash);
#endif
    const unsigned long long t1 = re4dc_ssb_us();
    re4dc_log("subscreen backing: close area=%08x restored=%u restore_us=%u hash=%08x %s pool_free=%u\n", u32(wk->pBuf),
              live_bytes, unsigned(t1 - t0), h, h == open_hash ? "ok" : "MISMATCH", re4dc_ssb_pool_free());
    if (h != open_hash) re4dc_missing("sub screen backing corrupted while the screen was open");
}

#if RE4DC_CRASH_SCREEN
// Read only, called after a stop. The overlay moves with pStFnt, so its exact
// runtime base is required to symbolize an inventory PC/PR from a photograph.
extern "C" void re4dc_subscreen_brief(char* out, unsigned size)
{
    if (!size) return;
    out[0] = 0;
    if (!swapped) return;
#if RE4DC_SUBSCREEN_OVL
    snprintf(out, size, "ss area %08x overlay %08x+%x", area_lo, area_lo + kDescriptorBytes, ovl_image_bytes);
#else
    snprintf(out, size, "ss area %08x+%x", area_lo, kSsAramSize);
#endif
}
#endif
#endif  // RE4DC_SUBSCREEN

// ------------------------------------------------------------------------------ W11 fixture
#if RE4DC_W11_FIXTURE
namespace {
// Item id of file `no` (ss_file.cpp fileNo2Id; that one lives in the sub screen module).
u16 file_item_id(unsigned no)
{
    return u16(no <= 0xC ? no + 0xAB : no <= 0x15 ? no + 0x3B : no <= 0x1F ? no + 0xDE : 0xAC);
}

struct Fixture {
    bool loaded;
    unsigned die_after, die_count, dies;    // "die <frames> <count> [room]"
    unsigned die_room;                      // hex room id (0: any room), e.g. 101
    int life_value;                         // "life <value> <frames>" (once, first room)
    unsigned life_after;
    bool life_done;
    unsigned generation, room_frames, rooms;
    unsigned death_frame;                   // retrace count at the kill (0: alive)
    bool continue_pending;
    unsigned done_events;                   // "done <events>": "w11 done" 300 game frames after
    bool done_logged;
    unsigned save_after, save_count, saves; // "save <frames> <count> [room] [slot]": the typewriter's
    unsigned save_room, save_slot;          // CardSave(slot, 1) (sce_at.cpp type 8), every `frames`
                                            // room frames (card screen frames do not count)
    // "mes <frames> <no> <kind> [room] [item] [num]" (hex no/room/item; up to 4 lines, in order):
    // once `frames` room frames in, with no event, sub screen or message up, show message `no`
    // as its game callers do. kind 0: a room message (r100_MesTruck: SceMesSet(no, 0, 1, ...),
    // here without its wait); kind 1: the item pick-up prompt (sce_at.cpp item type 2:
    // MesSet(no, 0x64, y, 0x211), m_item_no = item, number = num). State w11m=<i>/1 while
    // shown (padscript gate for the button that closes it); shots mes<i>-30/90/180.
    struct Mes { unsigned frames, no, kind, room, item, num, at; bool fired; } mes[4];
    unsigned nmes;
    // "file <frames> <no> [room]" (decimal file number 1..31, hex room; up to 4 lines, in order): once
    // `frames` room frames in, with no event, sub screen or message up, open file `no` in the file
    // reader as picking it up does (sce_at.cpp item type 0xA: SubScreenOpen(SS_OPEN_FILE, 0),
    // get_item_id = its item id; the reader adds it to the owned files). State w11f=<i>/1 once open.
    struct File { unsigned frames, no, room; bool fired; } file[4];
    unsigned nfile;
};
Fixture fx{};

void load_fixture()
{
    fx.loaded = true;
    fx.life_value = -1;
    static char text[512];
    const int n = re4dc_fixture_read("/cd/dc/w11.txt", text, sizeof(text) - 1);
    if (n <= 0) return;
    text[n] = 0;
    for (char* line = text; line && *line;) {
        char* next = strchr(line, '\n');
        if (next) *next++ = 0;
        unsigned a = 0, b = 0, r = 0, v2 = 0;
        int v = 0;
        if (sscanf(line, "die %u %u %x", &a, &b, &r) >= 2) {
            fx.die_after = a;
            fx.die_count = b;
            fx.die_room = r;
        } else if (sscanf(line, "life %d %u", &v, &b) == 2) {
            fx.life_value = v;
            fx.life_after = b;
        } else if (sscanf(line, "save %u %u %x %u", &a, &b, &r, &v2) >= 2) {
            fx.save_after = a;
            fx.save_count = b;
            fx.save_room = r;
            fx.save_slot = v2;
        } else if (fx.nmes < 4 && sscanf(line, "mes %u %x %u %x %x %u", &a, &b, &r, &v2, &fx.mes[fx.nmes].item,
                                         &fx.mes[fx.nmes].num) >= 3) {
            Fixture::Mes& m = fx.mes[fx.nmes++];
            m.frames = a;
            m.no = b;
            m.kind = r;
            m.room = v2;
            re4dc_log("w11 fixture: mes %u at room frame %u no=%x kind=%u room=%03x item=%x num=%u\n", fx.nmes, m.frames,
                      m.no, m.kind, m.room, m.item, m.num);
        } else if (fx.nfile < 4 && sscanf(line, "file %u %u %x", &a, &b, &r) >= 2) {
            Fixture::File& f = fx.file[fx.nfile++];
            f.frames = a;
            f.no = b;
            f.room = r;
            re4dc_log("w11 fixture: file %u at room frame %u no=%u room=%03x\n", fx.nfile, f.frames, f.no, f.room);
        } else if (sscanf(line, "done %u", &a) == 1) {
            fx.done_events = a;
        }
        line = next;
    }
    re4dc_log("w11 fixture: die after=%u count=%u room=%03x life=%d after=%u done=%u save after=%u count=%u room=%03x slot=%u\n",
              fx.die_after, fx.die_count, fx.die_room, fx.life_value, fx.life_after, fx.done_events, fx.save_after,
              fx.save_count, fx.save_room, fx.save_slot);
}

u32 items_hash()
{
    static u8 save[0x1400];
    const int n = ItemMgr.saveDataSize();
    if (n <= 0 || n > int(sizeof(save))) return 0;
    ItemMgr.save(save);
    u32 h = 2166136261U;
    for (int i = 0; i < n; ++i) h = (h ^ save[i]) * 16777619U;
    return h;
}

void census(const char* when)
{
    w11_text_check(when);
    u32 l2, l3, l4, l12;
    const int f2 = heap_free(2, &l2), f3 = heap_free(3, &l3), f4 = heap_free(4, &l4), f12 = heap_free(12, &l12);
    unsigned kfree = 0, kused = 0, kbreak = 0;
    re4dc_kos_heap_state(&kfree, &kused, &kbreak);
    re4dc_log("w11 census: %s room=%03x heap2=%d heap3=%d heap4=%d largest4=%u heap12=%d largest12=%u "
              "vram_free=%u kos_free=%u kos_break=%u\n",
              when, pG ? unsigned(pG->room_id) : 0, f2, f3, f4, l4, f12, l12, re4dc_vram_free(), kfree, kbreak);
}

void player_state(const char* when)
{
    if (!pG) return;
    re4dc_log("w11 state: %s room=%03x life=%d/%d wep=%04x items=%08x pos=(%d,%d,%d) rno=%d/%d\n", when,
              unsigned(pG->room_id), int(s16(pG->pl_life)), int(pG->pl_life_max), unsigned(ItemMgr.m_wep_id),
              items_hash(), pPL ? int(pPL->pos.x) : 0, pPL ? int(pPL->pos.y) : 0, pPL ? int(pPL->pos.z) : 0,
              int(pG->Rno0), int(pG->Rno1));
}

// Frame timing per phase, and the capture markers.
enum Phase { kBoot, kGame, kSub, kDead, kCard };
const char* const kPhaseName[] = {"boot", "game", "sub", "dead", "card"};
struct Window { unsigned frames; unsigned long long sum, max; };
Window window[5];
unsigned long long last_us;
Phase last_phase = kBoot;
unsigned phase_frames, opens, deaths, cards;

Phase phase_now()
{
    if (!pG) return kBoot;
    if (pG->System_flg & 0x1000) return kCard;  // CardMainTask running (card.cpp)
    if (SubScreenWk.type) return kSub;  // set by SubScreenOpen, cleared when the screen has closed
    if (fx.death_frame) return kDead;
    if (pG->Rno0 == 3) return kGame;
    return kBoot;
}

void shot(const char* fmt, unsigned a, unsigned b)
{
    char label[48];
    snprintf(label, sizeof(label), fmt, a, b);
    re4dc_log("w11 shot: %s\n", label);
}
}  // namespace

// Top of gameMainLoop (ui_bridge.cpp re4dc_room_cycle_poll), room heap live.
extern "C" int re4dc_w11_room_poll(unsigned generation)
{
    if (!fx.loaded) load_fixture();
    if (!pG || !pPL) return 0;
    if (generation != fx.generation) {
        fx.generation = generation;
        fx.room_frames = 0;
        ++fx.rooms;
        if (fx.continue_pending) {
            fx.continue_pending = false;
            fx.death_frame = 0;
        }
    }
    ++fx.room_frames;
    if (fx.room_frames == 90) {
        census(fx.dies ? "continue+90" : "room+90");
        player_state(fx.dies ? "continue+90" : "room+90");
        if (fx.dies) shot("continue%u-%u", fx.dies, 90);
    }
    for (unsigned i = 0; i < fx.nmes; ++i) {
        const Fixture::Mes& m = fx.mes[i];
        const unsigned k = fx.room_frames - m.at;
        if (m.fired && (k == 30 || k == 90 || k == 180)) shot("mes%u-%u", i + 1, k);
        if (m.fired && k == 1) player_state("mes");
    }
    if (pG->Status_flg[1] & 0x10000000) return 0;  // an event holds the game
    for (unsigned i = 0; i < fx.nmes; ++i) {
        Fixture::Mes& m = fx.mes[i];
        if (m.fired) continue;
        if (fx.room_frames < m.frames || (m.room && unsigned(pG->room_id) != m.room) || SubScreenWk.type ||
            (pG->System_flg & 0x1000) || (cMes.mes[0].be_flag & 1) || s16(pG->pl_life) <= 0)
            break;
        MesWork* w = cMes.getWork();
        const int ls = w->lineSpace, fh = w->m_font_h;
        if (m.kind == 0) {
            SceMesSet(int(m.no), 0x10, 1, 0x64, 0x150 - ls - fh - 1);  // 0x10: no wait (room messages are flags 0)
        } else {
            cMes.MesSet(int(m.no), 0x64, 0x129 - fh - ls, 0x211, 0, 0, 4);
            cMes.mes[0].m_item_no = u16(m.item);
            cMes.mes[0].setNumber(m.num, 0);
        }
        m.fired = true;
        m.at = fx.room_frames;
        re4dc_fixture_state("w11m", int(i + 1), 1);
        re4dc_log("w11 fixture: mes %u shown (no=%x kind=%u) at room frame %u\n", i + 1, m.no, m.kind, fx.room_frames);
        break;
    }
    for (unsigned i = 0; i < fx.nfile; ++i) {
        Fixture::File& f = fx.file[i];
        if (f.fired) continue;
        if (fx.room_frames < f.frames || (f.room && unsigned(pG->room_id) != f.room) || SubScreenWk.type ||
            (pG->System_flg & 0x1000) || (cMes.mes[0].be_flag & 1) || s16(pG->pl_life) <= 0)
            break;
        if (SubScreenOpen(SS_OPEN_FILE, 0) == 0) break;  // one is already requested
        SubScreenWk.get_item_id = file_item_id(f.no);
        f.fired = true;
        re4dc_fixture_state("w11f", int(i + 1), 1);
        re4dc_log("w11 fixture: file %u opened (no=%u id=%x) at room frame %u\n", i + 1, f.no,
                  unsigned(SubScreenWk.get_item_id), fx.room_frames);
        break;
    }
    if (fx.life_value >= 0 && !fx.life_done && fx.room_frames >= fx.life_after) {
        fx.life_done = true;
        re4dc_log("w11 fixture: life %d -> %d\n", int(s16(pG->pl_life)), fx.life_value);
        pG->pl_life = u16(fx.life_value);
    }
    if (fx.save_count && fx.saves < fx.save_count && fx.room_frames >= fx.save_after * (fx.saves + 1) &&
        (!fx.save_room || unsigned(pG->room_id) == fx.save_room) &&
        !SubScreenWk.type && !(pG->System_flg & 0x1000) && s16(pG->pl_life) > 0) {
        ++fx.saves;
        census("save");
        player_state("save");
        re4dc_log("w11 fixture: typewriter save %u/%u slot %u at room frame %u\n", fx.saves, fx.save_count,
                  fx.save_slot, fx.room_frames);
        CardSave(int(fx.save_slot), 1);  // returns when the card screen has closed
        census("save-closed");
        player_state("save-closed");
        re4dc_log("w11 fixture: typewriter save %u returned\n", fx.saves);
    }
    if (fx.die_count && fx.dies < fx.die_count && !fx.death_frame && fx.room_frames >= fx.die_after &&
        (!fx.die_room || unsigned(pG->room_id) == fx.die_room) &&
        !SubScreenWk.type && s16(pG->pl_life) > 0) {
        ++fx.dies;
        census("die");
        player_state("die");
        // The source damage entry, as an enemy hit would call it: life 1 first, so the hit
        // cannot take the "keep 1 point" branch (LifeDownSet2 flag bit 0), then a die motion.
        pG->pl_life = 1;
        PlSetDamage(7, 100, 0);
        fx.death_frame = re4dc_vi_retrace_count();
        fx.continue_pending = true;
        re4dc_log("w11 fixture: death %u/%u at room frame %u (life now %d)\n", fx.dies, fx.die_count, fx.room_frames,
                  int(s16(pG->pl_life)));
    }
    return 0;
}

// Once per frame (platform/pad.cpp PADRead -> ui_bridge.cpp re4dc_pad_context).
extern "C" void re4dc_w11_frame()
{
    if (!fx.loaded) load_fixture();
    const unsigned long long now = re4dc_ssb_us();
    const Phase p = phase_now();
    if (last_us && p == last_phase) {
        Window& w = window[p];
        const unsigned long long dt = now - last_us;
        ++w.frames;
        w.sum += dt;
        if (dt > w.max) w.max = dt;
        if (w.frames == 60) {
            u32 l12 = 0;
            re4dc_log("w11 frame: phase=%s frames=%u mean_us=%u max_us=%u heap12=%d\n", kPhaseName[p], w.frames,
                      unsigned(w.sum / w.frames), unsigned(w.max), p == kSub ? heap_free(12, &l12) : -1);
            w = Window{};
        }
    }
    if (p != last_phase) {
        window[p] = Window{};
        if (p == kSub) {
            ++opens;
            census("sub-open");
            player_state("sub-open");
        } else if (last_phase == kSub) {
            census("sub-closed");
            player_state("sub-closed");
        }
        if (p == kDead) ++deaths;
        if (p == kCard) {
            ++cards;
            census("card-open");
        } else if (last_phase == kCard) {
            census("card-closed");
        }
        re4dc_log("w11 phase: %s -> %s opens=%u deaths=%u frame=%u\n", kPhaseName[last_phase], kPhaseName[p], opens,
                  deaths, pG ? unsigned(pG->Frame_cnt) : 0);
        // Padscript anchor "w11=<phase>/<n>": sub/dead count their own events, game counts both.
        re4dc_fixture_state("w11", int(p), int(p == kSub ? opens : p == kDead ? deaths : p == kCard ? cards : opens + deaths));
        phase_frames = 0;
        last_phase = p;
    }
    ++phase_frames;
    if (p == kSub || (p == kGame && opens && phase_frames < 4)) {
        char when[32];
        snprintf(when, sizeof(when), "%s%u-f%u", kPhaseName[p], opens, phase_frames);
        w11_text_check(when);
    }
    if (p == kSub && phase_frames % 120 == 90 && phase_frames < 1500) shot("sub%u-%u", opens, phase_frames);
    if (p == kGame && opens && phase_frames == 60) shot("closed%u-%u", opens, phase_frames);
    if (p == kCard && phase_frames % 120 == 60 && phase_frames < 1500) shot("card%u-%u", cards, phase_frames);
    if (p == kGame && fx.done_events && !fx.done_logged && opens + deaths + cards >= fx.done_events && phase_frames == 300) {
        fx.done_logged = true;
        census("done");
        player_state("done");
        re4dc_log("w11 done: opens=%u deaths=%u cards=%u\n", opens, deaths, cards);
    }
    if (p == kDead && (phase_frames == 150 || phase_frames == 330 || phase_frames == 450)) shot("dead%u-%u", deaths, phase_frames);
    last_us = now;
}
#endif  // RE4DC_W11_FIXTURE

#if RE4DC_SS_BG_BLACK
// SS_BG_BLACK (platform/native_static.cpp re4dc_fog_frame): Status_flg[1] bit 1 is set by
// SubScreenExec step 2 (every Disp_flg hide bit on) and cleared by SubScreenExit step 4, so it
// spans the frames where the room draws nothing while the sub screen opens, runs and closes.
// Read only; the renderer uses it to pick the PVR background colour.
extern "C" int re4dc_ss_scene_hidden(void) { return (pG->Status_flg[1] & 2) != 0; }
#endif
