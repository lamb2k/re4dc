// D367 W11 (SUBSCREEN=1): Dreamcast storage behind the sub screen's GameCube ARAM swap.
// sscrn_bridge.cpp decides what to keep; this file only owns the KOS side:
//  - the backing store, two linear VRAM segments used in order:
//      1. the second TA vertex bank (32-bit area 0x400000 + TA_VERTBUF_KB KiB). pvr_init()
//         allocates two banks; with TA_DOUBLEBUF=0 the TA target never leaves bank 0. With
//         TA_DOUBLEBUF=1 the TA drops to bank 0 for the backing's lifetime
//         (re4dc_ui_ta_single_bank at open, re4dc_ui_ta_double_bank_later at close;
//         design-doublebuf), so bank 1's vertex buffer is never read or written by the TA
//         while it holds the backing. Its tile matrix and OPBs follow the vertex region and are
//         never touched (kBankBytes);
//      2. texture-pool blocks (pvr_mem_malloc, at most kMaxBlocks, halving the request when the
//         pool is fragmented) for the remainder, freed at close. When the pool is short, the
//         least recently used native UI uploads that the current scene does not reference are
//         released first (re4dc_ui_reclaim_one; the world is not drawn while the sub screen
//         opens and they reload on demand after it closes).
//    The data never reaches the PVR, so no render fence is involved.
//    SS_PACK=1 (sub screen only, sscrn_bridge.cpp): re4dc_ssb_open_grow + re4dc_ssb_put_packed store
//    the area LZ4-block compressed (~1.6:1 on r100 play, so 3 MiB of live bytes fit the 2 MiB bank).
//    Pool blocks are taken only as the stream outgrows the bank, from free pool memory first; the
//    preload is held (re4dc_ui_vram_hold) rather than claimed, so no contiguous 1 MiB is carved out of
//    the room's textures (the plain open released 2.3 MB / 159 uploads, a 5.8 s reload, per call).
//  - whole-file disc reads for the sub screen's own files (ss_cmmn / ss_pzzl);
//  - a microsecond clock for the open/close cost lines.
#if RE4DC_SUBSCREEN || RE4DC_W11_FIXTURE  // (subscreen.mk; empty in the default image)
#include <kos.h>
#include "cache_lines.h"
#include <fcntl.h>
#include <cctype>
#include <cstdio>
#include <cstring>

#include "re4dc_platform.h"
#include "native_io.h"
#if defined(RE4DC_LOGIC_TRACE_SWAPPED) && RE4DC_LOGIC_TRACE_SWAPPED
#include "../trace_spare.hpp"
#endif

#ifndef RE4DC_TA_VERTBUF_KB
#define RE4DC_TA_VERTBUF_KB 1024
#endif
#ifndef RE4DC_TA_DOUBLEBUF
#define RE4DC_TA_DOUBLEBUF 0
#endif
#if RE4DC_SUBSCREEN && RE4DC_TA_DOUBLEBUF
extern "C" void re4dc_ui_ta_single_bank();
extern "C" void re4dc_ui_ta_double_bank_later();
#endif

extern "C" int re4dc_dvd_native_path(const char* name, char* output, unsigned capacity);
extern "C" unsigned re4dc_ui_reclaim_one();
// TEX_RESIDENT builds (native_ui.cpp): empties the pool of unreferenced uploads until one block
// fits and holds the room preload until the matching unclaim. Weak: absent in other builds.
extern "C" int re4dc_ui_vram_claim(unsigned bytes) __attribute__((weak));
extern "C" void re4dc_ui_vram_unclaim() __attribute__((weak));
#if RE4DC_SS_PACK
extern "C" void re4dc_ui_vram_hold() __attribute__((weak));
extern "C" void re4dc_ssb_put(const void* src, unsigned bytes);
#endif

namespace {
constexpr unsigned kBankOffset = 0x400000;  // pvr_allocate_buffers(): bank 1 starts half way
constexpr unsigned kBankBytes = RE4DC_TA_VERTBUF_KB * 1024U;
volatile unsigned* const kBank = reinterpret_cast<volatile unsigned*>(PVR_RAM_BASE + kBankOffset);
#if RE4DC_SS_PACK
constexpr unsigned kMaxBlocks = 64, kMinBlock = 32 * 1024;
#else
constexpr unsigned kMaxBlocks = 16, kMinBlock = 32 * 1024;
#endif
struct Store {
    bool open;
    unsigned bytes, bank_bytes, pool_bytes;
    pvr_ptr_t block[kMaxBlocks];
    unsigned block_bytes[kMaxBlocks], nblock;
    unsigned cursor;  // byte position of the next put/get
    unsigned reclaimed_bytes, reclaimed_uploads;
    bool claimed;
#if RE4DC_SS_PACK
    bool grows;  // re4dc_ssb_open_grow: pool blocks are taken as the puts need them
#endif
};
Store store{};

// The segment holding byte `position` and the bytes left in it from there.
volatile unsigned* word_at(unsigned position, unsigned* run)
{
    if (position < store.bank_bytes) {
        *run = store.bank_bytes - position;
        return kBank + position / 4;
    }
    unsigned at = position - store.bank_bytes;
    for (unsigned i = 0; i < store.nblock; ++i) {
        if (at < store.block_bytes[i]) {
            *run = store.block_bytes[i] - at;
            return reinterpret_cast<volatile unsigned*>(reinterpret_cast<char*>(store.block[i]) + at);
        }
        at -= store.block_bytes[i];
    }
    re4dc_missing("subscreen backing: position outside the store");
    return nullptr;
}

void free_blocks()
{
    for (unsigned i = 0; i < store.nblock; ++i) pvr_mem_free(store.block[i]);
    store.nblock = 0;
}

#if RE4DC_SS_PACK
constexpr unsigned kGrowStep = 64 * 1024, kGrowMin = 8 * 1024;
constexpr unsigned kPackHashBits = 12, kPackTableBytes = 2U << kPackHashBits, kPackStage = 512;

// Adds pool blocks until `need` more bytes fit: free pool memory first (the largest block the pool
// gives, kGrowStep or more, halved down to kGrowMin), then the least recently used uploads.
bool grow(unsigned need)
{
    while (need) {
        if (store.nblock == kMaxBlocks) {
            re4dc_log("subscreen backing: %u blocks cannot hold %u B more\n", kMaxBlocks, need);
            return false;
        }
        unsigned ask = ((need > kGrowStep ? need : kGrowStep) + 31) & ~31U;
        pvr_ptr_t p = nullptr;
        while (!(p = pvr_mem_malloc(ask)) && ask > kGrowMin) ask = ((ask / 2) + 31) & ~31U;
        if (p) {
            store.block[store.nblock] = p;
            store.block_bytes[store.nblock++] = ask;
            store.bytes += ask;
            store.pool_bytes += ask;
            need -= ask < need ? ask : need;
            continue;
        }
        const unsigned freed = re4dc_ui_reclaim_one();
        if (!freed) {
            re4dc_log("subscreen backing: texture pool short by %u B (free %u, blocks %u) after releasing %u uploads\n",
                      need, (unsigned) pvr_mem_available(), store.nblock, store.reclaimed_uploads);
            return false;
        }
        store.reclaimed_bytes += freed;
        ++store.reclaimed_uploads;
    }
    return true;
}

// Byte loads only: the packed spans start anywhere (the SH-4 faults on a misaligned word load).
inline unsigned rd32(const unsigned char* p)
{
    return (unsigned) p[0] | (unsigned) p[1] << 8 | (unsigned) p[2] << 16 | (unsigned) p[3] << 24;
}

struct Emit {
    unsigned char* buf;  // kPackStage bytes, 4-aligned
    unsigned n, total;
};
inline void emit(Emit& e, unsigned v)
{
    e.buf[e.n++] = (unsigned char) v;
    ++e.total;
    if (e.n == kPackStage) {
        re4dc_ssb_put(e.buf, kPackStage);
        e.n = 0;
    }
}
inline void emit_ext(Emit& e, unsigned v)
{
    for (; v >= 255; v -= 255) emit(e, 255);
    emit(e, v);
}
void emit_bytes(Emit& e, const unsigned char* p, unsigned n)
{
    e.total += n;
    while (n) {
        unsigned k = kPackStage - e.n;
        if (k > n) k = n;
        memcpy(e.buf + e.n, p, k);
        e.n += k;
        p += k;
        n -= k;
        if (e.n == kPackStage) {
            re4dc_ssb_put(e.buf, kPackStage);
            e.n = 0;
        }
    }
}
}  // namespace
#else
}  // namespace
#endif

extern "C" {

// Reserves `bytes` (a multiple of 4) of backing: bank 1 first, then a pool block.
int re4dc_ssb_open(unsigned bytes, unsigned* bank_bytes, unsigned* pool_bytes)
{
    if (store.open) {
        re4dc_log("subscreen backing: already open\n");
        return 0;
    }
    store = Store{};
#if RE4DC_SUBSCREEN && RE4DC_TA_DOUBLEBUF
    re4dc_ui_ta_single_bank();  // before the first bank-1 write
#endif
    store.bytes = bytes;
    store.bank_bytes = bytes < kBankBytes ? bytes : kBankBytes;
    store.pool_bytes = bytes - store.bank_bytes;
    unsigned need = store.pool_bytes;
    store.claimed = need && re4dc_ui_vram_claim;
    if (store.claimed) re4dc_ui_vram_claim(need);
    while (need) {
        if (store.nblock == kMaxBlocks) {
            re4dc_log("subscreen backing: %u blocks cannot hold %u B (short %u)\n", kMaxBlocks, store.pool_bytes, need);
            free_blocks();
            if (store.claimed) re4dc_ui_vram_unclaim();
#if RE4DC_SUBSCREEN && RE4DC_TA_DOUBLEBUF
            re4dc_ui_ta_double_bank_later();
#endif
            return 0;
        }
        // Largest block the pool gives now, down to kMinBlock (or the remainder).
        unsigned ask = (need + 31) & ~31U;
        pvr_ptr_t p = nullptr;
        while (!(p = pvr_mem_malloc(ask)) && ask > kMinBlock) ask = ((ask / 2) + 31) & ~31U;
        if (p) {
            const unsigned got = ask < need ? ask : need;
            store.block[store.nblock] = p;
            store.block_bytes[store.nblock++] = got;
            need -= got;
            continue;
        }
        const unsigned freed = re4dc_ui_reclaim_one();
        if (!freed) {
            re4dc_log("subscreen backing: texture pool short by %u B (free %u, blocks %u) after releasing %u uploads\n",
                      need, (unsigned) pvr_mem_available(), store.nblock, store.reclaimed_uploads);
            free_blocks();
            if (store.claimed) re4dc_ui_vram_unclaim();
#if RE4DC_SUBSCREEN && RE4DC_TA_DOUBLEBUF
            re4dc_ui_ta_double_bank_later();
#endif
            return 0;
        }
        store.reclaimed_bytes += freed;
        ++store.reclaimed_uploads;
    }
    store.open = true;
    *bank_bytes = store.bank_bytes;
    *pool_bytes = store.pool_bytes;
    return 1;
}

#if RE4DC_SS_PACK
// The packed sub screen backing: bank 1 only at first; re4dc_ssb_put grows the store from the pool
// as the packed stream needs it. The preload is held until close.
int re4dc_ssb_open_grow()
{
    if (store.open) {
        re4dc_log("subscreen backing: already open\n");
        return 0;
    }
    store = Store{};
#if RE4DC_SUBSCREEN && RE4DC_TA_DOUBLEBUF
    re4dc_ui_ta_single_bank();  // before the first bank-1 write
#endif
    store.bytes = store.bank_bytes = kBankBytes;
    store.grows = true;
    store.claimed = re4dc_ui_vram_hold && re4dc_ui_vram_unclaim;
    if (store.claimed) re4dc_ui_vram_hold();
    store.open = true;
    return 1;
}

unsigned re4dc_ssb_cursor() { return store.cursor; }
unsigned re4dc_ssb_pack_scratch_bytes() { return kPackTableBytes + kPackStage; }
#endif

void re4dc_ssb_rewind() { store.cursor = 0; }

// Appends `bytes` (multiple of 4, `src` 4-aligned) at the cursor.
void re4dc_ssb_put(const void* src, unsigned bytes)
{
    const unsigned* s = static_cast<const unsigned*>(src);
#if RE4DC_SS_PACK
    if (store.open && store.grows && store.cursor + bytes > store.bytes && !grow(store.cursor + bytes - store.bytes))
        re4dc_missing("subscreen backing: no VRAM for the packed area");
#endif
    if (!store.open || store.cursor + bytes > store.bytes) re4dc_missing("subscreen backing overrun");
    while (bytes) {
        unsigned run;
        volatile unsigned* d = word_at(store.cursor, &run);
        if (run > bytes) run = bytes;
        for (unsigned n = run / 4; n; --n) *d++ = *s++;
        store.cursor += run;
        bytes -= run;
    }
}

// Reads `bytes` at the cursor.
void re4dc_ssb_get(void* dst, unsigned bytes)
{
    unsigned* d = static_cast<unsigned*>(dst);
    if (!store.open || store.cursor + bytes > store.bytes) re4dc_missing("subscreen backing underrun");
    while (bytes) {
        unsigned run;
        const volatile unsigned* s = word_at(store.cursor, &run);
        if (run > bytes) run = bytes;
        for (unsigned n = run / 4; n; --n) *d++ = *s++;
        store.cursor += run;
        bytes -= run;
    }
}

#if defined(RE4DC_LOGIC_TRACE_SWAPPED) && RE4DC_LOGIC_TRACE_SWAPPED
// Trace-only storage in spare capacity of the already-owned backing store: the captured raw bytes grow up
// from the saved window's end and the trace's span index (8-byte entries) grows down from the store's end,
// each refused before it would reach the other (trace_spare.hpp). Never allocate game RAM, grow the store,
// reclaim a texture, write below the saved window's end or move the restore cursor on reads.
static TraceSpare trace_spare;
int re4dc_ssb_trace_begin(unsigned saved_end) {
    if(!store.open || !trace_spare.start(saved_end,store.bytes))return 0;
    store.cursor=saved_end;return 1;
}
int re4dc_ssb_trace_append(const void* src,unsigned bytes,unsigned* offset) {
    if(!store.open || bytes>~0u-3)return 0;
    const unsigned padded=(bytes+3)&~3u;
    if(store.cursor!=trace_spare.end || store.cursor>store.bytes || !trace_spare.data(padded,offset)) {
        re4dc_log("LTSBACKFAIL begin=%u end=%u cursor=%u capacity=%u requested=%u padded=%u index_low=%u index_top=%u\n",trace_spare.begin,trace_spare.end,store.cursor,store.bytes,bytes,padded,trace_spare.low,trace_spare.top);
        return 0;
    }
    const unsigned char* input=static_cast<const unsigned char*>(src);
    unsigned left=bytes;
    while(left) {
        unsigned staging[8]{};
        const unsigned n=left<sizeof(staging)?left:sizeof(staging);
        memcpy(staging,input,n);
        re4dc_ssb_put(staging,(n+3)&~3u);
        input+=n;left-=n;
    }
    if(store.cursor!=trace_spare.end)re4dc_missing("logic trace: backing append position");
    return 1;
}
int re4dc_ssb_trace_read(void* dst,unsigned offset,unsigned bytes) {
    if(!store.open || !trace_spare.data_span(offset,bytes))return 0;
    unsigned char* output=static_cast<unsigned char*>(dst);
    while(bytes) {
        unsigned run;
        const unsigned word=*word_at(offset&~3u,&run);
        const unsigned skip=offset&3u;
        const unsigned n=bytes<4-skip?bytes:4-skip;
        memcpy(output,reinterpret_cast<const unsigned char*>(&word)+skip,n);
        output+=n;offset+=n;bytes-=n;
    }
    return 1;
}
// Span index entries: two words each, read and written in place; the cursor never moves.
static void trace_entry_io(unsigned at,unsigned* words,bool write) {
    for(unsigned k=0;k<2;++k) {
        unsigned run;
        volatile unsigned* w=word_at(at+4*k,&run);
        if(write)*w=words[k];else words[k]=*w;
    }
}
int re4dc_ssb_trace_index_push(const void* entry) {
    unsigned at;
    if(!store.open || !trace_spare.push(&at)) {
        re4dc_log("LTSBACKFAIL index begin=%u end=%u capacity=%u index_low=%u index_top=%u entries=%u\n",trace_spare.begin,trace_spare.end,store.bytes,trace_spare.low,trace_spare.top,trace_spare.entries());
        return 0;
    }
    unsigned words[2];memcpy(words,entry,8);
    trace_entry_io(at,words,true);return 1;
}
int re4dc_ssb_trace_index_read(unsigned i,void* entry) {
    unsigned at,words[2];
    if(!store.open || !trace_spare.entry(i,&at))return 0;
    trace_entry_io(at,words,false);memcpy(entry,words,8);return 1;
}
int re4dc_ssb_trace_index_write(unsigned i,const void* entry) {
    unsigned at,words[2];
    if(!store.open || !trace_spare.entry(i,&at))return 0;
    memcpy(words,entry,8);trace_entry_io(at,words,true);return 1;
}
// layout[0..4]: saved window end, raw bytes end, index low, index top (store end rounded down to 8), capacity.
void re4dc_ssb_trace_layout(unsigned* layout) {
    layout[0]=trace_spare.begin;layout[1]=trace_spare.end;layout[2]=trace_spare.low;layout[3]=trace_spare.top;layout[4]=store.bytes;
}
#endif

#if RE4DC_SS_PACK
// Appends [src, src + n) as one LZ4 block (greedy, 4096-entry hash table of 16-bit positions, offsets
// up to 64 KiB back into the same range): a word holding the block length, then the block padded to a
// word. `scratch` (re4dc_ssb_pack_scratch_bytes(), 4-aligned, outside the range) holds the table and
// the output staging. Returns the block length.
unsigned re4dc_ssb_put_packed(const void* srcv, unsigned n, void* scratch)
{
    const unsigned char* src = static_cast<const unsigned char*>(srcv);
    unsigned short* table = static_cast<unsigned short*>(scratch);
    Emit e{static_cast<unsigned char*>(scratch) + kPackTableBytes, 0, 0};
    for (unsigned i = 0; i < (1U << kPackHashBits); ++i) table[i] = 0;
    const unsigned header = store.cursor, zero = 0;
    re4dc_ssb_put(&zero, 4);
    unsigned ip = 0, anchor = 0, misses = 0;
    if (n >= 12) {
        const unsigned limit = n - 12, mend = n - 5;
        unsigned v = rd32(src);
        while (ip <= limit) {
            const unsigned h = (v * 2654435761U) >> (32 - kPackHashBits);
            // The table keeps the low 16 bits of a position: within the 64 KiB window that names it
            // exactly; anything else is rejected by the compare.
            const unsigned dist = (ip - table[h]) & 0xFFFFU;
            table[h] = (unsigned short) ip;
            if (dist && dist <= ip && rd32(src + ip - dist) == v) {
                const unsigned char* m = src + ip - dist;
                unsigned ml = 4;
                while (ip + ml < mend && m[ml] == src[ip + ml]) ++ml;
                const unsigned lit = ip - anchor, extra = ml - 4;
                emit(e, (lit < 15 ? lit : 15) << 4 | (extra < 15 ? extra : 15));
                if (lit >= 15) emit_ext(e, lit - 15);
                emit_bytes(e, src + anchor, lit);
                emit(e, dist & 0xFF);
                emit(e, dist >> 8);
                if (extra >= 15) emit_ext(e, extra - 15);
                ip += ml;
                anchor = ip;
                misses = 0;
                if (ip <= limit) v = rd32(src + ip);
            } else {
                // The LZ4 skip: after 64 misses in a row the probe steps 2 bytes, after 128 steps 3, ...
                // (r100 area: 21 % fewer probes, 1.624 -> 1.622 : 1).
                const unsigned step = 1 + (misses++ >> 6);
                ip += step;
                if (ip <= limit) v = step == 1 ? v >> 8 | (unsigned) src[ip + 3] << 24 : rd32(src + ip);
            }
        }
    }
    const unsigned lit = n - anchor;
    emit(e, (lit < 15 ? lit : 15) << 4);
    if (lit >= 15) emit_ext(e, lit - 15);
    emit_bytes(e, src + anchor, lit);
    if (e.n) {
        const unsigned padded = (e.n + 3) & ~3U;
        for (unsigned i = e.n; i < padded; ++i) e.buf[i] = 0;
        re4dc_ssb_put(e.buf, padded);
    }
    unsigned run;
    *word_at(header, &run) = e.total;
    return e.total;
}

// Reads one re4dc_ssb_put_packed block back into [dst, dst + n). Returns 0 if the block does not
// decode to exactly n bytes.
int re4dc_ssb_get_packed(void* dstv, unsigned n)
{
    unsigned char* const d0 = static_cast<unsigned char*>(dstv);
    unsigned char* d = d0;
    unsigned char* const end = d0 + n;
    unsigned length;
    re4dc_ssb_get(&length, 4);
    alignas(4) unsigned char buf[256];
    unsigned pos = 0, have = 0, left = (length + 3) & ~3U, used = 0;
    bool bad = false;
    auto refill = [&]() {
        have = left < sizeof(buf) ? left : sizeof(buf);
        re4dc_ssb_get(buf, have);
        left -= have;
        pos = 0;
    };
    auto next = [&]() -> unsigned {
        if (used == length) {
            bad = true;
            return 0;
        }
        if (pos == have) refill();
        ++used;
        return buf[pos++];
    };
    auto ext = [&](unsigned v) {
        unsigned b;
        do v += (b = next());
        while (b == 255 && !bad);
        return v;
    };
    while (used < length && !bad) {
        const unsigned token = next();
        unsigned lit = token >> 4;
        if (lit == 15) lit = ext(lit);
        if (bad || lit > unsigned(end - d)) return 0;
        while (lit) {
            if (pos == have) refill();
            unsigned k = have - pos;
            if (k > lit) k = lit;
            if (!k || k > length - used) return 0;
            memcpy(d, buf + pos, k);
            d += k;
            pos += k;
            used += k;
            lit -= k;
        }
        if (used == length) break;  // the last sequence is literals only
        const unsigned lo = next();
        const unsigned off = lo | next() << 8;
        unsigned ml = token & 15;
        if (ml == 15) ml = ext(ml);
        ml += 4;
        if (bad || !off || off > unsigned(d - d0) || ml > unsigned(end - d)) return 0;
        for (const unsigned char* m = d - off; ml; --ml) *d++ = *m++;
    }
    while (left) {  // the padding
        have = left < sizeof(buf) ? left : sizeof(buf);
        re4dc_ssb_get(buf, have);
        left -= have;
    }
    return !bad && d == end;
}
#endif

void re4dc_ssb_close()
{
    free_blocks();
    if (store.claimed) re4dc_ui_vram_unclaim();
    store = Store{};
#if defined(RE4DC_LOGIC_TRACE_SWAPPED) && RE4DC_LOGIC_TRACE_SWAPPED
    trace_spare = TraceSpare{};  // the trace's raw bytes and index end with the store
#endif
#if RE4DC_SUBSCREEN && RE4DC_TA_DOUBLEBUF
    re4dc_ui_ta_double_bank_later();  // bank 1 was read back: the TA may use it from the next scene
#endif
}

// Pool blocks in use and native UI uploads released by the last open.
void re4dc_ssb_stats(unsigned* blocks, unsigned* reclaimed_uploads, unsigned* reclaimed_bytes)
{
    *blocks = store.nblock;
    *reclaimed_uploads = store.reclaimed_uploads;
    *reclaimed_bytes = store.reclaimed_bytes;
}

unsigned re4dc_ssb_pool_free() { return (unsigned) pvr_mem_available(); }

#if defined(RE4DC_SS_CLOSE_POISON) && RE4DC_SS_CLOSE_POISON >= 2
// SS_CLOSE_POISON=2 (mcheck.mk; debug only): 0xA5 over the dead stack of the calling thread, from 256 bytes below
// this frame down to 8 KiB or the stack's guard word. No calls while filling (a callee's frame would lie inside).
void re4dc_poison_dead_stack(const char* tag)
{
    kthread_t* const t = thd_current;
    volatile unsigned probe = 0;
    const unsigned sp = (unsigned) (uintptr_t) &probe;
    const unsigned lo = t ? (unsigned) (uintptr_t) t->stack : 0;
    if (!lo || sp < lo + 512) {
        re4dc_log("subscreen backing: %s dead stack not poisoned (thread %d stack %08x sp %08x)\n", tag, t ? t->tid : -1, lo, sp);
        return;
    }
    const unsigned hi = (sp - 256) & ~3U;
    const unsigned from = hi - lo > 8192 + 16 ? hi - 8192 : lo + 16;
    for (volatile unsigned* w = reinterpret_cast<volatile unsigned*>(from); w < reinterpret_cast<volatile unsigned*>(hi); ++w)
        *w = 0xA5A5A5A5U;
    re4dc_log("subscreen backing: %s dead stack poison %08x-%08x (thread %d stack %08x+%x sp %08x)\n", tag, from, hi,
              t->tid, lo, (unsigned) t->stack_size, sp);
}
#endif
unsigned re4dc_ssb_bank_bytes() { return kBankBytes; }
unsigned long long re4dc_ssb_us() { return timer_us_gettime64(); }

// The disc path the source DVD layer would open for `name` ("SS/eng/ss_cmmn.dat").
static bool disc_path(const char* name, char* full, unsigned capacity)
{
    char rel[64];
    unsigned i = 0;
    while (*name == '/' || *name == '\\') ++name;
    for (; *name && i + 1 < sizeof(rel); ++name) rel[i++] = char(std::tolower((unsigned char) (*name == '\\' ? '/' : *name)));
    rel[i] = 0;
    return re4dc_dvd_native_path(rel, full, capacity);
}

long re4dc_ssb_file_size(const char* name)
{
    char full[96];
    if (!disc_path(name, full, sizeof(full))) return -1;
    Re4dcIoScope io;
    file_t f = fs_open(full, O_RDONLY);
    if (f < 0) return -1;
    const long size = (long) fs_total(f);
    fs_close(f);
    return size;
}

// Whole-file read into `dst` (at most `capacity` bytes). Returns the bytes read or -1.
long re4dc_ssb_file_read(const char* name, void* dst, unsigned capacity)
{
    char full[96];
    if (!disc_path(name, full, sizeof(full))) return -1;
    Re4dcIoScope io;
    file_t f = fs_open(full, O_RDONLY);
    if (f < 0) {
        re4dc_log("subscreen backing: open failed %s\n", full);
        return -1;
    }
    long total = (long) fs_total(f), got = 0;
    if (total > (long) capacity) total = (long) capacity;
    while (got < total) {
        const ssize_t r = fs_read(f, static_cast<char*>(dst) + got, (size_t) (total - got));
        if (r <= 0) break;
        got += (long) r;
    }
    fs_close(f);
    return got == total ? got : -1;
}

#if defined(RE4DC_SS_DATA_LZ) && RE4DC_SS_DATA_LZ
// SS_DATA_LZ=1 (lane inv23): the sub screen's data files packed offline (tools/d367/inv23/ss_lz.py):
// "SS/eng/ss_cmmn.dat" -> "SS/eng/ss_cmmn.lz" = 'SSLZ', u32 raw size, u32 packed size, u32 crc32 (checked offline
// by ss_lz.py verify), one LZ4 block. The decoder is bounds checked and must produce exactly the raw size.
static bool lz_name(const char* name, char* out, unsigned capacity)
{
    unsigned n = 0;
    while (name[n]) ++n;
    if (n < 4 || n + 1 > capacity || name[n - 4] != '.') return false;
    for (unsigned i = 0; i < n - 3; ++i) out[i] = name[i];
    out[n - 3] = 'l';
    out[n - 2] = 'z';
    out[n - 1] = 0;
    return true;
}

static unsigned lz_rd32(const unsigned char* p)
{
    return unsigned(p[0]) | unsigned(p[1]) << 8 | unsigned(p[2]) << 16 | unsigned(p[3]) << 24;
}

// Opens `name`'s packed copy and checks its header. Returns the file's total size, or -1.
static long lz_header(const char* name, char* full, unsigned full_capacity, unsigned* raw, unsigned* packed)
{
    char lzn[64];
    if (!lz_name(name, lzn, sizeof(lzn)) || !disc_path(lzn, full, full_capacity)) return -1;
    Re4dcIoScope io;
    file_t f = fs_open(full, O_RDONLY);
    if (f < 0) return -1;
    alignas(4) unsigned char h[16];
    const long total = (long) fs_total(f);
    const bool ok = total >= 16 && fs_read(f, h, 16) == 16;
    fs_close(f);
    if (!ok || h[0] != 'S' || h[1] != 'S' || h[2] != 'L' || h[3] != 'Z') return -1;
    *raw = lz_rd32(h + 4);
    *packed = lz_rd32(h + 8);
    if (long(*packed) + 16 > total) return -1;
    return total;
}

// The raw size of `name`'s packed copy, or -1 when there is none.
long re4dc_ssb_lz_size(const char* name)
{
    char full[96];
    unsigned raw, packed;
    return lz_header(name, full, sizeof(full), &raw, &packed) < 0 ? -1 : long(raw);
}

// One LZ4 block [s, s + n) into [dst, dst + cap). Returns the decoded bytes, or -1.
static long lz4_block_decode(const unsigned char* s, unsigned n, unsigned char* dst, unsigned cap)
{
    const unsigned char* const se = s + n;
    unsigned char* d = dst;
    unsigned char* const de = dst + cap;
    while (s < se) {
        const unsigned token = *s++;
        unsigned lit = token >> 4;
        if (lit == 15) {
            unsigned b;
            do {
                if (s >= se) return -1;
                lit += (b = *s++);
            } while (b == 255);
        }
        if (lit > unsigned(se - s) || lit > unsigned(de - d)) return -1;
        memcpy(d, s, lit);
        d += lit;
        s += lit;
        if (s == se) break;  // the last sequence is literals only
        if (se - s < 2) return -1;
        const unsigned off = unsigned(s[0]) | unsigned(s[1]) << 8;
        s += 2;
        unsigned ml = token & 15;
        if (ml == 15) {
            unsigned b;
            do {
                if (s >= se) return -1;
                ml += (b = *s++);
            } while (b == 255);
        }
        ml += 4;
        if (!off || off > unsigned(d - dst) || ml > unsigned(de - d)) return -1;
        const unsigned char* m = d - off;
        while (ml--) *d++ = *m++;  // an overlapping copy repeats the pattern
    }
    return long(d - dst);
}

// Reads `name`'s packed copy into `scratch` (the free tail of the sub screen area), decodes it into `dst` and
// zeroes the scratch bytes again. Returns the raw bytes, or -1 (the caller then reads the .dat file).
long re4dc_ssb_lz_read(const char* name, void* dst, unsigned capacity, void* scratch, unsigned scratch_capacity)
{
    char full[96];
    unsigned raw, packed;
    const long total = lz_header(name, full, sizeof(full), &raw, &packed);
    if (total < 0 || raw > capacity || unsigned(total) > scratch_capacity) return -1;
    long got = 0;
    {
        Re4dcIoScope io;
        file_t f = fs_open(full, O_RDONLY);
        if (f < 0) return -1;
        while (got < total) {
            const ssize_t r = fs_read(f, static_cast<char*>(scratch) + got, (size_t) (total - got));
            if (r <= 0) break;
            got += (long) r;
        }
        fs_close(f);
    }
    const long n = got == total ? lz4_block_decode(static_cast<const unsigned char*>(scratch) + 16, packed,
                                                   static_cast<unsigned char*>(dst), capacity)
                                : -1;
    memset(scratch, 0, (size_t) total);  // the area tail was zero (the open's memset)
    return n == long(raw) ? n : -1;
}
#endif

#if RE4DC_SUBSCREEN_OVL
// The sub screen overlay (SUBSCREEN_OVL=1): /cd/dc/sscrn.ovl, a Dreamcast-only file (no source
// DVD name), read whole into `dst`. Returns the bytes read or -1.
long re4dc_ssb_overlay_read(void* dst, unsigned capacity)
{
    Re4dcIoScope io;
    file_t f = fs_open("/cd/dc/sscrn.ovl", O_RDONLY);
    if (f < 0) return -1;
    long total = (long) fs_total(f), got = 0;
    if (total > (long) capacity) total = (long) capacity;
    while (got < total) {
        const ssize_t r = fs_read(f, static_cast<char*>(dst) + got, (size_t) (total - got));
        if (r <= 0) break;
        got += (long) r;
    }
    fs_close(f);
    return got == total ? got : -1;
}

// Code just written through the operand cache: write it back and drop stale instruction lines.
void re4dc_ssb_code_sync(void* p, unsigned bytes)
{
    RE4DC_DCACHE_WBACK(reinterpret_cast<uintptr_t>(p), bytes);
    icache_flush_range(reinterpret_cast<uintptr_t>(p), bytes);
}
#endif

}  // extern "C"
#endif  // RE4DC_SUBSCREEN || RE4DC_W11_FIXTURE
