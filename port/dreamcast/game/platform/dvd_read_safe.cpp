// DVD_READ_SAFE=1 (Phase 2 D4, default 0) and its test hook DVD_STUCK_TEST (default 0); built only with one of them.
//
// With the full test 7 data and the GC-bake r119 package, r119 after the boss logged "cdrom_stream_request: Previous
// DMA request is in progress" for every later disc stream request: 249 texture uploads failed and every tex.pak index
// re-read failed until the end of the run. The refusals never stop, so KOS's dma_in_progress flag (hardware/cdrom.c)
// is stuck, not briefly busy: once a stream command is running, the vblank handler leaves the flag alone (the command
// reports "streaming") and only a G1 DMA completion clears it. Which earlier request left it set depends on timing
// (the same configuration passes with the image a few hundred bytes larger).
//
// DVD_READ_SAFE=1 wraps cdrom_stream_start / cdrom_stream_request. A request KOS refuses (ERR_SYS) is retried for up
// to 10 ms (a genuine DMA would be done by then: fs_iso9660 serialises its reads and waits for each one); if it is
// still refused the flag is stale, so it is cleared the only public way, cdrom_abort_cmd(timeout, abort_dma=true),
// which aborts the stream command too (the G1 ATA semaphore is taken first: that abort path assumes it is held and
// signals it at the end). The stream is then started again where it stood (it is only restartable at a sector
// boundary of what was already handed out) and the request repeated. A request that succeeds the first time takes
// the old path, with one counter update.
//
// DVD_STUCK_TEST=<seconds> (test discs only, with DVD_STUCK_ADDR): sets the flag just before the first stream start after
// that much uptime: the stuck state on demand, with or without the fix.
//
// DISC_READ_FALLBACK=1 (issue #28, default 0): reads that a disc emulator does not complete. DreamShell's ISO loader
// (IDE-modded console) crashed test 10 at boot in Snd_str_blk_init: its log showed "cdrom_abort_cmd: Timeout exceeded,
// resetting." and then "DVD: Read Ok" for the sound stream table, whose contents were not the file. KOS ends a blocking
// DMA wait (cdrom_stream_request, cdrom_read_sectors_ex with dma) when the vblank handler sees the GD command no
// longer busy, and returns ERR_OK without checking that the transfer happened; when the emulated stream command
// fails, the buffer keeps its old bytes and fs_iso9660's stream stop then times out (the reset in the log). The fix:
// before each DMA read the last 32 bytes of the destination get a marker (written through the uncached P2 mirror: the
// read's dcache invalidate would drop a cached write); if the marker is still there after an "OK" read, or the read
// failed, or a stream stop timed out, the session latches to PIO: the read is done again by PIO sector reads
// (cdrom_read_sectors_ex dma=false, the stream stopped first), later stream starts are refused (fs_iso9660 then uses
// sector reads) and later sector reads use PIO. Normal discs never trip it: the cost is the marker (two 32-byte
// uncached accesses per DMA read).
//
// DISC_FAIL_TEST=1|2 (test discs only): every DMA stream request (1), and also every DMA sector read (2), is skipped
// and reported OK, as the emulator does: the failure on demand, with or without the fix.
//
// DISC_READ_VERIFY=1 (test 11 console faults, default 0): the console halted with disc-loaded data that was not the
// file (a model's texture pointer 0x99158863 in cModel::modelInit, OT links holding code or motion-key bytes), early
// and outside radio calls, never on Flycast (whose BIOS stream and sector DMAs land inside the syscall). KOS wakes a
// blocking DMA waiter from its vblank handler as soon as the BIOS says the GD command is no longer busy or streaming,
// without looking at the G1 DMA engine; a read handed back before its bytes land gives the caller the old memory and
// lets the late bytes overwrite whatever uses that memory next. With this knob a DMA read that KOS reports done waits
// until SB_GDST (G1 GD-DMA start/status, 0xA05F7418) is idle (2 s bound) and re-invalidates the destination's cache
// lines when it had to wait; fs_iso9660's one non-blocking request (32 bytes) is made blocking to get the same wait;
// DVD_READ_SAFE's stale-flag abort is held off while the engine is still running (2 s). Every late completion logs a
// "disc read verify:" line with counters.
#include <kos.h>
#include <dc/cdrom.h>

#include "re4dc_platform.h"

#ifndef RE4DC_DVD_READ_SAFE
#define RE4DC_DVD_READ_SAFE 0
#endif
#ifndef RE4DC_DVD_STUCK_TEST
#define RE4DC_DVD_STUCK_TEST 0
#endif
#ifndef RE4DC_DISC_READ_FALLBACK
#define RE4DC_DISC_READ_FALLBACK 0
#endif
#ifndef RE4DC_DISC_FAIL_TEST
#define RE4DC_DISC_FAIL_TEST 0
#endif
#ifndef RE4DC_DISC_READ_VERIFY
#define RE4DC_DISC_READ_VERIFY 0
#endif

extern "C" int __real_cdrom_stream_start(int sector, int cnt, bool dma);
extern "C" int __real_cdrom_stream_request(void* buffer, size_t size, bool block);
extern "C" semaphore_t _g1_ata_sem;
#if RE4DC_DISC_READ_FALLBACK || RE4DC_DISC_FAIL_TEST || RE4DC_DISC_READ_VERIFY
extern "C" int __real_cdrom_read_sectors_ex(void* buffer, uint32_t sector, size_t cnt, bool dma);
extern "C" int __real_cdrom_stream_stop(bool abort_dma);
#endif

namespace {
int s_sector, s_cnt;
bool s_dma;
size_t s_consumed;  // bytes requested from the current stream since its start
unsigned g_refused, g_recovered, g_failed;
#if RE4DC_DISC_READ_VERIFY
unsigned g_late, g_late_timeouts, g_late_max_us, g_held;
inline bool gd_dma_busy() { return (*(volatile uint32_t*) 0xA05F7418u & 1u) != 0; }
// A DMA read KOS reported done: wait for the G1 GD-DMA engine to finish moving its bytes. When it was still running,
// the destination's cache lines are invalidated again (nothing wrote them meanwhile: the reader was waiting) so the
// caller reads the landed bytes.
void dma_settle(const char* what, void* buf, size_t size)
{
    if (!gd_dma_busy()) return;
    const uint64_t t0 = timer_us_gettime64();
    bool timed_out = false;
    while (gd_dma_busy()) {
        if (timer_us_gettime64() - t0 > 2000000u) {
            timed_out = true;
            break;
        }
        thd_pass();
    }
    const unsigned us = (unsigned) (timer_us_gettime64() - t0);
    const uintptr_t a = (uintptr_t) buf;
    if ((a & 0xE0000000u) != 0xA0000000u && !(a & 31) && size >= 32) dcache_inval_range(a, size & ~(size_t) 31);
    ++g_late;
    if (timed_out) ++g_late_timeouts;
    if (us > g_late_max_us) g_late_max_us = us;
    re4dc_log("disc read verify: %s of %u bytes at %08x reported done while the GD DMA ran: %s after %u us "
              "(late %u timeouts %u max %u us)\n", what, (unsigned) size, (unsigned) a,
              timed_out ? "STILL RUNNING" : "landed", us, g_late, g_late_timeouts, g_late_max_us);
}
#endif
#if RE4DC_DVD_STUCK_TEST
// Compile-time: DVD_STUCK_ADDR (address of KOS dma_in_progress from a first build's symbols; the value does not change
// the code size, so a second build keeps the address) and DVD_STUCK_TEST (seconds of uptime). No file reads here: this
// runs inside fs_iso9660 with its handle mutex held.
bool g_done;
void stuck_test()
{
    if (!g_done && timer_ms_gettime64() >= 1000ULL * RE4DC_DVD_STUCK_TEST) {
        g_done = true;
        *(volatile bool*) (uintptr_t) RE4DC_DVD_STUCK_ADDR = true;
        re4dc_log("dvd stuck test: dma_in_progress set before a stream start\n");
    }
}
#endif
#if RE4DC_DISC_READ_FALLBACK
bool g_pio;  // session latch: DMA reads did not land, every read is PIO from now on
unsigned g_fb_dma, g_fb_reads;
alignas(32) uint8_t g_bounce[2048];

volatile uint32_t* mark_at(void* buf, size_t size)
{
    return (volatile uint32_t*) ((((uintptr_t) buf + size - 32) & 0x1FFFFFFFu) | 0xA0000000u);
}
uint32_t mark_word(volatile uint32_t* p, int i)
{
    return 0x5EAD0DC5u ^ (uint32_t) (uintptr_t) p ^ (uint32_t) i * 0x9E3779B9u;
}
// A DMA destination this can check: 32-byte aligned (the DMA requirement) and at least 32 bytes.
bool markable(void* buf, size_t size)
{
    return !((uintptr_t) buf & 31) && size >= 32;
}
void mark(void* buf, size_t size)
{
    volatile uint32_t* p = mark_at(buf, size);
    for (int i = 0; i < 8; ++i) p[i] = mark_word(p, i);
}
bool landed(void* buf, size_t size)
{
    volatile uint32_t* p = mark_at(buf, size);
    for (int i = 0; i < 8; ++i) {
        if (p[i] != mark_word(p, i)) return true;
    }
    return false;
}
void latch(const char* why)
{
    if (!g_pio) re4dc_log("disc read fallback: %s; reads use PIO sector reads from now on\n", why);
    g_pio = true;
}
// Bytes [pos, pos + size) of the run starting at `lba`, by PIO sector reads.
int pio_fill(uint8_t* dst, int lba, size_t pos, size_t size)
{
    while (size) {
        const int sec = lba + (int) (pos / 2048);
        const size_t off = pos % 2048;
        int rv;
        size_t k;
        if (!off && size >= 2048 && !((uintptr_t) dst & 1)) {
            k = size & ~(size_t) 2047;
            rv = __real_cdrom_read_sectors_ex(dst, sec, k / 2048, false);
        } else {
            rv = __real_cdrom_read_sectors_ex(g_bounce, sec, 1, false);
            k = 2048 - off < size ? 2048 - off : size;
            if (rv == ERR_OK) memcpy(dst, g_bounce + off, k);
        }
        if (rv != ERR_OK) return rv;
        dst += k;
        pos += k;
        size -= k;
    }
    return ERR_OK;
}
// A stream request that failed or did not land: stop the stream (fs_iso9660 then sees no transfer pending and ends
// its stream too) and fill the request from where the stream stood.
int stream_fallback(void* buffer, size_t size, const char* why)
{
    latch(why);
    ++g_fb_reads;
    __real_cdrom_stream_stop(false);
    const int rv = pio_fill((uint8_t*) buffer, s_sector, s_consumed, size);
    if (rv == ERR_OK) s_consumed += size;
    re4dc_log("disc read fallback: stream request (%u bytes at sector %d + %u) %s by PIO (fallbacks %u)\n",
              (unsigned) size, s_sector, (unsigned) (s_consumed - (rv == ERR_OK ? size : 0)),
              rv == ERR_OK ? "read" : "FAILED", g_fb_reads);
    return rv;
}
#endif
}

#if RE4DC_DISC_READ_FALLBACK || RE4DC_DISC_FAIL_TEST || RE4DC_DISC_READ_VERIFY
extern "C" int __wrap_cdrom_read_sectors_ex(void* buffer, uint32_t sector, size_t cnt, bool dma)
{
#if RE4DC_DISC_READ_FALLBACK
    if (!dma || g_pio || !markable(buffer, cnt * 2048)) return __real_cdrom_read_sectors_ex(buffer, sector, cnt, dma && !g_pio);
    mark(buffer, cnt * 2048);
#else
    if (!dma) return __real_cdrom_read_sectors_ex(buffer, sector, cnt, dma);
#endif
#if RE4DC_DISC_FAIL_TEST >= 2
    int rv = ERR_OK;  // skipped: the emulator's "done" without the transfer
#else
    int rv = __real_cdrom_read_sectors_ex(buffer, sector, cnt, true);
#endif
#if RE4DC_DISC_READ_VERIFY
    if (rv == ERR_OK) dma_settle("a sector read", buffer, cnt * 2048);
#endif
#if RE4DC_DISC_READ_FALLBACK
    if (rv != ERR_OK || !landed(buffer, cnt * 2048)) {
        latch(rv == ERR_OK ? "a DMA sector read reported OK but did not land" : "a DMA sector read failed");
        ++g_fb_dma;
        rv = __real_cdrom_read_sectors_ex(buffer, sector, cnt, false);
        re4dc_log("disc read fallback: %u sectors at %u read again by PIO: %s (fallbacks %u)\n", (unsigned) cnt,
                  (unsigned) sector, rv == ERR_OK ? "ok" : "FAILED", g_fb_dma);
    }
#endif
    return rv;
}

extern "C" int __wrap_cdrom_stream_stop(bool abort_dma)
{
    const int rv = __real_cdrom_stream_stop(abort_dma);
#if RE4DC_DISC_READ_FALLBACK
    if (rv == ERR_TIMEOUT) latch("a stream stop timed out (the drive was reset)");
#endif
    return rv;
}
#endif

#if defined(RE4DC_DISC_GD_ATOMIC) && RE4DC_DISC_GD_ATOMIC
// DISC_GD_ATOMIC=1 (Makefile): each GD-ROM BIOS syscall runs with interrupts masked, so KOS's vblank / G1 DMA handlers
// (which call exec_server and check_command from interrupt context) never enter the BIOS while a thread is inside it.
#include <dc/syscalls.h>
#define RE4DC_GD_WRAP(ret, name, params, args)                                  \
    extern "C" ret __real_syscall_gdrom_##name params;                          \
    extern "C" ret __wrap_syscall_gdrom_##name params                           \
    {                                                                           \
        const irq_mask_t o = irq_disable();                                     \
        const ret r = __real_syscall_gdrom_##name args;                         \
        irq_restore(o);                                                         \
        return r;                                                               \
    }
#define RE4DC_GD_WRAP_VOID(name, params, args)                                  \
    extern "C" void __real_syscall_gdrom_##name params;                         \
    extern "C" void __wrap_syscall_gdrom_##name params                          \
    {                                                                           \
        const irq_mask_t o = irq_disable();                                     \
        __real_syscall_gdrom_##name args;                                       \
        irq_restore(o);                                                         \
    }
RE4DC_GD_WRAP(int, check_drive, (cd_check_drive_status_t* st), (st))
RE4DC_GD_WRAP(gdc_cmd_hnd_t, send_command, (cd_cmd_code_t cmd, void* params), (cmd, params))
RE4DC_GD_WRAP(cd_cmd_chk_t, check_command, (gdc_cmd_hnd_t h, cd_cmd_chk_status_t* st), (h, st))
RE4DC_GD_WRAP_VOID(exec_server, (void), ())
RE4DC_GD_WRAP(int, abort_command, (gdc_cmd_hnd_t h), (h))
RE4DC_GD_WRAP_VOID(dma_callback, (uintptr_t cb, void* param), (cb, param))
RE4DC_GD_WRAP(int, dma_transfer, (gdc_cmd_hnd_t h, const cd_transfer_params_t* p), (h, p))
RE4DC_GD_WRAP(int, dma_check, (gdc_cmd_hnd_t h, size_t* size), (h, size))
RE4DC_GD_WRAP_VOID(pio_callback, (uintptr_t cb, void* param), (cb, param))
RE4DC_GD_WRAP(int, pio_transfer, (gdc_cmd_hnd_t h, const cd_transfer_params_t* p), (h, p))
RE4DC_GD_WRAP(int, pio_check, (gdc_cmd_hnd_t h, size_t* size), (h, size))
#endif

extern "C" int __wrap_cdrom_stream_start(int sector, int cnt, bool dma)
{
#if RE4DC_DVD_STUCK_TEST
    stuck_test();
#endif
#if RE4DC_DISC_READ_FALLBACK
    if (g_pio) return ERR_SYS;  // fs_iso9660 falls back to sector reads
#endif
    s_sector = sector;
    s_cnt = cnt;
    s_dma = dma;
    s_consumed = 0;
    return __real_cdrom_stream_start(sector, cnt, dma);
}

extern "C" int __wrap_cdrom_stream_request(void* buffer, size_t size, bool block)
{
#if RE4DC_DISC_READ_FALLBACK
    // fs_iso9660's one non-blocking request (32 bytes) polls for completion right after: blocking here is the same.
    const bool check = s_dma && markable(buffer, size);
    if (check) {
        block = true;
        mark(buffer, size);
    }
#endif
#if RE4DC_DISC_READ_VERIFY
    if (s_dma) block = true;  // fs_iso9660's 32-byte request polls for completion right after: the same, with the wait
#endif
#if RE4DC_DISC_FAIL_TEST
    int rv = s_dma ? ERR_OK : __real_cdrom_stream_request(buffer, size, block);  // skipped: "done" without the transfer
#else
    int rv = __real_cdrom_stream_request(buffer, size, block);
#endif
#if RE4DC_DISC_READ_VERIFY
    if (rv == ERR_OK && s_dma) dma_settle("a stream request", buffer, size);
#endif
    if (rv == ERR_OK) {
#if RE4DC_DISC_READ_FALLBACK
        if (check && !landed(buffer, size)) return stream_fallback(buffer, size, "a DMA stream request reported OK but did not land");
#endif
        s_consumed += size;
        return rv;
    }
#if RE4DC_DVD_READ_SAFE
#if RE4DC_DISC_READ_FALLBACK
    if (rv != ERR_SYS) return stream_fallback(buffer, size, "a stream request failed");
#else
    if (rv != ERR_SYS) return rv;
#endif
    ++g_refused;
    for (int i = 0; i < 5 && rv == ERR_SYS; ++i) {
        thd_sleep(2);
        rv = __real_cdrom_stream_request(buffer, size, block);
    }
#if RE4DC_DISC_READ_VERIFY
    // The flag is only stale when no GD DMA is moving: never abort a live transfer (a GD seek alone is 100+ ms).
    if (rv == ERR_SYS && gd_dma_busy()) {
        ++g_held;
        const uint64_t t0 = timer_us_gettime64();
        while (rv == ERR_SYS && gd_dma_busy() && timer_us_gettime64() - t0 < 2000000u) {
            thd_sleep(2);
            rv = __real_cdrom_stream_request(buffer, size, block);
        }
        re4dc_log("disc read verify: refused stream request held %u us for a running GD DMA: %s (held %u)\n",
                  (unsigned) (timer_us_gettime64() - t0), rv == ERR_OK ? "accepted" : "still refused", g_held);
    }
    if (rv == ERR_OK && s_dma) dma_settle("a held stream request", buffer, size);
#endif
    bool restarted = false;
    if (rv == ERR_SYS && sem_wait_timed(&_g1_ata_sem, 1000) == 0) {
        if (cdrom_abort_cmd(1000, true) == ERR_NO_ACTIVE) sem_signal(&_g1_ata_sem);  // took no ownership
        const size_t done_sectors = s_consumed / 2048;
        if (!(s_consumed % 2048) && (int) done_sectors < s_cnt &&
            __real_cdrom_stream_start(s_sector + (int) done_sectors, s_cnt - (int) done_sectors, s_dma) == ERR_OK) {
            s_sector += (int) done_sectors;
            s_cnt -= (int) done_sectors;
            s_consumed = 0;
            restarted = true;
            rv = __real_cdrom_stream_request(buffer, size, block);
        }
    }
    if (rv == ERR_OK) {
        s_consumed += size;
        ++g_recovered;
    } else {
        ++g_failed;
    }
    re4dc_log("dvd read safe: stream request refused, %s%s (%u bytes; refused %u recovered %u failed %u)\n",
              rv == ERR_OK ? "recovered" : "FAILED", restarted ? " after a stream restart" : "", (unsigned) size,
              g_refused, g_recovered, g_failed);
#endif
#if RE4DC_DISC_READ_FALLBACK
    if (rv != ERR_OK) rv = stream_fallback(buffer, size, "a stream request failed");
#endif
    return rv;
}
